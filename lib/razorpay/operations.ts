import { neon } from "@neondatabase/serverless";
import { ensureRazorpaySchema } from "./store";

export type OperationsSnapshot = {
  generatedAt: string;
  metrics: { cases: number; recovered: number; blocked: number; linksIssued: number; recoveredPaise: number; deliveries: number; duplicates: number };
  cases: Array<{ state: string; diagnosis: string; policy: string; action: string | null; updatedAt: string }>;
  events: Array<{ type: string; status: string; deliveries: number; receivedAt: string }>;
  audit: Array<{ type: string; actor: string; createdAt: string }>;
};
function record(value: unknown): Record<string, unknown> { return value && typeof value === "object" ? value as Record<string, unknown> : {}; }

export async function getOperationsSnapshot(): Promise<OperationsSnapshot> {
  if (!process.env.DATABASE_URL) throw new Error("DATABASE_URL is not configured");
  await ensureRazorpaySchema(); const db = neon(process.env.DATABASE_URL);
  const [metricRows, caseRows, eventRows, auditRows] = await Promise.all([
    db`SELECT count(*)::int cases,count(*) FILTER (WHERE state='recovered')::int recovered,count(*) FILTER (WHERE state='blocked')::int blocked,count(*) FILTER (WHERE state='link_issued')::int links_issued,coalesce(sum(recovered_paise),0)::bigint recovered_paise FROM recovery_cases`,
    db`SELECT c.state,c.diagnosis,c.policy_decision,c.updated_at,a.action_type FROM recovery_cases c LEFT JOIN LATERAL (SELECT action_type FROM recovery_actions WHERE case_id=c.id ORDER BY created_at DESC LIMIT 1) a ON true ORDER BY c.updated_at DESC LIMIT 20`,
    db`SELECT event_type,status,delivery_count,received_at FROM webhook_events ORDER BY received_at DESC LIMIT 20`,
    db`SELECT event_type,actor,created_at FROM audit_events ORDER BY created_at DESC LIMIT 40`,
  ]);
  const m=record(metricRows[0]); const deliveries=eventRows.reduce((sum,row)=>sum+Number(record(row).delivery_count??1),0);
  return {generatedAt:new Date().toISOString(),metrics:{cases:Number(m.cases??0),recovered:Number(m.recovered??0),blocked:Number(m.blocked??0),linksIssued:Number(m.links_issued??0),recoveredPaise:Number(m.recovered_paise??0),deliveries,duplicates:Math.max(0,deliveries-eventRows.length)},cases:caseRows.map(row=>{const r=record(row),d=record(r.diagnosis),p=record(r.policy_decision);return {state:String(r.state),diagnosis:String(d.category??"unknown"),policy:String(p.rule??"pending"),action:r.action_type?String(r.action_type):null,updatedAt:new Date(String(r.updated_at)).toISOString()};}),events:eventRows.map(row=>{const r=record(row);return {type:String(r.event_type),status:String(r.status),deliveries:Number(r.delivery_count??1),receivedAt:new Date(String(r.received_at)).toISOString()};}),audit:auditRows.map(row=>{const r=record(row);return {type:String(r.event_type),actor:String(r.actor),createdAt:new Date(String(r.created_at)).toISOString()};})};
}
