import { z } from "zod";
import { diagnose } from "./engine";
import type { Diagnosis, RecoveryRecord, RootCause } from "./types";

export const rootCauses = ["insufficient_funds", "gateway_downtime", "expired_card", "mandate_lapsed", "checkout_abandoned", "b2b_overdue", "fraud_suspected", "unknown"] as const satisfies readonly RootCause[];

export type AiDiagnosisResult = { diagnosis: Diagnosis; mode: "gemini" | "deterministic"; externalCalls: 0 | 1; fallbackReason?: string; model?: string };

export async function diagnoseWithGemini(record: RecoveryRecord): Promise<AiDiagnosisResult> {
  const fallback = (reason: string): AiDiagnosisResult => ({ diagnosis: diagnose(record), mode: "deterministic", externalCalls: 0, fallbackReason: reason });
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) return fallback("missing_api_key");
  const model = process.env.GEMINI_MODEL || "gemini-3.5-flash-lite";
  const safeSignals = { recordType: record.type, processorCode: record.errorCode ?? "none", priorAttemptBucket: record.attempts === 0 ? "none" : "one_or_more", hasRiskSignal: record.riskFlags.length > 0 };
  const prompt = `Classify this payment-recovery scenario into exactly one root cause: ${rootCauses.join(", ")}. Return concise JSON only. Signals: ${JSON.stringify(safeSignals)}`;
  try {
    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`, { method: "POST", headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey }, body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }], generationConfig: { temperature: 0.1, maxOutputTokens: 256, responseMimeType: "application/json", responseSchema: { type: "OBJECT", required: ["cause", "confidence", "reasoning"], properties: { cause: { type: "STRING", enum: rootCauses }, confidence: { type: "NUMBER", minimum: 0, maximum: 1 }, reasoning: { type: "STRING" } } } } }), signal: AbortSignal.timeout(15_000) });
    if (!response.ok) return fallback(`gemini_http_${response.status}`);
    const wire = await response.json() as { candidates?: { content?: { parts?: { text?: string }[] } }[] };
    const text = wire.candidates?.[0]?.content?.parts?.[0]?.text;
    const output = z.object({ cause: z.enum(rootCauses), confidence: z.number().min(0).max(1), reasoning: z.string().min(1).max(500) }).parse(JSON.parse(text || "{}"));
    return { diagnosis: { ...output, source: "gemini" }, mode: "gemini", model, externalCalls: 1 };
  } catch (error) {
    return fallback(error instanceof DOMException && error.name === "TimeoutError" ? "gemini_timeout" : "gemini_invalid_response");
  }
}
