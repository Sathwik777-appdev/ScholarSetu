"""Phase 7 (M3): the CLK v1 encoding is identical on both sides, balanced, and tolerant of spelling variants."""

import importlib
import sys
from pathlib import Path

from app.reach_radar import pprl

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "mocks"))
mock_clk = importlib.import_module("pprl_clk")
KEY = b"k" * 40


def test_core_and_udise_encoders_agree_bit_for_bit():
    for name, dob, district in [("Sunita Hansda", "2008-04-12", "Dumka"), ("Birsa Murmu", "2007-02-10", "Khunti")]:
        assert pprl.encode(KEY, name, dob, district) == mock_clk.encode(KEY, name, dob, district)
        assert pprl.apaar_token(KEY, "APAAR-1") == mock_clk.apaar_token(KEY, "APAAR-1")


def test_balanced_filters_have_constant_weight():
    weights = {pprl.encode(KEY, n, "2008-01-01", "Dumka").bit_count() for n in ("A B", "Sunita Hansda", "Xy Zzzzzzzzz")}
    assert weights == {pprl.M_BITS}  # nothing to learn from how many bits are set


def test_spelling_variants_link_and_different_people_do_not():
    a = pprl.encode(KEY, "Sunita Hansda", "2008-04-12", "Dumka")
    assert pprl.dice(a, pprl.encode(KEY, "Sunita Hansdah", "2008-04-12", "Dumka")) >= pprl.MATCH_THRESHOLD
    assert pprl.dice(a, pprl.encode(KEY, "Sunita Murmu", "2008-04-12", "Dumka")) < pprl.MATCH_THRESHOLD
    assert pprl.dice(a, pprl.encode(KEY, "Sunita Hansda", "2006-11-02", "Dumka")) < pprl.MATCH_THRESHOLD


def test_devanagari_names_are_encoded_after_transliteration():
    from app.verification.transliteration import to_latin
    latin = pprl.encode(KEY, "Sunita Hansda", "2008-04-12", "Dumka")
    deva = pprl.encode(KEY, to_latin("सुनीता हांसदा"), "2008-04-12", "Dumka")
    assert pprl.dice(latin, deva) == 1.0


def test_a_different_key_gives_unlinkable_encodings():
    a = pprl.encode(KEY, "Sunita Hansda", "2008-04-12", "Dumka")
    b = pprl.encode(b"z" * 40, "Sunita Hansda", "2008-04-12", "Dumka")
    assert pprl.dice(a, b) < 0.6


def test_linkage_is_one_to_one():
    x = pprl.encode(KEY, "Sunita Hansda", "2008-04-12", "Dumka")
    left = [(None, x), (None, x)]            # two identical enrolment records
    right = [(None, pprl.encode(KEY, "Sunita Hansdah", "2008-04-12", "Dumka"))]
    matches = pprl.link(left, right)
    assert len(matches) == 1


def test_namesakes_and_siblings_stay_below_the_threshold():
    base = pprl.encode(KEY, "Sonamuni Kisku", "2009-06-14", "Dumka")
    assert pprl.dice(base, pprl.encode(KEY, "Sonamuni Kisku", "2009-06-15", "Dumka")) < pprl.MATCH_THRESHOLD
    assert pprl.dice(base, pprl.encode(KEY, "Phulmani Kisku", "2009-06-14", "Dumka")) < pprl.MATCH_THRESHOLD
    assert pprl.dice(base, pprl.encode(KEY, "Sonamunee Kisku", "2009-06-14", "Dumka")) >= pprl.MATCH_THRESHOLD
