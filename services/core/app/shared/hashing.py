"""Hash chain for the ledger. The same function is used to write and to verify events."""

import hashlib
import json
from datetime import datetime
from typing import Any

GENESIS = "0" * 64


def canonical_json(obj: Any) -> str:
    """Sorted keys, no whitespace, UTF-8 kept as-is."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def event_hash(event_id: str, event_type: str, application_id: str, occurred_at: datetime,
               payload: dict[str, Any], hash_prev: str) -> str:
    body = {
        "event_id": event_id,
        "type": event_type,
        "application_id": application_id,
        "occurred_at": occurred_at.isoformat(),
        "payload": payload,
        "hash_prev": hash_prev,
    }
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
