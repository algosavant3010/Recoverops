import { ArrowLeft, Radar } from "lucide-react";
import Link from "next/link";
import styles from "./subnav.module.css";
import { MobileNavigation } from "./mobile-navigation";

export function Subnav({ active }: { active: "evaluation" | "safety" | "audit" | "ai" }) {
  return <header className={styles.nav}>
    <Link className={styles.brand} href="/"><span><Radar size={18} /></span>recover<em>ops</em></Link>
    <nav><Link className={active === "evaluation" ? styles.active : ""} href="/evaluation">Evaluation</Link><Link className={active === "safety" ? styles.active : ""} href="/safety">Safety center</Link><Link className={active === "audit" ? styles.active : ""} href="/audit">Audit explorer</Link><Link className={active === "ai" ? styles.active : ""} href="/ai-lab">AI lab</Link></nav>
    <Link className={styles.back} href="/"><ArrowLeft size={14} /> Demo lab</Link>
    <MobileNavigation active={active} />

  </header>;
}
