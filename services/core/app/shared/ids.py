"""Time-ordered identifiers (UUIDv7, RFC 9562)."""

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    """Return a UUIDv7: 48-bit Unix-ms timestamp followed by 74 random bits."""
    ts_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")
    value = (ts_ms & 0xFFFF_FFFF_FFFF) << 80
    value |= 0x7 << 76                          # version 7
    value |= ((rand >> 62) & 0xFFF) << 64       # rand_a (12 bits)
    value |= 0b10 << 62                         # RFC 4122 variant
    value |= rand & 0x3FFF_FFFF_FFFF_FFFF       # rand_b (62 bits)
    return uuid.UUID(int=value)


def new_id() -> str:
    return str(uuid7())
