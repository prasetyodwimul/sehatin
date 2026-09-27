from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Verdict = Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "INSUFFICIENT_EVIDENCE", "CONTRADICTED"]
EvidenceLevel = Literal["HIGH", "MODERATE", "LOW", "INSUFFICIENT"]
InputType = Literal["claim", "article", "url"]


class HealthCheckRequest(BaseModel):
    input_type: InputType = "claim"
    text: str | None = Field(default=None, max_length=20_000)
    url: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def validate_input(self):
        if self.text is not None:
            self.text = " ".join(self.text.strip().split())
            if "\x00" in self.text:
                raise ValueError("Input mengandung karakter yang tidak diizinkan")

        # Backwards compatibility: an URL-only payload can omit input_type.
        if self.url and not self.text and self.input_type == "claim":
            self.input_type = "url"

        if self.input_type == "url":
            if not self.url or not self.url.strip():
                raise ValueError("URL artikel wajib diisi")
        else:
            if not self.text or len(self.text) < 8:
                raise ValueError("Masukkan informasi kesehatan minimal 8 karakter")
            if self.input_type == "claim" and len(self.text) > 5000:
                raise ValueError("Klaim terlalu panjang untuk dianalisis")
        return self


class EvidenceItem(BaseModel):
    id: str
    title: str
    source: str
    source_type: str
    publication_date: str
    retrieved_at: str
    url: str
    stance: Literal["support", "contradict", "neutral"]
    excerpt: str
    authority_level: int
    authority_score: float
    evidence_quality_score: float
    recency_score: float
    relevance_score: float
    weighted_score: float
    demo: bool = True
    source_id: str | None = None
    verified: bool = True
    provider: str = "curated"
    canonical_url: str | None = None
    independent_group: str | None = None
    trace_note: str | None = None


class SourceSummary(BaseModel):
    name: str
    title: str
    source_type: str
    publication_date: str
    url: str
    last_checked: str
    verified: bool = True
    authority_level: int | None = None
    provider: str = "curated"
    why_considered: str | None = None


class ScoreBreakdown(BaseModel):
    source_authority: float
    evidence_quality: float
    recency: float
    relevance: float
    source_agreement: float
    independent_publishers: int


class ScoringWeights(BaseModel):
    source_authority: float
    evidence_quality: float
    recency: float
    claim_relevance: float


class EvidenceTrace(BaseModel):
    evidence_id: str
    source_name: str
    source_url: str
    stance: Literal["support", "contradict", "neutral"]


class HealthCheckResponse(BaseModel):
    claim: str
    verdict: Verdict
    result: Verdict
    trust_score: int
    evidence_confidence: int
    confidence: int
    score_breakdown: ScoreBreakdown
    scoring_weights: ScoringWeights
    evidence_level: EvidenceLevel
    explanation: str
    summary: str
    why_this_result: str
    reason: str
    supporting_evidence: list[EvidenceItem]
    contradicting_evidence: list[EvidenceItem]
    neutral_evidence: list[EvidenceItem] = Field(default_factory=list)
    sources: list[SourceSummary]
    sources_checked: int
    last_checked: str
    limitations: list[str]
    demo_evidence: bool = True

    # Extended transparent-checking metadata. Defaults preserve older callers.
    original_claim: str | None = None
    normalized_claim: str | None = None
    claim_id: str | None = None
    claim_type: str | None = None
    topic: str | None = None
    confidence_label: Literal["HIGH", "MODERATE", "LOW", "INSUFFICIENT"] | None = None
    evidence_trace: list[EvidenceTrace] = Field(default_factory=list)
    retrieval_notes: list[str] = Field(default_factory=list)


class ArticleInfo(BaseModel):
    title: str | None = None
    publisher: str | None = None
    published_date: str | None = None
    author: str | None = None
    url: str | None = None
    text_length: int = 0


class HealthCheckRunResponse(HealthCheckResponse):
    run_id: str
    input_type: InputType
    claims: list[HealthCheckResponse]
    article: ArticleInfo | None = None
    retrieval_mode: Literal["curated", "live+curated", "url+curated", "url+live+curated"] = "curated"
    source_outages: list[str] = Field(default_factory=list)
    checked_claims: int = 1
