# UI audit — Relief front end (pre-redesign baseline)

Snapshot as of the Phase B commit (`e1498f1`), before the Command Center /
Scenario Lab redesign. Written against the ten review lenses in the redesign
brief.

## Empty pages / dead interactions

Nine of thirteen routes render nothing but `RouteStub` — a placeholder that
literally prints internal planning language to the end user (see below):

- `/interventions`, `/interventions/[id]`
- `/constitution`
- `/audit/[decision_id]` — and there is no `/audit` index at all; the only
  audit route requires an ID nobody has been given yet
- `/provider`, `/provider/cases/[id]`
- `/settings`, `/settings/integrations`
- `/onboarding`

None of these have a real state — no data, no interaction, no next action.
A judge clicking any nav item other than Demo/Dashboard/Timeline hits a dead
end.

## Internal specification language leaking into the UI

`RouteStub` renders a `phase` prop directly in the page: strings like
`"Route: /interventions — all current interventions (Section 17, Phase C)"`
are visible, monospaced, at the top of every stub page. This is developer
scaffolding text, not product copy — it must not ship. (Section numbers also
appear throughout code comments, which is fine; the problem is only that one
component prints them to the DOM.)

## Component/data-source duplication

`/demo` and `/dashboard` currently show almost the same cards (Balance,
Resilience Score, obligations, risk summary) built from the same hooks
(`useHouseholdSnapshot`, `useResilienceScore`, `useForecast`), but as two
separate pages with separately duplicated JSX layout. There is no single
"Command Center" — the safety-summary-first framing the brief wants doesn't
exist; instead there are two dashboard-shaped pages competing for the same
role.

## Chart quality

`CashFlowTimeline` (used by both `/demo` and `/timeline`) plots only the
three `daily_summary` points present in the fixtures (start, collision day,
next payday) as a single median line with a lower/upper band. It has no
income/obligation event markers on the axis, no click-to-inspect, no risk
window highlighting, and no clustering — exactly the "generic three-point
line chart" the brief calls unacceptable. The reserve line and table
alternative are solid and worth keeping.

## Information hierarchy

The Resilience Score currently gets equal visual weight to Balance and Data
Freshness (three same-size cards in a row) — there's no single dominant
"is Sarah safe" statement, and the forecast trajectory chart is visually
subordinate to the card row above it despite being the more important
object. Nothing states a plain-English safety summary
("Protected through July 30" / "Reserve risk begins in 2 days").

## Navigation and shell

Current nav rail (`PrimaryNavigation`) has 7 flat links (Demo, Dashboard,
Timeline, Interventions, Constitution, Audit, Provider) with no environment
indicator beyond the per-page `EnvironmentBadge`, no system status, no
global forecast timestamp, no command palette, no notification center, and
no demo-reset affordance in the shell itself (reset only exists as a button
on `/demo`). `UserMenu` is a static initial with no menu.

## Hardcoded / weak states

- Loading state is a single generic spinner + label everywhere
  (`LoadingState`) — no skeletons matching the eventual layout.
- No error state has ever been exercised — `apiGet`/`apiPost` throw
  `ApiError`, but no page catches or renders it.
- No mobile/responsive behavior has been tested at any breakpoint; the shell
  is a fixed 224px sidebar + flex content with no drawer fallback.

## Accessibility

Existing work here is a real strength and should be preserved: `StatusBadge`
enforces text+icon (never color-only), the timeline has a genuine `<table>`
alternative, buttons are keyboard operable (tested), and reduced-motion is
respected in charts and skeletons. The gap is that none of the *new* pages
required by this redesign have been built yet, so this bar needs to be held
across Command Center, Scenario Lab, Interventions, Constitution, Audit,
Providers, and Data too.

## What to keep vs. replace

**Keep and extend:** `@relief/design-system` tokens/components, the MSW +
`@relief/contracts` data layer, `CashFlowTimeline`'s reserve line and table
alternative, `StatusBadge`'s text+icon discipline, the Sarah fixture
narrative and its exact numbers.

**Replace:** the flat 7-item nav → 8-item IA below, `/demo` +
`/dashboard` → single Command Center, `RouteStub` and everything it
renders, the 3-point chart → a real daily-forecast event graph.
