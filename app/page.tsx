"use client";

import { useMemo, useState } from "react";
import { ArrowRight, BadgeCheck, Ban, Braces, Check, ChevronRight, CircleDollarSign, Clock3, Fingerprint, LockKeyhole, Play, Radar, RefreshCw, ShieldCheck, Sparkles, TerminalSquare, TriangleAlert, Zap } from "lucide-react";
import { formatInr, runScenario } from "@/lib/recoverops/engine";
import { scenarios } from "@/lib/recoverops/scenarios";
import type { AuditEvent } from "@/lib/recoverops/types";
import { MobileNavigation } from "@/components/mobile-navigation";

const metrics = [
  { label: "Simulated recovery", value: "₹3.76L", delta: "+28.15 pp", icon: CircleDollarSign },
  { label: "Policy decisions", value: "1,246", delta: "100% traced", icon: ShieldCheck },
  { label: "Unsafe actions blocked", value: "143", delta: "zero executed", icon: Ban },
  { label: "Value per action", value: "₹2,707", delta: "8.4× baseline", icon: Zap },
];

function StatusIcon({ event }: { event: AuditEvent }) {
  if (event.status === "success") return <Check size={13} strokeWidth={3} />;
  if (event.status === "blocked") return <Ban size={13} strokeWidth={2.5} />;
  if (event.status === "pending") return <Clock3 size={13} strokeWidth={2.5} />;
  return <ChevronRight size={13} strokeWidth={2.5} />;
}

export default function Home() {
  const [selected, setSelected] = useState(0);
  const [hasRun, setHasRun] = useState(true);
  const scenario = scenarios[selected];
  const result = useMemo(() => runScenario(scenario.record, { forcedDiagnosis: scenario.forcedDiagnosis, duplicate: scenario.duplicate }), [scenario]);

  const run = () => {
    setHasRun(false);
    window.setTimeout(() => setHasRun(true), 320);
  };

  return (
    <main>
      <div className="noise" />
      <header className="nav shell">
        <a className="brand" href="#top" aria-label="RecoverOps home">
          <span className="brand-mark"><Radar size={19} /></span>
          <span>recover<span>ops</span></span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#lab">Live lab</a><a href="/safety">Safety</a><a href="/evaluation">Evaluation</a><a href="/audit">Audit</a><a href="/ai-lab">AI lab</a>
        </nav>
        <a className="nav-cta" href="#lab"><span className="live-dot" /> Live demo</a>
        <MobileNavigation active="lab" />

      </header>

      <section className="hero shell" id="top">
        <div className="hero-copy">
          <div className="eyebrow"><span>Razorpay AI Buildathon</span><i /> Track 03</div>
          <h1>Recover revenue.<br /><em>Never lose control.</em></h1>
          <p>RecoverOps diagnoses failed payments, chooses the next best action, and proves every decision—before touching a single rupee.</p>
          <div className="hero-actions">
            <a className="button primary" href="#lab"><Play size={16} fill="currentColor" /> Run a recovery</a>
            <a className="button secondary" href="/evaluation">Explore the evidence <ArrowRight size={16} /></a>
          </div>
          <div className="trust-row"><span><ShieldCheck size={15} /> Deterministic guardrails</span><span><Fingerprint size={15} /> Idempotent actions</span><span><Braces size={15} /> Replayable audit</span></div>
        </div>
        <div className="hero-visual" aria-label="RecoverOps architecture">
          <div className="orbit orbit-a" /><div className="orbit orbit-b" />
          <div className="core"><span><Sparkles size={22} /></span><strong>DIAGNOSE</strong><small>Gemini + rules</small></div>
          <div className="satellite sat-a"><LockKeyhole size={16} /><span><strong>GATE</strong><small>9 checks</small></span></div>
          <div className="satellite sat-b"><Zap size={16} /><span><strong>ACT</strong><small>bounded</small></span></div>
          <div className="satellite sat-c"><TerminalSquare size={16} /><span><strong>PROVE</strong><small>JSONL</small></span></div>
          <div className="flow-label">LLM proposes <ArrowRight size={13} /> Policy disposes</div>
        </div>
      </section>

      <section className="metric-strip shell" aria-label="Evaluation highlights">
        <div className="strip-label"><span>HELD-OUT</span><strong>Simulation</strong><small>200 synthetic records</small></div>
        {metrics.map(({ label, value, delta, icon: Icon }) => <div className="metric" key={label}><div className="metric-top"><Icon size={16} /><span>{label}</span></div><strong>{value}</strong><small>{delta}</small></div>)}
      </section>

      <section className="lab-section" id="lab">
        <div className="shell">
          <div className="section-heading"><div><span className="kicker">LIVE RECOVERY LAB</span><h2>Put the agent under pressure.</h2></div><p>Choose a case. Watch each plane decide. Try the adversarial scenarios—the guardrails do not trust the model.</p></div>
          <div className="lab-grid">
            <aside className="scenario-list">
              <div className="scenario-title"><span>SCENARIOS</span><small>{scenarios.length} ready</small></div>
              {scenarios.map((item, index) => <button className={index === selected ? "scenario active" : "scenario"} key={item.key} onClick={() => { setSelected(index); setHasRun(true); }}><span className="scenario-index">0{index + 1}</span><span><small>{item.eyebrow}</small><strong>{item.label}</strong></span><ChevronRight size={16} /></button>)}
            </aside>

            <div className="workbench">
              <div className="workbench-head">
                <div><span className="kicker">{scenario.eyebrow}</span><h3>{scenario.label}</h3><p>{scenario.description}</p></div>
                <button className="button primary run" onClick={run}><RefreshCw size={15} /> Run scenario</button>
              </div>
              <div className="record-grid">
                <div><small>RECORD</small><strong className="mono">{scenario.record.id}</strong></div>
                <div><small>AT RISK</small><strong>{formatInr(scenario.record.amountPaise)}</strong></div>
                <div><small>PRIOR ATTEMPTS</small><strong>{scenario.record.attempts}</strong></div>
                <div><small>RISK SIGNALS</small><strong className={scenario.record.riskFlags.length ? "danger-text" : "good-text"}>{scenario.record.riskFlags.length || "Clear"}</strong></div>
              </div>

              <div className={hasRun ? "timeline ready" : "timeline"}>
                {result.events.map((event, index) => <div className={`event ${event.status}`} style={{ "--delay": `${index * 70}ms` } as React.CSSProperties} key={event.id}>
                  <div className="event-rail"><span><StatusIcon event={event} /></span>{index < result.events.length - 1 && <i />}</div>
                  <div className="event-content"><div><small>{event.stage}</small><code>{new Date(event.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</code></div><strong>{event.title}</strong><p>{event.detail}</p></div>
                </div>)}
              </div>

              <div className={`verdict ${result.allowed ? "allowed" : "denied"}`}>
                <span className="verdict-icon">{result.allowed ? <BadgeCheck size={25} /> : <TriangleAlert size={25} />}</span>
                <div><small>POLICY VERDICT</small><strong>{result.allowed ? result.rule.replaceAll("_", " ") : "Action blocked safely"}</strong><p>{result.reason}</p></div>
                <div className="key"><small>IDEMPOTENCY KEY</small><code>{result.idempotencyKey}</code></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="proof shell" id="safety">
        <div className="section-heading"><div><span className="kicker">SAFETY BY CONSTRUCTION</span><h2>The model is never the cashier.</h2></div><p>Immutable transaction facts and deterministic limits sit downstream from AI. A confident wrong answer is still safe.</p></div>
        <div className="proof-grid">
          <article><span className="proof-no">01</span><ShieldCheck /><h3>Facts beat inference</h3><p>Fraud flags, opt-outs, prior attempts, and batch budgets are enforced independently of diagnosis.</p><small>FAIL CLOSED</small></article>
          <article><span className="proof-no">02</span><Fingerprint /><h3>One intent, one key</h3><p>Every money action receives a content-addressed idempotency key before execution.</p><small>NO DOUBLE ACTION</small></article>
          <article><span className="proof-no">03</span><Clock3 /><h3>Schedule, don&apos;t chase</h3><p>Cooldowns leave records open for their next eligible moment instead of escalating prematurely.</p><small>QUIET BY DEFAULT</small></article>
          <article><span className="proof-no">04</span><Braces /><h3>Every decision replays</h3><p>A shared run ID connects signals, reasoning, rules, execution, and terminal outcomes.</p><small>AUDIT READY</small></article>
        </div>
      </section>

      <section className="evidence" id="evidence"><div className="shell evidence-inner">
        <div><span className="kicker">HONEST EVIDENCE</span><h2>Built to be challenged,<br />not just applauded.</h2><p>Results are presented as a reproducible synthetic simulation—not live merchant revenue. The demo separates outreach, promises, and settled cash.</p></div>
        <div className="evidence-card">
          <div className="evidence-head"><span>Methodology contract</span><span className="verified"><Check size={12} /> VERIFIED IN CODE</span></div>
          {["Ground truth is removed before diagnosis", "Fraud can never produce simulated recovery", "Every shown metric traces to committed logic", "No API key is required for the core demo", "Promises are not counted as settled revenue"].map((item) => <div className="check-row" key={item}><span><Check size={13} /></span>{item}</div>)}
        </div>
      </div></section>

      <footer className="shell"><div className="brand"><span className="brand-mark"><Radar size={18} /></span><span>recover<span>ops</span></span></div><p>Autonomous recovery. Deterministic control. Complete evidence.</p><span className="footer-status"><i /> Demo system operational</span></footer>
    </main>
  );
}
