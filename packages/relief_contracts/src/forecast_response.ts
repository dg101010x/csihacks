import { z } from "zod";
import { ContractVersion } from "./shared";
import { DailySummaryEntryV1, TrajectoryPointV1, ReasonFactorV1 } from "./shared";

export const ForecastProviderName = z.enum(["mock", "deterministic", "relieffm"]);
export type ForecastProviderName = z.infer<typeof ForecastProviderName>;

/**
 * ModelMetadataV1 — populated only by the relieffm provider (Section 12).
 * The deterministic provider always sets `model_metadata: null`.
 */
export const ModelMetadataV1 = z.object({
  model_version: z.string(),
  calibration_version: z.string().nullable(),
  inference_latency_ms: z.number().nonnegative(),
});
export type ModelMetadataV1 = z.infer<typeof ModelMetadataV1>;

/**
 * ForecastResponseV1 (Section 12)
 *
 * Owner: Plan One + Plan Two (jointly)
 * Version: 1.0.0
 * Purpose: the single response shape returned by every forecast provider.
 *   No page, table, optimizer, or workflow may know which provider produced
 *   a given response — `provider` and `model_metadata` are the only signals,
 *   and both are optional to read.
 *
 * Required: contract_version, request_id, forecast_id, provider,
 *   provider_version, generated_at, valid_until, confidence, is_stale,
 *   warnings, daily_summary, trajectories, distress_probabilities,
 *   reason_factors, model_metadata (nullable — required key, nullable value).
 * Optional: none at 1.0.0.
 *
 * Validation rules:
 *   - confidence is 0..1.
 *   - model_metadata must be null for provider != "relieffm".
 *   - Every trajectory must reconcile: starting_balance_cents + inflow_cents
 *     - outflow_cents == ending_balance_cents (Section 45, Pass Ten).
 *
 * Migration notes: none yet (first version).
 */
export const ForecastResponseV1 = z
  .object({
    contract_version: ContractVersion,
    request_id: z.string(),
    forecast_id: z.string(),
    provider: ForecastProviderName,
    provider_version: z.string(),
    generated_at: z.string().datetime({ offset: true }),
    valid_until: z.string().datetime({ offset: true }),
    confidence: z.number().min(0).max(1),
    is_stale: z.boolean(),
    warnings: z.array(z.string()),
    daily_summary: z.array(DailySummaryEntryV1),
    trajectories: z.array(TrajectoryPointV1),
    distress_probabilities: z.object({
      negative_balance: z.number().min(0).max(1),
      essential_reserve_violation: z.number().min(0).max(1),
      missed_obligation: z.number().min(0).max(1),
    }),
    reason_factors: z.array(ReasonFactorV1),
    model_metadata: ModelMetadataV1.nullable(),
  })
  .refine((val) => val.provider === "relieffm" || val.model_metadata === null, {
    message: "model_metadata must be null unless provider is relieffm",
    path: ["model_metadata"],
  });
export type ForecastResponseV1 = z.infer<typeof ForecastResponseV1>;
