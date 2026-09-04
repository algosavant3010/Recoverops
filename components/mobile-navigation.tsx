import { ArrowUpRight, BarChart3, FlaskConical, Menu, Radar, ScrollText, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";
import styles from "./mobile-navigation.module.css";

const destinations = [
  { key: "lab", href: "/#lab", label: "Recovery lab", detail: "Run seven recovery scenarios", icon: FlaskConical },
  { key: "safety", href: "/safety", label: "Safety center", detail: "Stress-test deterministic controls", icon: ShieldCheck },
  { key: "evaluation", href: "/evaluation", label: "Evaluation", detail: "Inspect evidence and benchmarks", icon: BarChart3 },
  { key: "audit", href: "/audit", label: "Audit explorer", detail: "Trace every agent decision", icon: ScrollText },
  { key: "ai", href: "/ai-lab", label: "AI lab", detail: "Compare rules with Gemini", icon: Sparkles },
] as const;

type Destination = (typeof destinations)[number]["key"];

export function MobileNavigation({ active }: { active?: Destination }) {
  return (
    <details className={styles.menu}>
      <summary aria-label="Open RecoverOps navigation">
        <span className={styles.triggerIcon}><Menu size={18} /></span>
        <span className={styles.triggerLabel}>Menu</span>
      </summary>
      <div className={styles.panel}>
        <div className={styles.panelHead}>
          <span><Radar size={14} /> Explore RecoverOps</span>
          <small><i /> System live</small>
        </div>
        <nav aria-label="Mobile navigation">
          {destinations.map(({ key, href, label, detail, icon: Icon }, index) => (
            <Link className={active === key ? styles.active : ""} href={href} key={key} aria-current={active === key ? "page" : undefined}>
              <span className={styles.index}>{String(index + 1).padStart(2, "0")}</span>
              <span className={styles.linkIcon}><Icon size={17} /></span>
              <span className={styles.linkCopy}><strong>{label}</strong><small>{detail}</small></span>
              <ArrowUpRight className={styles.arrow} size={15} />
            </Link>
          ))}
        </nav>
        <div className={styles.panelFoot}>
          <span>AI proposes</span><i /><strong>Policy disposes</strong>
        </div>
      </div>
    </details>
  );
}
