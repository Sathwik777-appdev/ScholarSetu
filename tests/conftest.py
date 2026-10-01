"""Shared test setup.

Environment is fixed here, before the app is imported, so a developer's .env never
leaks in. Integration tests need Postgres from infra/docker-compose.yml (localhost:5434);
they use a separate `scholarsetu_test` database. Override with TEST_DATABASE_URL.
"""

import os
import re
import secrets
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="scholarsetu-tests-"))

os.environ["SCHOLARSETU_ENV_FILE"] = str(_TMP / "no-such.env")
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://scholarsetu:scholarsetu_dev@localhost:5434/scholarsetu_test")
os.environ["DATABASE_NULL_POOL"] = "true"
os.environ["JWT_SECRET"] = secrets.token_hex(32)
os.environ["SKILL_SERVICE_TOKEN"] = secrets.token_hex(24)
os.environ["SMS_GATEWAY_TOKEN"] = secrets.token_hex(24)
os.environ["PPRL_HMAC_KEY"] = secrets.token_hex(24)  # read by core and by the in-process UDISE+ mock
os.environ["DEMO_MODE"] = "false"
os.environ["OUTBOX_PUBLISHER_ENABLED"] = "false"
os.environ["ADAPTER_SYNC_INTERVAL_SECONDS"] = "0"
os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:5173"
# Per-client limits on the login endpoints: every test request comes from one address, so they are lifted here
# and tested on their own (tests/integration/test_audit_fixes.py).
os.environ["IP_CODE_REQUESTS_PER_10_MIN"] = "100000"
os.environ["IP_CODE_CHECKS_PER_10_MIN"] = "100000"
os.environ["ATTESTATION_PRIVATE_KEY_PATH"] = str(_TMP / "attestation_ed25519.pem")

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

Path(os.environ["ATTESTATION_PRIVATE_KEY_PATH"]).write_bytes(
    Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))

import asyncpg  # noqa: E402
import httpx  # noqa: E402
import pytest  # noqa: E402
from sqlalchemy import select, text  # noqa: E402

from app.database import AsyncSessionLocal, Base, engine  # noqa: E402
import app.models  # noqa: E402,F401
from app.gateway.models import OutboundSms, User  # noqa: E402
from app.main import app  # noqa: E402
from app.shared.types import UserRole  # noqa: E402

TEST_TMP_DIR = _TMP


async def _ensure_database() -> None:
    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    base, dbname = url.rsplit("/", 1)
    conn = await asyncpg.connect(f"{base}/postgres")
    try:
        if not await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", dbname):
            await conn.execute(f'CREATE DATABASE "{dbname}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session")
async def database():
    try:
        await _ensure_database()
    except (OSError, asyncpg.PostgresError) as exc:
        # Fail loudly: silently skipping would make a run without a database look green.
        pytest.fail(f"Postgres not reachable ({exc}). Start it with: "
                    "docker compose -f infra/docker-compose.yml up -d postgres", pytrace=False)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    # Reference data, loaded once: decision tables and the embedded guideline corpus.
    from app.eligibility.service import load_rule_files
    from app.jago_skill.embeddings import get_embedder
    from app.jago_skill.rag import ensure_index
    async with AsyncSessionLocal() as session:
        await load_rule_files(session)
        await ensure_index(session, get_embedder())
    yield
    await engine.dispose()
    get_embedder()._model = None  # release ONNX Runtime before interpreter shutdown
    import gc
    gc.collect()


REFERENCE_TABLES = {"rule_versions", "guideline_chunks"}


@pytest.fixture
async def db(database):
    names = ", ".join(t.name for t in Base.metadata.sorted_tables if t.name not in REFERENCE_TABLES)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def make_user(db, phone: str, role: UserRole, name: str = "Test User", student_id=None,
                    household_id=None, is_demo=False, jurisdiction=(None, None)) -> User:
    user = User(phone=phone, name=name, role=role, student_id=student_id, household_id=household_id,
                is_demo=is_demo, jurisdiction_state=jurisdiction[0], jurisdiction_district=jurisdiction[1])
    db.add(user)
    await db.commit()
    return user


async def latest_sms_code(db, phone: str) -> str:
    db.expire_all()
    rows = (await db.execute(select(OutboundSms).where(OutboundSms.to_phone == phone)
                             .order_by(OutboundSms.created_at.desc()))).scalars().all()
    assert rows, f"no SMS sent to {phone}"
    match = re.search(r"\b(\d{6})\b", rows[0].body)
    assert match, "SMS did not contain a 6-digit code"
    return match.group(1)


async def login(client, db, phone: str) -> str:
    r = await client.post("/v1/auth/otp/request", json={"phone": phone})
    assert r.status_code == 202, r.text
    code = await latest_sms_code(db, phone)
    r = await client.post("/v1/auth/otp/verify", json={"phone": phone, "otp": code})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Demo students and simulated government sources ───────────────────────────

import importlib  # noqa: E402
import sys  # noqa: E402
from datetime import date  # noqa: E402

from app.shared.types import Gender  # noqa: E402
from app.students.models import Student  # noqa: E402
from app.verification.sources import SourceClient, get_source_client  # noqa: E402

_MOCKS_DIR = Path(__file__).resolve().parents[1] / "mocks"
sys.path.insert(0, str(_MOCKS_DIR))
mocks_main = importlib.import_module("main")          # mocks/main.py: the mock government cluster
mocks_data = importlib.import_module("synthetic_data")
mocks_data.generate_synthetic_data()

SUNITA_STUDENT = dict(id="stu-sunita-001", full_name="Sunita Hansda", name_variants=["Sunita Hansda"],
                      dob=date(2008, 4, 12), gender=Gender.FEMALE, father_name="Babulal Hansda",
                      mother_name="Marangmai Hansda", tribe="Santal", state="Jharkhand", district="Dumka",
                      household_id="hh_hansda_001", aadhaar_ref_token="AREF-JH-0004912",
                      apaar_id="APAAR-JH-2026-0812")
RAHUL_STUDENT = dict(id="stu-rahul-002", full_name="Rahul Hansda", name_variants=["Rahul Hansda"],
                     dob=date(2010, 8, 15), gender=Gender.MALE, father_name="Babulal Hansda",
                     mother_name="Marangmai Hansda", tribe="Santal", state="Jharkhand", district="Dumka",
                     household_id="hh_hansda_001", aadhaar_ref_token="AREF-JH-0009914",
                     apaar_id="APAAR-JH-2025-4192")


async def make_student(db, **fields) -> Student:
    student = Student(**fields)
    db.add(student)
    await db.commit()
    return student


class GovSources:
    """The mock government cluster, in-process. Put path prefixes in `down` (or "*") to simulate outages."""

    def __init__(self):
        self.down: set[str] = set()
        self.calls: list[str] = []
        self.transport = _GovTransport(self)


class _GovTransport(httpx.AsyncBaseTransport):
    def __init__(self, gov: GovSources):
        self.gov = gov
        self.inner = httpx.ASGITransport(app=mocks_main.app)

    async def handle_async_request(self, request):
        path = request.url.path
        self.gov.calls.append(path)
        if "*" in self.gov.down or any(path.startswith(prefix) for prefix in self.gov.down):
            raise httpx.ConnectError("simulated outage", request=request)
        return await self.inner.handle_async_request(request)


@pytest.fixture
def gov():
    mocks_data.generate_synthetic_data()  # fresh mock state (bank accounts, portal statuses) per test
    sources = GovSources()

    async def _client():
        client = SourceClient("http://mocks", transport=sources.transport, attempts=2)
        try:
            yield client
        finally:
            await client.aclose()

    app.dependency_overrides[get_source_client] = _client
    yield sources
    app.dependency_overrides.pop(get_source_client, None)


# ── Seeded demo world (scripts/seed_demo.py) ─────────────────────────────────

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.seed_demo import seed as seed_demo  # noqa: E402

PHONES = {"headmaster": "9876543226", "sunita": "9876543210", "rahul": "9876543211", "salkhan": "9876543213", "guardian": "9876543212", "mitra": "9876543220",
          "institute": "9876543225", "district": "9876543230", "state": "9876543235", "ministry": "9876543240"}


@pytest.fixture
async def demo(db):
    """The demo world, created through the service layer. Returns the seeded application ids."""
    return await seed_demo(db)


class Logins:
    def __init__(self, client, db):
        self.client, self.db, self._cache = client, db, {}

    async def token(self, who: str) -> str:
        if who not in self._cache:
            self._cache[who] = await login(self.client, self.db, PHONES[who])
        return self._cache[who]

    async def headers(self, who: str) -> dict:
        return bearer(await self.token(who))


@pytest.fixture
def users(client, db, demo):
    return Logins(client, db)


async def grant_consent(client, headers: dict, items: list[str], requester="SCHOLARSETU_VERIFICATION_MESH",
                        days: int = 30) -> str:
    r = await client.post("/v1/consents", headers=headers, json={
        "requester": requester, "purpose": "Scholarship eligibility verification", "data_items": items,
        "duration_days": days})
    assert r.status_code == 201, r.text
    return r.json()["id"]


class MemoryStore:
    """In-memory stand-in for MinIO (the real store is exercised by the Docker acceptance run)."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    async def put(self, key, data, content_type):
        self.objects[key] = data

    async def get(self, key):
        return self.objects[key]


@pytest.fixture
def store():
    from app.wallet.storage import get_object_store
    memory = MemoryStore()
    app.dependency_overrides[get_object_store] = lambda: memory
    yield memory
    app.dependency_overrides.pop(get_object_store, None)


# ── Process exit ──────────────────────────────────────────────────────────────
# ONNX Runtime (the embedding model) can abort while its native thread pool is torn down at interpreter exit
# ("recursive_mutex lock failed"), turning a fully passing run into exit code 134. Once pytest has finished
# everything, leave with pytest's own status instead of running that native teardown.

_exit_status: dict = {}


def pytest_sessionfinish(session, exitstatus):
    _exit_status["code"] = int(exitstatus)


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    if "code" in _exit_status:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(_exit_status["code"])
