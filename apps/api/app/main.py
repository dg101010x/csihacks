from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import SessionLocal, create_all_tables
from .middleware import RequestIdMiddleware
from .routes import audit, constitution, data_trust, demo, forecasts, households, interventions, provider, providers_status
from .seed import seed_demo_household


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_all_tables()
    session = SessionLocal()
    try:
        seed_demo_household(session)
    finally:
        session.close()
    yield


app = FastAPI(title="Relief API", version="1.0.0", lifespan=lifespan)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    households.router,
    forecasts.router,
    demo.router,
    interventions.router,
    provider.router,
    constitution.router,
    audit.router,
    providers_status.router,
    data_trust.router,
):
    app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
