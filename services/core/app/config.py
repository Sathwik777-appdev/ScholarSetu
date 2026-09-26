import os

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
    SQL_ECHO: bool = False
    REDIS_URL: str = "redis://localhost:6379"
    NATS_URL: str = "nats://localhost:4222"
    MINIO_URL: str = "http://localhost:9000"
    MOCK_SERVICE_URL: str = "http://localhost:8100"

    # No default: the app refuses to start without a strong secret.
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int = 15

    OTP_TTL_MINUTES: int = 5
    OTP_MAX_ATTEMPTS: int = 5

    # Demo mode lets seeded demo users log in with DEMO_OTP. Off by default.
    DEMO_MODE: bool = False
    DEMO_OTP: str = "123456"

    ATTESTATION_PRIVATE_KEY_PATH: str = "secrets/attestation_ed25519.pem"

    # Shared secret JAGO presents on /v1/skill/tools/*. Unset = skill endpoints disabled.
    SKILL_SERVICE_TOKEN: str | None = None

    # Comma-separated list of browser origins allowed to call the API with credentials.
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"

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

    # Publish the transactional outbox to NATS from the API process.
    OUTBOX_PUBLISHER_ENABLED: bool = True

    LOG_LEVEL: str = "INFO"

    @field_validator("JWT_SECRET")
    @classmethod
    def _strong_jwt_secret(cls, v: str) -> str:
        if len(v) < MIN_SECRET_LENGTH:
            raise ValueError(f"JWT_SECRET must be at least {MIN_SECRET_LENGTH} characters")
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

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
