"""Labelled evaluation of guideline retrieval (JAGO search_guidelines).

Each relevant question lists a regex that the correct official passage contains. Unrelated
questions must return nothing (JAGO then says it does not know). Run with -s to see the table.
"""

import re

import pytest

from app.config import settings
from app.jago_skill import rag
from app.jago_skill.embeddings import get_embedder

RELEVANT = [
    ("What is the income limit for post matric?", r"2,50,000|2\.50 lakh"),
    ("पोस्ट मैट्रिक छात्रवृत्ति के लिए आय सीमा क्या है", r"2,50,000|2\.50 lakh"),
    ("post matric aay seema kitni hai", r"2,50,000|2\.50 lakh"),
    ("Who is eligible for post matric scholarship?", r"Scheduled Tribe|Matriculation"),
    ("What is the income limit for pre matric?", r"2,00,000|2\.00 lakh"),
    ("How much is the scholarship for hostellers under pre matric?", r"Hostellers|350"),
    ("What is the income limit for top class scholarship?", r"6\.0 lakh|6,00,000"),
    ("How much is the book allowance in top class?", r"Books|5000"),
    ("What is the fellowship amount for PhD?", r"31000|35000"),
    ("What is the age limit for NFST fellowship?", r"36 years"),
    ("What is the age limit for overseas scholarship?", r"[Aa]ge|years"),
    ("What is the income ceiling for national overseas scholarship?", r"6,00,000|Six lakh"),
    ("How many overseas scholarships are given every year?", r"20|slots|awards"),
    ("Is income certificate needed every year for post matric?", r"[Ii]ncome certificate"),
    ("What allowance is given to students with disability in post matric?", r"[Dd]isab|Divyang"),
    ("How long is the NFST fellowship tenure?", r"[Tt]enure|years"),
]
UNRELATED = [
    "What is the capital of France?",
    "How do I bake a chocolate cake?",
    "Which cricket team won the world cup?",
]


@pytest.fixture
async def search(db):
    async def _search(query):
        return await rag.search(db, get_embedder(), query, limit=3)
    return _search


async def test_relevant_questions_find_the_right_passage(search):
    rows, top1, top3 = [], 0, 0
    for query, pattern in RELEVANT:
        results = await search(query)
        ranks = [i for i, p in enumerate(results) if re.search(pattern, p.section + " " + p.text)]
        top1 += bool(ranks and ranks[0] == 0)
        top3 += bool(ranks)
        rows.append((query, results[0].score if results else 0.0, ranks[0] + 1 if ranks else "-",
                     results[0].section[:40] if results else "(nothing)"))
    print("\nGuideline retrieval (relevant questions): score, rank of correct passage, top section")
    for query, score, rank, section in rows:
        print(f"  {score:.3f}  rank={rank!s:2}  {query[:55]:55}  -> {section}")
    print(f"  top-1: {top1}/{len(RELEVANT)}   top-3: {top3}/{len(RELEVANT)}")
    assert top3 / len(RELEVANT) >= 0.85, "fewer than 85% of questions find the right passage in the top 3"


async def test_unrelated_questions_return_nothing(search):
    for query in UNRELATED:
        results = await search(query)
        assert results == [], f"{query!r} returned {[(p.score, p.section) for p in results]}"


def test_threshold_is_configured():
    assert 0 < settings.GUIDELINE_MIN_SCORE < 1
