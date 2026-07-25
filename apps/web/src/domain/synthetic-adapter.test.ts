import { describe, expect, it } from "vitest";
import { deriveRiskWindows, parseConstitutionRule, simulateConstitutionRule } from "./synthetic-adapter";
import type { ForecastEnvelope, ForecastPoint, InterventionPackage } from "./types";

function point(overrides: Partial<ForecastPoint>): ForecastPoint {
  return {
    date: "2026-07-27",
    median_balance_cents: 100000,
    lower_balance_cents: 90000,
    upper_balance_cents: 110000,
    reserve_violation_probability: 0.1,
    events: [],
    is_risk: false,
    ...overrides,
  };
}

const baseEvidence = {
  model_version: "deterministic-1.0.0",
  confidence: 0.8,
  generated_at: "2026-07-25T16:00:00Z",
  source_refs: ["synthetic_wells_fargo"],
  freshness: "current" as const,
  status: "simulated" as const,
};

describe("deriveRiskWindows", () => {
  it("groups contiguous risk days into one window and holds through non-risk days", () => {
    const envelope: ForecastEnvelope = {
      id: "f1",
      provider: "deterministic",
      horizon_days: 5,
      reserve_cents: 50000,
      points: [
        point({ date: "2026-07-26", is_risk: false }),
        point({ date: "2026-07-27", is_risk: true, median_balance_cents: 41000 }),
        point({ date: "2026-07-28", is_risk: true, median_balance_cents: 39401 }),
        point({ date: "2026-07-29", is_risk: false }),
        point({ date: "2026-07-30", is_risk: true, median_balance_cents: 45000 }),
      ],
      distress_probabilities: { negative_balance: 0.1, essential_reserve_violation: 0.8, missed_obligation: 0.2 },
      reason_factors: [],
      valid_until: "2026-07-25T17:00:00Z",
      evidence: baseEvidence,
      scenario_active: false,
    };

    const windows = deriveRiskWindows(envelope, { obligations: [] });

    expect(windows).toHaveLength(2);
    expect(windows[0]!.start_date).toBe("2026-07-27");
    expect(windows[0]!.end_date).toBe("2026-07-28");
    expect(windows[0]!.projected_lowest_balance_cents).toBe(39401);
    expect(windows[1]!.start_date).toBe("2026-07-30");
  });

  it("names the causal obligations from same-day outflow events", () => {
    const envelope: ForecastEnvelope = {
      id: "f1",
      provider: "deterministic",
      horizon_days: 1,
      reserve_cents: 50000,
      points: [
        point({
          date: "2026-07-27",
          is_risk: true,
          events: [
            {
              contract_version: "1.0.0",
              event_id: "e1",
              household_id: "hh_01",
              account_id: "acct_01",
              source: "synthetic_wells_fargo",
              source_event_id: "s1",
              event_type: "scheduled_payment",
              event_status: "scheduled",
              occurred_at: "2026-07-27T09:00:00Z",
              effective_at: "2026-07-27T09:00:00Z",
              amount_cents: 145000,
              currency: "USD",
              direction: "outflow",
              merchant_name: "Meridian Realty",
              merchant_category: "rent",
              obligation_id: "obl_rent_01",
              is_recurring: true,
              is_pending: false,
              metadata: {},
            },
          ],
        }),
      ],
      distress_probabilities: { negative_balance: 0.1, essential_reserve_violation: 0.8, missed_obligation: 0.2 },
      reason_factors: [],
      valid_until: "2026-07-25T17:00:00Z",
      evidence: baseEvidence,
      scenario_active: false,
    };

    const snapshot = {
      obligations: [{ obligation_id: "obl_rent_01", display_name: "Rent — Meridian Apartments" }],
    };

    const windows = deriveRiskWindows(envelope, snapshot);
    expect(windows[0]!.description).toContain("Rent — Meridian Apartments");
    expect(windows[0]!.causal_obligation_ids).toEqual(["obl_rent_01"]);
  });
});

describe("parseConstitutionRule (simulated interpretation)", () => {
  it("extracts scope, prohibitions, and approval requirement from the spec's example text", () => {
    const rule = parseConstitutionRule(
      "Never delay rent without asking me first. You may pause subscriptions under $25.00 when my essential reserve is at risk.",
    );
    expect(rule.status).toBe("draft");
    expect(rule.scope).toContain("housing");
    expect(rule.scope).toContain("subscriptions");
    expect(rule.permitted_actions).toContain("pause_subscription");
    expect(rule.approval_requirement).toBe("always_ask");
    expect(rule.maximum_monetary_impact_cents).toBe(2500);
  });

  it("falls back to 'all' scope for unrecognized text without crashing", () => {
    const rule = parseConstitutionRule("Do whatever seems reasonable.");
    expect(rule.scope).toEqual(["all"]);
    expect(rule.confidence).toBeGreaterThan(0);
    expect(rule.confidence).toBeLessThan(1);
  });
});

describe("simulateConstitutionRule", () => {
  it("blocks packages that touch a prohibited action or are marked constitution-incompatible", () => {
    const rule = parseConstitutionRule("Never extend a loan if it adds interest.");
    const packages: InterventionPackage[] = [
      {
        id: "pkg_ok",
        label: "OK package",
        description: "",
        actions: [],
        added_cost_cents: 0,
        new_minimum_balance_cents: 0,
        remaining_risk: { negative_balance: false, essential_reserve_violation: false },
        required_approvals: [],
        user_effort: "low",
        provider_acceptance_probability: null,
        reversibility: "fully_reversible",
        constitution_compatible: true,
        ranking_reason: "",
        stage: "review",
        evidence: baseEvidence,
      },
      {
        id: "pkg_blocked",
        label: "Blocked package",
        description: "",
        actions: [
          {
            action_id: "a1",
            action_type: "term_extension_with_interest",
            obligation_id: "obl_car_01",
            display_name: "Extend loan term",
            parameters: {},
            execution_mode: "provider_executable",
            provider_capability_id: null,
            consumer_status: "pending",
            provider_status: "pending",
          },
        ],
        added_cost_cents: 500,
        new_minimum_balance_cents: 0,
        remaining_risk: { negative_balance: false, essential_reserve_violation: false },
        required_approvals: [],
        user_effort: "low",
        provider_acceptance_probability: null,
        reversibility: "irreversible",
        constitution_compatible: true,
        ranking_reason: "",
        stage: "review",
        evidence: baseEvidence,
      },
    ];

    const result = simulateConstitutionRule(rule, packages);
    expect(result.allowed_package_ids).toEqual(["pkg_ok"]);
    expect(result.blocked_package_ids).toEqual(["pkg_blocked"]);
  });
});
