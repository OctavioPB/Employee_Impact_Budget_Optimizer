"""FastAPI backend for EIBO — wraps Python analytics modules as REST endpoints."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import dashboard, simulation, predictive, notifications, admin, forecast, compensation, knowledge, mobility, fairness, decision_room, resilience, ld, narrative, ohi

app = FastAPI(
    title="EIBO API",
    description="Employee Impact & Budget Optimizer — API layer",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# In dev: Vite runs on 3000, FastAPI on 8000.
# In Docker: requests come from the same origin via nginx proxy.
_ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(dashboard.router,    prefix="/api", tags=["dashboard"])
app.include_router(simulation.router,   prefix="/api", tags=["simulation"])
app.include_router(predictive.router,   prefix="/api", tags=["predictive"])
app.include_router(notifications.router,prefix="/api", tags=["notifications"])
app.include_router(admin.router,         prefix="/api", tags=["admin"])
app.include_router(forecast.router,      prefix="/api", tags=["forecast"])
app.include_router(compensation.router,  prefix="/api", tags=["compensation"])
app.include_router(knowledge.router,     prefix="/api", tags=["knowledge"])
app.include_router(mobility.router,      prefix="/api", tags=["mobility"])
app.include_router(fairness.router,      prefix="/api", tags=["fairness"])
app.include_router(decision_room.router, prefix="/api", tags=["decision-room"])
app.include_router(resilience.router,    prefix="/api", tags=["resilience"])
app.include_router(ld.router,            prefix="/api", tags=["ld"])
app.include_router(narrative.router,     prefix="/api", tags=["narrative"])
app.include_router(ohi.router,           prefix="/api", tags=["ohi"])


@app.get("/api/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "service": "eibo-api"}
