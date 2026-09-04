import { guardrails, interventions, moneyActions, nudgeActions, outreachActions, retryActions } from "./config";
import type { ActionKind, AuditEvent, Diagnosis, PolicyState, RecoveryRecord, RootCause, RunResult } from "./types";

const errorMap: Record<string, RootCause> = {
  "BAD_REQUEST_ERROR:insufficient_funds": "insufficient_funds",
  "GATEWAY_ERROR:insufficient_balance": "insufficient_funds",
  "GATEWAY_ERROR:issuer_down": "gateway_downtime",
  "GATEWAY_ERROR:acquirer_timeout": "gateway_downtime",
  "BAD_REQUEST_ERROR:invalid_card_expiry": "expired_card",
  "BAD_REQUEST_ERROR:card_expired": "expired_card",
  "BAD_REQUEST_ERROR:mandate_revoked": "mandate_lapsed",
  "BAD_REQUEST_ERROR:mandate_expired": "mandate_lapsed",
  "BAD_REQUEST_ERROR:risk_declined": "fraud_suspected",
};

const fraudFlags = new Set(["velocity_spike", "bin_mismatch", "geo_anomaly", "device_reuse"]);

export function diagnose(record: RecoveryRecord, forced?: RootCause): Diagnosis {
  if (forced) return { cause: forced, confidence: 0.94, reasoning: "Injected AI diagnosis for the safety challenge.", source: "injected" };
  if (record.riskFlags.some((flag) => fraudFlags.has(flag))) return { cause: "fraud_suspected", confidence: 0.98, reasoning: "High-risk transaction signals take priority over payment errors.", source: "rules" };
  if (record.errorCode && errorMap[record.errorCode]) return { cause: errorMap[record.errorCode], confidence: 0.91, reasoning: `The processor code maps to ${errorMap[record.errorCode].replaceAll("_", " ")}.`, source: "rules" };
  if (record.type === "abandoned_checkout") return { cause: "checkout_abandoned", confidence: 0.94, reasoning: "Checkout exists without a completed payment attempt.", source: "rules" };
  if (record.type === "overdue_invoice") return { cause: "b2b_overdue", confidence: 0.92, reasoning: "Invoice is beyond its due window.", source: "rules" };
  if (record.type === "failed_subscription") return { cause: "mandate_lapsed", confidence: 0.65, reasoning: "Subscription failure without a stronger processor signal.", source: "rules" };
  return { cause: "unknown", confidence: 0.3, reasoning: "Evidence is insufficient for a safe automated action.", source: "rules" };
}

function hash(input: string) {
  let value = 2166136261;
  for (let index = 0; index < input.length; index += 1) {
    value ^= input.charCodeAt(index);
    value = Math.imul(value, 16777619);
  }
  return (value >>> 0).toString(16).padStart(8, "0");
}

function isQuietHour(now: Date, timezone: string) {
  const hour = Number(new Intl.DateTimeFormat("en-GB", { timeZone: timezone, hour: "2-digit", hour12: false }).format(now));
  const { start, end } = guardrails.quietHours;
  return start <= end ? hour >= start && hour < end : hour >= start || hour < end;
}

function idempotencyKey(recordId: string, action: ActionKind, attempt: number) {
  return `idem_${hash(`${recordId}|${action}|${attempt}`)}${hash(`${action}|${recordId}`)}${hash(`${attempt}|recoverops`)}`;
}

function deterministicHit(recordId: string, action: ActionKind) {
  return parseInt(hash(`recoverops-demo|${recordId}|${action}`), 16) % 100 < 56;
}

function nextAction(cause: RootCause, state: PolicyState): ActionKind {
  return interventions[cause].find((action) => {
    if (retryActions.has(action) && state.retries >= guardrails.maxRetriesPerRecord) return false;
    if (nudgeActions.has(action) && state.nudges >= guardrails.maxNudgesPerRecord) return false;
    return true;
  }) ?? "escalate";
}

function gate(record: RecoveryRecord, diagnosis: Diagnosis, action: ActionKind, state: PolicyState, now: Date) {
  if (record.riskFlags.some((flag) => fraudFlags.has(flag)) && moneyActions.has(action)) return { allowed: false, rule: "fraud_signal_stop", reason: "Immutable fraud signals override the AI diagnosis." };
  if (record.customerOptedOut) return { allowed: false, rule: "customer_optout", reason: "Customer opted out of automated recovery." };
  if ((now.getTime() - new Date(record.createdAt).getTime()) / 86_400_000 > guardrails.maxWallclockDays) return { allowed: false, rule: "wallclock_expired", reason: "Record is outside the 21-day recovery window." };
  if (!interventions[diagnosis.cause].includes(action)) return { allowed: false, rule: "action_not_allowed", reason: `${action} is not allowed for ${diagnosis.cause}.` };
  if (state.batchActions >= guardrails.maxActionsPerBatch) return { allowed: false, rule: "batch_action_cap", reason: "Batch action budget has been exhausted." };
  if (state.totalActions >= guardrails.maxTotalActionsPerRecord) return { allowed: false, rule: "record_action_cap", reason: "Per-record action cap has been reached." };
  if (retryActions.has(action) && state.retries >= guardrails.maxRetriesPerRecord) return { allowed: false, rule: "retry_cap", reason: "Existing and RecoverOps retries reached the configured cap." };
  if (nudgeActions.has(action) && state.nudges >= guardrails.maxNudgesPerRecord) return { allowed: false, rule: "nudge_cap", reason: "Nudge cap has been reached." };
  if (outreachActions.has(action) && state.messagesToday >= guardrails.maxMessagesPerDay) return { allowed: false, rule: "daily_message_cap", reason: "Daily outreach limit has been reached." };
  if (outreachActions.has(action) && isQuietHour(now, record.timezone)) return { allowed: false, rule: "quiet_hours", reason: `Outreach is paused in ${record.timezone}.` };
  return { allowed: true, rule: "all_guardrails_passed", reason: "All deterministic policy checks passed." };
}

export function runScenario(record: RecoveryRecord, options?: { forcedDiagnosis?: RootCause; diagnosis?: Diagnosis; duplicate?: boolean; now?: Date }): RunResult {
  const now = options?.now ?? new Date("2026-08-28T10:30:00.000Z");
  const diagnosis = options?.diagnosis ?? diagnose(record, options?.forcedDiagnosis);
  const state: PolicyState = { totalActions: 0, retries: record.attempts, nudges: 0, messagesToday: 0, batchActions: 0, recoveredPaise: 0, lastActionAt: {} };
  const action = nextAction(diagnosis.cause, state);
  const decision = gate(record, diagnosis, action, state, now);
  const key = idempotencyKey(record.id, action, state.totalActions + 1);
  const runId = `run_${hash(`${record.id}|${now.toISOString()}`)}`;
  const events: AuditEvent[] = [];
  const push = (stage: AuditEvent["stage"], title: string, detail: string, status: AuditEvent["status"], data: Record<string, unknown>) => events.push({ id: `${runId}_${events.length + 1}`, stage, timestamp: new Date(now.getTime() + events.length * 380).toISOString(), title, detail, status, data });

  push("ingest", "Record received", `${record.type.replaceAll("_", " ")} · ${formatInr(record.amountPaise)} at risk`, "neutral", { record });
  push("diagnose", diagnosis.cause.replaceAll("_", " "), diagnosis.reasoning, diagnosis.source === "injected" ? "pending" : "neutral", { diagnosis });
  push("plan", action.replaceAll("_", " "), `Planner selected the highest-priority eligible action. Existing attempts: ${record.attempts}.`, "neutral", { action });
  push("gate", decision.rule.replaceAll("_", " "), decision.reason, decision.allowed ? "success" : "blocked", { ...decision, idempotencyKey: key });

  if (!decision.allowed) {
    push("terminal", "Safely stopped", "No external action was executed.", "blocked", { recoveredPaise: 0 });
    return { runId, record, diagnosis, action, allowed: false, rule: decision.rule, reason: decision.reason, idempotencyKey: key, outcome: "blocked", recoveredPaise: 0, events };
  }
  if (options?.duplicate) {
    push("execute", "First request reserved", "The idempotency key was reserved for this demo run.", "success", { idempotencyKey: key, status: "reserved" });
    push("execute", "Duplicate refused", "The replay matched an existing key; no second side effect occurred.", "blocked", { idempotencyKey: key, status: "duplicate" });
    push("terminal", "Duplicate prevented", "Protected the full at-risk amount from a repeated operation.", "success", { recoveredPaise: 0 });
    return { runId, record, diagnosis, action, allowed: true, rule: decision.rule, reason: decision.reason, idempotencyKey: key, outcome: "blocked", recoveredPaise: 0, events };
  }
  if (action === "hinglish_promise_to_pay") {
    push("execute", "Message drafted", "Outbound message is ready for approval. No customer promise or payment is assumed.", "pending", { status: "drafted", language: "hinglish" });
    push("terminal", "Awaiting customer response", "Revenue remains at risk until a payment webhook confirms settlement.", "pending", { recoveredPaise: 0 });
    return { runId, record, diagnosis, action, allowed: true, rule: decision.rule, reason: decision.reason, idempotencyKey: key, outcome: "scheduled", recoveredPaise: 0, events };
  }
  const success = deterministicHit(record.id, action);
  const recoveredPaise = success ? record.amountPaise : 0;
  push("execute", success ? "Simulation succeeded" : "Attempt completed", success ? `${formatInr(recoveredPaise)} marked as simulated recovered value.` : "No settlement observed; the next action will respect cooldowns.", success ? "success" : "pending", { status: success ? "success" : "failure", recoveredPaise });
  push("terminal", success ? "Recovery confirmed" : "Next action scheduled", success ? "This deterministic demo run reached a terminal success state." : "The record remains open; it was not prematurely escalated.", success ? "success" : "pending", { recoveredPaise });
  return { runId, record, diagnosis, action, allowed: true, rule: decision.rule, reason: decision.reason, idempotencyKey: key, outcome: success ? "success" : "scheduled", recoveredPaise, events };
}

export function formatInr(paise: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(paise / 100);
}
