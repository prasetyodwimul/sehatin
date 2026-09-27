from dataclasses import dataclass


@dataclass(frozen=True)
class TrustWeights:
    source_authority: float = 0.30
    evidence_quality: float = 0.30
    recency: float = 0.15
    claim_relevance: float = 0.25

    def __post_init__(self):
        total = self.source_authority + self.evidence_quality + self.recency + self.claim_relevance
        if abs(total - 1.0) > 1e-9:
            raise ValueError("Trust Engine weights must sum to 1.0")


DEFAULT_TRUST_WEIGHTS = TrustWeights()


MIN_EVIDENCE_RELEVANCE = 0.45
MAX_EVIDENCE_RESULTS = 6
