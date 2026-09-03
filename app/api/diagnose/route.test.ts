import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import { POST } from "./route";

describe("diagnose API", () => {
  it("uses zero external calls unless AI is explicitly requested", async () => {
    const request = new NextRequest("http://localhost/api/diagnose", { method: "POST", body: JSON.stringify({ scenarioKey: "funds", useAI: false }) });
    const body = await (await POST(request)).json();
    expect(body.mode).toBe("deterministic");
    expect(body.usage.externalCalls).toBe(0);
  });
  it("rejects arbitrary record payloads", async () => {
    const request = new NextRequest("http://localhost/api/diagnose", { method: "POST", body: JSON.stringify({ record: { id: "merchant-data" }, useAI: true }) });
    expect((await POST(request)).status).toBe(400);
  });
});
