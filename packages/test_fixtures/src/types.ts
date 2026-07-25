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
  actions: z.array(InterventionActionV1),
  added_cost_cents: z.number().int(),
  new_minimum_balance_cents: z.number().int(),
  remaining_risk: z.object({
    negative_balance: z.boolean(),
    essential_reserve_violation: z.boolean(),
  }),
  required_approvals: z.array(z.string()),
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
});
export type AuditEventV1 = z.infer<typeof AuditEventV1>;
