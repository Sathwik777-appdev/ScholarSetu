"""Security utilities: access tokens, OTP generation and hashing, service-token checks."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

from app.config import settings
from app.shared.ids import new_id

ACCESS_TOKEN_TYPE = "access"
_JWT_ALGORITHM = "HS256"


def create_access_token(user_id: str, role: str, expires_delta: Optional[timedelta] = None) -> tuple[str, int]:
    """Sign a short-lived access token. Returns (token, expires_in_seconds).

    Only the user id is authoritative; the role claim is informational and is
    re-read from the users table on every request.
    """
    now = datetime.now(timezone.utc)
    ttl = expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    claims = {
        "sub": user_id,
        "role": role,
        "typ": ACCESS_TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "jti": new_id(),
    }
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=_JWT_ALGORITHM), int(ttl.total_seconds())


def decode_access_token(token: str) -> Dict[str, Any]:
    """Verify signature, expiry and token type. Raises jwt.InvalidTokenError on any failure."""
    claims = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[_JWT_ALGORITHM],
        options={"require": ["sub", "exp", "iat", "typ"]},
    )
    if claims.get("typ") != ACCESS_TOKEN_TYPE:
        raise jwt.InvalidTokenError("wrong token type")
    return claims


def generate_otp(length: int = 6) -> str:
    """Generate a cryptographically random numeric OTP."""
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_otp(challenge_id: str, otp: str) -> str:
    """Keyed hash of an OTP, bound to its challenge so hashes cannot be replayed across challenges."""
    key = hmac.new(settings.JWT_SECRET.encode(), b"scholarsetu-otp-v1", hashlib.sha256).digest()
    return hmac.new(key, f"{challenge_id}:{otp}".encode(), hashlib.sha256).hexdigest()


def otp_matches(challenge_id: str, otp: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(challenge_id, otp), stored_hash)


def service_token_matches(presented: Optional[str]) -> bool:
    expected = settings.SKILL_SERVICE_TOKEN
    if not expected or not presented:
        return False
    return hmac.compare_digest(presented.encode(), expected.encode())
