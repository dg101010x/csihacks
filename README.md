# Relief

Financial safety infrastructure, not another budgeting app.

Relief sits between your accounts, your bills, your income, and your bank — watching for the moment those things are about to collide, and doing something about it before they do. Most finance apps show you what already happened to your money. Relief tries to tell you what's *about* to happen, and gives you a way to change the outcome before it hits your balance.

Built for [Hackathon Name] by a team spanning cloud infra, data engineering, and AI.

## Why we built this

54%+ of Americans are living paycheck to paycheck right now, and it's not just low earners — a big chunk of six-figure households say the same thing. The gap isn't always "not enough money." A lot of the time it's timing: rent, a car payment, and a subscription renewal all land in the same three days, right before a paycheck that's a little short. Nobody's dashboard tells you that's coming. Relief does.

## What it actually does

Relief runs six things continuously in the background:

1. Turns your raw transactions into a clean, structured event stream
2. Forecasts your future liquidity as a *range*, not a fake single number
3. Flags upcoming collisions — insufficient funds, missed payments, reserve violations, timing conflicts
4. Lets you simulate shocks (lost hours, a smaller paycheck, a surprise bill) before they're real
5. Generates and ranks concrete interventions, each with a modeled outcome and cost
6. Lets you write your own rules in plain English (a "financial constitution") for what Relief is and isn't allowed to touch

The point isn't a prettier spending chart. It's turning "I have a bad feeling about this month" into "here's exactly what's coming, here's why, and here's what you can do about it right now."

## How it's put together

Relief is split into two halves that talk to each other through a strict versioned contract (`packages/relief_contracts`), so either side can be rebuilt without breaking the other.

**The model side — ReliefFM (Plan One)**
A transformer-based model trained on financial event sequences (obligations, income, transfers — not raw transaction text). It doesn't touch your money or make decisions. It forecasts trajectories and estimates risk, that's it. The implemented sizes are Nano (6.5M parameters), Mini (59.6M, trained), and Flash (606M, training-ready) — roughly 670M parameters combined. Lives in [`relieffm/`](relieffm/).

**The platform side — Plan Two**
Everything that actually runs the product: the ledger, obligation detection, the deterministic cash-flow engine (a rules-based fallback that works even if the model is down), resilience/elasticity scoring, the intervention engine, the staged approval workflow, audit/replay, Plaid + Wells Fargo integrations, and the API/frontend serving all of it. See [`docs/architecture/relief_plan_two.md`](docs/architecture/relief_plan_two.md) for Plan Two's ownership boundaries and build order.

```
Known financial state
        ↓
Deterministic ledger (platform)
        ↓
ReliefFM trajectory forecasting (model)
        ↓
Reconciliation
        ↓
Intervention optimizer
        ↓
Approval workflow → provider → execution
```

The model predicts what *might* happen. The platform decides what's actually legal, contractual, and safe to propose. The model never gets to pull the trigger on a real financial action — that's on purpose.

There are always three forecast providers available, swappable via env var, so the front end never has to know or care which one is running:

```
FORECAST_PROVIDER=mock          # static fixtures, for UI dev
FORECAST_PROVIDER=deterministic # rules-based fallback, always works
FORECAST_PROVIDER=relieffm      # the actual model
```

`services/model_gateway` is Plan Two's side of that switch — it dispatches to whichever provider is requested and falls back to `deterministic` with an explicit warning if `relieffm` is requested but unreachable, rather than failing the request.

## Repo layout

```
relief/
  apps/
    web/                # Next.js frontend
    api/                 # FastAPI backend (Plan Two)
    workflow_worker/      # staged approval state machine
  services/
    model_gateway/         # Plan Two's only door into the model (mock/deterministic/relieffm dispatch)
    model_inference/        # model serving (owned by the model team; not built in this checkout)
  packages/
    relief_contracts/       # the shared contract — schemas, types, fixtures (both teams agree here first)
    design_system/
    test_fixtures/
  modules/                  # Plan Two business logic, each independently pip-installable
    ledger/ recurring_detection/ obligations/ deterministic_forecast/
    resilience/ elasticity/ interventions/ consumer_constitution/
    explanations/ audit/ integrations/
  ml/                       # Plan Two's placeholder boundary for the model workstream
  relieffm/                 # the complete Plan One implementation — model, training, evaluation
  infrastructure/           # database, containers, deployment, monitoring
  docs/                     # architecture, product, compliance, model_contracts, demo
```

`packages/relief_contracts` is the one directory both teams have to agree on before touching. Everything else is owned by whoever's building it — see `docs/architecture/relief_plan_two.md` for the exact boundary (Plan Two owns everything except `ml/` and `services/model_inference`).

## Stack

- **Frontend:** Next.js (App Router), React, TypeScript, Tailwind, shadcn, TanStack Query, Zod
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy — Postgres in production, SQLite for local dev
- **Workflows/AI:** an explicit staged-approval state graph today; LangChain/LangGraph are the eventual seam for the explanation layer and a model-driven approval agent, not required for the platform to function
- **Integrations:** Plaid Sandbox (real httpx client, not the SDK), synthetic Wells Fargo reference data
- **Model:** PyTorch, transformer encoder-decoder over financial event sequences

Money is handled as integer cents everywhere in the contracts. No floats near anything that touches a balance.

## The demo, in one paragraph

Sarah's got $2,480 in checking. She's expecting a $2,100 paycheck on the 31st, but rent ($1,450), an auto payment ($240), and a subscription renewal ($15.99) all land on the 27th and 28th — before that paycheck arrives. Drop her expected paycheck to $1,720 in Scenario Lab and watch Relief catch the collision, explain exactly which obligations caused it, and hand back ranked ways to fix it — split the auto payment, pause the subscription, or a provider hardship request — each with a modeled cost and outcome. Approve one, watch it move through provider review, and see the whole thing show up in the audit log. Takes under two minutes end to end.

## Running Plan Two (the platform) locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e packages/relief_contracts/python
for m in modules/*/; do pip install -e "$m"; done
pip install -e services/model_gateway -e apps/workflow_worker -e apps/api
pytest -q                                    # 108 tests, everything above
uvicorn app.main:app --app-dir apps/api      # http://localhost:8000
```

Or via Docker: `docker compose -f infrastructure/deployment/docker-compose.yml up` (Postgres + the API, see that file for env vars).

Frontend:

```bash
pnpm install
pnpm dev
```

## Running ReliefFM (the model) locally

```bash
cd relieffm
python -m venv .venv
source .venv/bin/activate
pip install -e .
pytest tests packages/relief_contracts/tests -q
```

The trained checkpoint is stored in GCS rather than Git. Follow [`relieffm/integration/README.md`](relieffm/integration/README.md) to pull and verify it, start the four-endpoint API, and connect Plan Two in shadow mode. Plan Two should still start with `FORECAST_PROVIDER=mock`, then `deterministic`; ReliefFM runs beside the deterministic provider until all activation gates pass.

## Where things stand

- [x] Shared contracts (`relief_contracts`)
- [x] Plan Two: every backend module (ledger through deployment infra), apps/api wired end-to-end, 108 tests passing
- [x] ReliefSim + deterministic known-event reconciliation
- [x] ReliefFM Nano trained and evaluated
- [x] ReliefFM Mini trained and evaluated on 25,000 synthetic households
- [x] Mini release manifest, JSON Schemas, OpenAPI, and real HTTP fixtures
- [x] Flash 606M architecture and GPU preflight code
- [ ] Plan Two ↔ ReliefFM shadow connection and deterministic comparison logging (`services/model_gateway` is ready on Plan Two's side; wiring up a live `RELIEFFM_INFERENCE_URL` against `relieffm/integration/` is next)
- [ ] Calibration, fairness, robustness, privacy, and live latency gates
- [ ] Flash training
- [ ] Real DB migrations (Alembic), metrics/alerting — see `infrastructure/database/README.md` and `infrastructure/monitoring/README.md`

Mini beats the seasonal balance baseline, but its distress head loses to the gradient-boosted baseline and its intervention evidence is still weak. ReliefFM is therefore a shadow-only provider and must not drive a user-facing decision yet — Plan Two's deterministic engine is the one actually serving forecasts today.

## A note on the data

Everything here runs on synthetic data — a made-up "Wells Fargo" formatted dataset and a household simulator (ReliefSim). No real bank, no real user, no real money moves. It's built to behave like the real thing would, but treat every number in this demo as fictional until stated otherwise.
