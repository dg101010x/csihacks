import { z } from "zod";
import { ContractVersion } from "./shared";

/**
 * InterventionActionInputV1 — one candidate action inside a simulation request.
 * `parameters` is intentionally an open record: each action_type defines its
 * own parameter shape (Section 56 action library), validated by the
 * interventions module rather than by this transport-level contract.
 */
export const InterventionActionInputV1 = z.object({
  action_type: z.string(),
  obligation_id: z.string(),
  parameters: z.record(z.unknown()),
});
export type InterventionActionInputV1 = z.infer<typeof InterventionActionInputV1>;

/**
 * InterventionSimulationRequestV1 (Section 13)
 *
 * Owner: Plan Two
 * Version: 1.0.0
 * Purpose: request to simulate a candidate intervention package against a
 *   base forecast, cloning the household snapshot and re-forecasting
 *   (Section 61).
 *
 * Required: contract_version, simulation_id, base_forecast_id,
 *   household_snapshot_id, interventions (at least one).
 * Optional: none at 1.0.0.
 *
 * Migration notes: none yet (first version).
 */
export const InterventionSimulationRequestV1 = z.object({
  contract_version: ContractVersion,
  simulation_id: z.string(),
  base_forecast_id: z.string(),
  household_snapshot_id: z.string(),
  interventions: z.array(InterventionActionInputV1).min(1),
});
export type InterventionSimulationRequestV1 = z.infer<typeof InterventionSimulationRequestV1>;
