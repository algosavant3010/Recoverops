import type { RecoveryRecord, RootCause } from "./types";

export interface Scenario {
  key: string;
  label: string;
  eyebrow: string;
  description: string;
  record: RecoveryRecord;
  forcedDiagnosis?: RootCause;
  duplicate?: boolean;
}

const base = { currency: "INR" as const, createdAt: "2026-08-24T10:00:00.000Z", attempts: 1, riskFlags: [] as string[], customerOptedOut: false, timezone: "Asia/Kolkata" };

export const scenarios: Scenario[] = [
  { key: "funds", label: "Insufficient funds", eyebrow: "SMART RETRY", description: "Schedule a retry around the customer's likely salary cycle.", record: { ...base, id: "pay_R9K2M1", type: "failed_payment", amountPaise: 849900, errorCode: "BAD_REQUEST_ERROR:insufficient_funds", lastAttemptAt: "2026-08-27T09:30:00.000Z" } },
  { key: "gateway", label: "Gateway downtime", eyebrow: "RESILIENT ROUTING", description: "Back off safely, then offer an alternate payment method.", record: { ...base, id: "pay_G7T4Q8", type: "failed_payment", amountPaise: 249900, errorCode: "GATEWAY_ERROR:issuer_down", lastAttemptAt: "2026-08-27T11:45:00.000Z" } },
  { key: "checkout", label: "Abandoned checkout", eyebrow: "RECOVERY LINK", description: "Create a bounded recovery link without repeating the charge.", record: { ...base, id: "cart_A3P8N5", type: "abandoned_checkout", amountPaise: 129900, attempts: 0, createdAt: "2026-08-27T12:00:00.000Z" } },
  { key: "b2b", label: "B2B invoice overdue", eyebrow: "HINGLISH OUTREACH", description: "Draft respectful local-language outreach; payment remains unconfirmed.", record: { ...base, id: "inv_B2B1042", type: "overdue_invoice", amountPaise: 7850000, attempts: 0, createdAt: "2026-08-14T10:00:00.000Z" } },
  { key: "fraud", label: "Fraud safety test", eyebrow: "ADVERSARIAL", description: "The AI is deliberately wrong. Immutable risk facts must still win.", forcedDiagnosis: "insufficient_funds", record: { ...base, id: "pay_FRAUD77", type: "failed_payment", amountPaise: 359900, errorCode: "BAD_REQUEST_ERROR:insufficient_funds", riskFlags: ["velocity_spike", "device_reuse"] } },
  { key: "duplicate", label: "Duplicate execution", eyebrow: "IDEMPOTENCY", description: "Replay the same operation and prove the second execution is refused.", duplicate: true, record: { ...base, id: "pay_DUPL204", type: "failed_payment", amountPaise: 499900, errorCode: "GATEWAY_ERROR:issuer_down" } },
  { key: "optout", label: "Customer opted out", eyebrow: "COMPLIANCE", description: "Recovery stops before planning can cause harm.", record: { ...base, id: "pay_OPTOUT9", type: "failed_payment", amountPaise: 189900, errorCode: "BAD_REQUEST_ERROR:invalid_card_expiry", customerOptedOut: true } },
];
