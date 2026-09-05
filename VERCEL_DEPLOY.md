# Vercel deployment

## Prerequisites

- Node.js 22.13 or newer
- pnpm 11
- A Vercel account

Gemini is optional. The deployed demo works without secrets.

## Preview deployment

```powershell
pnpm check
vercel link
vercel deploy
```

Verify these routes on the preview URL:

- `/`
- `/evaluation`
- `/safety`
- `/audit`
- `/ai-lab`
- `/operations`
- `/api/health`

## Optional Gemini

Add secrets in Vercel project settings, scoped separately for Preview and Production:

```text
GEMINI_API_KEY
GEMINI_MODEL=gemini-3.5-flash-lite
```

Never prefix the key with `NEXT_PUBLIC_`.

## Razorpay + protected evidence

Configure `DATABASE_URL`, the three `RAZORPAY_*` test-mode secrets, and `OPERATIONS_DASHBOARD_TOKEN`. In Razorpay Test Mode, register `https://<deployment>/api/webhooks/razorpay` for `payment.failed` and `payment_link.paid`. Keep the dashboard token private and enter it only on `/operations`; it is never persisted by the browser.

Before promotion, verify `/api/razorpay/health`, send one signed test webhook, resend the same event ID to prove deduplication, and confirm that `/operations` shows one case and one duplicate delivery.

## Production promotion

After testing the exact preview artifact:

```powershell
vercel promote <verified-preview-url>
```

Then confirm `/api/health`, run every safety challenge, and inspect production logs for errors.
