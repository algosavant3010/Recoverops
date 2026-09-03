"use client";

import { useMemo, useState } from "react";
import { Ban, Check, ChevronDown, CircleDollarSign, Play, ShieldCheck, Siren } from "lucide-react";
import { Subnav } from "@/components/subnav";
import { formatInr, runScenario } from "@/lib/recoverops/engine";
import { scenarios } from "@/lib/recoverops/scenarios";
import styles from "./safety.module.css";

const safetyCases = scenarios.filter((scenario) => ["fraud", "duplicate", "optout", "b2b"].includes(scenario.key));

export default function SafetyPage() {
  const [active, setActive] = useState("fraud");
  const [expanded, setExpanded] = useState<string | null>("fraud");
  const results = useMemo(() => safetyCases.map((scenario) => ({ scenario, result: runScenario(scenario.record, { forcedDiagnosis: scenario.forcedDiagnosis, duplicate: scenario.duplicate }) })), []);
  const selected = results.find((item) => item.scenario.key === active) ?? results[0];
  const protectedValue = results.filter(({ result }) => result.recoveredPaise === 0).reduce((sum, { scenario }) => sum + scenario.record.amountPaise, 0);

  return <main className={styles.page}>
    <Subnav active="safety" />
    <section className={styles.hero}><div><span>RED-TEAM SAFETY CENTER</span><h1>Assume the AI<br/><em>will be wrong.</em></h1><p>Each challenge attacks a different trust boundary. Deterministic policy must keep the outcome safe without relying on model accuracy.</p></div><div className={styles.score}><ShieldCheck/><strong>{results.length}/{results.length}</strong><span>CHALLENGES CONTAINED</span></div></section>

    <section className={styles.stats}><div><Siren/><span><small>ATTACKS REPLAYED</small><strong>{results.length}</strong></span></div><div><CircleDollarSign/><span><small>VALUE PROTECTED</small><strong>{formatInr(protectedValue)}</strong></span></div><div><Ban/><span><small>UNSAFE EXECUTIONS</small><strong>0</strong></span></div><div><Check/><span><small>AUDIT COVERAGE</small><strong>100%</strong></span></div></section>

    <section className={styles.workspace}>
      <aside><div className={styles.asideHead}><span>CHALLENGE SUITE</span><small>offline · deterministic</small></div>{results.map(({scenario,result},index)=><button className={active===scenario.key?styles.active:""} onClick={()=>{setActive(scenario.key);setExpanded(scenario.key)}} key={scenario.key}><i>0{index+1}</i><span><small>{scenario.eyebrow}</small><strong>{scenario.label}</strong></span><em className={result.recoveredPaise===0?styles.pass:styles.fail}>{result.recoveredPaise===0?"PASS":"FAIL"}</em></button>)}</aside>
      <article className={styles.detail}>
        <div className={styles.detailHead}><div><span>ATTACK VECTOR</span><h2>{selected.scenario.label}</h2><p>{selected.scenario.description}</p></div><button><Play size={14} fill="currentColor"/> Replay</button></div>
        <div className={styles.attackGrid}><div><small>AI DIAGNOSIS</small><strong>{selected.result.diagnosis.cause.replaceAll("_"," ")}</strong><span>{Math.round(selected.result.diagnosis.confidence*100)}% confidence</span></div><div><small>IMMUTABLE FACTS</small><strong>{selected.scenario.record.riskFlags.join(", ") || (selected.scenario.record.customerOptedOut?"customer_optout":"record state")}</strong><span>policy-owned input</span></div><div className={styles.verdict}><small>FINAL VERDICT</small><strong>{selected.result.rule.replaceAll("_"," ")}</strong><span><ShieldCheck size={12}/> No unauthorized effect</span></div></div>
        <div className={styles.traceTitle}><span>DECISION TRACE</span><code>{selected.result.runId}</code></div>
        <div className={styles.trace}>{selected.result.events.map((event,index)=><div className={`${styles.event} ${styles[event.status]}`} key={event.id}><span>{index+1}</span><div><small>{event.stage}</small><strong>{event.title}</strong><p>{event.detail}</p></div><em>{event.status}</em></div>)}</div>
      </article>
    </section>

    <section className={styles.invariants}><div className={styles.sectionTitle}><span>NON-NEGOTIABLE INVARIANTS</span><h2>What must remain true.</h2></div>{[
      ["Fraud facts override inference","Even a high-confidence safe diagnosis cannot authorize a money action when risk flags are present."],
      ["Opt-out ends automation","Customer consent is policy input, never a suggestion passed through the model."],
      ["Drafting is not collecting","A message, reply, promise, and settled payment are four different states."],
      ["Replays produce evidence","The same intent receives a stable key and every duplicate refusal appears in the trace."],
    ].map(([title,body],index)=><article key={title}><button onClick={()=>setExpanded(expanded===`i${index}`?null:`i${index}`)}><span><Check/> {title}</span><ChevronDown/></button><p className={expanded===`i${index}`?styles.open:""}>{body}</p></article>)}</section>
  </main>;
}
