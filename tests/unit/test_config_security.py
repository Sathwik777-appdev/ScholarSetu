"""Phase 1 / S7: the app refuses weak secrets and wildcard CORS."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def _settings(**overrides):
    base = {"JWT_SECRET": "x" * 32, "CORS_ALLOWED_ORIGINS": "http://localhost:5173"}
    base.update(overrides)
    return Settings(_env_file=None, **base)


def test_missing_jwt_secret_refuses(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None)


def test_short_jwt_secret_refuses():
    with pytest.raises(ValidationError, match="at least 32"):
        _settings(JWT_SECRET="short-secret")


def test_wildcard_cors_refused():
    with pytest.raises(ValidationError, match="explicit origins"):
        _settings(CORS_ALLOWED_ORIGINS="*")


def test_short_service_token_refused():
    with pytest.raises(ValidationError, match="SKILL_SERVICE_TOKEN"):
        _settings(SKILL_SERVICE_TOKEN="tooshort")


def test_defaults_are_safe():
    s = _settings()
    assert s.DEMO_MODE is False
    assert s.JWT_EXPIRE_MINUTES <= 60
    assert s.cors_origins == ["http://localhost:5173"]


def test_rejected_secret_is_not_echoed_in_errors():
    with pytest.raises(ValidationError) as exc:
        _settings(JWT_SECRET="leaky-but-short")
    assert "leaky-but-short" not in str(exc.value)
