import { z } from "zod";
import { ContractVersion } from "./shared";
import { HouseholdSnapshotV1 } from "./household_snapshot";

export const RequestedForecastOutput = z.enum([
  "daily_balance_trajectories",
  "distress_probabilities",
  "income_distribution",
  "variable_spending_distribution",
]);
export type RequestedForecastOutput = z.infer<typeof RequestedForecastOutput>;

/**
 * ForecastRequestV1 (Section 11)
 *
 * Owner: Plan Two
 * Version: 1.0.0
 * Purpose: request sent to any forecast provider (mock, deterministic, or
 *   relieffm) behind the shared `services/model_gateway` interface. All
 *   providers accept the same request shape and return `ForecastResponseV1`.
 *
 * Required: contract_version, request_id, snapshot, horizon_days,
 *   scenario_count, requested_outputs.
 * Optional: none at 1.0.0.
 *
 * Validation rules:
 *   - horizon_days must be positive.
 *   - scenario_count must be positive; a provider may return fewer scenarios
 *     but must explain the reduction (Integration Gate Two, Section 102).
 *
 * Migration notes: none yet (first version).
 */
export const ForecastRequestV1 = z.object({
  contract_version: ContractVersion,
  request_id: z.string(),
  snapshot: HouseholdSnapshotV1,
  horizon_days: z.number().int().positive(),
  scenario_count: z.number().int().positive(),
  requested_outputs: z.array(RequestedForecastOutput),
});
export type ForecastRequestV1 = z.infer<typeof ForecastRequestV1>;
