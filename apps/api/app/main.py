from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import SessionLocal, create_all_tables
from .logging_config import configure_logging
from .middleware import RequestIdMiddleware
from .rate_limit import RateLimitMiddleware
from .routes import audit, constitution, data_trust, demo, forecasts, households, integrations, interventions, models, provider, providers_status
from .security import auth_is_enforced, require_api_key
from .seed import seed_demo_household

logger = logging.getLogger("relief_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    if not auth_is_enforced():
        logger.warning(
            "RELIEF_API_KEY is not set — /v1/* routes are unauthenticated. "
            "Fine for local dev/demo; any real deployment must set it."
        )
    create_all_tables()
    session = SessionLocal()
    try:
        seed_demo_household(session)
    finally:
        session.close()
    yield


app = FastAPI(title="Relief API", version="1.0.0", lifespan=lifespan)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("RELIEF_ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


for router in (
    households.router,
    integrations.router,
    forecasts.router,
    demo.router,
    interventions.router,
    provider.router,
    constitution.router,
    audit.router,
    providers_status.router,
    data_trust.router,
    models.router,
):
    app.include_router(router, dependencies=[Depends(require_api_key)])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
