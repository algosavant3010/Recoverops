import { describe, expect, it } from "vitest";
import { evaluateSimulation } from "./evaluation";

describe("evaluation simulation", () => {
  it("is deterministic", () => expect(evaluateSimulation()).toEqual(evaluateSimulation()));
  it("reports bounded confidence intervals", () => {
    const result = evaluateSimulation();
    expect(result.recoverOpsRateInterval[0]).toBeGreaterThanOrEqual(0);
    expect(result.recoverOpsRateInterval[1]).toBeLessThanOrEqual(1);
  });
  it("keeps fraud and unknown outcomes out of automatic recovery", () => {
    const result = evaluateSimulation();
    expect(result.causes.find((item) => item.cause === "fraud suspected")?.records).toBeGreaterThan(0);
  });
});
