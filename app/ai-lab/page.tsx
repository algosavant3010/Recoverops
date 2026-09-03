"use client";

import { useState } from "react";
import { BrainCircuit, Check, Cpu, Loader2, Sparkles, WifiOff } from "lucide-react";
import { Subnav } from "@/components/subnav";
import { scenarios } from "@/lib/recoverops/scenarios";
import type { Diagnosis } from "@/lib/recoverops/types";
import styles from "./ai-lab.module.css";

interface ApiResult { diagnosis: Diagnosis; mode: "gemini" | "deterministic"; model?: string; fallbackReason?: string; usage: { externalCalls: number; maxOutputTokens?: number } }

export default function AiLabPage() {
  const [scenarioKey,setScenarioKey]=useState("funds");
  const [result,setResult]=useState<ApiResult|null>(null);
  const [loading,setLoading]=useState(false);
  const call=async(useAI:boolean)=>{setLoading(true);try{const response=await fetch("/api/diagnose",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({scenarioKey,useAI})});setResult(await response.json())}finally{setLoading(false)}};
  const scenario=scenarios.find(item=>item.key===scenarioKey)!;
  return <main className={styles.page}><Subnav active="ai"/><section className={styles.hero}><span>OPTIONAL AI LAB</span><h1>One model call.<br/><em>Only when you ask.</em></h1><p>The page makes zero automatic Gemini requests. Choose a synthetic scenario, inspect exactly what is shared, then opt in to one bounded call.</p></section>
    <section className={styles.grid}><article className={styles.controls}><div className={styles.cardHead}><Cpu/><div><span>01 / INPUT</span><strong>Synthetic scenario</strong></div></div><label>Scenario<select value={scenarioKey} onChange={event=>{setScenarioKey(event.target.value);setResult(null)}}>{scenarios.map(item=><option value={item.key} key={item.key}>{item.label}</option>)}</select></label><div className={styles.safePayload}><span>SAFE PAYLOAD PREVIEW</span><pre>{JSON.stringify({recordType:scenario.record.type,processorCode:scenario.record.errorCode??"none",priorAttemptBucket:scenario.record.attempts===0?"none":"one_or_more",hasRiskSignal:scenario.record.riskFlags.length>0},null,2)}</pre><small><Check/> No ID, exact amount, customer data, city, or merchant metadata.</small></div><div className={styles.actions}><button onClick={()=>call(false)} disabled={loading}><WifiOff/> Run rules · free</button><button className={styles.ai} onClick={()=>call(true)} disabled={loading}>{loading?<Loader2 className={styles.spin}/>:<Sparkles/>} Ask Gemini · 1 call</button></div></article>
      <article className={styles.output}><div className={styles.cardHead}><BrainCircuit/><div><span>02 / OUTPUT</span><strong>Structured diagnosis</strong></div>{result?<em className={result.mode==="gemini"?styles.live:styles.fallback}>{result.mode}</em>:null}</div>{result?<><div className={styles.diagnosis}><small>ROOT CAUSE</small><strong>{result.diagnosis.cause.replaceAll("_"," ")}</strong><span>{Math.round(result.diagnosis.confidence*100)}% confidence</span><p>{result.diagnosis.reasoning}</p></div><dl><div><dt>External calls</dt><dd>{result.usage.externalCalls}</dd></div><div><dt>Output ceiling</dt><dd>{result.usage.maxOutputTokens??0} tokens</dd></div><div><dt>Model</dt><dd>{result.model??"local rules"}</dd></div><div><dt>Fallback</dt><dd>{result.fallbackReason??"not used"}</dd></div></dl><div className={styles.boundary}><Check/> Diagnosis is still only a proposal. Deterministic policy decides whether an action is safe.</div></>:<div className={styles.empty}><BrainCircuit/><strong>No call made</strong><p>The demo starts at zero external usage.</p></div>}</article>
    </section></main>;
}
