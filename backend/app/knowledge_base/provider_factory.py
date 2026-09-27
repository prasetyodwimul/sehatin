from __future__ import annotations

from app.config import get_settings
from app.trust_engine.demo_evidence import DemoEvidenceProvider
from app.trust_engine.evidence_provider import EvidenceProvider, EvidenceRecord

from .database_provider import DatabaseEvidenceProvider


class AutoEvidenceProvider:
    """Prefer database evidence; demo fallback is development-only."""

    def __init__(self):
        self.database = DatabaseEvidenceProvider()
        self.demo = DemoEvidenceProvider()
        self._is_demo = True

    @property
    def is_demo(self) -> bool:
        return self._is_demo

    def records(self) -> list[EvidenceRecord]:
        db_records = self.database.records()
        if db_records:
            self._is_demo = all(item.demo for item in db_records)
            return db_records

        corpus = self.demo.records()
        curated = [item for item in corpus if not item.demo]
        demo_only = [item for item in corpus if item.demo]

        # Production may use the checked-in, source-traceable curated corpus,
        # but never the old scenario/demo records. Development keeps the demo
        # fixtures for existing tests and UI scenarios.
        if get_settings().environment.lower() == "production":
            self._is_demo = False
            return curated

        self._is_demo = all(item.demo for item in corpus)
        return [*curated, *demo_only]


def build_evidence_provider() -> EvidenceProvider:
    mode = get_settings().evidence_provider
    if mode == "database":
        return DatabaseEvidenceProvider()
    if mode == "auto":
        return AutoEvidenceProvider()
    return DemoEvidenceProvider()
