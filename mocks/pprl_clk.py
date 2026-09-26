"""CLK v1 encoder, as run locally by the (mock) UDISE+ data holder.

Must stay identical to services/core/app/reach_radar/pprl.py; tests/unit/test_pprl.py checks parity.
"""

import base64
import hashlib
import hmac
import random
import re
from dataclasses import dataclass
from typing import Optional

# Calibrated on synthetic pairs (tests/unit/test_pprl.py): same person with spelling variants >= 0.969;
# namesakes with another DOB <= 0.944; same-DOB siblings <= 0.948. Tune on real data before any pilot.
M_BITS = 1024
FIELD_K = {"name": 15, "dob": 50, "district": 10}
MATCH_THRESHOLD = 0.958


def _field_key(secret: bytes, field: str) -> bytes:
    return hmac.new(secret, f"clk-v1:{field}".encode(), hashlib.sha256).digest()


def _phonetic(token: str) -> str:
    key = token.replace("x", "ks")
    for src, dst in (("sh", "s"), ("ph", "f"), ("th", "t"), ("aa", "a"), ("ee", "i"), ("oo", "u"), ("w", "v")):
        key = key.replace(src, dst)
    if len(key) > 2 and key.endswith("h"):
        key = key[:-1]
    return re.sub(r"([bcdfghjklmnpqrstvwxyz])\1+", r"\1", key)


def normalise_name(latin_name: str) -> str:
    tokens = re.sub(r"[^a-z\s]", " ", latin_name.lower()).split()
    return " ".join(_phonetic(t) for t in tokens)


def _grams(field: str, value: str) -> list[str]:
    if field == "name":
        padded = f"_{value.replace(' ', '_')}_"
        return [padded[i:i + 2] for i in range(len(padded) - 1)]
    if field == "dob":
        year, month, day = value.split("-")
        return [f"y{year}", f"m{month}", f"d{day}"]
    return [value]


def _bloom(secret: bytes, fields: dict[str, str]) -> int:
    bits = 0
    for field, value in fields.items():
        key, k = _field_key(secret, field), FIELD_K[field]
        for gram in _grams(field, value):
            h1 = int.from_bytes(hmac.new(key, b"1" + gram.encode(), hashlib.sha256).digest()[:8], "big")
            h2 = int.from_bytes(hmac.new(key, b"2" + gram.encode(), hashlib.sha256).digest()[:8], "big")
            for i in range(k):
                bits |= 1 << ((h1 + i * h2) % M_BITS)
    return bits


def _permutation(secret: bytes) -> list[int]:
    order = list(range(2 * M_BITS))
    random.Random(hmac.new(secret, b"clk-v1:permutation", hashlib.sha256).digest()).shuffle(order)
    return order


def encode(secret: bytes, latin_name: str, dob: str, district: str) -> int:
    """Balanced CLK as an integer of 2*M_BITS bits."""
    raw = _bloom(secret, {"name": normalise_name(latin_name), "dob": dob, "district": district.strip().lower()})
    balanced = raw | ((~raw & ((1 << M_BITS) - 1)) << M_BITS)
    out = 0
    for dest, src in enumerate(_permutation(secret)):
        if balanced >> src & 1:
            out |= 1 << dest
    return out


def to_b64(clk: int) -> str:
    return base64.b64encode(clk.to_bytes(2 * M_BITS // 8, "big")).decode()


def from_b64(value: str) -> int:
    return int.from_bytes(base64.b64decode(value), "big")


def apaar_token(secret: bytes, apaar_id: Optional[str]) -> Optional[str]:
    """Keyed hash of the APAAR ID, for the deterministic first pass."""
    if not apaar_id:
        return None
    return hmac.new(secret, f"clk-v1:apaar:{apaar_id}".encode(), hashlib.sha256).hexdigest()


def dice(a: int, b: int) -> float:
    return 2 * (a & b).bit_count() / (a.bit_count() + b.bit_count())


@dataclass
class Match:
    left: int
    right: int
    score: float
    method: str


def link(left: list[tuple[Optional[str], int]], right: list[tuple[Optional[str], int]],
         threshold: float = MATCH_THRESHOLD) -> list[Match]:
    """One-to-one linkage: exact APAAR tokens first, then greedy best Dice pairs above the threshold."""
    matches: list[Match] = []
    used_l, used_r = set(), set()
    by_token = {tok: j for j, (tok, _) in enumerate(right) if tok}
    for i, (tok, _) in enumerate(left):
        j = by_token.get(tok) if tok else None
        if j is not None and j not in used_r:
            matches.append(Match(i, j, 1.0, "apaar"))
            used_l.add(i)
            used_r.add(j)
    candidates = [(dice(lc, rc), i, j) for i, (_, lc) in enumerate(left) if i not in used_l
                  for j, (_, rc) in enumerate(right) if j not in used_r]
    for score, i, j in sorted((c for c in candidates if c[0] >= threshold), reverse=True):
        if i not in used_l and j not in used_r:
            matches.append(Match(i, j, round(score, 4), "clk"))
            used_l.add(i)
            used_r.add(j)
    return matches
