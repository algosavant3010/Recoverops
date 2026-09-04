import { payloadHash, processRazorpayWebhook, verifyWebhookSignature } from "./webhook";
import type { RazorpayWebhook, RecoveryStore } from "./types";

type Scheduler = (work: () => Promise<void>) => void;

export async function handleRazorpayWebhookRequest(request: Request, store: RecoveryStore, schedule: Scheduler, secret = process.env.RAZORPAY_WEBHOOK_SECRET) {
  if (!secret) return Response.json({ error: "webhook_not_configured" }, { status: 503 });
  const rawBody = await request.text();
  if (!verifyWebhookSignature(rawBody, request.headers.get("x-razorpay-signature") ?? "", secret)) return Response.json({ error: "invalid_signature" }, { status: 401 });
  const eventId = request.headers.get("x-razorpay-event-id");
  if (!eventId) return Response.json({ error: "missing_event_id" }, { status: 400 });
  let payload: RazorpayWebhook;
  try { payload = JSON.parse(rawBody) as RazorpayWebhook; } catch { return Response.json({ error: "invalid_json" }, { status: 400 }); }
  if (!payload.event) return Response.json({ error: "missing_event_type" }, { status: 400 });
  try {
    const reserved = await store.reserveWebhook({ eventId, eventType: payload.event, payloadHash: payloadHash(rawBody), payload });
    if (!reserved) return Response.json({ received: true, duplicate: true });
    schedule(async () => {
      try { await processRazorpayWebhook(payload, eventId, store); await store.markWebhook(eventId, "processed"); }
      catch (error) { await store.markWebhook(eventId, "failed", error instanceof Error ? error.message : "unknown_error"); }
    });
    return Response.json({ received: true, duplicate: false }, { status: 202 });
  } catch { return Response.json({ error: "storage_unavailable" }, { status: 503 }); }
}
