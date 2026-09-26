"""Loading, creating and publishing the Ed25519 attestation signing key."""

import base64
import hashlib
import json
import logging
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

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
