import { z } from "zod";

/**
 * Plan-Two-owned product shapes used by the Sarah fixtures and MSW handlers.
 * These are NOT part of @relief/contracts — per Section 4, that package
 * covers only the shared Plan One / Plan Two boundary (forecasting).
 * Resilience scores, intervention packages, approvals, and audit records
 * are internal Plan Two API shapes (Sections 22, 60-61, 64, 85) and belong
 * here instead.
 */

export const ResilienceComponentV1 = z.object({
  key: z.string(),
  label: z.string(),
  weight: z.number().min(0).max(1),
  score: z.number().min(0).max(100),
  confidence: z.number().min(0).max(1),
});

export const ResilienceScoreV1 = z.object({
  version: z.string(),
  overall: z.number().min(0).max(100),
  confidence: z.number().min(0).max(1),
  trend: z.enum(["improving", "stable", "declining"]),
  components: z.array(ResilienceComponentV1),
  primary_weakness: z.string().nullable(),
  primary_stabilizing_factor: z.string().nullable(),
  data_freshness: z.enum(["current", "stale", "unavailable"]),
  disclosure: z.string(),
});
export type ResilienceScoreV1 = z.infer<typeof ResilienceScoreV1>;

export const ExecutionMode = z.enum([
  "recommendation_only",
  "draft_only",
  "simulated",
  "consumer_executable",
  "provider_executable",
]);

export const InterventionActionV1 = z.object({
  action_id: z.string(),
  action_type: z.string(),
  obligation_id: z.string(),
  display_name: z.string(),
  parameters: z.record(z.unknown()),
  execution_mode: ExecutionMode,
  provider_capability_id: z.string().nullable(),
  consumer_status: z.enum(["pending", "approved", "rejected"]),
  provider_status: z.enum(["pending", "approved", "rejected", "not_required"]),
});

export const InterventionCandidateV1 = z.object({
  package_id: z.string(),
  label: z.string(),
  description: z.string(),
  actions: z.array(InterventionActionV1),
  added_cost_cents: z.number().int(),
  new_minimum_balance_cents: z.number().int(),
  remaining_risk: z.object({
    negative_balance: z.boolean(),
    essential_reserve_violation: z.boolean(),
  }),
  required_approvals: z.array(z.string()),
  user_effort: z.enum(["low", "medium", "high"]),
  provider_acceptance_probability: z.number().min(0).max(1).nullable(),
  reversibility: z.enum(["fully_reversible", "partially_reversible", "irreversible"]),
  constitution_compatible: z.boolean(),
  confidence: z.number().min(0).max(1),
  ranking_reason: z.string(),
});
export type InterventionCandidateV1 = z.infer<typeof InterventionCandidateV1>;

export const ConsumerApprovalV1 = z.object({
  status: z.enum(["pending", "approved", "rejected"]),
  approved_at: z.string().datetime({ offset: true }).nullable(),
  approved_action_ids: z.array(z.string()),
  request_id: z.string(),
});

export const ProviderApprovalV1 = z.object({
  status: z.enum(["pending", "approved", "rejected"]),
  approved_at: z.string().datetime({ offset: true }).nullable(),
  approved_by: z.string().nullable(),
  request_id: z.string(),
});

export const ProviderCaseV1 = z.object({
  case_id: z.string(),
  provider_id: z.string(),
  action_id: z.string(),
  status: z.enum(["pending_review", "approved", "rejected", "information_requested"]),
  consumer_impact_summary: z.string(),
  provider_impact_summary: z.string(),
  policy_reference: z.object({
    document_id: z.string(),
    passage_id: z.string(),
    effective_date: z.string(),
    confidence: z.number().min(0).max(1),
    is_simulated: z.boolean(),
  }),
});
export type ProviderCaseV1 = z.infer<typeof ProviderCaseV1>;

/** Mirrors the audit_events table (Section 32.12) — append only. */
export const AuditEventV1 = z.object({
  event_id: z.string(),
  decision_id: z.string(),
  event_type: z.string(),
  actor_type: z.enum(["consumer", "provider", "system"]),
  actor_id: z.string(),
  request_id: z.string(),
  occurred_at: z.string().datetime({ offset: true }),
  payload_hash: z.string(),
  summary: z.string(),
  reason: z.string(),
  evidence: z.array(z.string()),
  before_state: z.string().nullable(),
  after_state: z.string().nullable(),
  related_model_version: z.string().nullable(),
  related_data_sources: z.array(z.string()),
  related_constitution_rule_id: z.string().nullable(),
});
export type AuditEventV1 = z.infer<typeof AuditEventV1>;

/**
 * ConstitutionRuleV1 (Section 71's structured interpretation, extended per
 * the redesign brief's Constitution page: trigger, scope, permitted/
 * prohibited actions, approval requirement, monetary cap, expiration,
 * priority, exceptions, confidence).
 */
export const ConstitutionRuleV1 = z.object({
  rule_id: z.string(),
  status: z.enum(["draft", "active"]),
  raw_text: z.string(),
  trigger: z.string(),
  scope: z.array(z.string()),
  permitted_actions: z.array(z.string()),
  prohibited_actions: z.array(z.string()),
  approval_requirement: z.enum(["none", "consumer_confirmation", "always_ask"]),
  maximum_monetary_impact_cents: z.number().int().nullable(),
  expiration: z.string().nullable(),
  priority: z.number().int(),
  exceptions: z.array(z.string()),
  confidence: z.number().min(0).max(1),
  created_at: z.string().datetime({ offset: true }),
});
export type ConstitutionRuleV1 = z.infer<typeof ConstitutionRuleV1>;

/** Section 76 integration status + Section 72 adapter capabilities. */
export const ProviderStatusV1 = z.object({
  provider_id: z.string(),
  display_name: z.string(),
  connection_status: z.enum(["connected", "degraded", "disconnected"]),
  accounts_available: z.number().int(),
  last_synced_at: z.string().datetime({ offset: true }),
  supported_actions: z.array(z.string()),
  unsupported_actions: z.array(z.string()),
  approval_requirements: z.string(),
  expected_response_time: z.string(),
  pending_requests: z.number().int(),
  is_simulated: z.boolean(),
});
export type ProviderStatusV1 = z.infer<typeof ProviderStatusV1>;

/** Section 26/76 freshness + Section 96 model trust, surfaced for the consumer. */
export const DataTrustV1 = z.object({
  source: z.string(),
  last_refresh_at: z.string().datetime({ offset: true }),
  coverage_start: z.string(),
  coverage_end: z.string(),
  missing_data_notes: z.array(z.string()),
  stale: z.boolean(),
  duplicate_events_detected: z.number().int(),
  event_classification_confidence: z.number().min(0).max(1),
  forecast_provider: z.string(),
  forecast_provider_version: z.string(),
  relieffm_version: z.string().nullable(),
  calibration_summary: z.string().nullable(),
  known_limitations: z.array(z.string()),
});
export type DataTrustV1 = z.infer<typeof DataTrustV1>;
