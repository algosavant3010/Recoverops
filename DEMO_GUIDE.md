# RecoverOps demo guide

## Local start

```powershell
pnpm install
pnpm dev
```

Open `http://localhost:3000`.

## 5-minute winning judge flow

1. **Problem (30s)** — failed payments are recoverable, but unsafe automation damages trust.
2. **Architecture (30s)** — state the contract: “Gemini diagnoses; deterministic policy decides; Razorpay executes in test mode; Neon proves.”
3. **Safe simulation (60s)** — run `Insufficient funds`, then the fraud conflict and duplicate scenarios.
4. **Live evidence (90s)** — open `/operations`, enter the private judge passcode, and show persisted webhook deliveries, decisions, blocked cases, links, and confirmed recovery.
5. **AI evidence (45s)** — use `/ai-lab` once; point out the external-call counter and deterministic fallback.
6. **Close (45s)** — show Evaluation and say exactly what is simulated versus confirmed by Razorpay.

## 90-second fallback flow

1. **Command center** — state the contract: “AI diagnoses; deterministic policy decides.”
2. **Live lab** — run `Insufficient funds` and point out the action, named policy verdict, idempotency key, and trace.
3. **Safety center** — open `/safety`, choose `Fraud safety test`, and show that an intentionally wrong high-confidence diagnosis is blocked by immutable risk facts.
4. **Duplicate defense** — show the first reservation and second refusal.
5. **Evaluation** — open `/evaluation`; disclose that the figures are synthetic, show the 30-seed interval, and explain the bounded claim.
6. **Audit explorer** — search `fraud`, select the gate event, and copy its raw JSON.
7. **AI lab** — show that the initial external-call count is zero. Use local rules first; use the one-call Gemini button only if a key is configured.

## Full verification

```powershell
pnpm check
```

This runs TypeScript checks, the complete unit/integration suite, ESLint, and a production build.

## Demo fallback

The complete demo works without Gemini or Razorpay credentials. If Gemini is unavailable, the API returns a structured deterministic diagnosis and names the fallback reason.
