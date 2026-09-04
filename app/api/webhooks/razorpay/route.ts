import { after } from "next/server";
import { recoveryStore } from "@/lib/razorpay/store";
import { payloadHash, processRazorpayWebhook, verifyWebhookSignature } from "@/lib/razorpay/webhook";
import type { RazorpayWebhook } from "@/lib/razorpay/types";

export const runtime = "nodejs";
export const maxDuration = 30;

export async function POST(request: Request) {
  const secret = process.env.RAZORPAY_WEBHOOK_SECRET; if (!secret) return Response.json({ error: "webhook_not_configured" }, { status: 503 });
  const rawBody = await request.text(); const signature = request.headers.get("x-razorpay-signature") ?? "";
  if (!verifyWebhookSignature(rawBody, signature, secret)) return Response.json({ error: "invalid_signature" }, { status: 401 });
  const eventId = request.headers.get("x-razorpay-event-id"); if (!eventId) return Response.json({ error: "missing_event_id" }, { status: 400 });
  let payload: RazorpayWebhook; try { payload = JSON.parse(rawBody) as RazorpayWebhook; } catch { return Response.json({ error: "invalid_json" }, { status: 400 }); }
  if (!payload.event) return Response.json({ error: "missing_event_type" }, { status: 400 });
  try {
    const reserved = await recoveryStore.reserveWebhook({ eventId, eventType: payload.event, payloadHash: payloadHash(rawBody), payload });
    if (!reserved) return Response.json({ received: true, duplicate: true });
    after(async () => { try { await processRazorpayWebhook(payload, eventId, recoveryStore); await recoveryStore.markWebhook(eventId, "processed"); } catch (error) { await recoveryStore.markWebhook(eventId, "failed", error instanceof Error ? error.message : "unknown_error"); } });
    return Response.json({ received: true, duplicate: false }, { status: 202 });
  } catch { return Response.json({ error: "storage_unavailable" }, { status: 503 }); }
}
