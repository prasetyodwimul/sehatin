from __future__ import annotations

import logging

from sqlalchemy import select

from app.database import session_scope
from app.models import EvidenceDocumentModel, EvidenceSourceModel
from app.trust_engine.evidence_provider import EvidenceRecord
from app.trust_engine.source_validator import source_tier

logger = logging.getLogger("sehatin.knowledge_base")


class DatabaseEvidenceProvider:
    """Reads curated evidence from PostgreSQL/SQLAlchemy knowledge-base tables."""

    @property
    def is_demo(self) -> bool:
        return False

    def records(self) -> list[EvidenceRecord]:
        try:
            with session_scope() as db:
                rows = db.execute(
                    select(EvidenceDocumentModel, EvidenceSourceModel)
                    .join(EvidenceSourceModel, EvidenceDocumentModel.source_id == EvidenceSourceModel.id)
                    .where(EvidenceSourceModel.verified.is_(True))
                ).all()
                return [
                    EvidenceRecord(
                        id=doc.id,
                        keywords=tuple(doc.keywords or []),
                        title=doc.title,
                        source=source.organization,
                        source_type=source.source_type,
                        publication_date=doc.publication_date.isoformat(),
                        retrieved_at=source.last_checked.date().isoformat(),
                        url=source.url,
                        stance=doc.stance_hint,
                        excerpt=doc.content,
                        quality=float(doc.evidence_quality),
                        authority_level=source_tier(source.source_type),
                        authority_score=float(source.authority_score),
                        verified=bool(source.verified),
                        demo=bool(doc.is_demo),
                        provider="database",
                        source_id=source.id,
                        canonical_url=source.url,
                        independent_group=source.organization,
                        trace_note="Curated evidence loaded from the SEHATIN knowledge-base database.",
                    )
                    for doc, source in rows
                ]
        except Exception as exc:
            logger.warning("Database evidence unavailable: %s", exc.__class__.__name__)
            return []
