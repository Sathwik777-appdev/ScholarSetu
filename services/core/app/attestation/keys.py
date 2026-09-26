"""Loading, creating and publishing the Ed25519 attestation signing key."""

import base64
import hashlib
import json
import logging
import os
from pathlib import Path

import jwt

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from app.config import settings

logger = logging.getLogger("scholarsetu.attestation")


class SigningKeyUnavailable(RuntimeError):
    pass


def load_or_create_signing_key(path: str, demo_mode: bool) -> Ed25519PrivateKey:
    """Load the PEM key at `path`. If it is missing, create one only in demo mode; otherwise refuse."""
    key_path = Path(path)
    if key_path.exists():
        key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise SigningKeyUnavailable(f"{path} is not an Ed25519 private key")
        return key

    if not demo_mode:
        raise SigningKeyUnavailable(
            f"Attestation signing key not found at {path}. Create one with `make keys` "
            "(or set DEMO_MODE=true to have a demo key generated)."
        )

    key = Ed25519PrivateKey.generate()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption())
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(pem)
    logger.warning("DEMO_MODE: generated a new attestation signing key at %s. Do not use this key in production.", path)
    return key


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def public_jwk(public_key: Ed25519PublicKey) -> dict:
    """RFC 8037 OKP JWK with an RFC 7638 thumbprint as the key id."""
    raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    x = _b64url(raw)
    thumbprint_input = json.dumps({"crv": "Ed25519", "kty": "OKP", "x": x}, separators=(",", ":"), sort_keys=True)
    kid = _b64url(hashlib.sha256(thumbprint_input.encode()).digest())
    return {"kty": "OKP", "crv": "Ed25519", "x": x, "kid": kid, "alg": "EdDSA", "use": "sig"}


class AttestationSigner:
    """Signs and verifies attestation payloads as compact JWS (EdDSA)."""

    ISSUER = "scholarsetu"

    def __init__(self, private_key: Ed25519PrivateKey):
        self._private_key = private_key
        self.public_key = private_key.public_key()
        self.jwk = public_jwk(self.public_key)

    def sign(self, payload: dict) -> str:
        return jwt.encode(payload, self._private_key, algorithm="EdDSA", headers={"kid": self.jwk["kid"], "typ": "JWT"})

    def decode(self, token: str) -> dict:
        """Verify the signature and return the payload. Raises jwt.InvalidTokenError otherwise."""
        return jwt.decode(token, self.public_key, algorithms=["EdDSA"], issuer=self.ISSUER,
                          options={"verify_exp": False, "verify_aud": False})


_signer: "AttestationSigner | None" = None


def get_signer() -> AttestationSigner:
    """Process-wide signer; loading it at startup makes the API refuse to start without a key."""
    global _signer
    if _signer is None:
        _signer = AttestationSigner(load_or_create_signing_key(settings.ATTESTATION_PRIVATE_KEY_PATH, settings.DEMO_MODE))
    return _signer


def reset_signer() -> None:
    """Drop the cached signer (tests use this to simulate a restart)."""
    global _signer
    _signer = None
