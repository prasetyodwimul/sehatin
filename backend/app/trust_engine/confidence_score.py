from collections.abc import Iterable


def _mean(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def agreement_score(support_publishers: set[str], contradict_publishers: set[str]) -> float:
    """How consistently independent publishers point in the same direction.

    A publisher appearing on both sides represents nuanced/mixed evidence and
    must not be interpreted as 100% agreement.
    """
    if not support_publishers and not contradict_publishers:
        return 0.0
    if support_publishers and contradict_publishers:
        all_publishers = support_publishers | contradict_publishers
        overlap = support_publishers & contradict_publishers
        if not all_publishers:
            return 0.0
        support_only = len(support_publishers - overlap)
        contradict_only = len(contradict_publishers - overlap)
        mixed = len(overlap)
        dominant = max(support_only, contradict_only)
        # Mixed publishers contribute half-credit to directional consistency.
        return round((dominant + 0.5 * mixed) / len(all_publishers), 4)
    publishers = support_publishers or contradict_publishers
    return 1.0 if len(publishers) >= 2 else 0.7


def claim_support_score(support_scores: list[float], contradict_scores: list[float]) -> int:
    """0..100: how strongly available evidence supports the submitted claim."""
    support = sum(support_scores)
    contradict = sum(contradict_scores)
    total = support + contradict
    if total == 0:
        return 0
    direction = support / total
    evidence_strength = min(1.0, total / 1.6)
    return round(100 * direction * (0.75 + 0.25 * evidence_strength))


def verdict_confidence_score(
    support_scores: list[float],
    contradict_scores: list[float],
    agreement: float,
    publisher_count: int,
) -> int:
    """0..100: confidence that the available evidence justifies the verdict."""
    all_scores = support_scores + contradict_scores
    if not all_scores:
        return 0
    dominant_strength = max(_mean(support_scores), _mean(contradict_scores))
    diversity = min(1.0, publisher_count / 2)
    volume = min(1.0, len(all_scores) / 3)
    score = 0.50 * dominant_strength + 0.25 * agreement + 0.15 * diversity + 0.10 * volume
    return round(min(1.0, score) * 100)
