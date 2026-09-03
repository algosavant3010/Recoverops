import { Activity, ArrowUpRight, BarChart3, CheckCircle2, FlaskConical, ShieldAlert } from "lucide-react";
import { Subnav } from "@/components/subnav";
import { formatInr } from "@/lib/recoverops/engine";
import { evaluateSimulation } from "@/lib/recoverops/evaluation";
import styles from "./evaluation.module.css";

export default function EvaluationPage() {
  const report = evaluateSimulation();
  const ours = report.strategies[2];
  const maxAmount = Math.max(...report.strategies.map((item) => item.recoveredPaise));
  return <main className={styles.page}>
    <Subnav active="evaluation" />
    <section className={styles.hero}>
      <div><span className={styles.kicker}>REPRODUCIBLE EVALUATION</span><h1>Evidence, with the<br/><em>assumptions visible.</em></h1><p>A deterministic synthetic benchmark over {report.runs} seeds. These are simulated outcomes—not live merchant revenue.</p></div>
      <div className={styles.heroStat}><small>RECOVEROPS RATE</small><strong>{(ours.recoveryRate * 100).toFixed(1)}%</strong><span><ArrowUpRight size={14}/>{report.liftOverNaivePp.toFixed(1)} pp over naive retry</span></div>
    </section>

    <section className={styles.disclosure}><FlaskConical size={18}/><div><strong>Synthetic holdout</strong><p>Amounts, causes, and response probabilities are generated. Use this to compare strategy behavior—not to predict merchant revenue.</p></div><span>{report.records} records · {formatInr(report.totalAtRiskPaise)} at risk</span></section>

    <section className={styles.panel}>
      <div className={styles.panelHead}><div><span>STRATEGY SHOWDOWN</span><h2>Same records. Different decisions.</h2></div><small>Primary seed: 20,260</small></div>
      <div className={styles.strategies}>{report.strategies.map((strategy, index) => <article className={index === 2 ? styles.winner : ""} key={strategy.name}>
        <div className={styles.strategyTitle}><span>0{index + 1}</span><strong>{strategy.name}</strong>{index === 2 ? <em><CheckCircle2 size={11}/> CAUSE-AWARE</em> : null}</div>
        <strong className={styles.amount}>{formatInr(strategy.recoveredPaise)}</strong><small>SIMULATED RECOVERED VALUE</small>
        <div className={styles.bar}><i style={{width:`${maxAmount ? strategy.recoveredPaise / maxAmount * 100 : 0}%`}}/></div>
        <dl><div><dt>Recovery rate</dt><dd>{(strategy.recoveryRate * 100).toFixed(1)}%</dd></div><div><dt>Records</dt><dd>{strategy.recordsRecovered}/{report.records}</dd></div><div><dt>Actions</dt><dd>{strategy.actions}</dd></div><div><dt>Value/action</dt><dd>{formatInr(strategy.valuePerAction)}</dd></div></dl>
      </article>)}</div>
    </section>

    <section className={styles.twoCol}>
      <article className={styles.panel}><div className={styles.panelHead}><div><span>MULTI-SEED STABILITY</span><h2>30-run interval</h2></div><Activity size={20}/></div><div className={styles.interval}><strong>{(report.recoverOpsRateInterval[0]*100).toFixed(1)}%</strong><div><i/><span style={{left:`${report.recoverOpsRateInterval[0]*100}%`,width:`${(report.recoverOpsRateInterval[1]-report.recoverOpsRateInterval[0])*100}%`}}/></div><strong>{(report.recoverOpsRateInterval[1]*100).toFixed(1)}%</strong></div><p className={styles.note}>Empirical 95% interval across deterministic seeds. A wider interval signals that the headline is sensitive to batch composition.</p></article>
      <article className={styles.panel}><div className={styles.panelHead}><div><span>WHAT THIS PROVES</span><h2>Bounded claim</h2></div><ShieldAlert size={20}/></div><ul className={styles.claims}><li><CheckCircle2/> Cause-aware routing beats this narrow baseline.</li><li><CheckCircle2/> Fraud never produces simulated recovery.</li><li><CheckCircle2/> Results reproduce from committed logic.</li><li><BarChart3/> Real causal lift still requires merchant data.</li></ul></article>
    </section>

    <section className={styles.panel}><div className={styles.panelHead}><div><span>DIAGNOSIS BY CAUSE</span><h2>Coverage, not a perfect-score theatre.</h2></div><small>Noise included in displayed accuracy</small></div><div className={styles.causes}>{report.causes.map(item=><div key={item.cause}><span>{item.cause}</span><div><i style={{width:`${item.accuracy*100}%`}}/></div><strong>{(item.accuracy*100).toFixed(0)}%</strong><small>{item.records} records</small></div>)}</div></section>
  </main>;
}
