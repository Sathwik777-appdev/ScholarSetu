import os

base_dir = "/Users/sathwikjpoojary/Documents/SIH26238"

files = {
    ".gitignore": """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
env/
.venv/
.env

# Flutter
.dart_tool/
.packages
build/
.pub-cache/
.pub/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Docker
.docker/

# OS generated
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
""",
    "README.md": """# ScholarSetu

ScholarSetu is a unified scholarship platform for tribal students in India, integrating 5 MoTA scholarship schemes across 3 portals (NSP, SFMP, NOS).

## Setup Instructions

1. Make sure you have Docker and Docker Compose installed.
2. Run `make setup` to initialize the project (if applicable).
3. Run `make dev` to start the development environment via docker-compose.
""",
    "Makefile": """setup:
\t@echo "Setting up project..."

dev:
\tdocker-compose -f infra/docker-compose.yml -f infra/docker-compose.override.yml up --build

down:
\tdocker-compose -f infra/docker-compose.yml down

migrate:
\tdocker-compose -f infra/docker-compose.yml exec core alembic upgrade head

seed:
\t@echo "Seeding database..."

test:
\tpytest

lint:
\tflake8 services/core

format:
\tblack services/core
""",
    "infra/docker-compose.yml": """version: '3.8'

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: scholarsetu
      POSTGRES_USER: scholarsetu
      POSTGRES_PASSWORD: scholarsetu_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - scholarsetu-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U scholarsetu"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    networks:
      - scholarsetu-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  nats:
    image: nats:2.10
    command: ["-js"]
    ports:
      - "4222:4222"
      - "8222:8222"
    networks:
      - scholarsetu-net
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8222/healthz"]
      interval: 5s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    networks:
      - scholarsetu-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 5s
      timeout: 5s
      retries: 5

  mock-services:
    image: python:3.12-slim
    command: python -m http.server 8100
    ports:
      - "8100:8100"
    networks:
      - scholarsetu-net

  core:
    build:
      context: ../services/core
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://scholarsetu:scholarsetu_dev@postgres:5432/scholarsetu
      - REDIS_URL=redis://redis:6379
      - NATS_URL=nats://nats:4222
      - MINIO_URL=http://minio:9000
      - MOCK_SERVICE_URL=http://mock-services:8100
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      nats:
        condition: service_healthy
    networks:
      - scholarsetu-net

volumes:
  postgres_data:
  minio_data:

networks:
  scholarsetu-net:
    driver: bridge
""",
    "infra/docker-compose.override.yml": """version: '3.8'

services:
  core:
    volumes:
      - ../services/core:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
""",
    "services/core/Dockerfile": """FROM python:3.12-slim as builder

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
    "services/core/pyproject.toml": """[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "scholarsetu-core"
version = "0.1.0"
dependencies = [
    "fastapi[standard]",
    "uvicorn[standard]",
    "sqlalchemy[asyncio]",
    "asyncpg",
    "alembic",
    "pydantic>=2.0",
    "pydantic-settings",
    "python-jose[cryptography]",
    "passlib[bcrypt]",
    "python-multipart",
    "nats-py",
    "redis[hiredis]",
    "cryptography",
    "PyNaCl",
    "rapidfuzz",
    "indic-transliteration",
    "httpx",
    "structlog",
    "python-json-logger",
    "tenacity",
    "faker"
]

[project.optional-dependencies]
test = [
    "pytest",
    "pytest-asyncio",
    "httpx"
]
""",
    "services/core/alembic.ini": """[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
""",
    "services/core/alembic/env.py": """import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool
from alembic import context
from app.database import Base
from app.config import settings

# Import all models here so Alembic can discover them
# e.g. from app.gateway.models import *

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    connectable = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    pass
else:
    run_migrations_online()
""",
    "services/core/app/__init__.py": "",
    "services/core/app/main.py": """from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config import settings
from app.database import engine
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect DB, Redis, NATS, etc. here
    yield
    # Cleanup here

app = FastAPI(
    title="ScholarSetu Core API",
    description="Unified scholarship platform for tribal students",
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Include routers
app.include_router(gateway_router, prefix="/v1/gateway", tags=["gateway"])
app.include_router(ledger_router, prefix="/v1/ledger", tags=["ledger"])
app.include_router(verification_router, prefix="/v1/verification", tags=["verification"])
app.include_router(attestation_router, prefix="/v1/attestation", tags=["attestation"])
app.include_router(eligibility_router, prefix="/v1/eligibility", tags=["eligibility"])
app.include_router(dbt_guardian_router, prefix="/v1/dbt_guardian", tags=["dbt_guardian"])
app.include_router(wallet_router, prefix="/v1/wallet", tags=["wallet"])
app.include_router(consent_router, prefix="/v1/consent", tags=["consent"])
app.include_router(nudge_router, prefix="/v1/nudge", tags=["nudge"])
app.include_router(jago_skill_router, prefix="/v1/jago_skill", tags=["jago_skill"])
app.include_router(reach_radar_router, prefix="/v1/reach_radar", tags=["reach_radar"])
""",
    "services/core/app/config.py": """from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://scholarsetu:scholarsetu_dev@localhost:5432/scholarsetu"
    REDIS_URL: str = "redis://localhost:6379"
    NATS_URL: str = "nats://localhost:4222"
    MINIO_URL: str = "http://localhost:9000"
    MOCK_SERVICE_URL: str = "http://localhost:8100"
    
    JWT_SECRET: str = "secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    
    ATTESTATION_PRIVATE_KEY_PATH: str = "private.pem"
    ATTESTATION_PUBLIC_KEY_PATH: str = "public.pem"
    
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
""",
    "services/core/app/database.py": """from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
""",
    "services/core/app/dependencies.py": """from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

async def get_db_session(session: AsyncSession = Depends(get_db)) -> AsyncSession:
    return session

async def get_current_user():
    pass

async def get_redis():
    pass

async def get_nats():
    pass
""",
    "services/core/app/shared/__init__.py": "",
    "services/core/app/shared/events.py": """from pydantic import BaseModel
from typing import Any, Dict

class BaseEvent(BaseModel):
    event_id: str
    type: str
    occurred_at: str
    correlation_id: str
    payload: Dict[str, Any]

class EventBus:
    async def publish(self, subject: str, event: BaseEvent):
        pass
    
    async def subscribe(self, subject: str, handler):
        pass

class NATSEventBus(EventBus):
    # NATS JetStream implementation
    pass
""",
    "services/core/app/shared/types.py": """from enum import Enum

class CanonicalState(str, Enum):
    Draft = "Draft"
    Submitted = "Submitted"
    InstituteVerification = "InstituteVerification"
    DeficiencyRaised = "DeficiencyRaised"
    Resubmitted = "Resubmitted"
    AuthorityVerification = "AuthorityVerification"
    Sanctioned = "Sanctioned"
    Rejected = "Rejected"
    PaymentInitiated = "PaymentInitiated"
    Credited = "Credited"
    PaymentFailed = "PaymentFailed"
    RenewalDue = "RenewalDue"

class SchemeType(str, Enum):
    PRE_MATRIC = "PRE_MATRIC"
    POST_MATRIC = "POST_MATRIC"
    TOP_CLASS = "TOP_CLASS"
    NFST = "NFST"
    NOS = "NOS"

class SourceSystem(str, Enum):
    NSP = "NSP"
    SFMP = "SFMP"
    NOS_PORTAL = "NOS_PORTAL"

class VerificationMethod(str, Enum):
    API = "API"
    OCR_ASSISTED = "OCR_ASSISTED"
    MANUAL = "MANUAL"

class ClaimType(str, Enum):
    IDENTITY = "IDENTITY"
    ST_STATUS = "ST_STATUS"
    INCOME = "INCOME"
    DOMICILE = "DOMICILE"
    SCHOOL_ENROLMENT = "SCHOOL_ENROLMENT"
    HIGHER_ED = "HIGHER_ED"
    ACADEMIC_RECORDS = "ACADEMIC_RECORDS"
    NET_JRF = "NET_JRF"
    DISABILITY = "DISABILITY"
    TOP_CLASS_INSTITUTION = "TOP_CLASS_INSTITUTION"
    FOREIGN_ADMISSION = "FOREIGN_ADMISSION"

class AttestationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PROVISIONAL = "PROVISIONAL"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"

class PaymentState(str, Enum):
    INITIATED = "INITIATED"
    CREDITED = "CREDITED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"

class ReviewDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_MORE_INFO = "NEEDS_MORE_INFO"

class MitraScope(str, Enum):
    UPLOAD_DOCS = "UPLOAD_DOCS"
    FILL_FORM = "FILL_FORM"
    VIEW_STATUS = "VIEW_STATUS"
    FULL_ACCESS = "FULL_ACCESS"

class NotificationChannel(str, Enum):
    PUSH = "PUSH"
    SMS = "SMS"
    IVR = "IVR"
    WHATSAPP = "WHATSAPP"
    JAGO = "JAGO"
""",
    "services/core/app/shared/errors.py": """class ScholarSetuError(Exception):
    pass

class NotFoundError(ScholarSetuError):
    pass

class ConflictError(ScholarSetuError):
    pass

class ValidationError(ScholarSetuError):
    pass

class AuthorizationError(ScholarSetuError):
    pass

class ExternalServiceError(ScholarSetuError):
    pass

class AdapterError(ScholarSetuError):
    pass

class ConsentRequiredError(ScholarSetuError):
    pass

class ConsentExpiredError(ScholarSetuError):
    pass

class SchemeConflictError(ScholarSetuError):
    pass

class AttestationExpiredError(ScholarSetuError):
    pass
""",
    "services/core/app/shared/security.py": """def create_jwt_token(data: dict) -> str:
    pass

def verify_jwt_token(token: str) -> dict:
    pass

def hash_password(password: str) -> str:
    pass

def generate_otp() -> str:
    pass
""",
    "services/core/app/shared/hashing.py": """import hashlib
import json
from typing import Any, Dict

def compute_hash(event_data: Dict[str, Any], prev_hash: str) -> str:
    data_str = json.dumps(event_data, sort_keys=True)
    combined = f"{prev_hash}{data_str}"
    return hashlib.sha256(combined.encode()).hexdigest()
"""
}

modules = [
    "gateway", "ledger", "verification", "attestation", "eligibility",
    "dbt_guardian", "wallet", "consent", "nudge", "jago_skill", "reach_radar"
]

for module in modules:
    prefix = f"services/core/app/{module}"
    files[f"{prefix}/__init__.py"] = ""
    files[f"{prefix}/models.py"] = f"""from app.database import Base
from sqlalchemy.orm import mapped_column

class {module.capitalize()}Model(Base):
    __tablename__ = "{module}_table"
    id = mapped_column(primary_key=True)
"""
    files[f"{prefix}/schemas.py"] = f"""from pydantic import BaseModel

class {module.capitalize()}Response(BaseModel):
    message: str
"""
    files[f"{prefix}/router.py"] = f"""from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health():
    return {{"status": "{module} module is healthy"}}
"""
    files[f"{prefix}/service.py"] = f"""from sqlalchemy.ext.asyncio import AsyncSession

class {module.capitalize()}Service:
    def __init__(self, db: AsyncSession):
        self.db = db
"""

for filepath, content in files.items():
    full_path = os.path.join(base_dir, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)

print("Project setup complete!")
