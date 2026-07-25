import { describe, expect, it } from "vitest";
import {
  HouseholdSnapshotV1,
  ForecastResponseV1,
  InterventionSimulationRequestV1,
} from "@relief/contracts";
import {
  sarahBaseline,
  sarahIncomeShock,
  sarahInterventionOptions,
  sarahProviderApproval,
  sarahCompletedCase,
  sarahConstitution,
  sarahProviderStatus,
  sarahDataTrust,
  ResilienceScoreV1,
  InterventionCandidateV1,
  ConsumerApprovalV1,
  ProviderApprovalV1,
  ProviderCaseV1,
  AuditEventV1,
  ConstitutionRuleV1,
  ProviderStatusV1,
  DataTrustV1,
} from "../src";

// Section 24: "Each fixture must validate against relief_contracts."
describe("Sarah fixtures validate against @relief/contracts", () => {
  it("sarah_baseline.household_snapshot", () => {
    expect(() => HouseholdSnapshotV1.parse(sarahBaseline.household_snapshot)).not.toThrow();
  });
  it("sarah_baseline.forecast", () => {
    expect(() => ForecastResponseV1.parse(sarahBaseline.forecast)).not.toThrow();
  });
  it("sarah_income_shock.household_snapshot", () => {
    expect(() => HouseholdSnapshotV1.parse(sarahIncomeShock.household_snapshot)).not.toThrow();
  });
  it("sarah_income_shock.forecast", () => {
    expect(() => ForecastResponseV1.parse(sarahIncomeShock.forecast)).not.toThrow();
  });
  it("sarah_intervention_options.simulation_request", () => {
    expect(() =>
      InterventionSimulationRequestV1.parse(sarahInterventionOptions.simulation_request),
    ).not.toThrow();
  });
});

describe("Sarah fixtures validate against the Plan Two product shapes", () => {
  it("resilience scores", () => {
    expect(() => ResilienceScoreV1.parse(sarahBaseline.resilience_score)).not.toThrow();
    expect(() => ResilienceScoreV1.parse(sarahIncomeShock.resilience_score)).not.toThrow();
    expect(() => ResilienceScoreV1.parse(sarahCompletedCase.final_resilience_score)).not.toThrow();
  });

  it("intervention candidates", () => {
    for (const candidate of sarahInterventionOptions.candidates) {
      expect(() => InterventionCandidateV1.parse(candidate)).not.toThrow();
    }
  });

  it("consumer and provider approvals", () => {
    expect(() => ConsumerApprovalV1.parse(sarahProviderApproval.consumer_approval)).not.toThrow();
    expect(() => ProviderCaseV1.parse(sarahProviderApproval.provider_case)).not.toThrow();
    expect(() => ConsumerApprovalV1.parse(sarahCompletedCase.consumer_approval)).not.toThrow();
    expect(() => ProviderApprovalV1.parse(sarahCompletedCase.provider_approval)).not.toThrow();
  });

  it("audit trail", () => {
    for (const event of sarahCompletedCase.audit_trail) {
      expect(() => AuditEventV1.parse(event)).not.toThrow();
    }
  });
});

// Pass Ten / Section 45: "Starting balance plus net event flow equals ending
// balance within the permitted tolerance."
describe("Forecast trajectories reconcile (Pass Ten, Section 45)", () => {
  for (const [label, fixture] of [
    ["sarah_baseline", sarahBaseline],
    ["sarah_income_shock", sarahIncomeShock],
  ] as const) {
    it(`${label}.forecast.trajectories`, () => {
      for (const point of fixture.forecast.trajectories) {
        expect(point.starting_balance_cents + point.inflow_cents - point.outflow_cents).toBe(
          point.ending_balance_cents,
        );
      }
    });

    it(`${label}.forecast.trajectories chain day to day`, () => {
      const points = fixture.forecast.trajectories;
      for (let i = 1; i < points.length; i++) {
        expect(points[i]!.starting_balance_cents).toBe(points[i - 1]!.ending_balance_cents);
      }
    });
  }
});

describe("The income shock is exactly $380.00 (Section 16.3)", () => {
  it("reduces the paycheck from $2,100.00 to $1,720.00", () => {
    const original = sarahIncomeShock.trigger_event.metadata.original_amount_cents as number;
    const shocked = sarahIncomeShock.trigger_event.amount_cents;
    expect(original - shocked).toBe(38000);
    expect(shocked).toBe(172000);
  });
});

describe("Constitution, provider status, and data trust fixtures (redesign brief)", () => {
  it("constitution rules and starter rules", () => {
    for (const rule of sarahConstitution.rules) {
      expect(() => ConstitutionRuleV1.parse(rule)).not.toThrow();
    }
    for (const rule of sarahConstitution.starter_rules) {
      expect(() => ConstitutionRuleV1.parse(rule)).not.toThrow();
    }
  });

  it("provider status", () => {
    for (const provider of sarahProviderStatus.providers) {
      expect(() => ProviderStatusV1.parse(provider)).not.toThrow();
    }
  });

  it("data trust", () => {
    for (const source of sarahDataTrust.sources) {
      expect(() => DataTrustV1.parse(source)).not.toThrow();
    }
  });
});
