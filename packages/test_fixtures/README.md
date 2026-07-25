# @relief/test-fixtures

Sarah persona fixtures (Section 24) and Mock Service Worker handlers. Lets
front end development proceed without waiting for the real backend
(Section 7, item 5).

## Fixtures

All built around household `hh_01` / account `acct_01` — the same IDs used in
`@relief/contracts`' own example JSON (Sections 9-13), so the story traces
straight back to the spec:

- `sarah_baseline.json` — healthy state: $2,480.00 balance, Resilience Score 82,
  no distress.
- `sarah_income_shock.json` — the Section 16.3 shock simulator: the most recent
  paycheck is retroactively reduced by exactly $380.00 ($2,100.00 →
  $1,720.00), which collides with rent ($1,450.00) and the auto loan
  ($240.00) both due the same day, dropping the Resilience Score to 54 and
  projecting an essential reserve violation.
- `sarah_intervention_options.json` — three candidate packages (Section 60:
  recommended / lowest added cost / lowest provider modification), plus the
  raw `InterventionSimulationRequestV1` for the recommended package.
- `sarah_provider_approval.json` — state right after consumer approval, case
  awaiting provider review.
- `sarah_completed_case.json` — provider-approved, executed (simulated), full
  10-event audit trail (Section 85), and the recovered Resilience Score (79).

`household_snapshot`, `forecast`, and `simulation_request` slices validate
against `@relief/contracts`; the resilience score / intervention / approval /
audit shapes validate against this package's own Zod types in `src/types.ts`
(Plan-Two-owned product shapes — outside `@relief/contracts`' scope per
Section 4). See `tests/fixtures.test.ts`, including a trajectory
reconciliation check (Pass Ten, Section 45).

## MSW handlers

`msw/handlers.ts` implements the Section 24 list (accounts, transactions,
forecasts, interventions, approvals, audit data, provider policies,
integration status) as an in-memory state machine over the fixtures above:
`POST /v1/forecasts` triggers the shock, `POST /v1/interventions/:id/approve`
then `POST /v1/provider/cases/:id/approve` walk the case to completion.

- `msw/browser.ts` — `setupWorker` for `apps/web`.
- `msw/node.ts` — `setupServer` for Vitest/Playwright.

Every response uses the Section 30 API envelope (`request_id`, `data`,
`errors`, `warnings`, `metadata.contract_version`).
