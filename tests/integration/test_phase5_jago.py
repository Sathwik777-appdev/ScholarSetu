"""Phase 5 (C5): JAGO answers only from the ledger, the eligibility engine and the official guidelines."""

import re
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.config import settings
from app.ledger.models import Application, Payment
from app.ledger.service import LedgerService
from app.shared.types import PaymentState

RUPEES = re.compile(r"(?:Rs|₹)\s?([\d,]+(?:\.\d+)?)")


async def chat(client, headers, message, language="en"):
    r = await client.post("/v1/jago/chat", headers=headers, json={"message": message, "language": language})
    assert r.status_code == 200, r.text
    return r.json()


def ledger_figures(money: dict) -> set[float]:
    figures = {money[k] for k in ("total_sanctioned", "total_credited", "total_failed", "total_pending")}
    for app in money["applications"]:
        figures |= {app["sanctioned"], app["credited"], app["failed"], app["pending"]}
        figures |= {p["amount"] for p in app["instalments"]}
    return figures


async def _sanction_and_send(db, app_id, fail_second=False):
    """Move Sunita's application to money so JAGO has sanctioned, sent and failed amounts to report."""
    ledger = LedgerService(db)
    app = await db.get(Application, app_id)
    payments = await ledger.sanction(app, [("Maintenance allowance", Decimal("5000")),
                                           ("Compulsory fees", Decimal("3200"))], "system:test")
    await ledger.update_payment(app, payments[0].id, PaymentState.INITIATED, "system:test", pfms_ref="PFMS-T-1")
    if fail_second:
        await ledger.update_payment(app, payments[1].id, PaymentState.INITIATED, "system:test", pfms_ref="PFMS-T-2")
        await ledger.update_payment(app, payments[1].id, PaymentState.FAILED, "system:test",
                                    failure_code="AADHAAR_NOT_SEEDED")
    await db.commit()


# ── money comes only from the ledger ─────────────────────────────────────────


@pytest.mark.parametrize("language", ["en", "hi"])
async def test_every_rupee_figure_matches_the_ledger(client, db, demo, users, language):
    await _sanction_and_send(db, demo["sunita_application"], fail_second=True)
    for who in ("sunita", "rahul"):
        headers = await users.headers(who)
        money = (await client.get("/v1/me/payments", headers=headers)).json()
        answer = await chat(client, headers, "Mera paisa kab aayega?", language)
        assert answer["intent"] == "payment_info"
        quoted = {float(m.replace(",", "")) for m in RUPEES.findall(answer["response_text"])}
        assert quoted, answer["response_text"]
        assert quoted <= ledger_figures(money), f"{who}: {quoted - ledger_figures(money)} not in the ledger"


async def test_old_hardcoded_answers_are_gone(client, demo, users):
    text = (await chat(client, await users.headers("sunita"), "When will I get my payment?"))["response_text"]
    assert "APP123" not in text and "12,000" not in text and "12000" not in text


async def test_unsanctioned_application_gets_no_invented_date(client, demo, users):
    answer = await chat(client, await users.headers("sunita"), "Mera paisa kab aayega?")
    assert answer["intent"] == "payment_info"
    assert demo["sunita_application"] in answer["response_text"]
    assert "Nothing has been sanctioned yet" in answer["response_text"]
    assert not RUPEES.search(answer["response_text"])


async def test_payment_in_transit_and_failed_are_reported_from_the_ledger(client, db, demo, users):
    await _sanction_and_send(db, demo["sunita_application"], fail_second=True)
    text = (await chat(client, await users.headers("sunita"), "Has my scholarship been credited?"))["response_text"]
    assert "Rs 5,000 (instalment 1) was sent to PFMS" in text and "no credit date" in text
    assert "Rs 3,200 (instalment 2) failed: AADHAAR_NOT_SEEDED" in text


async def test_status_answer_comes_from_the_ledger(client, demo, users):
    answer = await chat(client, await users.headers("sunita"), "What is the status of my application?")
    assert answer["intent"] == "status_check"
    assert demo["sunita_application"] in answer["response_text"]
    assert "district/state authority" in answer["response_text"]
    assert answer["tool_calls_made"][0]["tool_name"] == "get_applications"


async def test_pending_actions_answer(client, demo, users):
    await client.post(f"/v1/officer/applications/{demo['sunita_application']}/deficiencies",
                      headers=await users.headers("district"),
                      json={"code": "INCOME_CERT_EXPIRED", "description": "Upload the FY 2026-27 income certificate"})
    answer = await chat(client, await users.headers("sunita"), "Mere form me kya kami hai?")
    assert answer["intent"] == "deficiency_help"
    assert "Upload the FY 2026-27 income certificate" in answer["response_text"]


# ── guidelines: cited official text, or an honest "don't know" ──────────────


async def test_income_limit_question_is_answered_with_a_citation(client, demo, users):
    answer = await chat(client, await users.headers("sunita"), "What is the income limit for post matric?")
    assert answer["intent"] == "guideline_query"
    assert answer["citations"], answer
    top = answer["citations"][0]
    assert "Post-matric" in top["url"] or "Post-matric" in top["source"] or "Post Matric" in top["source"]
    assert re.search(r"2,50,000|2\.50 lakh", answer["response_text"]), answer["response_text"]
    assert top["url"].startswith("https://")


async def test_hindi_guideline_question_finds_the_english_passage(client, demo, users):
    answer = await chat(client, await users.headers("sunita"), "पोस्ट मैट्रिक छात्रवृत्ति के लिए आय सीमा क्या है", "hi")
    assert answer["intent"] == "guideline_query" and answer["citations"]
    assert answer["citations"][0]["url"].endswith("Post-matric-guidelines-ST.pdf")


async def test_nothing_relevant_means_i_dont_know(client, demo, users, monkeypatch):
    monkeypatch.setattr(settings, "GUIDELINE_MIN_SCORE", 0.99)
    answer = await chat(client, await users.headers("sunita"), "What is the rule for hostel curfew?")
    assert answer["intent"] == "guideline_query" and answer["citations"] == []
    assert "I don't have this information" in answer["response_text"]
    assert "nodal officer" in answer["response_text"]  # no invented helpline number


async def test_public_guideline_search(client, demo):
    r = await client.get("/v1/jago/guidelines/search", params={"query": "age limit for overseas scholarship"})
    assert r.status_code == 200 and r.json()
    assert r.json()[0]["scheme"] == "NOS" and r.json()[0]["url"].startswith("https://tribal.nic.in/")


# ── language and error handling ─────────────────────────────────────────────


async def test_unsupported_language_falls_back_to_hindi(client, demo, users):
    answer = await chat(client, await users.headers("sunita"), "status", "sat")
    assert answer["language"] == "hi" and answer["language_note"]


async def test_bad_tool_parameters_are_422(client, users):
    service = {"X-Service-Token": settings.SKILL_SERVICE_TOKEN, "X-Student-Session": await users.token("sunita")}
    r = await client.post("/v1/skill/tools/check_eligibility", headers=service, json={"scheme": "MOON_SCHEME"})
    assert r.status_code == 422
    r = await client.post("/v1/skill/tools/get_timeline", headers=service, json={"application_id": "APP-NOPE"})
    assert r.status_code == 404


async def test_internal_errors_never_leak(client, users, monkeypatch):
    from app.jago_skill import service as jago_service

    async def boom(*args, **kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(jago_service.JAGOSkillService, "process_message", boom)
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t") as c:
        r = await c.post("/v1/jago/chat", headers=await users.headers("sunita"), json={"message": "hi"})
    assert r.status_code == 500
    assert r.json()["detail"] == "Internal error" and "error_id" in r.json()
    assert "secret internal detail" not in r.text and "Traceback" not in r.text


async def test_skill_tool_money_matches_ledger(client, db, demo, users):
    await _sanction_and_send(db, demo["sunita_application"])
    service = {"X-Service-Token": settings.SKILL_SERVICE_TOKEN, "X-Student-Session": await users.token("sunita")}
    tool = (await client.post("/v1/skill/tools/get_payments", headers=service, json={})).json()["result"]
    ledger = (await client.get("/v1/me/payments", headers=await users.headers("sunita"))).json()
    assert tool["total_sanctioned"] == ledger["total_sanctioned"] == 8200
    payments = (await db.execute(select(Payment))).scalars().all()
    assert sum(float(p.amount) for p in payments if p.application_id == demo["sunita_application"]) == 8200


async def test_hindi_status_answer_has_no_english_step(client, demo, users):
    answer = await chat(client, await users.headers("sunita"), "Meri application ka status kya hai?", "hi")
    assert "आगे:" in answer["response_text"] and "verifying" not in answer["response_text"]


async def test_readiness_reports_guideline_index(client):
    body = (await client.get("/health/ready")).json()
    assert body["checks"]["guideline_index"].startswith("ok (")
