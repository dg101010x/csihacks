import { z } from "zod";
import { ContractVersion, Currency, MoneyCents } from "./shared";

/**
 * FinancialEventV1 (Section 9)
 *
 * Owner: Plan Two
 * Version: 1.0.0
 * Purpose: one immutable, source-attributed financial event in the ledger.
 *
 * Required: contract_version, event_id, household_id, account_id, source,
 *   source_event_id, event_type, event_status, occurred_at, effective_at,
 *   amount_cents, currency, direction, is_recurring, is_pending, metadata.
 * Optional: merchant_name, merchant_category, obligation_id (all nullable —
 *   not every event is merchant-attributed or obligation-linked).
 *
 * Validation rules:
 *   - amount_cents is always a non-negative integer; direction carries the sign.
 *   - (source, source_event_id, account_id) must be unique (Section 32.5) —
 *     enforced at the database layer, not by this schema.
 *   - Money must never be represented as a float, in any language binding.
 *
 * Migration notes: none yet (first version).
 */
export const FinancialEventV1 = z.object({
  contract_version: ContractVersion,
  event_id: z.string(),
  household_id: z.string(),
  account_id: z.string(),
  source: z.string(),
  source_event_id: z.string(),
  event_type: z.string(),
  event_status: z.enum(["scheduled", "pending", "posted", "cancelled", "corrected"]),
  occurred_at: z.string().datetime({ offset: true }),
  effective_at: z.string().datetime({ offset: true }),
  amount_cents: MoneyCents.nonnegative(),
  currency: Currency,
  direction: z.enum(["inflow", "outflow"]),
  merchant_name: z.string().nullable(),
  merchant_category: z.string().nullable(),
  obligation_id: z.string().nullable(),
  is_recurring: z.boolean(),
  is_pending: z.boolean(),
  metadata: z.record(z.unknown()),
});
export type FinancialEventV1 = z.infer<typeof FinancialEventV1>;
