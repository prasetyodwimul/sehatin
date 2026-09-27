from datetime import date, datetime

from .config import DEFAULT_TRUST_WEIGHTS, TrustWeights


def recency_score(publication_date: str, today: date | None = None) -> float:
    # Unknown/invalid dates receive the conservative floor; retrieval time is not publication time.
    if not publication_date:
        return 0.6
    today = today or date.today()
    try:
        published = datetime.strptime(publication_date, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return 0.6
    age_days = max(0, (today - published).days)
    if age_days <= 365:
        return 1.0
    if age_days <= 365 * 2:
        return 0.9
    if age_days <= 365 * 5:
        return 0.75
    return 0.6


def weighted_evidence_score(
    authority: float,
    quality: float,
    recency: float,
    relevance: float,
    weights: TrustWeights = DEFAULT_TRUST_WEIGHTS,
) -> float:
    score = (
        authority * weights.source_authority
        + quality * weights.evidence_quality
        + recency * weights.recency
        + relevance * weights.claim_relevance
    )
    return round(max(0.0, min(1.0, score)), 4)
