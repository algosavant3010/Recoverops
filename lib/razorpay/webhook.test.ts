import { createHmac } from "node:crypto";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { processRazorpayWebhook, verifyWebhookSignature } from "./webhook";
import type { RazorpayWebhook, RecoveryStore } from "./types";

class MemoryStore implements RecoveryStore {
  events = new Set<string>(); actions = new Set<string>(); recovered = false; completed = false; audits: string[] = [];
  async reserveWebhook(input: Parameters<RecoveryStore["reserveWebhook"]>[0]) { if (this.events.has(input.eventId)) return false; this.events.add(input.eventId); return true; }
  async markWebhook() {}
  async upsertFailedCase(input: Parameters<RecoveryStore["upsertFailedCase"]>[0]) { return { id: input.caseId, razorpayPaymentId: input.record.id, amountPaise: input.record.amountPaise, currency: input.record.currency, state: input.result.allowed ? "approved" : "blocked" }; }
  async reserveAction(input: Parameters<RecoveryStore["reserveAction"]>[0]) { if (this.actions.has(input.idempotencyKey)) return false; this.actions.add(input.idempotencyKey); return true; }
  async completeAction() { this.completed = true; }
  async failAction() {}
  async markRecoveredByReference() { this.recovered = true; return true; }
  async appendAudit(_caseId: string | null, eventType: string) { this.audits.push(eventType); }
}

const failedPayment: RazorpayWebhook = { event: "payment.failed", payload: { payment: { entity: { id: "pay_test_failed_01", order_id: "order_test_01", amount: 849900, currency: "INR", error_code: "BAD_REQUEST_ERROR", error_reason: "insufficient_funds", error_description: "Test insufficient funds", created_at: 1788550200 } } } };

describe("Razorpay Phase 1", () => {
  beforeEach(() => vi.stubEnv("GEMINI_API_KEY", ""));
  afterEach(() => vi.unstubAllEnvs());

  it("validates the raw body HMAC and rejects a modified signature", () => {
    const raw = JSON.stringify(failedPayment); const secret = "test_webhook_secret"; const signature = createHmac("sha256", secret).update(raw).digest("hex");
    expect(verifyWebhookSignature(raw, signature, secret)).toBe(true);
    expect(verifyWebhookSignature(`${raw} `, signature, secret)).toBe(false);
  });

  it("turns a failed payment into exactly one test Payment Link action", async () => {
    const store = new MemoryStore(); const createLink = vi.fn(async (input: { referenceId: string }) => ({ id: "plink_test_01", short_url: "https://rzp.io/i/test", reference_id: input.referenceId, amount: 849900, status: "issued" }));
    const first = await processRazorpayWebhook(failedPayment, "event_01", store, createLink);
    const second = await processRazorpayWebhook(failedPayment, "event_01_replay", store, createLink);
    expect(first.status).toBe("link_issued"); expect(second.status).toBe("duplicate_action"); expect(createLink).toHaveBeenCalledTimes(1); expect(store.completed).toBe(true);
  });

  it("reconciles a paid Payment Link as verified recovered revenue", async () => {
    const store = new MemoryStore();
    const result = await processRazorpayWebhook({ event: "payment_link.paid", payload: { payment_link: { entity: { id: "plink_test_01", reference_id: "ro_test", amount_paid: 849900 } } } }, "event_paid_01", store);
    expect(result).toEqual({ status: "recovered", recoveredPaise: 849900 }); expect(store.recovered).toBe(true); expect(store.audits).toContain("payment_reconciled");
  });
});
