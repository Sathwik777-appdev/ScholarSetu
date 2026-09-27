"""Phase 4: persistent ledger, hash chain, IDs, read models, outbox → NATS, nudge, migrations (C2, C4, C7, M5)."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select, text

from app.database import AsyncSessionLocal, engine
from app.ledger.models import Application, LedgerEvent, OutboxMessage
from app.ledger.service import LedgerError, LedgerService
from app.nudge.models import Notification
from app.nudge.service import NudgeService
from app.shared.events import BaseEvent, NATSEventBus, publish_pending
from app.shared.types import CanonicalState, NotificationChannel, SchemeType

CORE = Path(__file__).resolve().parents[2] / "services" / "core"
NATS_URL = os.environ.get("TEST_NATS_URL", "nats://localhost:4223")


# ── hash chain ───────────────────────────────────────────────────────────────


async def test_every_seeded_chain_verifies(client, demo, users):
    officer = await users.headers("district")
    for app_id in demo.values():
        r = await client.get(f"/v1/applications/{app_id}/verify-chain", headers=officer)
        assert r.status_code == 200 and r.json()["valid"] is True and r.json()["events_checked"] >= 3, r.json()


async def test_editing_an_event_by_hand_breaks_the_chain(client, db, demo, users):
    app_id = demo["rahul_application"]
    officer = await users.headers("district")
    # Someone quietly changes a credited amount in the database.
    await db.execute(text("UPDATE ledger_events SET payload = jsonb_set(payload::jsonb, '{amount}', '99999')::json "
                          "WHERE application_id = :a AND type = 'PaymentCredited' AND sequence_no = "
                          "(SELECT min(sequence_no) FROM ledger_events WHERE application_id = :a AND type = 'PaymentCredited')"),
                     {"a": app_id})
    await db.commit()
    body = (await client.get(f"/v1/applications/{app_id}/verify-chain", headers=officer)).json()
    assert body["valid"] is False and body["reason"] == "event content does not match its hash"


async def test_deleting_an_event_breaks_the_chain(client, db, demo, users):
    app_id = demo["sunita_application"]
    await db.execute(text("DELETE FROM ledger_events WHERE application_id = :a AND sequence_no = 2"), {"a": app_id})
    await db.commit()
    body = (await client.get(f"/v1/applications/{app_id}/verify-chain", headers=await users.headers("district"))).json()
    assert body["valid"] is False and body["reason"] == "sequence gap or reorder"


# ── ids, transactions, persistence ───────────────────────────────────────────


async def test_two_applications_get_different_ids_and_chains(client, db, users):
    sunita = await users.headers("sunita")
    ids = []
    for scheme in ("NFST", "NOS"):
        r = await client.post("/v1/applications", headers=sunita, json={"scheme": scheme, "academic_year": "2027-28"})
        assert r.status_code == 201
        ids.append(r.json()["id"])
    assert ids[0] != ids[1]
    assert ids[0].startswith("APP-NFST-2027-") and ids[1].startswith("APP-NOS-2027-")
    first_events = (await db.execute(select(LedgerEvent).where(LedgerEvent.application_id.in_(ids),
                                                               LedgerEvent.sequence_no == 1))).scalars().all()
    assert len(first_events) == 2 and first_events[0].hash != first_events[1].hash
    assert {e.hash_prev for e in first_events} == {"0" * 64}


async def test_create_writes_row_event_and_outbox_together(db, demo):
    ledger = LedgerService(db)
    app = await ledger.create_application("stu-rahul-002", SchemeType.PRE_MATRIC, "2026-27", "system:test")
    await db.rollback()  # nothing committed: the row, its event and its outbox message all disappear
    assert await db.get(Application, app.id) is None
    assert await db.scalar(select(func.count()).select_from(LedgerEvent).where(LedgerEvent.application_id == app.id)) == 0
    assert await db.scalar(select(func.count()).select_from(OutboxMessage).where(
        OutboxMessage.payload["correlation_id"].as_string() == app.id)) == 0


async def test_data_survives_a_restart(demo):
    await engine.dispose()  # drop every connection, as a process restart would
    async with AsyncSessionLocal() as fresh:
        app = await fresh.get(Application, demo["sunita_application"])
        assert app is not None and app.canonical_state == CanonicalState.AUTHORITY_VERIFICATION
        assert (await LedgerService(fresh).verify_chain(app.id)).valid


async def test_invalid_transitions_are_refused(db, demo):
    ledger = LedgerService(db)
    app = await db.get(Application, demo["sunita_application"])
    with pytest.raises(LedgerError) as exc:
        await ledger.transition(app, CanonicalState.CREDITED, "system:test")
    assert exc.value.status_code == 409


# ── read models ──────────────────────────────────────────────────────────────


async def test_money_view_is_computed_from_payments(client, db, demo, users):
    money = (await client.get("/v1/me/payments", headers=await users.headers("rahul"))).json()
    rules = json.loads((Path(__file__).resolve().parents[2] / "rules" / "pre_matric_2026_v1.json").read_text())
    expected = rules["amounts"]["hosteller_per_year"]["value"]["class_9"] + rules["amounts"]["adhoc_grant"]["value"]
    assert money["total_sanctioned"] == money["total_credited"] == expected
    assert money["total_pending"] == 0 and len(money["applications"][0]["instalments"]) == 2
    sunita = (await client.get("/v1/me/payments", headers=await users.headers("sunita"))).json()
    assert sunita["total_sanctioned"] == 0 and sunita["applications"][0]["instalments"] == []


async def test_dashboard_and_pending_actions_follow_a_deficiency(client, demo, users):
    app_id = demo["sunita_application"]
    r = await client.post(f"/v1/officer/applications/{app_id}/deficiencies", headers=await users.headers("district"),
                          json={"code": "INCOME_CERT_EXPIRED", "description": "Upload the FY 2026-27 income certificate"})
    assert r.status_code == 200
    sunita = await users.headers("sunita")
    brief = (await client.get("/v1/me/dashboard", headers=sunita)).json()["applications"][0]
    assert brief["current_state"] == "DEFICIENCY_RAISED"
    assert brief["next_action"] == "Respond to the deficiency: Upload the FY 2026-27 income certificate"
    actions = (await client.get("/v1/me/pending-actions", headers=sunita)).json()
    deficiency = next(a for a in actions if a["type"] == "DEFICIENCY")

    r = await client.post(deficiency["action_url"], headers=sunita, json={"response_text": "Uploaded the new certificate"})
    assert r.status_code == 200 and r.json()["type"] == "DeficiencyResponded"
    brief = (await client.get("/v1/me/dashboard", headers=sunita)).json()["applications"][0]
    assert brief["current_state"] == "RESUBMITTED"
    assert (await client.get("/v1/me/pending-actions", headers=sunita)).json() == []


async def test_sla_monitor_flags_breaches(client, db, demo, users, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "SLA_DAYS_AUTHORITY_VERIFICATION", 5)  # Sunita has waited 9 days
    rows = (await client.get("/v1/analytics/sla", headers=await users.headers("ministry"))).json()
    row = next(r for r in rows if r["application_id"] == demo["sunita_application"])
    assert row["breached"] is True and row["days_in_state"] >= 9 and row["district"] == "Dumka"


# ── outbox → NATS ────────────────────────────────────────────────────────────


async def test_outbox_publishes_to_nats_once(db, demo):
    bus = NATSEventBus(NATS_URL)
    try:
        await asyncio.wait_for(bus.connect(), timeout=5)
    except Exception as exc:
        pytest.fail(f"NATS not reachable at {NATS_URL} ({exc}). Start it: docker compose -f infra/docker-compose.yml up -d nats",
                    pytrace=False)
    received: list[BaseEvent] = []
    import nats
    nc = await nats.connect(NATS_URL)

    async def collect(msg):
        received.append(BaseEvent(**json.loads(msg.data)))

    sub = await nc.subscribe("application.>", cb=collect)
    try:
        pending = await db.scalar(select(func.count()).select_from(OutboxMessage).where(OutboxMessage.published_at.is_(None)))
        assert pending > 0
        published = await publish_pending(AsyncSessionLocal, bus, batch=1000)
        assert published == pending
        await asyncio.sleep(0.3)
        seeded_ids = {e.event_id for e in received if e.correlation_id == demo["sunita_application"]}
        assert len(seeded_ids) == 3  # created, institute verification, authority verification
        assert await publish_pending(AsyncSessionLocal, bus) == 0  # nothing left, nothing re-sent
    finally:
        await sub.unsubscribe()
        await nc.drain()
        await bus.close()


# ── nudge engine ─────────────────────────────────────────────────────────────


async def test_nudge_notifies_student_and_guardian_once(db, demo):
    ledger = LedgerService(db)
    app = await db.get(Application, demo["sunita_application"])
    deficiency = await ledger.raise_deficiency(app, "INCOME_CERT_EXPIRED", "Upload the FY 2026-27 income certificate",
                                               "DISTRICT_OFFICER", "system:test")
    await db.commit()
    message = (await db.execute(select(OutboxMessage).where(OutboxMessage.event_type == "DeficiencyRaised"))).scalar_one()
    event = BaseEvent(**message.payload)

    stored = await NudgeService(db).handle_event(event)
    assert stored == 4  # student + guardian, each PUSH + SMS (a deficiency is critical)
    assert await NudgeService(db).handle_event(event) == 0  # redelivery is a no-op

    rows = (await db.execute(select(Notification).where(Notification.event_id == event.event_id))).scalars().all()
    assert {r.channel for r in rows} == {NotificationChannel.PUSH, NotificationChannel.SMS}
    push = next(r for r in rows if r.channel == NotificationChannel.PUSH)
    assert push.language == "hi" and "Upload the FY 2026-27 income certificate" in push.body
    assert deficiency.id  # the deficiency row exists alongside its event


async def test_notifications_api_lists_only_my_push_messages(client, db, demo, users):
    ledger = LedgerService(db)
    app = await db.get(Application, demo["sunita_application"])
    await ledger.raise_deficiency(app, "MARKSHEET_MISSING", "Upload your Class 10 marksheet", "DISTRICT_OFFICER",
                                  "system:test")
    await db.commit()
    message = (await db.execute(select(OutboxMessage).where(OutboxMessage.event_type == "DeficiencyRaised"))).scalar_one()
    await NudgeService(db).handle_event(BaseEvent(**message.payload))
    mine = (await client.get("/v1/notifications", headers=await users.headers("sunita"))).json()
    assert len(mine) == 1 and mine[0]["channel"] == "PUSH" and "Class 10 marksheet" in mine[0]["body"]
    assert (await client.get("/v1/notifications", headers=await users.headers("rahul"))).json() == []
    r = await client.post(f"/v1/notifications/{mine[0]['id']}/read", headers=await users.headers("rahul"))
    assert r.status_code == 404


# ── migrations ───────────────────────────────────────────────────────────────


async def test_migrations_build_the_schema_on_an_empty_database(database):
    import asyncpg
    base = os.environ["DATABASE_URL"].rsplit("/", 1)[0]
    conn = await asyncpg.connect(base.replace("postgresql+asyncpg://", "postgresql://") + "/postgres")
    await conn.execute("DROP DATABASE IF EXISTS scholarsetu_migration_test")
    await conn.execute("CREATE DATABASE scholarsetu_migration_test")
    await conn.close()
    env = {**os.environ, "DATABASE_URL": f"{base}/scholarsetu_migration_test"}
    for args in (["upgrade", "head"], ["check"], ["downgrade", "base"], ["upgrade", "head"]):
        result = subprocess.run([sys.executable, "-m", "alembic", *args], cwd=CORE, env=env,
                                capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, f"alembic {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}"


async def test_event_times_in_other_offsets_still_verify(db, demo):
    from datetime import datetime, timedelta, timezone as tz
    ledger = LedgerService(db)
    ist = tz(timedelta(hours=5, minutes=30))
    app = await ledger.create_application("stu-rahul-002", SchemeType.PRE_MATRIC, "2026-27", "system:test",
                                          occurred_at=datetime(2026, 9, 5, 10, 0, tzinfo=ist))
    app_id = app.id
    await db.commit()
    db.expire_all()
    assert (await LedgerService(db).verify_chain(app_id)).valid
