import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.attestation.keys import get_signer
from app.config import settings
from app.database import AsyncSessionLocal, engine
from app.shared.events import NATSEventBus, get_event_bus, run_outbox_publisher, set_event_bus
from app.shared.ids import new_id

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
from app.adapters.router import router as adapters_router
from app.channels.router import router as channels_router
from app.sync.router import router as sync_router

logging.basicConfig(level=settings.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("scholarsetu.core")

NUDGE_SUBJECTS = {"application.>": "nudge-application", "deficiency.>": "nudge-deficiency",
                  "payment.>": "nudge-payment", "verification.>": "nudge-verification",
                  "pathway.>": "nudge-pathway", "dbt.>": "nudge-dbt", "sla.>": "nudge-sla"}


async def _prepare_reference_data() -> None:
    """Load decision tables (fail loudly on a bad rule file) and index the guideline corpus."""
    from app.eligibility.service import load_rule_files
    from app.jago_skill.embeddings import get_embedder
    from app.jago_skill.rag import ensure_index
    async with AsyncSessionLocal() as db:
        loaded = await load_rule_files(db)
        logger.info("rule versions loaded: %d new", loaded)
    try:
        async with AsyncSessionLocal() as db:
            await ensure_index(db, get_embedder())
    except Exception:
        logger.exception("guideline index build failed; JAGO guideline answers will say they cannot answer")


async def _handle_for_nudge(event) -> None:
    from app.nudge.service import NudgeService
    async with AsyncSessionLocal() as db:
        await NudgeService(db).handle_event(event)


async def _run_event_bus(stop: asyncio.Event) -> None:
    """Connect to NATS (retrying until it is reachable), then publish the outbox and run consumers."""
    bus = NATSEventBus(settings.NATS_URL)
    while not stop.is_set():
        try:
            await bus.connect()
            break
        except Exception as exc:
            logger.warning("NATS not reachable (%s); retrying in 2s. Events wait safely in the outbox.", exc)
            try:
                await asyncio.wait_for(stop.wait(), timeout=2)
            except asyncio.TimeoutError:
                pass
    if stop.is_set():
        return
    set_event_bus(bus)
    for subject, durable in NUDGE_SUBJECTS.items():
        await bus.subscribe(subject, durable, _handle_for_nudge)
    logger.info("Connected to NATS JetStream at %s", settings.NATS_URL)
    try:
        await run_outbox_publisher(AsyncSessionLocal, bus, stop=stop)
    finally:
        await bus.close()
        set_event_bus(None)


async def _poll_portals(stop: asyncio.Event) -> None:
    """Periodically sync NSP/SFMP/NOS statuses into the ledger."""
    from app.adapters.sync_service import AdapterSyncService
    from app.verification.sources import SourceClient
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.ADAPTER_SYNC_INTERVAL_SECONDS)
            break
        except asyncio.TimeoutError:
            pass
        client = SourceClient(settings.MOCK_SERVICE_URL)
        try:
            async with AsyncSessionLocal() as db:
                results = await AdapterSyncService(db, client).sync_all()
            logger.info("portal sync: %d students, %d imported, %d parked", len(results),
                        sum(len(r.imported) for r in results), sum(r.parked for r in results))
        except Exception:
            logger.exception("portal sync failed")
        finally:
            await client.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ScholarSetu core")
    get_signer()  # refuse to start without a usable attestation signing key
    if settings.DEMO_MODE:
        logger.warning("DEMO_MODE is ON: seeded demo users can log in with the demo OTP. Never enable in production.")
    stop = asyncio.Event()
    reference_task = asyncio.create_task(_prepare_reference_data())
    bus_task = asyncio.create_task(_run_event_bus(stop)) if settings.OUTBOX_PUBLISHER_ENABLED else None
    poll_task = asyncio.create_task(_poll_portals(stop)) if settings.ADAPTER_SYNC_INTERVAL_SECONDS > 0 else None
    yield
    stop.set()
    await asyncio.wait([t for t in (bus_task, reference_task, poll_task) if t], timeout=5)
    await engine.dispose()
    logger.info("ScholarSetu core stopped")


app = FastAPI(
    title="ScholarSetu Core API",
    description="Unified scholarship platform for ST students (MoTA): ledger, verification mesh, "
                "attestations, eligibility, DBT Guardian, JAGO skill and Reach Radar.",
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
    allow_headers=["Authorization", "Content-Type", "X-Mitra-Session", "Idempotency-Key"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    """Never expose internals: log with an error id and return only that id."""
    error_id = new_id()
    logger.exception("unhandled error %s on %s %s", error_id, request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal error", "error_id": error_id})


@app.get("/health", tags=["System"])
async def health_check():
    """Liveness: the API process is up."""
    return {"status": "ok", "service": "scholarsetu-core", "version": app.version}


@app.get("/health/ready", tags=["System"])
async def readiness():
    """Readiness: checks the database and the event bus."""
    checks = {}
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"
    try:
        from app.jago_skill.models import GuidelineChunk
        from app.jago_skill.rag import corpus_version
        from sqlalchemy import func, select
        async with AsyncSessionLocal() as db:
            indexed = await db.scalar(select(func.count()).select_from(GuidelineChunk)
                                      .where(GuidelineChunk.corpus_version == corpus_version()))
        # Informational: until built, JAGO says it cannot answer guideline questions (it never guesses).
        checks["guideline_index"] = f"ok ({indexed} passages)" if indexed else "building"
    except Exception as exc:
        checks["guideline_index"] = f"error: {type(exc).__name__}"
    bus = get_event_bus()
    checks["event_bus"] = "ok" if bus is not None and getattr(bus, "connected", False) else "unavailable"
    ready = checks["database"] == "ok"
    return JSONResponse(status_code=200 if ready else 503, content={"ready": ready, "checks": checks})


for router in (gateway_router, ledger_router, verification_router, attestation_router, eligibility_router,
               dbt_guardian_router, wallet_router, consent_router, nudge_router, jago_skill_router,
               reach_radar_router, adapters_router, channels_router, sync_router):
    app.include_router(router)
