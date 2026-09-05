import type { Diagnosis, RecoveryRecord, RunResult } from "@/lib/recoverops/types";

export type RazorpayEntity = Record<string, unknown> & { id?: string };
export type RazorpayWebhook = { event: string; payload?: { payment?: { entity?: RazorpayEntity }; payment_link?: { entity?: RazorpayEntity }; order?: { entity?: RazorpayEntity } } };
export type StoredCase = { id: string; razorpayPaymentId: string; amountPaise: number; currency: string; state: string };

export interface RecoveryStore {
  reserveWebhook(input: { eventId: string; eventType: string; payloadHash: string; payload: RazorpayWebhook }): Promise<boolean>;
  markWebhook(eventId: string, status: "processed" | "failed", error?: string): Promise<void>;
  upsertFailedCase(input: { caseId: string; payment: RazorpayEntity; record: RecoveryRecord; diagnosis: Diagnosis; result: RunResult }): Promise<StoredCase>;
  reserveAction(input: { actionId: string; caseId: string; idempotencyKey: string; referenceId: string; actionType: string }): Promise<boolean>;
  completeAction(input: { actionId: string; paymentLinkId: string; shortUrl: string; raw: unknown }): Promise<void>;
  failAction(actionId: string, reason: string): Promise<void>;
  markRecoveredByReference(input: { referenceId: string; paymentLinkId?: string; recoveredPaise: number; raw: unknown }): Promise<boolean>;
  appendAudit(caseId: string | null, eventType: string, actor: string, details: unknown): Promise<void>;
}
