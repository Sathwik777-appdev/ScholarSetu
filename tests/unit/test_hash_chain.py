"""The ledger hash covers every stored field; changing any one of them changes the hash."""

from datetime import datetime, timezone

import pytest

from app.shared.hashing import GENESIS, canonical_json, event_hash

BASE = dict(event_id="01a0-e", event_type="ReviewDecisionRecorded", application_id="APP-PM-2026-000002",
            sequence_no=4, student_id="stu-sunita-001", scheme="POST_MATRIC", source="SCHOLARSETU",
            actor="user:officer-1:DISTRICT_OFFICER", occurred_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
            payload={"decision": "APPROVE", "amount": 5000}, hash_prev=GENESIS)


def test_hash_is_deterministic():
    assert event_hash(**BASE) == event_hash(**BASE)
    assert len(event_hash(**BASE)) == 64


@pytest.mark.parametrize("field,value", [
    ("event_id", "01a0-f"), ("event_type", "Rejected"), ("application_id", "APP-PM-2026-000003"),
    ("sequence_no", 5), ("student_id", "stu-rahul-002"), ("scheme", "NFST"), ("source", "NSP"),
    ("actor", "user:officer-2:DISTRICT_OFFICER"), ("occurred_at", datetime(2026, 9, 1, 10, 1, tzinfo=timezone.utc)),
    ("payload", {"decision": "APPROVE", "amount": 50000}), ("hash_prev", "1" * 64),
])
def test_changing_any_field_changes_the_hash(field, value):
    assert event_hash(**{**BASE, field: value}) != event_hash(**BASE)


def test_canonical_json_ignores_key_order_and_keeps_unicode():
    assert canonical_json({"b": 1, "a": "सुनीता"}) == canonical_json({"a": "सुनीता", "b": 1}) == '{"a":"सुनीता","b":1}'
