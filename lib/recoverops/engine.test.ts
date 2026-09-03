import { describe, expect, it } from "vitest";
import { runScenario } from "./engine";
import { scenarios } from "./scenarios";

const byKey = (key: string) => {
  const scenario = scenarios.find((item) => item.key === key);
  if (!scenario) throw new Error(`Missing scenario: ${key}`);
  return scenario;
};

describe("RecoverOps safety engine", () => {
  it("blocks a money action when immutable fraud facts contradict the diagnosis", () => {
    const scenario = byKey("fraud");
    const result = runScenario(scenario.record, { forcedDiagnosis: scenario.forcedDiagnosis });
    expect(result.diagnosis.cause).toBe("insufficient_funds");
    expect(result.allowed).toBe(false);
    expect(result.rule).toBe("fraud_signal_stop");
    expect(result.recoveredPaise).toBe(0);
  });

  it("enforces customer opt-out independently of diagnosis", () => {
    const scenario = byKey("optout");
    const result = runScenario(scenario.record);
    expect(result.allowed).toBe(false);
    expect(result.rule).toBe("customer_optout");
  });

  it("does not count drafted B2B outreach as recovered cash", () => {
    const scenario = byKey("b2b");
    const result = runScenario(scenario.record);
    expect(result.outcome).toBe("scheduled");
    expect(result.recoveredPaise).toBe(0);
    expect(result.events.at(-1)?.title).toBe("Awaiting customer response");
  });

  it("uses stable idempotency keys", () => {
    const scenario = byKey("duplicate");
    const first = runScenario(scenario.record, { duplicate: true });
    const second = runScenario(scenario.record, { duplicate: true });
    expect(first.idempotencyKey).toBe(second.idempotencyKey);
    expect(first.events.some((event) => event.title === "Duplicate refused")).toBe(true);
  });
});
