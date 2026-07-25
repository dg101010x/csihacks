# Relief

Financial safety infrastructure, not another budgeting app.

Relief sits between your accounts, your bills, your income, and your bank — watching for the moment those things are about to collide, and doing something about it before they do. Most finance apps show you what already happened to your money. Relief tries to tell you what's *about* to happen, and gives you a way to change the outcome before it hits your balance.

Built for [Hackathon Name] by a team of six engineers spanning cloud infra, data engineering, and AI.

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

Relief is split into two halves that talk to each other through a strict versioned contract, so either side can be rebuilt without breaking the other.

**The model side — ReliefFM**
A transformer-based model trained on financial event sequences (think obligations, income, transfers — not just raw transaction text). It doesn't touch your money or make decisions. It forecasts trajectories and estimates risk, that's it. Three sizes exist depending on how much compute we've got: Nano (hackathon-scale, ~8-15M params), Mini, and Base.

**The platform side**
Everything that actually runs the product: the ledger, obligation detection, the deterministic cash-flow engine (a rules-based fallback that works even if the model is down), the intervention engine, approval workflows, and the interface itself.

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

## Repo layout

```
relief/
  apps/
    web/              # Next.js frontend
    api/               # FastAPI backend
    workflow_worker/    # LangGraph approval workflows
  services/
    model_gateway/       # platform's only door into the model
    model_inference/      # model serving (owned by the model team)
  packages/
    relief_contracts/     # the shared contract — schemas, types, fixtures
    design_system/
    financial_math/
  modules/
    ledger/ obligations/ resilience/ elasticity/
    interventions/ provider_policies/ consumer_constitution/
    explanations/ audit/ integrations/
  ml/
    relieffm/ simulator/ training/ evaluation/
  docs/
```

`packages/relief_contracts` is the one directory both teams have to agree on before touching. Everything else is owned by whoever's building it.

## Stack

- **Frontend:** Next.js (App Router), React, TypeScript, Tailwind, shadcn, TanStack Query, Zod, Recharts/ECharts
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Redis
- **Workflows/AI:** LangChain (explanations), LangGraph (durable approval workflows), LangSmith (tracing)
- **Integrations:** Plaid Sandbox, synthetic Wells Fargo reference data
- **Model:** PyTorch, transformer encoder-decoder over financial event sequences

Money is handled as integer cents everywhere in the contracts. No floats near anything that touches a balance.

## The demo, in one paragraph

Sarah's got $2,480 in checking. She's expecting a $2,100 paycheck on the 31st, but rent ($1,450), an auto payment ($240), and a subscription renewal ($15.99) all land on the 27th and 28th — before that paycheck arrives. Drop her expected paycheck to $1,720 in Scenario Lab and watch Relief catch the collision, explain exactly which obligations caused it, and hand back three ranked ways to fix it — split the auto payment, pause the subscription, or pull from a reserve account — each with a modeled cost and outcome. Approve one, watch it move through provider review, and see the whole thing show up in the audit log. Takes under two minutes end to end.

## Running it locally

```bash
git clone <repo-url>
cd relief
pnpm install          # frontend + shared packages
pip install -r requirements.txt   # backend + ml

cp .env.example .env
# set FORECAST_PROVIDER=mock to start without any backend at all

pnpm dev              # frontend
uvicorn apps.api.main:app --reload   # backend
```

Start with `FORECAST_PROVIDER=mock` — the whole demo works off static fixtures before you connect anything real. Flip it to `deterministic` once the ledger and obligation detection are wired up, and `relieffm` once the model service is actually running.

## Where things stand

- [x] Shared contracts (`relief_contracts`)
- [x] Deterministic cash-flow engine
- [x] Obligation detection (recurring transaction clustering)
- [x] Frontend: Command Center, Timeline, Scenario Lab, Interventions
- [ ] LangGraph approval workflow — in progress
- [ ] ReliefFM Nano — training against synthetic households
- [ ] Provider adapter (Plaid Sandbox) — wired, not stress-tested
- [ ] Audit replay UI

Currently everything demoable runs on the deterministic engine + synthetic Wells Fargo data. ReliefFM is real but running in shadow mode — it's not driving anything user-facing yet.

## Team

- **Prakshal Doshi** — cloud infrastructure & reliability
- **Lokesh Kank** — AI/ML engineering
- **Aran Yogesh** — product & platform engineering
- **Mogana Kumaran S** — data engineering, pipeline architecture
- **Hemalatha Krishnan** — backend systems & QA
- **Sakthivel Natarajan** — analytics & engineering delivery

## A note on the data

Everything here runs on synthetic data — a made-up "Wells Fargo" formatted dataset and a household simulator we built ourselves (ReliefSim). No real bank, no real user, no real money moves. It's built to behave like the real thing would, but treat every number in this demo as fictional until stated otherwise.
