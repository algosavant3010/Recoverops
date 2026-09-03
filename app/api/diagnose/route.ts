import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { diagnose } from "@/lib/recoverops/engine";
import { scenarios } from "@/lib/recoverops/scenarios";
import type { Diagnosis } from "@/lib/recoverops/types";

export const runtime = "nodejs";
export const maxDuration = 20;

const causes = ["insufficient_funds","gateway_downtime","expired_card","mandate_lapsed","checkout_abandoned","b2b_overdue","fraud_suspected","unknown"] as const;
const requestSchema = z.object({ scenarioKey: z.enum(["funds","gateway","checkout","b2b","fraud","duplicate","optout"]), useAI: z.boolean().default(false) });

function fallback(scenarioKey: string, reason: string) {
  const scenario = scenarios.find(item => item.key === scenarioKey)!;
  return NextResponse.json({ diagnosis: diagnose(scenario.record), mode: "deterministic", fallbackReason: reason, usage: { externalCalls: 0 } });
}

export async function POST(request: NextRequest) {
  let parsed: z.infer<typeof requestSchema>;
  try { parsed = requestSchema.parse(await request.json()); }
  catch { return NextResponse.json({ error: "invalid_request" }, { status: 400 }); }
  if (!parsed.useAI) return fallback(parsed.scenarioKey, "ai_not_requested");
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) return fallback(parsed.scenarioKey, "missing_api_key");

  const scenario = scenarios.find(item => item.key === parsed.scenarioKey)!;
  const model = process.env.GEMINI_MODEL || "gemini-3.5-flash-lite";
  // Only coarse, synthetic demo signals leave the server. IDs, amounts and metadata do not.
  const safeSignals = { recordType: scenario.record.type, processorCode: scenario.record.errorCode ?? "none", priorAttemptBucket: scenario.record.attempts === 0 ? "none" : "one_or_more", hasRiskSignal: scenario.record.riskFlags.length > 0 };
  const prompt = `Classify this synthetic payment-recovery scenario into exactly one root cause: ${causes.join(", ")}. Return concise JSON only. Signals: ${JSON.stringify(safeSignals)}`;
  try {
    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }], generationConfig: { temperature: 0.1, maxOutputTokens: 256, responseMimeType: "application/json", responseSchema: { type: "OBJECT", required: ["cause","confidence","reasoning"], properties: { cause: { type: "STRING", enum: causes }, confidence: { type: "NUMBER", minimum: 0, maximum: 1 }, reasoning: { type: "STRING" } } } } }),
      signal: AbortSignal.timeout(15_000),
    });
    if (!response.ok) return fallback(parsed.scenarioKey, `gemini_http_${response.status}`);
    const wire = await response.json() as { candidates?: { content?: { parts?: { text?: string }[] } }[] };
    const text = wire.candidates?.[0]?.content?.parts?.[0]?.text;
    const output = z.object({ cause: z.enum(causes), confidence: z.number().min(0).max(1), reasoning: z.string().min(1).max(500) }).parse(JSON.parse(text || "{}"));
    const diagnosis: Diagnosis = { ...output, source: "gemini" };
    return NextResponse.json({ diagnosis, mode: "gemini", model, usage: { externalCalls: 1, maxOutputTokens: 256 } });
  } catch (error) {
    return fallback(parsed.scenarioKey, error instanceof DOMException && error.name === "TimeoutError" ? "gemini_timeout" : "gemini_invalid_response");
  }
}
