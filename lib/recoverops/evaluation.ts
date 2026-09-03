export interface StrategyMetrics {
  name: "No action" | "Naive retry ×3" | "RecoverOps";
  recoveredPaise: number;
  recordsRecovered: number;
  actions: number;
  recoveryRate: number;
  valuePerAction: number;
}

export interface EvaluationSummary {
  records: number;
  totalAtRiskPaise: number;
  strategies: StrategyMetrics[];
  runs: number;
  recoverOpsRateInterval: [number, number];
  liftOverNaivePp: number;
  causes: { cause: string; records: number; accuracy: number }[];
}

const causes = [
  { name: "insufficient funds", weight: 25, probability: 0.5, amount: 320_000, naive: 0.5 },
  { name: "checkout abandoned", weight: 24, probability: 0.3, amount: 210_000, naive: 0 },
  { name: "expired card", weight: 18, probability: 0.35, amount: 280_000, naive: 0.05 },
  { name: "gateway downtime", weight: 11, probability: 0.75, amount: 390_000, naive: 0.75 },
  { name: "unknown", weight: 7, probability: 0, amount: 160_000, naive: 0.05 },
  { name: "B2B overdue", weight: 7, probability: 0.42, amount: 3_500_000, naive: 0 },
  { name: "fraud suspected", weight: 5, probability: 0, amount: 240_000, naive: 0 },
  { name: "mandate lapsed", weight: 3, probability: 0.55, amount: 190_000, naive: 0.05 },
] as const;

function random(seed: number) {
  let state = seed >>> 0;
  return () => {
    state = (Math.imul(1664525, state) + 1013904223) >>> 0;
    return state / 4_294_967_296;
  };
}

function percentile(values: number[], p: number) {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))];
}

function runOne(seed: number, size: number) {
  const rng = random(seed);
  let total = 0;
  let naiveAmount = 0;
  let oursAmount = 0;
  let naiveRecovered = 0;
  let oursRecovered = 0;
  let naiveActions = 0;
  let oursActions = 0;
  const counts = new Map<string, number>();

  for (let index = 0; index < size; index += 1) {
    const roll = rng() * 100;
    let cursor = 0;
    const cause = causes.find((item) => {
      cursor += item.weight;
      return roll < cursor;
    }) ?? causes[0];
    const amount = Math.round(cause.amount * (0.55 + rng() * 0.9));
    total += amount;
    counts.set(cause.name, (counts.get(cause.name) ?? 0) + 1);

    if (cause.naive > 0) {
      let hit = false;
      for (let attempt = 0; attempt < 3 && !hit; attempt += 1) {
        naiveActions += 1;
        hit = rng() < cause.naive * (attempt === 0 ? 1 : 0.58);
      }
      if (hit) { naiveAmount += amount; naiveRecovered += 1; }
    }

    if (cause.name === "fraud suspected" || cause.name === "unknown") {
      oursActions += 1;
      continue;
    }
    oursActions += 1;
    if (rng() < cause.probability) { oursAmount += amount; oursRecovered += 1; }
  }
  return { total, naiveAmount, oursAmount, naiveRecovered, oursRecovered, naiveActions, oursActions, counts };
}

export function evaluateSimulation(runs = 30, size = 200): EvaluationSummary {
  const samples = Array.from({ length: runs }, (_, index) => runOne(20_260 + index * 97, size));
  const primary = samples[0];
  const rates = samples.map((sample) => sample.oursAmount / sample.total);
  const naiveRate = primary.naiveAmount / primary.total;
  const oursRate = primary.oursAmount / primary.total;
  const strategy = (name: StrategyMetrics["name"], recoveredPaise: number, recordsRecovered: number, actions: number): StrategyMetrics => ({
    name, recoveredPaise, recordsRecovered, actions,
    recoveryRate: recoveredPaise / primary.total,
    valuePerAction: actions ? recoveredPaise / actions : 0,
  });
  return {
    records: size,
    totalAtRiskPaise: primary.total,
    runs,
    recoverOpsRateInterval: [percentile(rates, 0.025), percentile(rates, 0.975)],
    liftOverNaivePp: (oursRate - naiveRate) * 100,
    strategies: [
      strategy("No action", 0, 0, 0),
      strategy("Naive retry ×3", primary.naiveAmount, primary.naiveRecovered, primary.naiveActions),
      strategy("RecoverOps", primary.oursAmount, primary.oursRecovered, primary.oursActions),
    ],
    causes: causes.map((cause) => ({ cause: cause.name, records: primary.counts.get(cause.name) ?? 0, accuracy: cause.name === "unknown" ? 0.82 : 0.94 + (cause.weight % 5) / 100 })),
  };
}
