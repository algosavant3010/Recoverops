export type RootCause = "insufficient_funds" | "gateway_downtime" | "expired_card" | "mandate_lapsed" | "checkout_abandoned" | "b2b_overdue" | "fraud_suspected" | "unknown";
export type ActionKind = "smart_retry" | "switch_method" | "nudge" | "nudge_update_method" | "reauth_mandate" | "recovery_link" | "small_incentive" | "hinglish_promise_to_pay" | "skip" | "escalate";
export type RecordType = "failed_payment" | "abandoned_checkout" | "overdue_invoice" | "failed_subscription";

export interface RecoveryRecord {
  id: string;
  type: RecordType;
  amountPaise: number;
  currency: "INR";
  createdAt: string;
  lastAttemptAt?: string;
  attempts: number;
  errorCode?: string;
  riskFlags: string[];
  customerOptedOut: boolean;
  timezone: string;
}

export interface Diagnosis {
  cause: RootCause;
  confidence: number;
  reasoning: string;
  source: "rules" | "gemini" | "injected";
}

export interface PolicyState {
  totalActions: number;
  retries: number;
  nudges: number;
  messagesToday: number;
  batchActions: number;
  recoveredPaise: number;
  lastActionAt: Partial<Record<ActionKind, string>>;
}

export interface AuditEvent {
  id: string;
  stage: "ingest" | "diagnose" | "plan" | "gate" | "execute" | "terminal";
  timestamp: string;
  title: string;
  detail: string;
  status: "neutral" | "success" | "blocked" | "pending";
  data: Record<string, unknown>;
}

export interface RunResult {
  runId: string;
  record: RecoveryRecord;
  diagnosis: Diagnosis;
  action: ActionKind;
  allowed: boolean;
  rule: string;
  reason: string;
  idempotencyKey: string;
  outcome: "success" | "failure" | "blocked" | "scheduled";
  recoveredPaise: number;
  events: AuditEvent[];
}
