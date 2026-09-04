import { ensureRazorpaySchema } from "@/lib/razorpay/store";

export const runtime = "nodejs";

export async function GET() {
  const configuration = {
    database: Boolean(process.env.DATABASE_URL),
    testKey: process.env.RAZORPAY_KEY_ID?.startsWith("rzp_test_") ?? false,
    keySecret: Boolean(process.env.RAZORPAY_KEY_SECRET),
    webhookSecret: Boolean(process.env.RAZORPAY_WEBHOOK_SECRET),
  };
  try {
    if (configuration.database) await ensureRazorpaySchema();
    return Response.json({ status: Object.values(configuration).every(Boolean) ? "ready" : "configuration_required", mode: "razorpay_test", configuration, schema: configuration.database ? "ready" : "unavailable" });
  } catch {
    return Response.json({ status: "storage_unavailable", mode: "razorpay_test", configuration, schema: "error" }, { status: 503 });
  }
}
