"""Every event the core publishes must match contracts/events.schema.json (what consumers code against)."""

import json
from decimal import Decimal
from pathlib import Path

import jsonschema
from sqlalchemy import select

from app.ledger.models import Application, Deficiency, OutboxMessage
from app.ledger.service import LedgerService
from app.shared.types import CanonicalState, PaymentState

SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "contracts" / "events.schema.json").read_text())


async def _drive_a_full_lifecycle(db, demo):
    ledger = LedgerService(db)
    app = await db.get(Application, demo["sunita_application"])
    await ledger.raise_deficiency(app, "INCOME_CERT_EXPIRED", "Upload a current income certificate",
                                  "DISTRICT_OFFICER", "system:test")
    await db.commit()
    deficiency_id = (await db.execute(select(Deficiency.id).where(Deficiency.application_id == app.id))).scalar_one()
    await ledger.respond_deficiency(app, deficiency_id, {"response_text": "Uploaded", "document_ids": []},
                                    "system:test")
    await ledger.transition(app, CanonicalState.INSTITUTE_VERIFICATION, "system:test")
    await ledger.transition(app, CanonicalState.AUTHORITY_VERIFICATION, "system:test")
    [payment] = await ledger.sanction(app, [("Maintenance allowance", Decimal("5000"))], "system:test")
    await ledger.update_payment(app, payment.id, PaymentState.INITIATED, "system:test", pfms_ref="PFMS-C1")
    await ledger.update_payment(app, payment.id, PaymentState.FAILED, "system:test", failure_code="ACCOUNT_CLOSED")
    await db.commit()


async def test_published_events_match_the_contract(db, demo):
    await _drive_a_full_lifecycle(db, demo)
    messages = (await db.execute(select(OutboxMessage))).scalars().all()
    assert len(messages) >= 10
    validator = jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker())
    problems = {}
    for m in messages:
        errors = [e.message for e in validator.iter_errors(m.payload)]
        if errors:
            problems.setdefault(m.payload.get("type"), errors[0])
    assert problems == {}, f"events that break the contract: {problems}"
    # The contract is enforced, not decorative: a malformed ledger event is rejected.
    broken = {**messages[0].payload, "payload": {"application_id": "APP-1"}}
    assert not validator.is_valid(broken)
    seen = {m.payload["type"] for m in messages}
    assert {"ApplicationCreated", "DeficiencyRaised", "Sanctioned", "PaymentFailed"} <= seen


async def test_verification_consent_and_dbt_events_match_the_contract(client, db, demo, users, gov):
    from tests.conftest import grant_consent
    sunita = await users.headers("sunita")
    claims = ["IDENTITY", "ST_STATUS", "INCOME"]
    consent_id = await grant_consent(client, sunita, claims)
    r = await client.post("/v1/verify/claims", headers=sunita, json={
        "application_id": demo["sunita_application"], "required_claims": claims, "consent_id": consent_id})
    assert r.status_code == 200
    assert (await client.post(f"/v1/dbt/health-check/{demo['sunita_application']}", headers=sunita)).status_code == 200
    assert (await client.delete(f"/v1/consents/{consent_id}", headers=sunita)).status_code == 200

    validator = jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker())
    messages = (await db.execute(select(OutboxMessage))).scalars().all()
    seen = {m.payload["type"] for m in messages}
    assert {"ConsentGranted", "VerificationCompleted", "ReviewCaseOpened", "DBTHealthChecked", "ConsentRevoked"} <= seen
    bad = {m.payload["type"]: next(validator.iter_errors(m.payload)).message
           for m in messages if not validator.is_valid(m.payload)}
    assert bad == {}
