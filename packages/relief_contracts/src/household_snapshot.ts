import { z } from "zod";
import { ContractVersion, Currency, AccountV1, ObligationV1, ProviderCapabilityV1, ConsumerConstitutionV1 } from "./shared";
import { FinancialEventV1 } from "./financial_event";

/**
 * HouseholdSnapshotV1 (Section 10)
 *
 * Owner: Plan Two
 * Version: 1.0.0
 * Purpose: the complete, self-contained input to every forecast provider. The
 *   model team must never query Plan Two's production database directly —
 *   Plan Two constructs and validates this snapshot instead.
 *
 * Required: all fields below (arrays may be empty, consumer_constitution may
 *   be an empty/default object if the consumer has not yet configured rules).
 * Optional: none at 1.0.0.
 *
 * Migration notes: none yet (first version).
 */
export const HouseholdSnapshotV1 = z.object({
  contract_version: ContractVersion,
  snapshot_id: z.string(),
  household_id: z.string(),
  generated_at: z.string().datetime({ offset: true }),
  timezone: z.string(),
  currency: Currency,
  accounts: z.array(AccountV1),
  obligations: z.array(ObligationV1),
  recent_events: z.array(FinancialEventV1),
  known_future_events: z.array(FinancialEventV1),
  consumer_constitution: ConsumerConstitutionV1,
  provider_capabilities: z.array(ProviderCapabilityV1),
});
export type HouseholdSnapshotV1 = z.infer<typeof HouseholdSnapshotV1>;
