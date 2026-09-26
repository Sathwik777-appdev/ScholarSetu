"""Phase 3 / C1 acceptance: the Identity Resolver's rules, one test per rule."""

from datetime import date

import pytest

from app.config import settings
from app.verification.identity_resolver import (
    AUTO_VERIFY, MANUAL_REVIEW, PROVISIONAL, IdentityRecord, IndicIdentityResolver, phonetic_key, prepare_name,
)
from app.verification.transliteration import to_latin

DOB = date(2008, 4, 12)
resolver = IndicIdentityResolver()


def rec(name, dob=DOB, father="Babulal Hansda", district="Dumka", gender="FEMALE", mother=None, source="source"):
    return IdentityRecord(source, name, dob, gender, father, mother, district)


def resolve(a, b):
    return resolver.resolve([a, b])


# ── acceptance criteria ─────────────────────────────────────────────────────


def test_twins_are_not_auto_verified():
    res = resolve(rec("Sunita Hansda"), rec("Anita Hansda"))
    assert res.decision == MANUAL_REVIEW
    assert "'sunita' vs 'anita'" in res.explanation


def test_same_first_name_different_surname_is_not_auto_verified():
    res = resolve(rec("Sunita Hansda"), rec("Sunita Murmu"))
    assert res.decision == MANUAL_REVIEW and res.overall_score < settings.IDENTITY_REVIEW_THRESHOLD


def test_honorific_inside_a_name_is_not_stripped():
    res = resolve(rec("Srinivas Munda"), rec("Nivas Munda"))
    assert res.overall_score < settings.IDENTITY_REVIEW_THRESHOLD and res.decision == MANUAL_REVIEW
    assert prepare_name("Srinivas Munda").tokens == ["srinivas", "munda"]


def test_devanagari_matches_latin():
    res = resolve(rec("Sunita Hansda"), rec("सुनीता हांसदा"))
    assert res.overall_score >= 0.92 and res.decision == AUTO_VERIFY
    assert "(Devanagari) read as 'sunita hansda'" in res.explanation


def test_hansdah_with_dob_and_father_follows_the_rules_and_names_the_trailing_h():
    res = resolve(rec("Sunita Hansda"), rec("Sunita Hansdah"))
    # Same pronunciation key, and DOB + father's name match exactly, no conflict → AUTO_VERIFY.
    assert res.decision == AUTO_VERIFY
    assert "trailing 'h'" in res.explanation and "'hansda' vs 'hansdah'" in res.explanation
    assert "DOB matches" in res.explanation and "Father's name matches" in res.explanation


def test_hansdah_certificate_without_corroboration_is_provisional():
    res = resolve(rec("Sunita Hansda"), rec("Sunita Hansdah", dob=None, father=None, district=None, gender=None))
    assert res.decision == PROVISIONAL
    assert "no corroborating field" in res.explanation


# ── rules ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("raw,tokens", [
    ("Smt. Sunita Hansda", ["sunita", "hansda"]),
    ("Kumari Sunita Hansda", ["sunita", "hansda"]),
    ("Sunita Kumari", ["sunita", "kumari"]),          # Kumari as the surname is kept
    ("Kumari Devi", ["kumari", "devi"]),              # only given name: kept
    ("Ravi Kumar Soren", ["ravi", "kumar", "soren"]), # Kumar is a name, never a title
    ("Sunita Hansda D/O Babulal Hansda", ["sunita", "hansda"]),
    ("Dr. Late Ramesh Tudu", ["ramesh", "tudu"]),
    ("Shrikant Oraon", ["shrikant", "oraon"]),
])
def test_titles_are_removed_only_as_whole_tokens(raw, tokens):
    assert prepare_name(raw).tokens == tokens


@pytest.mark.parametrize("a,b", [("hansdah", "hansda"), ("murmoo", "murmu"), ("wijay", "vijay"),
                                 ("phulmani", "fulmani"), ("suneeta", "sunita"), ("lakshmi", "laxmi"),
                                 ("rameshwar", "rameswar"), ("sunitha", "sunita"), ("baskey", "baskey")])
def test_phonetic_keys_fold_known_variants(a, b):
    assert phonetic_key(a) == phonetic_key(b)


@pytest.mark.parametrize("text,latin", [
    ("सुनीता हांसदा", "sunita hansda"), ("सोरेन", "soren"), ("फूलमनी", "phulmani"), ("रामचरण", "ramcharan"),
    ("कमल", "kamal"), ("ओरांव", "oraon"), ("বিরসা মুণ্ডা", "birsa munda"), ("ବିରସା ମୁଣ୍ଡା", "birsa munda"),
    ("சுனிதா", "sunita"), ("సునీత", "sunita"), ("ಸುನೀತಾ", "sunita"), ("സുനിത", "sunita"), ("ਸੁਨੀਤਾ", "sunita"),
])
def test_transliteration(text, latin):
    assert to_latin(text) == latin


def test_unsupported_script_goes_to_manual_review_not_a_low_score():
    res = resolve(rec("Sunita Hansda"), rec("ᱥᱩᱱᱤᱛᱟ ᱦᱟᱸᱥᱫᱟ"))
    assert res.decision == MANUAL_REVIEW
    assert "script not supported for automatic matching (Ol Chiki)" in res.explanation


def test_given_name_is_not_rescued_by_surname_or_fields():
    res = resolve(rec("Pinky Marandi", father="Lakhan Marandi"), rec("Rinky Marandi", father="Lakhan Marandi"))
    assert res.decision == MANUAL_REVIEW and "different first letter" in res.explanation


def test_corroboration_is_a_gate_not_a_bonus():
    # Name in the review band, every corroborating field matching: fields must not lift it to auto-verify
    # (the old resolver added up to +0.35 for matching fields).
    res = resolve(rec("Sunil Tirkey", father="Anand Tirkey"), rec("Sunil Tirki", father="Anand Tirkey"))
    assert res.overall_score == res.name_comparisons[0].score < settings.IDENTITY_AUTO_VERIFY_THRESHOLD
    assert res.decision == PROVISIONAL


def test_zero_corroboration_is_provisional_even_for_identical_names():
    res = resolve(rec("Sunita Hansda"), rec("Sunita Hansda", dob=None, father=None, district=None, gender=None))
    assert res.overall_score == 1.0 and res.decision == PROVISIONAL


@pytest.mark.parametrize("field,other", [("dob", date(2006, 1, 1)), ("district", "Ranchi"),
                                         ("gender", "MALE"), ("father", "Somai Murmu")])
def test_any_conflicting_field_forces_manual_review(field, other):
    res = resolve(rec("Sunita Hansda"), rec("Sunita Hansda", **{field: other}))
    assert res.decision == MANUAL_REVIEW and "conflicting" in res.explanation


def test_initials_are_consistent_but_never_auto_verify():
    res = resolve(rec("Sunita Hansda"), rec("S. Hansda"))
    assert res.decision == PROVISIONAL and "initial 'S.' is consistent with 'sunita'" in res.explanation


def test_reordered_names_match_with_a_small_penalty():
    res = resolve(rec("Sunita Hansda"), rec("HANSDA SUNITA"))
    assert res.decision == AUTO_VERIFY and res.overall_score == pytest.approx(settings.IDENTITY_REORDER_PENALTY)
    assert "different order" in res.explanation


def test_missing_surname_is_capped_into_review():
    res = resolve(rec("Sunita Hansda"), rec("Sunita"))
    assert res.decision == PROVISIONAL and "surname missing" in res.explanation.lower()


def test_never_auto_rejects():
    res = resolve(rec("Sunita Hansda"), rec("Mary Kujur", dob=date(2001, 1, 1), father="Joseph Kujur", district="Simdega"))
    assert res.decision == MANUAL_REVIEW  # a human decides; there is no REJECT outcome


def test_thresholds_come_from_config(monkeypatch):
    monkeypatch.setattr(settings, "IDENTITY_AUTO_VERIFY_THRESHOLD", 0.99)
    res = resolve(rec("Sunita Hansda"), rec("HANSDA SUNITA"))  # 0.98 after the reorder penalty
    assert res.decision == PROVISIONAL
