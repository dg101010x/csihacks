import * as synthetic from "./synthetic-adapter";
import type { ScenarioDefinition } from "./types";

/**
 * One central Relief data client (Section 14). Every page calls through
 * this object — never `fetch`, MSW, or fixture JSON directly. Today every
 * method delegates to the synthetic adapter; a live client would implement
 * the same method signatures against Plan One's real endpoints and get
 * swapped in here.
 */
export const reliefClient = {
  getForecastEnvelope: synthetic.fetchForecastEnvelope,
  getRiskWindows: synthetic.deriveRiskWindows,
  getScenarioBaseline: synthetic.fetchScenarioBaseline,
  applyScenario: (scenario: ScenarioDefinition) => synthetic.applyScenario(scenario),
  resetScenario: synthetic.resetScenario,
  getInterventionPackages: synthetic.fetchInterventionPackages,
  approveIntervention: synthetic.approveIntervention,
  approveProviderCase: synthetic.approveProviderCase,
  getConstitutionRules: synthetic.fetchConstitutionRules,
  parseConstitutionRule: synthetic.parseConstitutionRule,
  simulateConstitutionRule: synthetic.simulateConstitutionRule,
  getAuditRecords: synthetic.fetchAuditRecords,
  getProviderStatus: synthetic.fetchProviderStatus,
  getDataTrust: synthetic.fetchDataTrust,
};

export const SCENARIO_PRESETS: ScenarioDefinition[] = [
  {
    id: "scenario_paycheck_reduction",
    label: "Paycheck reduction",
    kind: "preset",
    paycheck_delta_cents: -38000,
    description: "Sarah's expected paycheck changes from $2,100.00 to $1,720.00.",
  },
  {
    id: "scenario_paycheck_delay",
    label: "Paycheck delay",
    kind: "preset",
    paycheck_delta_cents: 0,
    description: "The next paycheck arrives 3 days later than scheduled.",
  },
  {
    id: "scenario_medical",
    label: "Unexpected medical expense",
    kind: "preset",
    paycheck_delta_cents: 0,
    description: "A $220.00 out-of-pocket medical charge posts unexpectedly.",
  },
  {
    id: "scenario_vehicle_repair",
    label: "Vehicle repair",
    kind: "preset",
    paycheck_delta_cents: 0,
    description: "A $450.00 vehicle repair is needed this week.",
  },
  {
    id: "scenario_rent_increase",
    label: "Rent increase",
    kind: "preset",
    paycheck_delta_cents: 0,
    description: "Rent increases from $1,450.00 to $1,550.00 next cycle.",
  },
  {
    id: "scenario_duplicate_charge",
    label: "Duplicate charge",
    kind: "preset",
    paycheck_delta_cents: 0,
    description: "A $75.00 card payment posts twice due to a merchant error.",
  },
  {
    id: "scenario_subscription_increase",
    label: "Subscription increase",
    kind: "preset",
    paycheck_delta_cents: 0,
    description: "StreamCo Plus increases from $15.99 to $22.99.",
  },
  {
    id: "scenario_income_loss",
    label: "Temporary income loss",
    kind: "preset",
    paycheck_delta_cents: -210000,
    description: "One full paycheck is missed entirely.",
  },
];
