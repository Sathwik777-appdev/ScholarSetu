import os
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.shared.types import CanonicalState

MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Tests point this at a non-existent file so a developer's .env never leaks in.
        env_file=os.environ.get("SCHOLARSETU_ENV_FILE", ".env"),
        extra="ignore",
        # Never echo a rejected value (it may be a secret) in validation errors.
        hide_input_in_errors=True,
    )

    DATABASE_URL: str = "postgresql+asyncpg://scholarsetu:scholarsetu_dev@localhost:5432/scholarsetu"
    # NullPool avoids sharing asyncpg connections across event loops (used by the test suite).
    DATABASE_NULL_POOL: bool = False
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    SQL_ECHO: bool = False
    REDIS_URL: str = "redis://localhost:6379"
    NATS_URL: str = "nats://localhost:4222"
    MINIO_URL: str = "http://localhost:9000"
    # Object storage for wallet documents. No defaults: without credentials the wallet reports 503.
    MINIO_ACCESS_KEY: str | None = None
    MINIO_SECRET_KEY: str | None = None
    MINIO_BUCKET: str = "scholarsetu-wallet"
    WALLET_MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024
    MOCK_SERVICE_URL: str = "http://localhost:8100"

    # No default: the app refuses to start without a strong secret.
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int = 15
    # A refresh token renews the short access token without signing in again. Rotated on every use; a reused
    # (stolen) one revokes the whole family. Idle for this long = sign in again.
    REFRESH_TOKEN_DAYS: int = 30

    OTP_TTL_MINUTES: int = 5
    OTP_MAX_ATTEMPTS: int = 5
    # Per phone and purpose, over a rolling hour: codes that may be requested, and wrong guesses (across
    # all codes) before the phone is locked out. A new code does not reset the guess count.
    OTP_REQUESTS_PER_HOUR: int = 5
    OTP_FAILURES_PER_HOUR: int = 10
    # Per client address over 10 minutes, across all phone numbers (app/shared/ratelimit.py).
    IP_CODE_REQUESTS_PER_10_MIN: int = 30
    IP_CODE_CHECKS_PER_10_MIN: int = 60

    # Demo mode lets seeded demo users log in with DEMO_OTP. Off by default.
    DEMO_MODE: bool = False
    DEMO_OTP: str = "123456"

    # Console sign-in codes by email (app/gateway/email.py): Microsoft 365 SMTP with STARTTLS.
    # SMTP_PASSWORD comes from Secret Manager; without it no code is emailed (logged as a warning).
    SMTP_HOST: str = "smtp.office365.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = "contact@yugnext-ai.com"
    SMTP_FROM: str | None = None  # defaults to SMTP_USERNAME
    SMTP_FROM_NAME: str = "ScholarSetu"
    SMTP_PASSWORD: str | None = None

    ATTESTATION_PRIVATE_KEY_PATH: str = "secrets/attestation_ed25519.pem"

    # Shared secret JAGO presents on /v1/skill/tools/*. Unset = skill endpoints disabled.
    SKILL_SERVICE_TOKEN: str | None = None

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.8-flash"

    # DigiLocker, authorised-partner OAuth 2.0 (authorisation code + PKCE).
    #   mock       the test DigiLocker in mocks/: documents are test data, never issuer-signed, and never
    #              count as proof in verification unless DEMO_MODE is on
    #   sandbox    DigiLocker's partner sandbox (also test data)
    #   production the real service
    # Going live changes configuration only: DIGILOCKER_MODE, the two URLs and the client credentials.
    DIGILOCKER_MODE: str = "mock"
    DIGILOCKER_API_URL: str | None = None        # server-to-server base; mock default MOCK_SERVICE_URL/digilocker
    DIGILOCKER_AUTHORIZE_URL: str | None = None  # the page the student's browser opens (see digilocker_authorize_url)
    DIGILOCKER_CLIENT_ID: str | None = None
    DIGILOCKER_CLIENT_SECRET: str | None = None
    # True while verification answers come from the test government services (mocks/). Attestations issued from
    # them are marked test_data, shown as "(test)" and carry test_data in the signed payload, so a scanned passport
    # never claims UIDAI or e-District confirmed something the synthetic services made up. Set false when the
    # real sources are connected.
    SOURCES_ARE_TEST: bool = True

    # Where DigiLocker returns a person after "Sign in with DigiLocker": the app's scheme. It must be registered
    # with the DigiLocker partner client (the sandbox client uses scholarsetu://digilocker-callback).
    DIGILOCKER_LOGIN_REDIRECT_URI: str = "scholarsetu://digilocker-callback"
    # Public address of this API, for OAuth redirects (e.g. https://scholarsetu-api-....run.app).
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # Comma-separated list of browser origins allowed to call the API with credentials.
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:8080"  # Vite dev server, compose console

    MITRA_MAX_SESSION_MINUTES: int = 30

    # Identity Resolver (ARCHITECTURE.md §6.4.3). Tune on anonymised pilot data.
    IDENTITY_AUTO_VERIFY_THRESHOLD: float = 0.92   # name score for auto-verify (also needs corroboration)
    IDENTITY_REVIEW_THRESHOLD: float = 0.75        # below this: manual review
    IDENTITY_TOKEN_MISMATCH_THRESHOLD: float = 0.85  # a name token scoring below this is a different name
    IDENTITY_INITIAL_SCORE: float = 0.90           # "S." vs "Sunita": consistent but never enough to auto-verify
    IDENTITY_EXTRA_TOKEN_PENALTY: float = 0.97     # per given-name token present on only one record
    IDENTITY_REORDER_PENALTY: float = 0.98         # surname written first, etc.
    IDENTITY_MISSING_SURNAME_CAP: float = 0.85     # one record has no surname

    # Days an application may sit in a state before its SLA is breached (targets, not official norms).
    SLA_DAYS_SUBMITTED: float = 7
    SLA_DAYS_INSTITUTE_VERIFICATION: float = 15
    SLA_DAYS_RESUBMITTED: float = 7
    SLA_DAYS_AUTHORITY_VERIFICATION: float = 21
    SLA_DAYS_SANCTIONED: float = 15
    SLA_DAYS_PAYMENT_INITIATED: float = 10
    SLA_DAYS_PAYMENT_FAILED: float = 7
    ATTESTATION_EXPIRY_WARNING_DAYS: int = 30
    # After a breach, the next officer tier is reminded after this long (institute -> district -> state).
    SLA_ESCALATION_DAYS: float = 3
    # DEMO_MODE only: every SLA and escalation interval becomes this many seconds, to show breaches live.
    SLA_DEMO_SECONDS: int = 120

    # Temporal (durable workflows: SLA timers, DBT retries). Empty = workflows disabled.
    TEMPORAL_ADDRESS: str | None = None
    TEMPORAL_NAMESPACE: str = "default"
    TEMPORAL_TASK_QUEUE: str = "scholarsetu"
    WORKFLOW_RECONCILE_SECONDS: int = 30

    # Shared secret the SMS gateway sends on inbound webhooks (X-SMS-Gateway-Token). Empty = inbound disabled.
    SMS_GATEWAY_TOKEN: str | None = None

    # JAGO guideline search (ARCHITECTURE.md §6.7): multilingual embeddings in pgvector + keyword match.
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_CACHE_DIR: str | None = None
    # Below this JAGO says it could not find an answer. Chosen on tests/integration/test_guideline_retrieval.py:
    # unrelated questions score <= 0.16, the weakest correct answer about 0.3.
    GUIDELINE_MIN_SCORE: float = 0.25
    # Human helpline JAGO offers when it cannot answer. No number is invented: unset = institute nodal officer.
    JAGO_HELPLINE: str | None = None

    # Versioned eligibility decision tables (rules/*.json). In the container they live at /rules.
    RULES_DIR: str = next((str(parent / "rules") for parent in Path(__file__).resolve().parents
                           if (parent / "rules").is_dir()), "/rules")
    # Shared secret for privacy-preserving record linkage (CLK v1). No default: Reach Radar is off without it.
    PPRL_HMAC_KEY: str | None = None

    # Portal state maps (adapters/<portal>/state_map.yaml). In the container they live at /adapters.
    ADAPTERS_DIR: str = next((str(parent / "adapters") for parent in Path(__file__).resolve().parents
                              if (parent / "adapters" / "nsp" / "state_map.yaml").is_file()), "/adapters")
    # How often the API polls the portals for status changes (0 disables polling).
    ADAPTER_SYNC_INTERVAL_SECONDS: int = 300
    RETENTION_INTERVAL_SECONDS: int = 21600   # how often old rows are deleted (app/privacy/retention.py); 0 = never
    # Academic years start in this month (e.g. 4 = April: 2026-04-01 starts 2026-27).
    ACADEMIC_YEAR_START_MONTH: int = 4

    # Offline sync holds back ledger events younger than this, so a late-committing transaction is never skipped.
    SYNC_SETTLE_SECONDS: int = 5

    # Run the outbox publisher, notification consumers and portal polling in the Temporal worker process
    # (set OUTBOX_PUBLISHER_ENABLED=false and ADAPTER_SYNC_INTERVAL_SECONDS=0 on the API then).
    WORKER_RUNS_BACKGROUND_JOBS: bool = False
    # Development only: keep wallet files on local disk when no object store is configured. Unset = 503.
    WALLET_LOCAL_DIR: str | None = None

    # Hosted demo only: the private power manager that wakes the sleeping database and VM (deploy/gcp/power-manager).
    # When set, a request that cannot reach the database asks it to wake everything (app/shared/wake.py).
    POWER_MANAGER_URL: str | None = None

    # Publish the transactional outbox to NATS from the API process.
    OUTBOX_PUBLISHER_ENABLED: bool = True

    LOG_LEVEL: str = "INFO"

    @field_validator("JWT_SECRET")
    @classmethod
    def _strong_jwt_secret(cls, v: str) -> str:
        if len(v) < MIN_SECRET_LENGTH:
            raise ValueError(f"JWT_SECRET must be at least {MIN_SECRET_LENGTH} characters")
        return v

    @field_validator("PPRL_HMAC_KEY")
    @classmethod
    def _strong_pprl_key(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        if len(v) < MIN_SECRET_LENGTH:
            raise ValueError(f"PPRL_HMAC_KEY must be at least {MIN_SECRET_LENGTH} characters")
        return v

    @field_validator("SKILL_SERVICE_TOKEN")
    @classmethod
    def _strong_service_token(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        if len(v) < MIN_SECRET_LENGTH:
            raise ValueError(f"SKILL_SERVICE_TOKEN must be at least {MIN_SECRET_LENGTH} characters")
        return v

    @model_validator(mode="after")
    def _no_wildcard_cors(self) -> "Settings":
        if "*" in self.cors_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must list explicit origins; '*' is not allowed with credentials")
        return self

    @property
    def sla_days(self) -> dict[CanonicalState, float]:
        return {state: getattr(self, f"SLA_DAYS_{state.value}")
                for state in CanonicalState if hasattr(self, f"SLA_DAYS_{state.value}")}

    def sla_seconds(self, state: CanonicalState) -> float | None:
        days = self.sla_days.get(state)
        if days is None:
            return None
        return float(self.SLA_DEMO_SECONDS) if self.DEMO_MODE else days * 86400

    @property
    def escalation_seconds(self) -> float:
        return float(self.SLA_DEMO_SECONDS) if self.DEMO_MODE else self.SLA_ESCALATION_DAYS * 86400

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

    @field_validator("DIGILOCKER_MODE")
    @classmethod
    def _digilocker_mode(cls, v: str) -> str:
        if v not in ("mock", "sandbox", "production"):
            raise ValueError("DIGILOCKER_MODE must be mock, sandbox or production")
        return v

    @property
    def digilocker_is_test(self) -> bool:
        """Documents from a mock or sandbox DigiLocker are test data: never issuer-signed."""
        return self.DIGILOCKER_MODE != "production"

    @property
    def digilocker_api_url(self) -> str:
        return (self.DIGILOCKER_API_URL or f"{self.MOCK_SERVICE_URL.rstrip('/')}/digilocker").rstrip("/")

    @property
    def digilocker_authorize_url(self) -> str:
        # The mock runs on a private network, so in mock mode its sign-in page is served through this API.
        default = (f"{self.PUBLIC_BASE_URL.rstrip('/')}/v1/digilocker-test/authorize" if self.DIGILOCKER_MODE == "mock"
                   else f"{self.digilocker_api_url}/public/oauth2/1/authorize")
        return self.DIGILOCKER_AUTHORIZE_URL or default

    @property
    def digilocker_redirect_uri(self) -> str:
        return f"{self.PUBLIC_BASE_URL.rstrip('/')}/v1/digilocker/callback"


settings = Settings()
