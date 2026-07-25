import { z } from "zod";

/**
 * Money is always integer cents on the wire (Section 9). Never floating point.
 */
export const MoneyCents = z.number().int();

export const ContractVersion = z
  .string()
  .regex(/^\d+\.\d+\.\d+$/, "contract_version must be a semantic version, e.g. 1.0.0");

export const Currency = z.string().length(3);

/**
 * AccountV1 — embedded in HouseholdSnapshotV1.accounts.
 * Not one of the five core contracts from Part One, but required to give
 * `accounts: []` a concrete shape. Mirrors the `accounts` table (Section 32.4).
 */
export const AccountV1 = z.object({
  account_id: z.string(),
  provider: z.string(),
  account_type: z.string(),
  account_subtype: z.string().nullable(),
  display_name: z.string(),
  current_balance_cents: MoneyCents,
  available_balance_cents: MoneyCents.nullable(),
  balance_updated_at: z.string().datetime({ offset: true }),
  data_status: z.enum(["current", "stale", "unavailable"]),
  is_simulated: z.boolean(),
});
export type AccountV1 = z.infer<typeof AccountV1>;

/**
 * ObligationV1 — embedded in HouseholdSnapshotV1.obligations.
 * Mirrors the `obligations` table (Section 32.6) and the obligation model (Section 36).
 */
export const ObligationV1 = z.object({
  obligation_id: z.string(),
  provider_id: z.string().nullable(),
  obligation_type: z.string(),
  display_name: z.string(),
  principal_balance_cents: MoneyCents.nullable(),
  scheduled_amount_cents: MoneyCents,
  next_due_at: z.string().datetime({ offset: true }).nullable(),
  recurrence_rule: z.string().nullable(),
  essentiality_score: z.number().min(0).max(1),
  status: z.enum(["active", "paused", "closed"]),
  source_confidence: z.number().min(0).max(1),
  consumer_confirmed: z.boolean(),
});
export type ObligationV1 = z.infer<typeof ObligationV1>;

/**
 * ProviderCapabilityV1 — embedded in HouseholdSnapshotV1.provider_capabilities.
 * Mirrors the `provider_capabilities` table (Section 32.7). Evidence hierarchy is
 * defined in Section 52; `is_simulated` must be surfaced wherever this is displayed.
 */
export const ProviderCapabilityV1 = z.object({
  provider_id: z.string(),
  product_type: z.string(),
  action_type: z.string(),
  eligibility_rule: z.string().nullable(),
  cost_rule: z.string().nullable(),
  timing_rule: z.string().nullable(),
  evidence_source: z.enum([
    "provider_structured_policy",
    "provider_published_policy_document",
    "confirmed_product_contract",
    "consumer_supplied_contract_information",
    "simulated_demonstration_policy",
    "unknown",
  ]),
  effective_from: z.string().datetime({ offset: true }).nullable(),
  effective_until: z.string().datetime({ offset: true }).nullable(),
  is_simulated: z.boolean(),
});
export type ProviderCapabilityV1 = z.infer<typeof ProviderCapabilityV1>;

/**
 * ConsumerConstitutionV1 — the structured, consumer-confirmed rule set (Section 71).
 * The parsed result never becomes active without explicit consumer confirmation;
 * this contract represents the *confirmed* state embedded in a snapshot.
 */
export const ConsumerConstitutionV1 = z.object({
  version: z.number().int().nonnegative(),
  protected_categories: z.array(z.string()),
  allow_term_extension: z.boolean(),
  maximum_added_interest_cents: MoneyCents,
  require_confirmation_for_subscriptions: z.boolean(),
});
export type ConsumerConstitutionV1 = z.infer<typeof ConsumerConstitutionV1>;

/**
 * DailySummaryEntryV1 — one day of ForecastResponseV1.daily_summary.
 * Aggregated across scenarios (median/lower/upper), distinct from a single
 * scenario's per-day row in `trajectories` (forecast_trajectories, Section 32.9).
 */
export const DailySummaryEntryV1 = z.object({
  event_date: z.string().date(),
  median_ending_balance_cents: MoneyCents,
  lower_ending_balance_cents: MoneyCents,
  upper_ending_balance_cents: MoneyCents,
  reserve_violation_probability: z.number().min(0).max(1),
});
export type DailySummaryEntryV1 = z.infer<typeof DailySummaryEntryV1>;

/**
 * TrajectoryPointV1 — one scenario's per-day row, mirrors forecast_trajectories
 * (Section 32.9).
 */
export const TrajectoryPointV1 = z.object({
  scenario_index: z.number().int().nonnegative(),
  event_date: z.string().date(),
  starting_balance_cents: MoneyCents,
  inflow_cents: MoneyCents,
  outflow_cents: MoneyCents,
  ending_balance_cents: MoneyCents,
  essential_reserve_cents: MoneyCents,
});
export type TrajectoryPointV1 = z.infer<typeof TrajectoryPointV1>;

/**
 * ReasonFactorV1 — a single structured contributor to distress, consumed by the
 * explanation layer (Section 67 `primary_factors`) without ever being invented
 * by the language model.
 */
export const ReasonFactorV1 = z.object({
  factor: z.string(),
  weight: z.number().min(0).max(1),
  description: z.string(),
});
export type ReasonFactorV1 = z.infer<typeof ReasonFactorV1>;
