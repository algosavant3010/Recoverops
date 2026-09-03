# RecoverOps demo guide

## Local start

```powershell
pnpm install
pnpm dev
```

Open `http://localhost:3000`.

## 90-second judge flow

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

This runs TypeScript checks, nine tests, ESLint, and a production build.

## Demo fallback

The complete demo works without Gemini or Razorpay credentials. If Gemini is unavailable, the API returns a structured deterministic diagnosis and names the fallback reason.
