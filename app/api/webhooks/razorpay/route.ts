import { after } from "next/server";
import { handleRazorpayWebhookRequest } from "@/lib/razorpay/handler";
import { recoveryStore } from "@/lib/razorpay/store";
export const runtime = "nodejs";
export const maxDuration = 30;
export async function POST(request: Request) { return handleRazorpayWebhookRequest(request, recoveryStore, (work) => after(work)); }