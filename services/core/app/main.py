from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import engine
from app.attestation.service import get_attestation_service

# Routers
from app.gateway.router import router as gateway_router
from app.ledger.router import router as ledger_router
from app.verification.router import router as verification_router
from app.attestation.router import router as attestation_router
from app.eligibility.router import router as eligibility_router
from app.dbt_guardian.router import router as dbt_guardian_router
from app.wallet.router import router as wallet_router
from app.consent.router import router as consent_router
from app.nudge.router import router as nudge_router
from app.jago_skill.router import router as jago_skill_router
from app.reach_radar.router import router as reach_radar_router

logger = logging.getLogger("scholarsetu.core")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize background resources and clean up on exit."""
    logger.info("Starting ScholarSetu Modular Monolith Core...")
    # Fail fast: refuse to start without a usable attestation signing key.
    get_attestation_service()
    if settings.DEMO_MODE:
        logger.warning("DEMO_MODE is ON: seeded demo users can log in with the demo OTP. Never enable this in production.")
    yield
    logger.info("Shutting down ScholarSetu Core...")
    await engine.dispose()


app = FastAPI(
    title="ScholarSetu Core API",
    description=(
        "Unified Scholarship Platform for Tribal Students (MoTA) — "
        "Smart Automation & Integration Layer for Pre-Matric, Post-Matric, "
        "Top Class Education, NFST, and National Overseas Scholarships."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS: explicit origins only (validated in config; "*" is rejected because credentials are allowed).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Mitra-Session"],
)


@app.get("/health", tags=["System"])
async def health_check():
    """Liveness only: reports that the API process is up, not the state of its dependencies."""
    return {"status": "ok", "service": "scholarsetu-core", "version": "1.0.0"}


# Include all routers directly — each router defines its own /v1/ namespace
app.include_router(gateway_router)
app.include_router(ledger_router)
app.include_router(verification_router)
app.include_router(attestation_router)
app.include_router(eligibility_router)
app.include_router(dbt_guardian_router)
app.include_router(wallet_router)
app.include_router(consent_router)
app.include_router(nudge_router)
app.include_router(jago_skill_router)
app.include_router(reach_radar_router)
