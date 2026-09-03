"use client";

import { useMemo, useState } from "react";
import { Braces, Check, Copy, Filter, Search, ShieldCheck } from "lucide-react";
import { Subnav } from "@/components/subnav";
import { runScenario } from "@/lib/recoverops/engine";
import { scenarios } from "@/lib/recoverops/scenarios";
import styles from "./audit.module.css";

export default function AuditPage() {
  const [query, setQuery] = useState("");
  const [stage, setStage] = useState("all");
  const [selected, setSelected] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const runs = useMemo(() => scenarios.map((scenario) => ({ scenario, result: runScenario(scenario.record, { forcedDiagnosis: scenario.forcedDiagnosis, duplicate: scenario.duplicate }) })), []);
  const events = runs.flatMap(({scenario,result}) => result.events.map(event => ({...event,recordId:scenario.record.id,runId:result.runId,rule:result.rule})));
  const filtered = events.filter(event => (stage === "all" || event.stage === stage) && (!query || `${event.recordId} ${event.title} ${event.detail} ${event.rule}`.toLowerCase().includes(query.toLowerCase())));
  const current = events.find(event => event.id === selected) ?? filtered[0] ?? events[0];

  const copy = async () => { await navigator.clipboard.writeText(JSON.stringify(current, null, 2)); setCopied(true); window.setTimeout(()=>setCopied(false),1200); };

  return <main className={styles.page}><Subnav active="audit"/>
    <section className={styles.hero}><div><span>REPLAYABLE EVIDENCE</span><h1>Every decision leaves<br/><em>a complete trace.</em></h1><p>Search across the exact inputs, diagnoses, rules, and outcomes produced by the deterministic demo engine.</p></div><div className={styles.counter}><Braces/><strong>{events.length}</strong><span>EVENTS INDEXED</span></div></section>
    <section className={styles.toolbar}><label><Search size={15}/><input value={query} onChange={event=>setQuery(event.target.value)} placeholder="Search record, rule, or decision…"/></label><div><Filter size={14}/><select value={stage} onChange={event=>setStage(event.target.value)} aria-label="Filter audit stage"><option value="all">All stages</option>{["ingest","diagnose","plan","gate","execute","terminal"].map(item=><option key={item}>{item}</option>)}</select></div><span>{filtered.length} of {events.length} events</span></section>
    <section className={styles.explorer}>
      <div className={styles.table}><div className={styles.tableHead}><span>TIME</span><span>STAGE</span><span>RECORD</span><span>EVENT</span><span>RULE</span></div>{filtered.map(event=><button className={current?.id===event.id?styles.active:""} onClick={()=>setSelected(event.id)} key={event.id}><time>{new Date(event.timestamp).toLocaleTimeString("en-IN",{hour:"2-digit",minute:"2-digit",second:"2-digit"})}</time><em className={styles[event.status]}>{event.stage}</em><code>{event.recordId}</code><strong>{event.title}</strong><span>{event.rule.replaceAll("_"," ")}</span></button>)}</div>
      <aside className={styles.inspector}><div className={styles.inspectorHead}><div><span>EVENT INSPECTOR</span><strong>{current.stage} / {current.title}</strong></div><button onClick={copy}>{copied?<Check/>:<Copy/>}{copied?"Copied":"Copy JSON"}</button></div><dl><div><dt>RUN ID</dt><dd>{current.runId}</dd></div><div><dt>RECORD ID</dt><dd>{current.recordId}</dd></div><div><dt>POLICY RULE</dt><dd>{current.rule}</dd></div><div><dt>STATUS</dt><dd className={styles[current.status]}>{current.status}</dd></div></dl><div className={styles.jsonHead}><span>RAW EVENT</span><ShieldCheck size={14}/></div><pre>{JSON.stringify(current,null,2)}</pre></aside>
    </section>
  </main>;
}
