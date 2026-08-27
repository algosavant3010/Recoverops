"""Root-cause taxonomy and record types.

The taxonomy is a *closed set*: the LLM can only classify into one of these
labels, and the policy engine only knows how to act on these labels. That
closure is what makes the system auditable.
"""
from __future__ import annotations

from enum import Enum


class RecordType(str, Enum):
    """The kinds of at-risk records RecoverOps ingests."""

    FAILED_PAYMENT = "failed_payment"
    ABANDONED_CHECKOUT = "abandoned_checkout"
    OVERDUE_INVOICE = "overdue_invoice"
    FAILED_SUBSCRIPTION = "failed_subscription"


class RootCause(str, Enum):
    """Closed-set root-cause labels. Extend deliberately, never ad-hoc."""

    INSUFFICIENT_FUNDS = "insufficient_funds"
    GATEWAY_DOWNTIME = "gateway_downtime"
    EXPIRED_CARD = "expired_card"
    MANDATE_LAPSED = "mandate_lapsed"
    CHECKOUT_ABANDONED = "checkout_abandoned"
    B2B_OVERDUE = "b2b_overdue"
    FRAUD_SUSPECTED = "fraud_suspected"
    UNKNOWN = "unknown"


class ActionKind(str, Enum):
    """Every intervention the system can propose. Closed set on purpose."""

    SMART_RETRY = "smart_retry"
    SWITCH_METHOD = "switch_method"
    NUDGE = "nudge"
    NUDGE_UPDATE_METHOD = "nudge_update_method"
    REAUTH_MANDATE = "reauth_mandate"
    RECOVERY_LINK = "recovery_link"
    SMALL_INCENTIVE = "small_incentive"
    HINGLISH_PROMISE_TO_PAY = "hinglish_promise_to_pay"
    SKIP = "skip"
    ESCALATE = "escalate"


# Which observable error codes are consistent with each root cause. Used by
# the synthetic generator to produce realistic signals, and by the (later)
# rule-based fallback classifier.
ERROR_CODES_BY_CAUSE: dict[RootCause, tuple[str, ...]] = {
    RootCause.INSUFFICIENT_FUNDS: ("BAD_REQUEST_ERROR:insufficient_funds", "GATEWAY_ERROR:insufficient_balance"),
    RootCause.GATEWAY_DOWNTIME: ("GATEWAY_ERROR:issuer_down", "GATEWAY_ERROR:acquirer_timeout"),
    RootCause.EXPIRED_CARD: ("BAD_REQUEST_ERROR:invalid_card_expiry", "BAD_REQUEST_ERROR:card_expired"),
    RootCause.MANDATE_LAPSED: ("BAD_REQUEST_ERROR:mandate_revoked", "BAD_REQUEST_ERROR:mandate_expired"),
    RootCause.CHECKOUT_ABANDONED: (),
    RootCause.B2B_OVERDUE: (),
    RootCause.FRAUD_SUSPECTED: ("BAD_REQUEST_ERROR:risk_declined",),
    RootCause.UNKNOWN: ("GATEWAY_ERROR:unknown",),
}

# Which record types each cause can plausibly appear on.
CAUSES_BY_RECORD_TYPE: dict[RecordType, tuple[RootCause, ...]] = {
    RecordType.FAILED_PAYMENT: (
        RootCause.INSUFFICIENT_FUNDS,
        RootCause.GATEWAY_DOWNTIME,
        RootCause.EXPIRED_CARD,
        RootCause.FRAUD_SUSPECTED,
        RootCause.UNKNOWN,
    ),
    RecordType.ABANDONED_CHECKOUT: (RootCause.CHECKOUT_ABANDONED,),
    RecordType.OVERDUE_INVOICE: (RootCause.B2B_OVERDUE,),
    RecordType.FAILED_SUBSCRIPTION: (
        RootCause.MANDATE_LAPSED,
        RootCause.INSUFFICIENT_FUNDS,
        RootCause.EXPIRED_CARD,
    ),
}
