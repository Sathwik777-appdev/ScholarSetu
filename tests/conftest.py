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
os.environ["DEMO_MODE"] = "false"
os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:5173"
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
from app.db_tables import LIVE_TABLES  # noqa: E402
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
        await conn.run_sync(lambda c: Base.metadata.drop_all(c, tables=LIVE_TABLES))
        await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=LIVE_TABLES))
    yield
    await engine.dispose()


@pytest.fixture
async def db(database):
    names = ", ".join(t.name for t in LIVE_TABLES)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {names} CASCADE"))
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def make_user(db, phone: str, role: UserRole, name: str = "Test User", student_id=None,
                    household_id=None, is_demo=False) -> User:
    user = User(phone=phone, name=name, role=role, student_id=student_id, household_id=household_id,
                is_demo=is_demo)
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
