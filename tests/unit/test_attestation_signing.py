"""Phase 1 / C8: persistent Ed25519 key, full-payload JWS, tamper detection, UUIDv7 ids."""

import base64
import json
import os
import stat
import uuid

import jwt
import pytest

from app.attestation.keys import SigningKeyUnavailable, load_or_create_signing_key
from app.attestation.service import AttestationService, get_attestation_service, reset_attestation_service
from app.config import settings
from app.shared.types import ClaimType

SIGNED_FIELDS = {"iss", "attestation_id", "subject", "claim", "source", "method", "confidence",
                 "evidence_hash", "issued_at", "valid_until", "status"}


async def _issue(service: AttestationService):
    return await service.issue_attestation(
        student_id="stu-test-1", claim_type=ClaimType.ST_STATUS, claim_value={"tribe": "Santal"},
        source="DIGILOCKER", method="API", confidence=0.97, evidence_hash="sha256:abc")


async def test_restart_does_not_invalidate_old_attestations():
    reset_attestation_service()
    before = get_attestation_service()
    att = await _issue(before)
    kid_before = before.jwk["kid"]

    reset_attestation_service()  # simulate a process restart: key is reloaded from ATTESTATION_PRIVATE_KEY_PATH
    after = get_attestation_service()

    assert after is not before
    assert after.jwk["kid"] == kid_before
    assert after.verify_jws(att.signature).is_valid


async def test_signature_covers_every_field():
    service = get_attestation_service()
    att = await _issue(service)
    payload = service.decode_jws(att.signature)
    assert set(payload) == SIGNED_FIELDS
    assert payload["confidence"] == 0.97
    assert payload["claim"] == {"type": "ST_STATUS", "value": {"tribe": "Santal"}}
    assert jwt.get_unverified_header(att.signature)["alg"] == "EdDSA"


async def test_tampering_with_stored_confidence_breaks_verification():
    service = get_attestation_service()
    att = await _issue(service)
    assert (await service.verify_attestation(att.attestation_id)).is_valid

    service._store[att.attestation_id].confidence = 0.2
    result = await service.verify_attestation(att.attestation_id)
    assert not result.is_valid
    assert "does not match" in result.reason


async def test_tampering_with_jws_payload_breaks_signature():
    service = get_attestation_service()
    att = await _issue(service)
    header, payload_b64, sig = att.signature.split(".")
    payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)))
    payload["confidence"] = 1.0
    forged_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    forged = f"{header}.{forged_payload}.{sig}"

    result = service.verify_jws(forged)
    assert not result.is_valid
    assert result.reason == "Invalid cryptographic signature"


async def test_revocation_is_signed():
    service = get_attestation_service()
    att = await _issue(service)
    await service.revoke_attestation(att.attestation_id, "test")
    stored = service._store[att.attestation_id]
    assert service.decode_jws(stored.signature)["status"] == "REVOKED"
    result = await service.verify_attestation(att.attestation_id)
    assert not result.is_valid and "REVOKED" in result.reason


async def test_attestation_ids_are_uuidv7():
    att = await _issue(get_attestation_service())
    assert uuid.UUID(att.attestation_id).version == 7


def test_missing_key_refuses_outside_demo_mode(tmp_path):
    with pytest.raises(SigningKeyUnavailable):
        load_or_create_signing_key(str(tmp_path / "missing.pem"), demo_mode=False)
    assert not (tmp_path / "missing.pem").exists()


def test_missing_key_is_generated_in_demo_mode(tmp_path):
    path = tmp_path / "keys" / "demo.pem"
    key = load_or_create_signing_key(str(path), demo_mode=True)
    assert path.exists()
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    reloaded = load_or_create_signing_key(str(path), demo_mode=False)
    assert reloaded.public_key().public_bytes_raw() == key.public_key().public_bytes_raw()


def test_public_jwk_shape():
    jwk = get_attestation_service().jwk
    assert jwk["kty"] == "OKP" and jwk["crv"] == "Ed25519" and jwk["alg"] == "EdDSA"
    assert len(base64.urlsafe_b64decode(jwk["x"] + "=")) == 32
    assert settings.ATTESTATION_PRIVATE_KEY_PATH.endswith(".pem")
