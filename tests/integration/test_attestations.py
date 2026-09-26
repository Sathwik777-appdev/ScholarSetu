"""C8: persistent Ed25519 key, full-payload JWS, tamper detection, UUIDv7 ids, DB persistence."""

import base64
import json
import os
import stat
import uuid

import jwt
import pytest

from app.attestation.keys import SigningKeyUnavailable, get_signer, load_or_create_signing_key, reset_signer
from app.attestation.models import Attestation
from app.attestation.service import AttestationService
from app.shared.types import AttestationStatus, ClaimType, VerificationMethod
from tests.conftest import SUNITA_STUDENT, make_student

SIGNED_FIELDS = {"iss", "attestation_id", "subject", "claim", "source", "method", "confidence",
                 "evidence_hash", "issued_at", "valid_until", "status"}


@pytest.fixture
async def service(db):
    await make_student(db, **SUNITA_STUDENT)
    return AttestationService(db, get_signer())


async def _issue(service: AttestationService) -> Attestation:
    att = await service.issue_attestation(
        student_id=SUNITA_STUDENT["id"], claim_type=ClaimType.ST_STATUS, claim_value={"tribe": "Santal"},
        source="e-District", method=VerificationMethod.API, confidence=0.97, evidence_hash="sha256:abc")
    await service.db.commit()
    return att


async def test_restart_does_not_invalidate_old_attestations(service, db):
    att = await _issue(service)
    kid_before = service.jwk["kid"]

    reset_signer()  # simulate a process restart: the key is reloaded from ATTESTATION_PRIVATE_KEY_PATH
    db.expunge_all()
    after = AttestationService(db, get_signer())

    assert after.signer is not service.signer
    assert after.jwk["kid"] == kid_before
    assert (await after.verify_attestation(att.id)).is_valid          # stored copy, looked up by id
    assert after.verify_jws(att.signature).is_valid                   # presented JWS, offline check


async def test_signature_covers_every_field(service):
    att = await _issue(service)
    payload = service.signer.decode(att.signature)
    assert set(payload) == SIGNED_FIELDS
    assert payload["confidence"] == 0.97 and payload["method"] == "API" and payload["status"] == "ACTIVE"
    assert payload["claim"] == {"type": "ST_STATUS", "value": {"tribe": "Santal"}}
    assert jwt.get_unverified_header(att.signature)["alg"] == "EdDSA"


async def test_tampering_with_stored_confidence_breaks_verification(service, db):
    att = await _issue(service)
    assert (await service.verify_attestation(att.id)).is_valid
    att.confidence = 0.2
    await db.commit()
    result = await service.verify_attestation(att.id)
    assert not result.is_valid and "does not match" in result.reason


async def test_tampering_with_jws_payload_breaks_signature(service):
    att = await _issue(service)
    header, payload_b64, sig = att.signature.split(".")
    payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)))
    payload["confidence"] = 1.0
    forged_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    result = service.verify_jws(f"{header}.{forged_payload}.{sig}")
    assert not result.is_valid and result.reason == "Invalid cryptographic signature"


async def test_status_change_is_signed(service):
    att = await _issue(service)
    await service.set_status(att, AttestationStatus.REVOKED)
    assert service.signer.decode(att.signature)["status"] == "REVOKED"
    result = await service.verify_attestation(att.id)
    assert not result.is_valid and "REVOKED" in result.reason


async def test_provisional_attestations_are_not_reused(service):
    await service.issue_attestation(SUNITA_STUDENT["id"], ClaimType.INCOME, {"annual_income": 1}, "e-District",
                                    VerificationMethod.API, 0.5, None, status=AttestationStatus.PROVISIONAL)
    assert await service.find_valid_attestations(SUNITA_STUDENT["id"], [ClaimType.INCOME]) == {}


async def test_attestation_ids_are_uuidv7(service):
    att = await _issue(service)
    assert uuid.UUID(att.id).version == 7


def test_missing_key_refuses_outside_demo_mode(tmp_path):
    with pytest.raises(SigningKeyUnavailable):
        load_or_create_signing_key(str(tmp_path / "missing.pem"), demo_mode=False)
    assert not (tmp_path / "missing.pem").exists()


def test_missing_key_is_generated_in_demo_mode(tmp_path):
    path = tmp_path / "keys" / "demo.pem"
    key = load_or_create_signing_key(str(path), demo_mode=True)
    assert path.exists() and stat.S_IMODE(os.stat(path).st_mode) == 0o600
    reloaded = load_or_create_signing_key(str(path), demo_mode=False)
    assert reloaded.public_key().public_bytes_raw() == key.public_key().public_bytes_raw()


def test_public_jwk_shape():
    jwk = get_signer().jwk
    assert jwk["kty"] == "OKP" and jwk["crv"] == "Ed25519" and jwk["alg"] == "EdDSA"
    assert len(base64.urlsafe_b64decode(jwk["x"] + "=")) == 32
