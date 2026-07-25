import type { FinancialEventV1, ObligationV1 } from "@relief/contracts";
import type { ForecastEnvelope } from "@/domain/types";

export type { ForecastEnvelope };

/** Derived from HouseholdSnapshotV1 once per page load — avoids every card re-deriving "next income" independently. */
export interface HouseholdSnapshotSummary {
  currentBalanceCents: number;
  nextIncome: FinancialEventV1 | null;
  nextObligation: ObligationV1 | null;
}
