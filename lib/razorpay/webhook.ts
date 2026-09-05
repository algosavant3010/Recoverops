import { createHash, createHmac, timingSafeEqual } from "node:crypto";
import { diagnoseWithGemini } from "@/lib/recoverops/ai-diagnosis";
import { runScenario } from "@/lib/recoverops/engine";
import type { RecoveryRecord } from "@/lib/recoverops/types";
import { createTestPaymentLink } from "./client";
import type { RazorpayEntity, RazorpayWebhook, RecoveryStore } from "./types";

export function verifyWebhookSignature(rawBody: string, receivedSignature: string, secret: string) { if (!receivedSignature || !secret) return false; const expected = createHmac("sha256", secret).update(rawBody).digest("hex"); const expectedBuffer = Buffer.from(expected); const receivedBuffer = Buffer.from(receivedSignature); return expectedBuffer.length === receivedBuffer.length && timingSafeEqual(expectedBuffer, receivedBuffer); }
export function payloadHash(rawBody: string) { return createHash("sha256").update(rawBody).digest("hex"); }
function text(entity: RazorpayEntity, key: string) { return typeof entity[key] === "string" ? entity[key] as string : undefined; }
function number(entity: RazorpayEntity, key: string) { return typeof entity[key] === "number" ? entity[key] as number : undefined; }
export function paymentToRecoveryRecord(payment: RazorpayEntity): RecoveryRecord { const id = text(payment, "id"); const amount = number(payment, "amount"); if (!id || !amount || amount < 100) throw new Error("payment.failed payload is missing a valid payment id or amount"); const errorCode = [text(payment, "error_code"), text(payment, "error_reason")].filter(Boolean).join(":") || undefined; const createdAt = number(payment, "created_at"); return { id, type: "failed_payment", amountPaise: amount, currency: "INR", createdAt: new Date((createdAt ?? Math.floor(Date.now() / 1000)) * 1000).toISOString(), lastAttemptAt: new Date().toISOString(), attempts: 1, errorCode, riskFlags: [], customerOptedOut: false, timezone: "Asia/Kolkata" }; }
function compactId(prefix: string, source: string) { return `${prefix}_${createHash("sha256").update(source).digest("hex").slice(0, 20)}`; }

export async function processRazorpayWebhook(payload: RazorpayWebhook, eventId: string, store: RecoveryStore, createLink = createTestPaymentLink) {
  if (payload.event === "payment.failed") {
    const payment = payload.payload?.payment?.entity; if (!payment) throw new Error("payment.failed payload has no payment entity");
    const record = paymentToRecoveryRecord(payment); const ai = await diagnoseWithGemini(record); const result = runScenario(record, { diagnosis: ai.diagnosis, now: new Date() }); const caseId = compactId("case", record.id);
    await store.upsertFailedCase({ caseId, payment, record, diagnosis: ai.diagnosis, result });
    await store.appendAudit(caseId, "diagnosis_completed", ai.mode, { diagnosis: ai.diagnosis, externalCalls: ai.externalCalls, fallbackReason: ai.fallbackReason });
    await store.appendAudit(caseId, "policy_decided", "policy", { allowed: result.allowed, action: result.action, rule: result.rule, reason: result.reason });
    if (!result.allowed || ["skip", "escalate", "hinglish_promise_to_pay"].includes(result.action)) return { status: "blocked", caseId, result };
    const actionId = compactId("act", result.idempotencyKey); const referenceId = compactId("ro", record.id); const reserved = await store.reserveAction({ actionId, caseId, idempotencyKey: result.idempotencyKey, referenceId, actionType: "payment_link" });
    if (!reserved) return { status: "duplicate_action", caseId, result };
    try { const link = await createLink({ amountPaise: record.amountPaise, referenceId, caseId, description: `Recover payment ${record.id.slice(-8)}` }); await store.completeAction({ actionId, paymentLinkId: link.id, shortUrl: link.short_url, raw: link }); await store.appendAudit(caseId, "payment_link_issued", "razorpay", { paymentLinkId: link.id, shortUrl: link.short_url, referenceId }); return { status: "link_issued", caseId, result, link }; }
    catch (error) { const reason = error instanceof Error ? error.message : "unknown Razorpay error"; await store.failAction(actionId, reason); await store.appendAudit(caseId, "payment_link_failed", "razorpay", { reason }); throw error; }
  }
  if (payload.event === "payment_link.paid") { const link = payload.payload?.payment_link?.entity; if (!link) throw new Error("payment_link.paid payload has no payment_link entity"); const referenceId = text(link, "reference_id"); if (!referenceId) throw new Error("payment_link.paid payload has no reference_id"); const recoveredPaise = number(link, "amount_paid") ?? number(link, "amount") ?? 0; const matched = await store.markRecoveredByReference({ referenceId, paymentLinkId: text(link, "id"), recoveredPaise, raw: link }); await store.appendAudit(null, "payment_reconciled", "razorpay", { eventId, referenceId, recoveredPaise, matched }); return { status: matched ? "recovered" : "unmatched_payment_link", recoveredPaise }; }
  return { status: "ignored" };
}
