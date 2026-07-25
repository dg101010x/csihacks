# Implementation sequence

1. Domain/adapter layer (`src/domain/`) — everything downstream depends on
   this existing first.
2. Shell rebuild (nav rail, indicators, command palette, notification
   center, responsive drawer) — every page mounts inside it.
3. Command Center — the primary demo entry point.
4. Timeline — shares `ForecastChart` with Command Center; building it next
   proves the chart primitive works for both a summary and a full view.
5. Scenario Lab — depends on the domain client's `applyScenario`, and its
   output (risk windows, deltas) feeds Command Center and Interventions.
6. Interventions — ranked cards + comparison + staged approval, consuming
   `InterventionPackage` from the domain layer.
7. Constitution — rule input, structured preview, simulation against the
   active forecast.
8. Audit — ledger list + detail, reading `AuditRecord`.
9. Providers, then Data — lower priority than the core demo path (Command
   Center → Scenario Lab → Timeline → Interventions → Constitution →
   Audit), built once that path is solid.
10. Testing, lint/typecheck/build, the ten review passes, screenshots, final
    report.

Old routes (`/demo`, `/dashboard`, `/provider*`) get redirects in the same
pass as the route that replaces them, not deferred to the end — so the app
never has a moment with a dangling broken link mid-implementation.
