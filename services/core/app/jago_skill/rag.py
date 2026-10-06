"""Guideline retrieval: hybrid pgvector similarity + Postgres full-text match over official passages.

Only verbatim passages from the official documents are returned, each with its citation.
If nothing scores above GUIDELINE_MIN_SCORE, the caller must say it does not know.
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy import delete, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.jago_skill.embeddings import Embedder
from app.jago_skill.models import GuidelineChunk
from app.shared.types import SchemeType

logger = logging.getLogger("scholarsetu.jago.rag")

CORPUS_PATH = Path(__file__).with_name("guidelines") / "corpus.jsonl"
VECTOR_WEIGHT, KEYWORD_WEIGHT = 0.5, 0.5

SCHEME_CUES = [
    (SchemeType.PRE_MATRIC, r"pre[\s-]?matric|प्री[\s-]?मैट्रिक|class (ix|x|9|10)\b"),
    (SchemeType.POST_MATRIC, r"post[\s-]?matric|पोस्ट[\s-]?मैट्रिक"),
    (SchemeType.TOP_CLASS, r"top[\s-]?class|टॉप क्लास|premier institut"),
    (SchemeType.NFST, r"\bnfst\b|fellowship|m\.?\s?phil|ph\.?\s?d|फ़ेलोशिप|फेलोशिप"),
    (SchemeType.NOS, r"overseas|abroad|\bnos\b|foreign|विदेश|प्रवासी"),
]


@dataclass
class Passage:
    chunk_id: str
    scheme: str
    section: str
    text: str
    source_title: str
    source_url: str
    effective: str
    score: float


def corpus_version() -> str:
    return hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest()


def detect_scheme(query: str) -> Optional[SchemeType]:
    q = query.lower()
    for scheme, pattern in SCHEME_CUES:
        if re.search(pattern, q):
            return scheme
    return None


async def ensure_index(db: AsyncSession, embedder: Optional[Embedder] = None) -> int:
    """(Re)embed the corpus when it changed. Returns the number of chunks indexed now (0 if already current)."""
    version = corpus_version()
    rows = [json.loads(line) for line in CORPUS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    current = await db.scalar(select(func.count()).select_from(GuidelineChunk)
                              .where(GuidelineChunk.corpus_version == version))
    if current == len(rows):
        return 0

    precomputed_file = Path(__file__).with_name("guidelines") / "precomputed_embeddings.json"
    if precomputed_file.exists():
        try:
            precomputed = json.loads(precomputed_file.read_text(encoding="utf-8"))
            vectors = [precomputed.get(r["id"]) for r in rows]
            if all(v is not None for v in vectors):
                await db.execute(delete(GuidelineChunk))
                db.add_all(GuidelineChunk(id=r["id"], scheme=r["scheme"], section=r["section"], text=r["text"],
                                          source_title=r["source_title"], source_url=r["source_url"], effective=r["effective"],
                                          corpus_version=version, embedding=v) for r, v in zip(rows, vectors, strict=True))
                await db.commit()
                logger.info("indexed %d guideline chunks from precomputed cache (corpus %s)", len(rows), version[:12])
                return len(rows)
        except Exception:
            logger.exception("failed reading precomputed embeddings; falling back to dynamic embedding")

    if embedder is not None:
        vectors = await embedder.embed([f"{r['section']}\n{r['text']}" for r in rows])
        await db.execute(delete(GuidelineChunk))
        db.add_all(GuidelineChunk(id=r["id"], scheme=r["scheme"], section=r["section"], text=r["text"],
                                  source_title=r["source_title"], source_url=r["source_url"], effective=r["effective"],
                                  corpus_version=version, embedding=v) for r, v in zip(rows, vectors, strict=True))
        await db.commit()
        logger.info("indexed %d guideline chunks (corpus %s)", len(rows), version[:12])
        return len(rows)
    return 0


# Hindi / Hinglish words mapped to the English terms the official guidelines use, so the keyword half
# of the search works for questions asked in Hindi. The vector half is multilingual already.
GLOSSARY = {
    "आय": "income", "आमदनी": "income", "aay": "income", "amdani": "income", "सीमा": "limit ceiling",
    "seema": "limit ceiling", "आयु": "age", "उम्र": "age", "umar": "age", "umra": "age", "छात्रवृत्ति": "scholarship",
    "राशि": "amount value", "वजीफा": "stipend", "छात्रावास": "hostel hosteller", "hostel": "hostel hosteller",
    "दस्तावेज़": "documents required", "दस्तावेज": "documents required", "dastavej": "documents required",
    "kagaz": "documents required", "पात्रता": "eligibility conditions", "पात्र": "eligibility conditions",
    "patrata": "eligibility conditions", "शुल्क": "fee", "फीस": "fee", "fees": "fee", "अवधि": "duration",
    "नवीनीकरण": "renewal", "renewal": "renewal", "फ़ेलोशिप": "fellowship", "फेलोशिप": "fellowship",
    "विदेश": "overseas abroad", "आवेदन": "application", "चयन": "selection", "किस्त": "instalment",
    "दिव्यांग": "disability divyangjan", "लड़कियों": "female girls", "किताब": "books",
}
_STOP = {"what", "which", "how", "much", "is", "the", "for", "of", "a", "an", "to", "in", "on", "and", "are",
         "under", "scheme", "scholarship", "ka", "ki", "ke", "hai", "kya", "kitna", "kitni", "me", "mein"}


# Words that name a scheme are handled by scheme filtering, so they do not count towards coverage.
_SCHEME_WORDS = {"post", "pre", "matric", "top", "class", "national", "overseas", "nfst", "nos", "fellowship",
                 "scholarship", "scholarships", "st", "students", "student", "tribe", "tribal"}


def _terms(query: str) -> list[str]:
    """Content terms of a question, with Hindi/Hinglish words mapped through the glossary."""
    words = re.findall(r"[\w\u0900-\u097F]+", query.lower())
    terms: list[str] = []
    for word in words:
        expansion = GLOSSARY.get(word)
        if expansion:
            terms.extend(expansion.split())
        elif re.fullmatch(r"[a-z0-9]{2,}", word) and word not in _STOP:
            terms.append(word)
    return list(dict.fromkeys(terms))


def _or_query(query: str) -> Optional[str]:
    terms = _terms(query)
    return " | ".join(terms) if terms else None


def _coverage(terms: list[str], section: str, text: str) -> float:
    """Share of content terms a passage contains (prefix match tolerates inflection); a heading hit counts more."""
    content = [t for t in terms if t not in _SCHEME_WORDS]
    if not content:
        return 0.0
    section_l, body_l = section.lower(), text.lower()
    total = 0.0
    for term in content:
        stem = term[:5]
        if stem in section_l:
            total += 1.0
        elif stem in body_l:
            total += 0.7
    return total / len(content)


async def search(db: AsyncSession, embedder: Embedder, query: str, scheme: Optional[SchemeType] = None,
                 limit: int = 3) -> list[Passage]:
    """Merge the best vector matches with the best keyword matches, then rank by the combined score."""
    scheme = scheme or detect_scheme(query)
    [vector] = await embedder.embed([query])
    similarity = (1 - GuidelineChunk.embedding.cosine_distance(vector)).label("similarity")
    or_query = _or_query(query)
    if or_query:
        keyword = func.ts_rank_cd(GuidelineChunk.tsv, func.to_tsquery("english", or_query), 32).label("keyword")
    else:
        keyword = literal(0.0).label("keyword")
    base = select(GuidelineChunk, similarity, keyword)
    if scheme is not None:
        base = base.where(GuidelineChunk.scheme == scheme.value)
    candidates = {}
    for order in (similarity.desc(), keyword.desc()):
        for chunk, sim, kw in (await db.execute(base.order_by(order).limit(20))).all():
            candidates[chunk.id] = (chunk, float(sim), float(kw or 0))
    terms = _terms(query)
    has_content_terms = any(t not in _SCHEME_WORDS for t in terms)
    scored = []
    for chunk, sim, _kw in candidates.values():
        if has_content_terms:
            score = VECTOR_WEIGHT * sim + KEYWORD_WEIGHT * _coverage(terms, chunk.section, chunk.text)
        else:  # nothing to match lexically (e.g. untranslated Hindi): rely on the multilingual embedding
            score = sim
        scored.append(Passage(chunk.id, chunk.scheme, chunk.section, chunk.text, chunk.source_title,
                              chunk.source_url, chunk.effective, round(score, 4)))
    scored.sort(key=lambda p: p.score, reverse=True)
    # The threshold decides whether anything is relevant; if the best match clears it, return the top results.
    if not scored or scored[0].score < settings.GUIDELINE_MIN_SCORE:
        return []
    return scored[:limit]


async def section_text(db: AsyncSession, passage: Passage, max_chars: int = 1400) -> str:
    """The whole official section a passage belongs to (all of its chunks, in document order)."""
    document = passage.chunk_id.split(":")[0]
    base = passage.section.removesuffix(" (cont.)")
    chunks = (await db.execute(
        select(GuidelineChunk.text).where(GuidelineChunk.id.like(f"{document}:%"),
                                          GuidelineChunk.section.in_([base, f"{base} (cont.)"]))
        .order_by(GuidelineChunk.id)
    )).scalars().all()
    text = " ".join(" ".join(c.split()) for c in chunks) or passage.text
    return text if len(text) <= max_chars else text[:max_chars].rsplit(" ", 1)[0] + " …"
