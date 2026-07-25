# UI architecture — Command Center redesign

## Information architecture

Eight routes, replacing the previous 13-route flat list:

| Nav label | Route | Replaces |
|---|---|---|
| Command Center | `/` | `/dashboard`, `/demo` (merged) |
| Timeline | `/timeline` | `/timeline` (rebuilt) |
| Scenario Lab | `/scenario-lab` | `/demo`'s shock control |
| Interventions | `/interventions`, `/interventions/[id]` | same paths, real content |
| Constitution | `/constitution` | same path, real content |
| Audit | `/audit`, `/audit/[id]` | adds a missing index page |
| Providers | `/providers` | `/provider*` (renamed) |
| Data | `/data` | new |

`/onboarding` and `/settings*` are dropped from primary nav — not part of
the brief's IA and not part of the demo narrative. Old paths (`/demo`,
`/dashboard`, `/provider`, `/provider/cases/[id]`) redirect to their new
homes so no link 404s.

## Domain / adapter layer (`src/domain/`)

One typed boundary between the UI and data, so no page ever imports MSW or
fixture JSON directly and no forecast/scenario logic lives inside a
component. Types: `ForecastEnvelope`, `ForecastPoint`, `FinancialEvent`,
`RiskWindow`, `ScenarioDefinition`, `ScenarioResult`, `InterventionPackage`,
`ConstitutionRule`, `ProviderAction`, `AuditRecord`, `ModelEvidence`. Every
model-generated object carries `id`, `generated_at`, `model_version`,
`confidence`, `source_refs`, `freshness`, `status` — the "model trust"
fields the brief requires everywhere.

`src/domain/client.ts` exports one `reliefClient` with methods
(`getForecastEnvelope`, `getRiskWindows`, `getInterventionPackages`,
`applyScenario`, `resetScenario`, `getConstitutionRules`, `getAuditRecords`,
`getProviderStatus`, `getDataTrust`). Today every method is backed by the
synthetic adapter (`src/domain/synthetic-adapter.ts`), which wraps the
existing `@relief/test-fixtures` MSW handlers and `@relief/contracts`
parsing already built in Phase B. When Plan One ships live endpoints, only
`synthetic-adapter.ts` needs a live counterpart registered in
`client.ts` — no page or component changes.

All pages read through `reliefClient` via TanStack Query hooks in
`src/domain/hooks.ts`, all keyed off one shared query key
(`["relief-scenario"]`) so applying a scenario in Scenario Lab invalidates
every dependent screen at once — this is what makes "one scenario updates
the entire application" true rather than aspirational.

## Shell (`src/components/shell/`)

- `NavRail` — compact 8-item rail, active state via `usePathname`, collapses
  to a drawer under 1024px.
- `EnvironmentIndicator` — persistent "Synthetic Wells Fargo" + system
  status (current/delayed/degraded), sourced from `reliefClient.getProviderStatus()`.
- `GlobalTimestamp` — forecast `generated_at`, shared across the shell so
  every page agrees on freshness.
- `ScenarioBadge` — appears in the shell only when a scenario is active,
  clears on reset.
- `CommandPalette` — `Cmd/Ctrl+K`, navigates the 8 routes + fires demo
  reset; kept intentionally small (nav + one action) rather than a full
  fuzzy-everything palette, given the size of the rest of this brief.
- `NotificationCenter` — surfaces the current risk window and any pending
  provider action as dismissible items; not a persistence layer, reflects
  live query state.
- `UserMenu` — adds a real "Reset demo" action wired to
  `reliefClient.resetScenario()`.

## Chart

`ForecastChart` replaces `CashFlowTimeline` as the shared primitive: daily
points (not just 3), income/obligation markers on the axis, a shaded risk
window region, click-to-open detail panel, 7/14/30 day toggle preserved,
table alternative preserved and extended with event type/classification
columns.

## Reused unchanged

`@relief/design-system` tokens and Phase A primitives, `@relief/contracts`,
`@relief/test-fixtures`' underlying Sarah numbers (only the shock-trigger
plumbing moves from a page-local mutation to `reliefClient.applyScenario`).
