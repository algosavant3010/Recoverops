import { Subnav } from "@/components/subnav";
import { OperationsClient } from "./operations-client";
import styles from "./operations.module.css";

export default function OperationsPage(){return <main className={styles.page}><Subnav active="operations"/><section className={styles.hero}><span>LIVE TEST-MODE EVIDENCE</span><h1>Operations cockpit</h1><p>Inspect persisted Razorpay webhook outcomes without exposing customer data. Live evidence is access-controlled; the public simulation remains available in the recovery lab.</p></section><OperationsClient/></main>}
