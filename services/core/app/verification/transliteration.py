"""Script detection and transliteration of Indian-script names to plain Latin.

Supported: Devanagari, Bengali, Gurmukhi, Gujarati, Odia, Tamil, Telugu, Kannada, Malayalam.
Anything else (e.g. Ol Chiki, used for Santali) is reported as unsupported so the caller can
route it to a human instead of producing a misleading low score.

For scripts whose languages drop the inherent vowel in speech (Hindi, Bengali, Punjabi,
Gujarati), the silent schwa is removed before transliteration: हांसदा → "hansda", not "hamsada".
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

from indic_transliteration import sanscript

# Unicode block start → (script name, sanscript scheme, drops schwa)
_BLOCKS = {
    0x0900: ("Devanagari", sanscript.DEVANAGARI, True),
    0x0980: ("Bengali", sanscript.BENGALI, True),
    0x0A00: ("Gurmukhi", sanscript.GURMUKHI, True),
    0x0A80: ("Gujarati", sanscript.GUJARATI, True),
    0x0B00: ("Odia", sanscript.ORIYA, True),     # Odia names are romanized without the inherent vowel
    0x0B80: ("Tamil", None, False),       # mapped through Devanagari, see _tamil_to_devanagari
    0x0C00: ("Telugu", sanscript.TELUGU, False),
    0x0C80: ("Kannada", sanscript.KANNADA, False),
    0x0D00: ("Malayalam", sanscript.MALAYALAM, False),
}

# Offsets inside an ISCII-derived Unicode block (identical layout across these scripts).
_VIRAMA = 0x4D
_NUKTA = 0x3C


def _is_consonant(off: int) -> bool:
    return 0x15 <= off <= 0x39 or 0x58 <= off <= 0x5F


def _is_matra(off: int) -> bool:
    return 0x3E <= off <= 0x4C or 0x55 <= off <= 0x57 or 0x62 <= off <= 0x63


def _is_independent_vowel(off: int) -> bool:
    return 0x05 <= off <= 0x14 or 0x60 <= off <= 0x61


def _is_modifier(off: int) -> bool:  # candrabindu, anusvara, visarga
    return 0x01 <= off <= 0x03


# Scripts used for tribal languages that have no automatic transliteration here.
_UNSUPPORTED_BLOCKS = [
    (0x1C50, 0x1C7F, "Ol Chiki"),        # Santali
    (0x118A0, 0x118FF, "Warang Citi"),   # Ho
    (0x11D00, 0x11D5F, "Masaram Gondi"),
    (0x11D60, 0x11DAF, "Gunjala Gondi"),
]


def _unsupported_block_name(cp: int) -> Optional[str]:
    for start, end, name in _UNSUPPORTED_BLOCKS:
        if start <= cp <= end:
            return name
    return None


def _unicode_script_guess(ch: str) -> str:
    try:  # "TIBETAN LETTER KA" -> "Tibetan"
        return re.split(r" (?:LETTER|SIGN|VOWEL|DIGIT|MARK|SYLLABLE)\b", unicodedata.name(ch))[0].title()
    except ValueError:
        return f"U+{ord(ch):04X}"


@dataclass
class ScriptInfo:
    scripts: set[str] = field(default_factory=set)
    unsupported: set[str] = field(default_factory=set)

    @property
    def is_latin_only(self) -> bool:
        return self.scripts <= {"Latin"}


def detect_scripts(text: str) -> ScriptInfo:
    info = ScriptInfo()
    for ch in text:
        if not ch.isalpha():
            continue
        cp = ord(ch)
        if cp < 0x0250:
            info.scripts.add("Latin")
            continue
        block = cp & ~0x7F
        if block in _BLOCKS:
            info.scripts.add(_BLOCKS[block][0])
            continue
        name = _unsupported_block_name(cp) or _unicode_script_guess(ch)
        info.scripts.add(name)
        info.unsupported.add(name)
    return info


@dataclass
class _Unit:
    consonant: bool
    vowel: Optional[str]  # "inherent" | "matra" | "virama" | None (independent vowel)
    deleted: bool = False

    @property
    def sounds_vowel(self) -> bool:
        return (not self.consonant) or self.vowel == "matra" or (self.vowel == "inherent" and not self.deleted)


def _delete_schwas(word: str, base: int) -> str:
    """Insert a virama after consonants whose inherent vowel is silent in speech."""
    offs = [ord(c) - base if (ord(c) & ~0x7F) == base else None for c in word]
    units: list[_Unit] = []
    positions: list[int] = []  # index in `word` after which a virama would go
    i = 0
    while i < len(word):
        off = offs[i]
        if off is not None and _is_consonant(off):
            j = i + 1
            if j < len(word) and offs[j] == _NUKTA:
                j += 1
            if j < len(word) and offs[j] == _VIRAMA:
                vowel = "virama"
            elif j < len(word) and offs[j] is not None and _is_matra(offs[j]):
                vowel = "matra"
            else:
                vowel = "inherent"
            units.append(_Unit(True, vowel))
            positions.append(j - 1)
            i = j
            continue
        if off is not None and _is_independent_vowel(off):
            units.append(_Unit(False, None))
            positions.append(i)
        i += 1

    n = len(units)
    if n > 1 and units[-1].consonant and units[-1].vowel == "inherent":
        units[-1].deleted = True  # word-final schwa: सोरेन → soren
    # Medial schwas left to right, so compounds split correctly: फूलमनी → phulmani, रामचरण → ramcharan.
    for k in range(1, n - 1):
        u = units[k]
        if (u.consonant and u.vowel == "inherent" and units[k - 1].sounds_vowel
                and units[k + 1].consonant and units[k + 1].sounds_vowel):
            u.deleted = True  # V C(a) C V  →  V C C V

    out = list(word)
    virama = chr(base + _VIRAMA)
    for u, pos in sorted(zip(units, positions), key=lambda t: -t[1]):
        if u.deleted:
            out.insert(pos + 1, virama)
    return "".join(out)


_TAMIL_INITIAL_CA = re.compile(r"\bch")


def _tamil_to_devanagari(text: str) -> str:
    """Tamil shares the ISCII layout; shift into Devanagari so one pipeline handles both."""
    return "".join(chr(ord(c) - 0x0B80 + 0x0900) if 0x0B80 <= ord(c) <= 0x0BFF else c for c in text)


def _hk_to_plain(hk: str) -> str:
    """Harvard-Kyoto → plain lowercase Latin as Indian names are usually spelled."""
    hk = re.sub(r"\d", "", hk)                      # sanscript's nukta/variant markers
    hk = re.sub(r"M(?=[pbmPB])", "m", hk)           # anusvara before labials
    for src, dst in (("C", "chh"), ("c", "ch"), ("~", "n"), ("M", "n"), ("H", "h"), ("z", "sh"), ("S", "sh"),
                     ("RR", "ri"), ("R", "ri"), ("G", "n"), ("J", "n")):
        hk = hk.replace(src, dst)
    return hk.lower()


def to_latin(text: str) -> str:
    """Transliterate every supported Indic-script word to Latin; Latin words pass through."""
    words = []
    for word in text.split():
        cps = [ord(c) & ~0x7F for c in word if ord(c) >= 0x0900]
        block = cps[0] if cps else None
        if block not in _BLOCKS:
            words.append(word)
            continue
        _, scheme, drops_schwa = _BLOCKS[block]
        if block == 0x0B80:
            converted = _tamil_to_devanagari(word)
            latin = _hk_to_plain(sanscript.transliterate(converted, sanscript.DEVANAGARI, sanscript.HK))
            latin = _TAMIL_INITIAL_CA.sub("s", latin)  # word-initial ச is usually written "s"
        else:
            if drops_schwa:
                word = _delete_schwas(word, block)
            latin = _hk_to_plain(sanscript.transliterate(word, scheme, sanscript.HK))
            if block == 0x0980:
                latin = latin.replace("v", "b")  # Bengali ব is written "b" in names
            if block == 0x0900:
                latin = re.sub(r"anv$", "aon", latin)  # word-final -ांव reads "aon": गांव gaon, ओरांव Oraon
        words.append(latin)
    return " ".join(words)
