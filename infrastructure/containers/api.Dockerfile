# Relief API (apps/api) — Section 20 deployment hardening.
#
# Every module is its own independently pip-installable package (Section 29),
# so the build stage installs them explicitly in dependency order rather than
# relying on a single requirements.txt. Build from the repo root:
#   docker build -f infrastructure/containers/api.Dockerfile -t relief-api .
FROM python:3.11-slim AS build

WORKDIR /build

COPY packages/relief_contracts/python packages/relief_contracts/python
COPY modules modules
COPY services/model_gateway services/model_gateway
COPY apps/workflow_worker apps/workflow_worker
COPY apps/api apps/api

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "psycopg[binary]>=3.1" \
    && pip install --no-cache-dir \
        ./packages/relief_contracts/python \
        ./modules/ledger \
        ./modules/recurring_detection \
        ./modules/obligations \
        ./modules/deterministic_forecast \
        ./modules/resilience \
        ./modules/elasticity \
        ./modules/interventions \
        ./modules/consumer_constitution \
        ./modules/explanations \
        ./modules/audit \
        ./modules/integrations \
        ./services/model_gateway \
        ./apps/workflow_worker \
        ./apps/api

FROM python:3.11-slim

RUN useradd --create-home --uid 10001 relief
WORKDIR /app
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /usr/local/bin /usr/local/bin
COPY apps/api/app ./app

USER relief
EXPOSE 8000
ENV DATABASE_URL=postgresql+psycopg://relief:relief@db:5432/relief

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
