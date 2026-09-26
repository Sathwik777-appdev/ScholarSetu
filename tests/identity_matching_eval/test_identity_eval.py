"""Labelled evaluation of the Identity Resolver (ARCHITECTURE.md §6.4.3).

Labels in pairs.csv are the decision a careful officer would want, not whatever the resolver
currently outputs. Run `pytest tests/identity_matching_eval -s` to see the confusion matrix.

Hard rule: no hard negative (a different person) may ever be AUTO_VERIFY.
"""

import csv
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from app.verification.identity_resolver import IdentityRecord, IndicIdentityResolver

PAIRS = Path(__file__).with_name("pairs.csv")
DECISIONS = ["AUTO_VERIFY", "PROVISIONAL", "MANUAL_REVIEW"]
MIN_EXACT_AGREEMENT = 0.90


def _date(value: str):
    return date.fromisoformat(value) if value else None


def _load():
    with PAIRS.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _run(row):
    a = IdentityRecord("A", row["name_a"], _date(row["dob_a"]), None, row["father_a"] or None, None,
                       row["district_a"] or None)
    b = IdentityRecord("B", row["name_b"], _date(row["dob_b"]), None, row["father_b"] or None, None,
                       row["district_b"] or None)
    return IndicIdentityResolver().resolve([a, b])


@pytest.fixture(scope="module")
def results():
    rows = _load()
    return [(row, _run(row)) for row in rows]


def test_dataset_is_large_and_balanced():
    rows = _load()
    assert len(rows) >= 80
    categories = Counter(r["category"] for r in rows)
    for needed in ("spelling_variant", "initials", "transliteration", "honorific_inside_name", "reordered",
                   "twins_siblings", "same_given_diff_surname", "different_person"):
        assert categories[needed] >= 2, needed
    assert sum(r["hard_negative"] == "yes" for r in rows) >= 20


def test_no_hard_negative_is_auto_verified(results):
    leaks = [(r["id"], r["name_a"], r["name_b"], res.overall_score)
             for r, res in results if r["hard_negative"] == "yes" and res.decision == "AUTO_VERIFY"]
    assert not leaks, f"different people auto-verified: {leaks}"


def test_confusion_matrix_and_agreement(results):
    matrix = Counter((r["expected_decision"], res.decision) for r, res in results)
    width = max(len(d) for d in DECISIONS) + 2
    lines = ["", "Identity resolver: expected (rows) vs actual (columns)",
             " " * width + "".join(d.rjust(width) for d in DECISIONS)]
    for exp in DECISIONS:
        lines.append(exp.ljust(width) + "".join(str(matrix[(exp, act)]).rjust(width) for act in DECISIONS))
    misses = [(r["id"], r["category"], r["name_a"], r["name_b"], r["expected_decision"], res.decision,
               round(res.overall_score, 3)) for r, res in results if res.decision != r["expected_decision"]]
    agreement = 1 - len(misses) / len(results)
    lines.append(f"agreement: {agreement:.1%} ({len(results) - len(misses)}/{len(results)})")
    for miss in misses:
        lines.append(f"  miss #{miss[0]} [{miss[1]}] {miss[2]!r} vs {miss[3]!r}: expected {miss[4]}, got {miss[5]} ({miss[6]})")
    print("\n".join(lines))
    assert agreement >= MIN_EXACT_AGREEMENT, "\n".join(lines)
