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
- `/api/health`

## Optional Gemini

Add secrets in Vercel project settings, scoped separately for Preview and Production:

```text
GEMINI_API_KEY
GEMINI_MODEL=gemini-3.5-flash-lite
```

Never prefix the key with `NEXT_PUBLIC_`.

## Production promotion

After testing the exact preview artifact:

```powershell
vercel promote <verified-preview-url>
```

Then confirm `/api/health`, run every safety challenge, and inspect production logs for errors.
