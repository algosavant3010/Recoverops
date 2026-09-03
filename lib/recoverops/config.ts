import type { ActionKind, RootCause } from "./types";

export const guardrails = {
  maxRetriesPerRecord: 3,
  maxNudgesPerRecord: 2,
  maxTotalActionsPerRecord: 5,
  maxActionsPerBatch: 100,
  maxDiscountPct: 5,
  maxMessagesPerDay: 1,
  maxWallclockDays: 21,
  quietHours: { start: 21, end: 9 },
};

export const interventions: Record<RootCause, readonly ActionKind[]> = {
  insufficient_funds: ["smart_retry", "nudge"],
  gateway_downtime: ["smart_retry", "switch_method"],
  expired_card: ["nudge_update_method", "switch_method"],
  mandate_lapsed: ["reauth_mandate", "nudge"],
  checkout_abandoned: ["recovery_link", "nudge", "small_incentive"],
  b2b_overdue: ["hinglish_promise_to_pay", "nudge"],
  fraud_suspected: ["skip", "escalate"],
  unknown: ["escalate"],
};

export const retryActions = new Set<ActionKind>(["smart_retry", "switch_method", "reauth_mandate", "recovery_link", "small_incentive"]);
export const nudgeActions = new Set<ActionKind>(["nudge", "nudge_update_method"]);
export const outreachActions = new Set<ActionKind>(["nudge", "nudge_update_method", "recovery_link", "hinglish_promise_to_pay"]);
export const moneyActions = new Set<ActionKind>(["smart_retry", "switch_method", "reauth_mandate", "recovery_link", "small_incentive"]);
