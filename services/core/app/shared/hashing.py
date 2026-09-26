"""Cryptographic hash chain utilities for tamper-evident ledger integrity."""

import hashlib
import json
from typing import Any, Dict, Union


def compute_hash(*args, **kwargs) -> str:
    """Compute deterministic SHA-256 hash for ledger event chain.
    
    Supports:
      - compute_hash(event_dict, prev_hash)
      - compute_hash(event_type, application_id, timestamp, payload_json, prev_hash)
    """
    if len(args) == 2 and isinstance(args[0], dict):
        event_dict, prev_hash = args
        data_str = json.dumps(event_dict, sort_keys=True)
        combined = f"{prev_hash}:{data_str}"
    elif len(args) >= 2:
        parts = [str(a) for a in args]
        combined = ":".join(parts)
    elif "event_data" in kwargs:
        data_str = json.dumps(kwargs["event_data"], sort_keys=True)
        prev_hash = kwargs.get("prev_hash", "genesis")
        combined = f"{prev_hash}:{data_str}"
    else:
        combined = str(args)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()
