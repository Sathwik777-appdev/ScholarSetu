"""Indic-aware identity resolution with explainable decisions (ARCHITECTURE.md §6.4.3).

Pipeline for each pair of records:
  1. Normalise: lowercase, unify punctuation, drop titles and relation markers as whole tokens.
  2. Transliterate Indian scripts to Latin (unsupported scripts go to manual review).
  3. Phonetic key per token (w→v, sh→s, th→t, aa→a, ee→i, oo→u, ph→f, x→ks, final h dropped,
     doubled consonants collapsed).
  4. Score given name and surname separately with Jaro-Winkler; name score is the lower of the
     two, so a different first name cannot be rescued by a shared surname. A token scoring
     below the mismatch threshold marks the names as different.
  5. Corroborating fields (DOB, father's/mother's name, gender, district) are a gate, never a
     bonus: auto-verify needs at least one exact match and no conflict.
  6. Decide: AUTO_VERIFY / PROVISIONAL / MANUAL_REVIEW. Never auto-reject.
"""

import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from itertools import permutations
from typing import Optional

from rapidfuzz.distance import JaroWinkler

from app.config import settings
from app.verification.transliteration import detect_scripts, to_latin

AUTO_VERIFY = "AUTO_VERIFY"
PROVISIONAL = "PROVISIONAL"
MANUAL_REVIEW = "MANUAL_REVIEW"
_DECISION_RANK = {AUTO_VERIFY: 0, PROVISIONAL: 1, MANUAL_REVIEW: 2}

# Titles and markers removed only as whole tokens ("sri" inside "Srinivas" is kept).
_TITLES = {"shri", "sri", "shree", "smt", "shrimati", "shrimti", "srimati", "kumari", "km", "kum",
           "late", "mr", "mrs", "ms", "miss", "dr", "master"}
# Removed only when they are a prefix title and at least a given name + surname remain.
_PROTECTED_AS_NAMES = {"kumari", "km", "kum"}
_VOWELS = set("aeiou")
_RELATION_MARKER = re.compile(r"\b(?:s|d|w|c)\s*/\s*o\b|\b(?:son|daughter|wife|care)\s+of\b")


@dataclass
class IdentityRecord:
    source: str
    name: str
    dob: Optional[date]
    gender: Optional[str]
    father_name: Optional[str]
    mother_name: Optional[str]
    district: Optional[str]
    additional: Optional[dict] = None


@dataclass
class PreparedName:
    raw: str
    latin: str
    tokens: list[str]            # normalised Latin tokens
    keys: list[str]              # phonetic keys, aligned with tokens
    removed: list[str] = field(default_factory=list)
    transliterated_from: Optional[str] = None
    unsupported_script: Optional[str] = None


@dataclass
class TokenPair:
    a: Optional[str]
    b: Optional[str]
    score: Optional[float]
    note: str


@dataclass
class NameMatchResult:
    name_a: str
    name_b: str
    score: float
    given_score: Optional[float]
    surname_score: Optional[float]
    different_names: bool
    reordered: bool
    unsupported_script: Optional[str]
    pairs: list[TokenPair]
    notes: list[str]


class FieldStatus(str, Enum):
    MATCH = "MATCH"
    CONFLICT = "CONFLICT"
    NEUTRAL = "NEUTRAL"   # missing on a record, or close but not exact


@dataclass
class CorroborationResult:
    fields: dict[str, tuple[FieldStatus, str]]

    @property
    def matches(self) -> list[str]:
        return [f for f, (s, _) in self.fields.items() if s == FieldStatus.MATCH]

    @property
    def conflicts(self) -> list[str]:
        return [f for f, (s, _) in self.fields.items() if s == FieldStatus.CONFLICT]

    @property
    def details(self) -> dict[str, str]:
        return {f: d for f, (s, d) in self.fields.items() if s == FieldStatus.MATCH}


@dataclass
class IdentityResolution:
    overall_score: float
    decision: str
    name_comparisons: list[NameMatchResult]
    corroboration: CorroborationResult
    explanation: str
    details: dict


def phonetic_key(token: str) -> str:
    key = token.replace("ş", "s").replace("x", "ks")
    for src, dst in (("sh", "s"), ("ph", "f"), ("th", "t"), ("aa", "a"), ("ee", "i"), ("oo", "u"), ("w", "v")):
        key = key.replace(src, dst)
    if len(key) > 2 and key.endswith("h"):
        key = key[:-1]
    return re.sub(r"([bcdfghjklmnpqrstvwxyz])\1+", r"\1", key)


def prepare_name(raw: str) -> PreparedName:
    info = detect_scripts(raw or "")
    if info.unsupported:
        return PreparedName(raw=raw, latin="", tokens=[], keys=[],
                            unsupported_script=", ".join(sorted(info.unsupported)))
    latin = to_latin(raw) if not info.is_latin_only else raw
    text = latin.lower()
    marker = _RELATION_MARKER.search(text)
    if marker:  # "Sunita Hansda D/O Babulal Hansda" → the part before the marker is the person
        text = text[:marker.start()]
    text = re.sub(r"[^a-z\s]", " ", text.replace("ş", "s"))
    tokens = text.split()

    removed = []
    kept = []
    for i, tok in enumerate(tokens):
        if tok in _TITLES:
            is_prefix = all(t in _TITLES for t in tokens[:i])
            remaining = len(tokens) - i - 1
            if tok in _PROTECTED_AS_NAMES and not (is_prefix and remaining >= 2):
                kept.append(tok)  # "Sunita Kumari": Kumari is the surname here
                continue
            removed.append(tok)
            continue
        kept.append(tok)
    return PreparedName(raw=raw, latin=latin, tokens=kept, keys=[phonetic_key(t) for t in kept], removed=removed,
                        transliterated_from=None if info.is_latin_only else ", ".join(sorted(info.scripts - {"Latin"})))


def _describe_difference(a: str, b: str, ka: str, kb: str, score: float) -> str:
    if ka == kb:
        if a.rstrip("h") == b.rstrip("h") and a != b:
            return f"differs only by a trailing 'h' ('{a}' vs '{b}')"
        return f"spelling variant with the same pronunciation key ('{a}' vs '{b}' → '{ka}')"
    return f"'{a}' vs '{b}' (similarity {score:.2f})"


class IndicIdentityResolver:
    """Stateless; thresholds come from settings so they can be tuned without code changes."""

    @property
    def auto_threshold(self) -> float:
        return settings.IDENTITY_AUTO_VERIFY_THRESHOLD

    @property
    def review_threshold(self) -> float:
        return settings.IDENTITY_REVIEW_THRESHOLD

    # ── token and name scoring ──────────────────────────────

    def _token_score(self, a: str, ka: str, b: str, kb: str) -> tuple[float, str]:
        if len(a) == 1 or len(b) == 1:
            initial, full = (a, b) if len(a) == 1 else (b, a)
            if full.startswith(initial):
                return settings.IDENTITY_INITIAL_SCORE, f"initial '{initial.upper()}.' is consistent with '{full}'"
            return 0.0, f"initial '{initial.upper()}.' does not match '{full}'"
        if a == b:
            return 1.0, f"'{a}' identical"
        score = JaroWinkler.similarity(ka, kb)
        # Spelling variants keep the first sound (ph/f, w/v, sh/s are already folded into the key);
        # a different first letter means a different name: Smita/Mita, Pinky/Rinky, Sita/Gita.
        if ka and kb and ka[0] != kb[0] and not (ka[0] in _VOWELS and kb[0] in _VOWELS):
            capped = min(score, settings.IDENTITY_TOKEN_MISMATCH_THRESHOLD - 0.01)
            return capped, f"'{a}' vs '{b}': different first letter (similarity {score:.2f})"
        return score, _describe_difference(a, b, ka, kb, score)

    def _align_given(self, ga: list[tuple[str, str]], gb: list[tuple[str, str]]) -> tuple[Optional[float], list[TokenPair]]:
        if not ga and not gb:
            return None, []
        short, long_, swapped = (ga, gb, False) if len(ga) <= len(gb) else (gb, ga, True)
        used: set[int] = set()
        pairs: list[TokenPair] = []
        scores: list[float] = []
        for tok, key in short:
            best = max(((j, *self._token_score(tok, key, lt, lk)) for j, (lt, lk) in enumerate(long_) if j not in used),
                       key=lambda t: t[1], default=None)
            if best is None:
                continue
            j, score, note = best
            used.add(j)
            scores.append(score)
            a, b = (tok, long_[j][0]) if not swapped else (long_[j][0], tok)
            pairs.append(TokenPair(a, b, score, note))
        for j, (lt, _) in enumerate(long_):
            if j not in used:
                pairs.append(TokenPair(None if not swapped else lt, lt if not swapped else None, None,
                                       f"'{lt}' appears on only one record"))
        if not scores:
            return 0.0, pairs
        extra = len(long_) - len(short)
        return sum(scores) / len(scores) * settings.IDENTITY_EXTRA_TOKEN_PENALTY ** extra, pairs

    def _score_split(self, a: PreparedName, b_tokens: list[tuple[str, str]], reordered: bool) -> NameMatchResult:
        a_tok = list(zip(a.tokens, a.keys, strict=True))
        ga, sa = (a_tok[:-1], a_tok[-1]) if len(a_tok) >= 2 else (a_tok, None)
        gb, sb = (b_tokens[:-1], b_tokens[-1]) if len(b_tokens) >= 2 else (b_tokens, None)

        given_score, pairs = self._align_given(ga, gb)
        notes: list[str] = []
        if sa and sb:
            surname_score, note = self._token_score(sa[0], sa[1], sb[0], sb[1])
            pairs.append(TokenPair(sa[0], sb[0], surname_score, f"surname: {note}"))
        else:
            surname_score = None
            notes.append("surname missing on one record")

        parts = [s for s in (given_score, surname_score) if s is not None]
        score = min(parts) if parts else 0.0
        if surname_score is None:
            score = min(score, settings.IDENTITY_MISSING_SURNAME_CAP)
        different = any(p.score is not None and p.score < settings.IDENTITY_TOKEN_MISMATCH_THRESHOLD for p in pairs)
        if different:
            notes.append("at least one name part is a different name, not a spelling variant")
            score = min(score, self.review_threshold - 0.01)
        if reordered:
            score *= settings.IDENTITY_REORDER_PENALTY
            notes.append("name parts are written in a different order")
        return NameMatchResult(name_a="", name_b="", score=round(score, 4), given_score=given_score,
                               surname_score=surname_score, different_names=different, reordered=reordered,
                               unsupported_script=None, pairs=pairs, notes=notes)

    def compare_names(self, name_a: str, name_b: str) -> NameMatchResult:
        a, b = prepare_name(name_a), prepare_name(name_b)
        unsupported = a.unsupported_script or b.unsupported_script
        if unsupported:
            return NameMatchResult(name_a, name_b, 0.0, None, None, False, False, unsupported, [],
                                   [f"script not supported for automatic matching ({unsupported})"])
        if not a.tokens or not b.tokens:
            return NameMatchResult(name_a, name_b, 0.0, None, None, True, False, None, [], ["a name is empty"])

        b_tok = list(zip(b.tokens, b.keys, strict=True))
        best = self._score_split(a, b_tok, reordered=False)
        if len(b_tok) <= 4:  # try other token orders (e.g. surname written first in school registers)
            for perm in permutations(b_tok):
                if list(perm) == b_tok:
                    continue
                candidate = self._score_split(a, list(perm), reordered=True)
                if candidate.score > best.score:
                    best = candidate
        best.name_a, best.name_b = name_a, name_b
        for prepared in (a, b):
            if prepared.transliterated_from:
                best.notes.insert(0, f"'{prepared.raw}' ({prepared.transliterated_from}) read as '{prepared.latin}'")
            if prepared.removed:
                best.notes.insert(0, f"ignored title(s) {', '.join(repr(t) for t in prepared.removed)} in '{prepared.raw}'")
        return best

    # ── corroboration ───────────────────────────────────────

    def _corroborate(self, a: IdentityRecord, b: IdentityRecord) -> CorroborationResult:
        fields: dict[str, tuple[FieldStatus, str]] = {}
        if a.dob and b.dob:
            fields["DOB"] = ((FieldStatus.MATCH, f"DOB matches ({a.dob})") if a.dob == b.dob
                             else (FieldStatus.CONFLICT, f"DOB differs ({a.dob} vs {b.dob})"))
        ga, gb = _norm_gender(a.gender), _norm_gender(b.gender)
        if ga and gb:
            fields["gender"] = ((FieldStatus.MATCH, "gender matches") if ga == gb
                                else (FieldStatus.CONFLICT, f"gender differs ({ga} vs {gb})"))
        for label, va, vb in (("father's name", a.father_name, b.father_name),
                              ("mother's name", a.mother_name, b.mother_name)):
            if va and vb:
                fields[label] = self._corroborate_name(label, va, vb)
        if a.district and b.district:
            da, db = a.district.strip().lower(), b.district.strip().lower()
            fields["district"] = ((FieldStatus.MATCH, f"district matches ({a.district})") if da == db
                                  else (FieldStatus.CONFLICT, f"district differs ({a.district} vs {b.district})"))
        return CorroborationResult(fields)

    def _corroborate_name(self, label: str, va: str, vb: str) -> tuple[FieldStatus, str]:
        pa, pb = prepare_name(va), prepare_name(vb)
        if pa.unsupported_script or pb.unsupported_script or not pa.keys or not pb.keys:
            return FieldStatus.NEUTRAL, f"{label} could not be compared automatically"
        if pa.keys == pb.keys:
            return FieldStatus.MATCH, f"{label} matches ('{va}' / '{vb}')"
        comparison = self.compare_names(va, vb)
        if comparison.score < self.review_threshold:
            return FieldStatus.CONFLICT, f"{label} differs ('{va}' vs '{vb}')"
        return FieldStatus.NEUTRAL, f"{label} is close but not exact ('{va}' vs '{vb}', {comparison.score:.2f})"

    # ── decision ────────────────────────────────────────────

    def _decide_pair(self, name: NameMatchResult, corr: CorroborationResult) -> tuple[str, str]:
        if name.unsupported_script:
            return MANUAL_REVIEW, f"script not supported for automatic matching ({name.unsupported_script})"
        if corr.conflicts:
            return MANUAL_REVIEW, f"conflicting {', '.join(corr.conflicts)}"
        if name.score < self.review_threshold:
            return MANUAL_REVIEW, f"name score {name.score:.2f} is below {self.review_threshold:.2f}"
        if name.score >= self.auto_threshold:
            if corr.matches:
                return AUTO_VERIFY, f"name score {name.score:.2f} and {', '.join(corr.matches)} match"
            return PROVISIONAL, (f"name score {name.score:.2f} but no corroborating field "
                                 "(DOB, father's/mother's name, gender, district) is available on both records")
        return PROVISIONAL, f"name score {name.score:.2f} is in the review band ({self.review_threshold:.2f}–{self.auto_threshold:.2f})"

    def resolve(self, source_records: list[IdentityRecord]) -> IdentityResolution:
        """Compare the first record (the student) with every other record; the weakest link decides."""
        if len(source_records) < 2:
            return IdentityResolution(0.0, MANUAL_REVIEW, [], CorroborationResult({}),
                                      "Only one record: there is nothing to confirm the identity against.", {})
        base = source_records[0]
        worst_decision, worst_score = AUTO_VERIFY, 1.0
        comparisons, sentences, last_corr = [], [], CorroborationResult({})
        for record in source_records[1:]:
            name = self.compare_names(base.name, record.name)
            corr = self._corroborate(base, record)
            decision, why = self._decide_pair(name, corr)
            comparisons.append(name)
            last_corr = corr
            if _DECISION_RANK[decision] > _DECISION_RANK[worst_decision]:
                worst_decision = decision
            worst_score = min(worst_score, name.score)
            sentences.append(self._explain(record, name, corr, decision, why))
        return IdentityResolution(
            overall_score=worst_score, decision=worst_decision, name_comparisons=comparisons,
            corroboration=last_corr, explanation=" ".join(sentences),
            details={"thresholds": {"auto_verify": self.auto_threshold, "review": self.review_threshold}},
        )

    @staticmethod
    def _explain(other: IdentityRecord, name: NameMatchResult, corr: CorroborationResult,
                 decision: str, why: str) -> str:
        # Report every token that is not spelled identically, even when its phonetic key matches.
        differing = [p.note for p in name.pairs if p.score is None or p.a != p.b]
        parts = [f"{decision} vs {other.source}: {why}."]
        parts.extend(f"{n[0].upper()}{n[1:]}." for n in name.notes)
        if differing:
            parts.append("Name differences: " + "; ".join(differing) + ".")
        elif name.pairs:
            parts.append("Names match token for token.")
        if corr.fields:
            parts.append(" ".join(f"{d[0].upper()}{d[1:]}." for _, d in corr.fields.values()))
        else:
            parts.append("No corroborating field is present on both records.")
        return " ".join(parts)


def _norm_gender(g: Optional[str]) -> Optional[str]:
    if not g:
        return None
    g = g.strip().upper()
    return {"M": "MALE", "F": "FEMALE", "O": "OTHER"}.get(g, g)
