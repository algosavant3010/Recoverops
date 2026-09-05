import { createHash, timingSafeEqual } from "node:crypto";
import { getOperationsSnapshot } from "@/lib/razorpay/operations";
export const runtime="nodejs"; export const dynamic="force-dynamic";
function allowed(request:Request){const configured=process.env.OPERATIONS_DASHBOARD_TOKEN;const received=request.headers.get("authorization")?.replace(/^Bearer\s+/i,"");if(!configured||!received)return false;const a=Buffer.from(createHash("sha256").update(configured).digest("hex"));const b=Buffer.from(createHash("sha256").update(received).digest("hex"));return timingSafeEqual(a,b);}
export async function GET(request:Request){if(!allowed(request))return Response.json({error:"dashboard_locked"},{status:401});try{return Response.json(await getOperationsSnapshot(),{headers:{"Cache-Control":"no-store"}});}catch{return Response.json({error:"operations_unavailable"},{status:503});}}
