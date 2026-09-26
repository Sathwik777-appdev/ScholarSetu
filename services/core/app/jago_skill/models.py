from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

EMBEDDING_DIMS = 384


class GuidelineChunk(Base):
    """A verbatim passage of an official scheme guideline, with its embedding and keyword index."""
    __tablename__ = "guideline_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    scheme: Mapped[str] = mapped_column(String, index=True, nullable=False)
    section: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source_title: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    effective: Mapped[str] = mapped_column(String, nullable=False)
    corpus_version: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMS), nullable=False)
    # Section headings weigh more than body text (A vs B) so "Income Criteria" beats a passing mention.
    tsv = mapped_column(TSVECTOR, Computed("setweight(to_tsvector('english', section), 'A') || "
                                           "setweight(to_tsvector('english', text), 'B')", persisted=True))
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                                                 nullable=False)

    __table_args__ = (Index("idx_guideline_tsv", "tsv", postgresql_using="gin"),)
