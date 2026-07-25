import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { server } from "../msw/node";
import { resetHandlerState } from "../msw/handlers";

// Node's global fetch types (undici, via @types/node) type Response.json()
// as Promise<unknown> rather than DOM lib's Promise<any> — this package's
// tsconfig doesn't pull in "dom". These are test-only envelope bodies.
function json(res: Response): Promise<any> {
  return res.json();
}

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  resetHandlerState();
});
afterAll(() => server.close());

describe("MSW handlers back the consumer journey (Section 16.1)", () => {
  it("serves the baseline snapshot and resilience score before any shock", async () => {
    const snapshot = await fetch("http://localhost/v1/households/current/snapshot").then(json);
    expect(snapshot.data.snapshot_id).toBe("snap_sarah_baseline");

    const score = await fetch("http://localhost/v1/resilience/current").then(json);
    expect(score.data.overall).toBe(82);
  });

  it("POST /v1/forecasts alone does not mutate household state", async () => {
    const forecast = await fetch("http://localhost/v1/forecasts", { method: "POST" }).then(json);
    expect(forecast.data.forecast_id).toBe("forecast_sarah_baseline");

    const snapshot = await fetch("http://localhost/v1/households/current/snapshot").then(json);
    expect(snapshot.data.snapshot_id).toBe("snap_sarah_baseline");
  });

  it("switches to the shocked snapshot after POST /v1/demo/shock (Section 16.3)", async () => {
    const shockResult = await fetch("http://localhost/v1/demo/shock", { method: "POST" }).then(json);
    expect(shockResult.data.forecast.forecast_id).toBe("forecast_sarah_shock");
    expect(shockResult.data.forecast.distress_probabilities.essential_reserve_violation).toBeGreaterThan(0.5);

    const snapshot = await fetch("http://localhost/v1/households/current/snapshot").then(json);
    expect(snapshot.data.snapshot_id).toBe("snap_sarah_shock");

    const forecast = await fetch("http://localhost/v1/forecasts", { method: "POST" }).then(json);
    expect(forecast.data.forecast_id).toBe("forecast_sarah_shock");
  });

  it("POST /v1/demo/reset returns to baseline", async () => {
    await fetch("http://localhost/v1/demo/shock", { method: "POST" });
    await fetch("http://localhost/v1/demo/reset", { method: "POST" });
    const snapshot = await fetch("http://localhost/v1/households/current/snapshot").then(json);
    expect(snapshot.data.snapshot_id).toBe("snap_sarah_baseline");
  });

  it("walks consumer approval through provider approval to a completed case", async () => {
    const consumerApproval = await fetch("http://localhost/v1/interventions/int_sarah_recommended/approve", {
      method: "POST",
    }).then(json);
    expect(consumerApproval.data.workflow_status).toBe("awaiting_provider_approval");

    const providerApproval = await fetch("http://localhost/v1/provider/cases/provcase_sarah_01/approve", {
      method: "POST",
    }).then(json);
    expect(providerApproval.data.workflow_status).toBe("executed");
    expect(providerApproval.data.audit_trail).toHaveLength(10);
  });

  it("every envelope carries a request_id and contract_version metadata (Section 30)", async () => {
    const res = await fetch("http://localhost/v1/accounts").then(json);
    expect(res.request_id).toBeTruthy();
    expect(res.metadata.contract_version).toBe("1.0.0");
  });
});
