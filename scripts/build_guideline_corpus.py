"""Build JAGO's guideline corpus from the official MoTA documents.

Downloads each document listed in services/core/app/jago_skill/guidelines/sources.json, checks
its SHA-256, extracts the text and splits it into section-sized chunks, and writes corpus.jsonl.
The chunks are verbatim document text; nothing is summarised or rewritten.

    python scripts/build_guideline_corpus.py            # download + rebuild
    python scripts/build_guideline_corpus.py --pdf-dir DIR   # use already-downloaded PDFs named <id>.pdf

Requires: pypdf, httpx.
"""

import argparse
import hashlib
import io
import json
import re
from pathlib import Path

import httpx
from pypdf import PdfReader

GUIDELINES = Path(__file__).resolve().parents[1] / "services" / "core" / "app" / "jago_skill" / "guidelines"
MAX_CHUNK = 650
# "3.2. Conditions of eligibility", "2.6 Value of Fellowship", "4. CONDITIONS OF ELIGIBILITY"
HEADING = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){0,3})\.?\s+([A-Z][A-Za-z&/’'(),\- ]{2,80}?)\s*:?\s*$")
PART_B = re.compile(r"PART\s*[-–]\s*B", re.I)
# Headings written inline with their text: "2.3 Age limit: Maximum 36 years, as on ..."
INLINE_HEADING = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){1,3})\.?\s+([A-Z][A-Za-z&/' ]{2,40}?)\s*:\s+(\S.*)$")


def _pdf_bytes(doc: dict, pdf_dir: Path | None) -> bytes:
    if pdf_dir:
        data = (pdf_dir / f"{doc['id']}.pdf").read_bytes()
    else:
        response = httpx.get(doc["url"], follow_redirects=True, timeout=60)
        response.raise_for_status()
        data = response.content
    digest = hashlib.sha256(data).hexdigest()
    if digest != doc["sha256"]:
        raise SystemExit(f"{doc['id']}: SHA-256 mismatch ({digest}); the published document changed. "
                         "Review it and update sources.json deliberately.")
    return data


def _sections(text: str) -> list[tuple[str, str]]:
    """Split into (heading, body) pairs; the table of contents is dropped as it has no body text."""
    sections: list[tuple[str, list[str]]] = [("Preamble", [])]
    for line in text.splitlines():
        m = HEADING.match(line)
        inline = INLINE_HEADING.match(line)
        if m and not re.search(r"\s\d{1,2}(-\d{1,2})?\s*$", line):  # TOC lines end with a page number
            sections.append((f"{m.group(1)} {m.group(2).strip()}", []))
        elif inline:
            sections.append((f"{inline.group(1)} {inline.group(2).strip()}", [inline.group(3)]))
        else:
            sections[-1][1].append(line)
    out = []
    for heading, lines in sections:
        body = re.sub(r"[ \t]+", " ", "\n".join(lines))
        body = re.sub(r"\n\s*\n+", "\n", body).strip()
        if len(body) >= 40 and sum(c.isalpha() for c in body) / len(body) > 0.55:
            out.append((heading, body))
    return out


def _windows(body: str) -> list[str]:
    if len(body) <= MAX_CHUNK:
        return [body]
    # Split at sentence ends and at list items like "a.", "(ii)", "i." so each clause stays whole.
    sentences = re.split(r"(?<=[.;:])\s+|\n(?=\s*(?:\(?[a-z]{1,4}\)|[a-z]{1,3}\.|\d{1,2}\.)\s)", body)
    chunks, current = [], ""
    for sentence in sentences:
        if current and len(current) + len(sentence) > MAX_CHUNK:
            chunks.append(current.strip())
            current = ""
        current += sentence + " "
    if current.strip():
        chunks.append(current.strip())
    return chunks


def build(pdf_dir: Path | None) -> list[dict]:
    manifest = json.loads((GUIDELINES / "sources.json").read_text())
    corpus = []
    for doc in manifest["documents"]:
        reader = PdfReader(io.BytesIO(_pdf_bytes(doc, pdf_dir)))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        part_b_at = None
        if doc.get("part_b_scheme"):
            matches = list(PART_B.finditer(text))
            part_b_at = matches[-1].start() if matches else None  # the last match is the body, not the TOC
        parts = [(text[:part_b_at], doc["schemes"][0]), (text[part_b_at:], doc["part_b_scheme"])] if part_b_at \
            else [(text, doc["schemes"][0])]
        for part_text, scheme in parts:
            for heading, body in _sections(part_text):
                for i, chunk in enumerate(_windows(body)):
                    corpus.append({
                        "id": f"{doc['id']}:{len(corpus):04d}",
                        "scheme": scheme,
                        "section": heading if i == 0 else f"{heading} (cont.)",
                        "text": chunk,
                        "source_title": doc["title"],
                        "source_url": doc["url"],
                        "effective": doc["effective"],
                    })
    return corpus


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dir", type=Path)
    args = parser.parse_args()
    corpus = build(args.pdf_dir)
    out = GUIDELINES / "corpus.jsonl"
    out.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in corpus), encoding="utf-8")
    by_scheme: dict[str, int] = {}
    for c in corpus:
        by_scheme[c["scheme"]] = by_scheme.get(c["scheme"], 0) + 1
    print(f"wrote {len(corpus)} chunks to {out}: {by_scheme}")


if __name__ == "__main__":
    main()
