from dataclasses import dataclass
from typing import Literal, Protocol

Stance = Literal["support", "contradict", "neutral"]


@dataclass(frozen=True)
class EvidenceRecord:
    id: str
    keywords: tuple[str, ...]
    title: str
    source: str
    source_type: str
    publication_date: str
    retrieved_at: str
    url: str
    stance: Stance
    excerpt: str
    quality: float
    authority_level: int
    authority_score: float | None = None
    verified: bool = True
    demo: bool = True
    provider: str = "curated"
    source_id: str | None = None
    canonical_url: str | None = None
    independent_group: str | None = None
    trace_note: str | None = None


class EvidenceProvider(Protocol):
    @property
    def is_demo(self) -> bool: ...

    def records(self) -> list[EvidenceRecord]: ...
