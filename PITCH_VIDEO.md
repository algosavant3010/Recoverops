# RecoverOps — 5-minute pitch video script

**Track 03 · AI Revenue Recovery · Razorpay AI Buildathon**

Deliver crisp. Camera on face when talking, screen share for demos. Total
budget: **5:00**. Practice hitting 4:45 to leave breathing room.

---

## 0:00 – 0:20 · The one-liner

> "I built **RecoverOps** — an autonomous, auditable revenue-recovery agent
> for Razorpay merchants. On a held-out batch of 200 records with ₹9.4 lakh
> at risk, it recovers **3.8× more money than a naive retry-3x baseline**
> using less than half the operational actions."

**Show:** dashboard Overview tab · point at the "3.8×" hero + `+28.15 pp lift`.

---

## 0:20 – 0:50 · The thesis in 3 sentences

> "Most merchants either do nothing or retry blindly.
> Real revenue loss is not one clean failure — a payment degrades,
> a checkout gets abandoned, an invoice goes overdue.
> RecoverOps closes that loop: **the LLM diagnoses, a deterministic
> policy engine executes, and every rupee action is auditable.**"

**Show:** the 5 tabs sliding across, ending on Overview.

---

## 0:50 – 1:40 · Architecture — 4 planes

> "The system has four planes and I keep them strictly separated."

**Show:** live-narrated tour of the code.

1. **Reasoning plane (Gemini)** — classifies each at-risk record into a
   closed-set root cause. Structured output enforced at the API boundary.
   Rate-limited + a rule-based fallback so the batch never dies.

2. **Policy plane** — 8 named rules that gate every proposed action.
   Idempotency keys, retry caps, nudge caps, cooldowns, quiet hours,
   wallclock, fraud-safety. **The LLM proposes, this layer disposes.**

3. **Execution plane** — a mock executor with a `GroundTruthOracle` for
   evaluation. The Razorpay test-mode adapter slots in behind the same
   `Executor` protocol.

4. **Observability plane** — every event streams to a JSONL audit log with
   deterministic trace IDs per record. **One command replays the entire
   run report from the log.**

---

## 1:40 – 2:40 · The numbers (this is what judges want)

**Show:** `python scripts/eval.py --batch data/holdout/batch.jsonl`

> "Every strategy runs against the same synthetic oracle so the comparison
> is apples-to-apples."

| Strategy | Records rec. | Amount rec. | Rate | Actions |
|---|---:|---:|---:|---:|
| no_op | 0/200 | ₹0 | 0.0% | 0 |
| naive_retry_3x | 71/200 | ₹98,249 | 9.9% | 306 |
| **recoverops** | **67/200** | **₹3,76,346** | **38.1%** | **139** |

> "Fewer records than naive, but **3.8× more money** — because naive only
> touches failed payments. RecoverOps' cause-aware routing unlocks B2B
> invoices and abandoned checkouts, which are the big-ticket recoveries."

**Point out on the confusion-matrix tab:** 100% diagnosis accuracy on the
closed-set taxonomy.

**Point at the honest exceptions list:** "108 records blocked by policy
guardrails, 14 unknown-diagnosis, and 11 fraud records that we
**correctly refused to chase.**"

---

## 2:40 – 3:30 · The Hinglish differentiator

**Show:** dashboard Promise inbox tab.

> "For B2B overdue invoices, Gemini drafts a polite Hinglish message asking
> for a specific promise-to-pay date. The promise is captured with a
> promised-by timestamp under existing outreach guardrails —
> quiet hours, one message per day."

Read one message out loud:

> *"Namaste ji, aapka invoice rec_dev_000052 ka amount ₹1,39,893 pending hai
> (16 din se). Kya aap next 3 working days mein settle kar sakte hain?
> Thoda confirm kar dijiye. — Team RecoverOps."*

> "This is what unlocks the B2B recovery lane naive retry can't see."

---

## 3:30 – 4:30 · "What broke and how I got out"

**Show:** `python scripts/demo_failures.py` streaming through the terminal.

> "Four real production failures forced into a single batch run — nothing
> stubbed to pass."

1. **Flaky diagnoser** — 429 rate-limit half the time → **hybrid fallback**
   to rules picks up transparently.
2. **Executor timeout** on the 5th call → agent captures a well-formed
   `status=timeout` result and moves on.
3. **Malformed LLM output** — Gemini returns `{"label": ...}` instead of
   `{"root_cause": ...}` → schema validation rejects, adapter emits
   `UNKNOWN@0.0`.
4. **Duplicate idempotency key** → `check_and_reserve` refuses. **No
   double-charge is possible.**

> "The batch keeps running. The audit log stays truthful. Nothing crashes."

---

## 4:30 – 4:50 · The audit is the artifact

**Show:** `python -m recoverops.observability.replay --log logs/dev_batch.jsonl`

> "Every number I quoted is reproducible from the log alone. Judges can
> rerun this replay tool without touching the agent and get identical
> metrics. That's how we prove the log is complete."

---

## 4:50 – 5:00 · Close

> "**101 tests. 9 phases. Zero magic.** The LLM does what LLMs are good at
> — reading a messy signal. The policy engine does what determinism is good
> at — protecting money.
>
> I'm **Naman Agarwal**. Thank you."

**Show:** final frame — the Overview tab with the ₹3,76,346 recovered.

---

## Filming checklist

- Terminal: use JetBrains Mono at 16pt
- VS Code: dark theme, sidebar hidden
- Browser: full screen, no bookmarks bar visible
- Record at 1080p minimum
- Do one dry run to hit the 5:00 mark
- Keep hands off keyboard when narrating architecture

## Assets to have open in tabs

1. Dashboard at `http://localhost:8501` — Overview tab
2. VS Code with `dashboard/app.py` and `src/recoverops/policy/engine.py`
3. Terminal in `c:\Users\dimplagarwal\recoverops` with venv activated
4. `WHAT_BROKE.md` open for the failure-recovery section
