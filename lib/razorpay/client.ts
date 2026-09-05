export type PaymentLinkResult = { id: string; short_url: string; reference_id: string; amount: number; status: string };

export async function createTestPaymentLink(input: { amountPaise: number; referenceId: string; caseId: string; description: string }): Promise<PaymentLinkResult> {
  const keyId = process.env.RAZORPAY_KEY_ID;
  const keySecret = process.env.RAZORPAY_KEY_SECRET;
  if (!keyId || !keySecret) throw new Error("Razorpay API credentials are not configured");
  if (!keyId.startsWith("rzp_test_")) throw new Error("RecoverOps Phase 1 only permits Razorpay test-mode keys");
  const response = await fetch("https://api.razorpay.com/v1/payment_links", { method: "POST", headers: { Authorization: `Basic ${Buffer.from(`${keyId}:${keySecret}`).toString("base64")}`, "Content-Type": "application/json" }, body: JSON.stringify({ amount: input.amountPaise, currency: "INR", accept_partial: false, reference_id: input.referenceId, description: input.description.slice(0, 2048), expire_by: Math.floor(Date.now() / 1000) + 86_400, notify: { sms: false, email: false }, reminder_enable: false, notes: { recoverops_case_id: input.caseId } }), signal: AbortSignal.timeout(8_000) });
  const body = await response.json() as Record<string, unknown>;
  if (!response.ok) throw new Error(`Razorpay Payment Link failed (${response.status})`);
  if (typeof body.id !== "string" || typeof body.short_url !== "string") throw new Error("Razorpay returned an invalid Payment Link response");
  return body as unknown as PaymentLinkResult;
}
