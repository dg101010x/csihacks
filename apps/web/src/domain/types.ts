import type { FinancialEventV1, ObligationV1 } from "@relief/contracts";
import type {
  ConstitutionRuleV1,
  InterventionActionV1,
  ProviderStatusV1,
  DataTrustV1,
} from "@relief/test-fixtures";

/**
 * Domain / adapter layer. No page or component may reach past this file
 * into MSW, fixture JSON, or raw @relief/contracts shapes directly — every
 * screen reads through `reliefClient` (client.ts) and gets one of these
 * types back. When Plan One ships live services, only synthetic-adapter.ts
 * needs a live counterpart; nothing here or in any component changes.
 *
 * Every model-generated object carries a `ModelEvidence` block — the
 * identifier/timestamp/version/confidence/sources/freshness/status fields
 * the redesign brief requires everywhere a score, risk, or recommendation
 * appears, so uncertainty and provenance are never silently dropped.
 */
export interface ModelEvidence {
  model_version: string | null;
  confidence: number;
  generated_at: string;
  source_refs: string[];
  freshness: "current" | "stale" | "unavailable";
  status: "simulated" | "live";
}

export type FinancialEvent = FinancialEventV1;
export type Obligation = ObligationV1;

export interface ForecastPoint {
  date: string;
  median_balance_cents: number;
  lower_balance_cents: number;
  upper_balance_cents: number;
  reserve_violation_probability: number;
  events: FinancialEvent[];
  is_risk: boolean;
}

export interface ForecastEnvelope {
  id: string;
  provider: "mock" | "deterministic" | "relieffm";
  horizon_days: number;
  reserve_cents: number;
  points: ForecastPoint[];
  distress_probabilities: {
    negative_balance: number;
    essential_reserve_violation: number;
    missed_obligation: number;
  };
  reason_factors: { factor: string; weight: number; description: string }[];
  valid_until: string;
  evidence: ModelEvidence;
}

export interface RiskWindow {
  id: string;
  start_date: string;
  end_date: string;
  kind: "essential_reserve_violation" | "negative_balance" | "missed_obligation";
  probability: number;
  projected_lowest_balance_cents: number;
  causal_obligation_ids: string[];
  description: string;
  evidence: ModelEvidence;
}

export interface ScenarioDefinition {
  id: string;
  label: string;
  kind: "baseline" | "preset" | "custom";
  paycheck_delta_cents: number;
  description: string;
}

export interface ScenarioDelta {
  lowest_balance_delta_cents: number;
  days_below_reserve_delta: number;
  missed_obligation_probability_delta: number;
  negative_balance_probability_delta: number;
  added_intervention_cost_cents: number;
  recovery_date: string | null;
}

export interface ScenarioResult {
  scenario: ScenarioDefinition;
  baseline: ForecastEnvelope;
  active: ForecastEnvelope;
  deltas: ScenarioDelta;
  riskWindows: RiskWindow[];
}

export type InterventionActionStage =
  | "review"
  | "confirmed"
  | "submitted"
  | "pending_provider"
  | "accepted"
  | "rejected"
  | "executed";

export interface InterventionPackage {
  id: string;
  label: string;
  description: string;
  actions: InterventionActionV1[];
  added_cost_cents: number;
  new_minimum_balance_cents: number;
  remaining_risk: { negative_balance: boolean; essential_reserve_violation: boolean };
  required_approvals: string[];
  user_effort: "low" | "medium" | "high";
  provider_acceptance_probability: number | null;
  reversibility: "fully_reversible" | "partially_reversible" | "irreversible";
  constitution_compatible: boolean;
  ranking_reason: string;
  stage: InterventionActionStage;
  evidence: ModelEvidence;
}

export type ConstitutionRule = ConstitutionRuleV1;

export interface ConstitutionSimulationResult {
  rule: ConstitutionRule;
  allowed_package_ids: string[];
  blocked_package_ids: string[];
  conflicts: { with_rule_id: string; description: string }[];
}

export interface ProviderAction {
  id: string;
  provider_id: string;
  provider_display_name: string;
  action_type: string;
  status: "pending_review" | "approved" | "rejected" | "information_requested";
  consumer_impact_summary: string;
  provider_impact_summary: string;
  policy_reference: {
    document_id: string;
    passage_id: string;
    effective_date: string;
    confidence: number;
    is_simulated: boolean;
  } | null;
}

export type ProviderStatus = ProviderStatusV1;
export type DataTrust = DataTrustV1;

export interface AuditRecord {
  id: string;
  decision_id: string;
  event_type: string;
  actor_type: "consumer" | "provider" | "system";
  actor_id: string;
  request_id: string;
  occurred_at: string;
  summary: string;
  reason: string;
  evidence: string[];
  before_state: string | null;
  after_state: string | null;
  related_model_version: string | null;
  related_data_sources: string[];
  related_constitution_rule_id: string | null;
}
