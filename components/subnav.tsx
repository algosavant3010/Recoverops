import { ArrowLeft, Menu, Radar } from "lucide-react";
import Link from "next/link";
import styles from "./subnav.module.css";

export function Subnav({ active }: { active: "evaluation" | "safety" | "audit" | "ai" }) {
  return <header className={styles.nav}>
    <Link className={styles.brand} href="/"><span><Radar size={18} /></span>recover<em>ops</em></Link>
    <nav><Link className={active === "evaluation" ? styles.active : ""} href="/evaluation">Evaluation</Link><Link className={active === "safety" ? styles.active : ""} href="/safety">Safety center</Link><Link className={active === "audit" ? styles.active : ""} href="/audit">Audit explorer</Link><Link className={active === "ai" ? styles.active : ""} href="/ai-lab">AI lab</Link></nav>
    <Link className={styles.back} href="/"><ArrowLeft size={14} /> Demo lab</Link>
    <details className={styles.mobileMenu}>
      <summary aria-label="Open navigation"><Menu size={20} /><span>Menu</span></summary>
      <nav aria-label="Mobile navigation"><Link href="/">Demo lab</Link><Link className={active === "evaluation" ? styles.active : ""} href="/evaluation">Evaluation</Link><Link className={active === "safety" ? styles.active : ""} href="/safety">Safety center</Link><Link className={active === "audit" ? styles.active : ""} href="/audit">Audit explorer</Link><Link className={active === "ai" ? styles.active : ""} href="/ai-lab">AI lab</Link></nav>
    </details>
  </header>;
}
