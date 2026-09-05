import { createHmac } from "node:crypto";
import { describe, expect, it, vi } from "vitest";
import { handleRazorpayWebhookRequest } from "./handler";
import type { RecoveryStore } from "./types";

const secret="whsec_test"; const body=JSON.stringify({event:"payment.failed",payload:{payment:{entity:{id:"pay_test",amount:25000}}}});
function request(headers:Record<string,string>={}){return new Request("https://example.test/api/webhooks/razorpay",{method:"POST",body,headers:{"x-razorpay-event-id":"evt_1","x-razorpay-signature":createHmac("sha256",secret).update(body).digest("hex"),...headers}})}
function store(reserved=true):RecoveryStore{return {reserveWebhook:vi.fn().mockResolvedValue(reserved),markWebhook:vi.fn(),upsertFailedCase:vi.fn(),reserveAction:vi.fn(),completeAction:vi.fn(),failAction:vi.fn(),markRecoveredByReference:vi.fn(),appendAudit:vi.fn()} as unknown as RecoveryStore;}

describe("Razorpay webhook HTTP boundary",()=>{
  it("rejects an invalid signature before storage",async()=>{const s=store();const response=await handleRazorpayWebhookRequest(request({"x-razorpay-signature":"bad"}),s,vi.fn(),secret);expect(response.status).toBe(401);expect(s.reserveWebhook).not.toHaveBeenCalled();});
  it("requires Razorpay's event id",async()=>{const s=store();const signed=request();const response=await handleRazorpayWebhookRequest(new Request(signed.url,{method:"POST",body,headers:{"x-razorpay-signature":signed.headers.get("x-razorpay-signature")!}}),s,vi.fn(),secret);expect(response.status).toBe(400);});
  it("accepts once and schedules background processing",async()=>{const schedule=vi.fn();const response=await handleRazorpayWebhookRequest(request(),store(),schedule,secret);expect(response.status).toBe(202);expect(schedule).toHaveBeenCalledOnce();expect(await response.json()).toEqual({received:true,duplicate:false});});
  it("acknowledges duplicates without scheduling another action",async()=>{const schedule=vi.fn();const response=await handleRazorpayWebhookRequest(request(),store(false),schedule,secret);expect(response.status).toBe(200);expect(schedule).not.toHaveBeenCalled();expect(await response.json()).toEqual({received:true,duplicate:true});});
});
