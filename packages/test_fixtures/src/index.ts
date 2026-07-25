export * from "./types";

import sarahBaselineJson from "../fixtures/sarah_baseline.json";
import sarahIncomeShockJson from "../fixtures/sarah_income_shock.json";
import sarahInterventionOptionsJson from "../fixtures/sarah_intervention_options.json";
import sarahProviderApprovalJson from "../fixtures/sarah_provider_approval.json";
import sarahCompletedCaseJson from "../fixtures/sarah_completed_case.json";

/**
 * The Sarah persona fixtures (Section 24). Each one is a realistic,
 * internally consistent slice of the consumer journey (Section 16.1) built
 * around household hh_01 / account acct_01 — the same IDs used in
 * @relief/contracts' own example fixtures, so the story traces back to the
 * spec's own JSON examples (Sections 9-13).
 */
export const sarahBaseline = sarahBaselineJson;
export const sarahIncomeShock = sarahIncomeShockJson;
export const sarahInterventionOptions = sarahInterventionOptionsJson;
export const sarahProviderApproval = sarahProviderApprovalJson;
export const sarahCompletedCase = sarahCompletedCaseJson;
