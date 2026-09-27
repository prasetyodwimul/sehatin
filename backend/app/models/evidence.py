from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_str


class HealthClaimModel(TimestampMixin, Base):
    __tablename__ = "health_claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    claim_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Raw claim persistence is opt-in. Default runtime stores NULL for privacy.
    claim_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    trust_score: Mapped[int] = mapped_column(nullable=False)
    confidence: Mapped[int] = mapped_column(nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class EvidenceSourceModel(TimestampMixin, Base):
    __tablename__ = "evidence_sources"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(220), nullable=False)
    organization: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    authority_score: Mapped[float] = mapped_column(Float, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    publication_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_checked: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceDocumentModel(TimestampMixin, Base):
    __tablename__ = "evidence_documents"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("evidence_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    publication_date: Mapped[date] = mapped_column(Date, nullable=False)
    evidence_quality: Mapped[float] = mapped_column(Float, nullable=False)
    keywords: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    stance_hint: Mapped[str] = mapped_column(String(16), nullable=False, default="neutral")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ClaimEvidenceModel(TimestampMixin, Base):
    __tablename__ = "claim_evidence"
    __table_args__ = (
        UniqueConstraint("claim_id", "evidence_document_id", name="claim_evidence_unique_document"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    claim_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("health_claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_document_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("evidence_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stance: Mapped[str] = mapped_column(String(16), nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    authority_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    recency_score: Mapped[float] = mapped_column(Float, nullable=False)
    weighted_score: Mapped[float] = mapped_column(Float, nullable=False)
