# RecoverOps — Build Plan

Track 03 · AI Revenue Recovery · Razorpay AI Buildathon.

## Thesis
Autonomous, auditable revenue-recovery agent. LLM diagnoses; a deterministic
policy engine executes. Measured lift over baselines on a held-out batch.

## Winning moats
1. **Measured lift** vs no-action and naive-retry baselines on a held-out set.
2. **Safe by construction** — LLM proposes, policy engine disposes; idempotency
   keys, caps, cooldowns, stopping rules.
3. **Hinglish promise-to-pay** channel for B2B receivables — India-native
   differentiator.

## Root-cause taxonomy → intervention
| Cause | Signal | Bounded intervention |
|---|---|---|
| insufficient_funds | error code + amount | salary-cycle retry + 1 nudge |
| gateway_downtime | issuer error, time-clustered | smart backoff + switch method |
| expired_card | card error code | nudge to update method |
| mandate_lapsed | mandate status | re-auth mandate |
| checkout_abandoned | cart, no attempt | recovery link + small incentive |
| b2b_overdue | due date passed | Hinglish promise-to-pay |
| fraud_suspected | risk flags | skip + escalate |

## Anti-vibecoded engineering signals
- Idempotency keys on every money action
- Deterministic policy engine, unit-tested independently of the LLM
- Stopping rules + cooldown windows
- Held-out eval set (dev vs holdout split)
- Baseline comparison (no-op, naive retry)
- Root-cause confusion matrix (precision/recall)
- Injected failure-recovery demo (API timeout → backoff → clean escalation)
- Structured replayable audit trail (one JSON line per decision)
- YAML-driven guardrails (reviewable policy)
- Deterministic seeds (batches + runs reproducible)

## Phases
1. **Foundations** — repo, typed models, guardrails config, seeded generator ← *current*
2. **Reasoning plane** — Gemini root-cause classifier + intervention proposer (structured output)
3. **Policy + execution** — gate, idempotency, stopping rules, Razorpay test-mode / mock adapter
4. **Observability** — structured JSON audit log, trace IDs
5. **Evaluation** — baselines, metrics, confusion matrix, exceptions list
6. **Hinglish promise-to-pay** differentiator
7. **Streamlit dashboard**
8. **Failure-injection demo**
9. **Polish** — README, video script, "what broke" log
