# Relief — Plan Two

Platform, engine, front end, and infrastructure for Relief. This workstream (Plan Two)
transforms Relief from a model into usable financial infrastructure. See
`docs/architecture/` for the full plan.

## Ownership boundaries

Plan Two owns everything in this repository **except**:

- `ml/`
- `services/model_inference/`

Those belong to the model workstream (Plan One / ReliefFM). Both teams jointly approve
changes to `packages/relief_contracts/`.

## Repository layout

```
apps/            web (Next.js), api (FastAPI), workflow_worker
services/        model_gateway (Plan Two owned), model_inference (Plan One owned)
packages/        relief_contracts, design_system, financial_math, configuration,
                  test_fixtures, eslint_config, typescript_config
modules/         authentication, ledger, accounts, obligations, recurring_detection,
                  deterministic_forecast, resilience, elasticity, interventions,
                  provider_policies, consumer_constitution, explanations, audit,
                  integrations
ml/              relieffm, training, evaluation, datasets   (Plan One owned)
infrastructure/  database, containers, deployment, monitoring
docs/            architecture, product, compliance, model_contracts, demo
```

## Core architectural rule

The platform must work before ReliefFM is connected. Three forecast providers are
supported behind one interface (`ForecastResponseV1`): `mock`, `deterministic`,
`relieffm`, selected via `FORECAST_PROVIDER`. No page, table, optimizer, or workflow
may know which provider produced a result.

## Development strategy (build order)

1. Shared contracts (`packages/relief_contracts`)
2. Front end design system (`packages/design_system`)
3. Front end demonstration experience (fixtures + Mock Service Worker)
4. Front end application state
5. Mock backend
6. Core backend
7. Immutable ledger
8. Deterministic forecasting
9. Obligation detection
10. Resilience calculation
11. Elasticity calculation
12. Intervention optimizer
13. LangChain explanation layer
14. LangGraph approval workflow
15. Plaid integration
16. Wells Fargo reference adapter
17. Audit and replay
18. Security hardening
19. ReliefFM integration
20. Deployment and demonstration hardening

Front end implementation begins before production backend work.

## Getting started

```bash
pnpm install
pnpm dev
```
