from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Literal

ClaimType = Literal[
    "HEALTH_TREATMENT",
    "NUTRITION",
    "PREVENTION",
    "SYMPTOM",
    "MEDICATION",
    "VACCINE",
    "DIET",
    "CAUSE",
    "RISK",
    "GENERAL_HEALTH",
]


@dataclass(frozen=True)
class ExtractedClaim:
    claim_id: str
    claim_text: str
    normalized_claim: str
    claim_type: ClaimType
    importance: float
    topic: str


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_WORDS = re.compile(r"[A-Za-zÀ-ÿ0-9]+")

_STOPWORDS = {
    "yang", "dan", "atau", "dengan", "untuk", "dari", "pada", "dalam", "adalah", "bisa", "dapat",
    "akan", "ini", "itu", "sebagai", "karena", "agar", "lebih", "juga", "the", "and", "with", "for",
    "from", "that", "this", "can", "could", "may", "health", "kesehatan",
}

_TYPE_RULES: list[tuple[ClaimType, tuple[str, ...]]] = [
    ("VACCINE", ("vaksin", "vaccine", "imunisasi", "immunization")),
    ("MEDICATION", ("obat", "medicine", "medication", "antibiotik", "antibiotic", "dosis", "dose")),
    ("NUTRITION", ("nutrisi", "nutrition", "protein", "karbohidrat", "vitamin", "mineral", "sayur", "buah")),
    ("DIET", ("diet", "pola makan", "makan", "food", "meal")),
    ("PREVENTION", ("mencegah", "prevent", "prevention", "mengurangi risiko", "reduce risk")),
    ("SYMPTOM", ("gejala", "symptom", "demam", "batuk", "nyeri", "pain")),
    ("CAUSE", ("menyebabkan", "cause", "causes", "akibat", "karena")),
    ("RISK", ("risiko", "risk", "berisiko", "associated with")),
    ("HEALTH_TREATMENT", ("menyembuhkan", "mengobati", "treatment", "treat", "cure", "therapy", "terapi")),
]

_IMPORTANT_VERBS = (
    "menyembuhkan", "mengobati", "mencegah", "menyebabkan", "menurunkan", "meningkatkan", "berisiko",
    "cure", "treat", "prevent", "cause", "reduce", "increase", "risk", "effective", "safe",
)


def normalize_claim_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def classify_claim(text: str) -> ClaimType:
    lowered = text.lower()
    for claim_type, terms in _TYPE_RULES:
        if any(term in lowered for term in terms):
            return claim_type
    return "GENERAL_HEALTH"


def _topic(text: str) -> str:
    words = [word.lower() for word in _WORDS.findall(text)]
    candidates = [word for word in words if len(word) >= 4 and word not in _STOPWORDS]
    if not candidates:
        return "general health"
    counts: dict[str, int] = {}
    for word in candidates:
        counts[word] = counts.get(word, 0) + 1
    ranked = sorted(counts, key=lambda word: (-counts[word], candidates.index(word)))
    return " ".join(ranked[:3])


def _importance(text: str) -> float:
    lowered = text.lower()
    score = 0.45
    if any(verb in lowered for verb in _IMPORTANT_VERBS):
        score += 0.30
    if any(term in lowered for term in ("obat", "vaksin", "antibiotik", "dosis", "medicine", "vaccine")):
        score += 0.15
    if len(text) >= 45:
        score += 0.05
    return round(min(1.0, score), 2)


def _claim_id(text: str, index: int) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"claim-{index + 1}-{digest}"


def extract_claims(text: str, *, max_claims: int = 5) -> list[ExtractedClaim]:
    """Extract independently checkable health claims without generating new facts.

    The extractor is deliberately deterministic. It splits article/text input into
    sentence-like units, preserves the user's wording, and only keeps statements
    long enough to be meaningfully checked. It does not rewrite a claim into a
    stronger medical assertion.
    """
    normalized_input = normalize_claim_text(text)
    if not normalized_input:
        return []

    raw_parts = [normalize_claim_text(part) for part in _SENTENCE_SPLIT.split(text)]
    parts = [part for part in raw_parts if len(part) >= 12]
    if not parts:
        parts = [normalized_input]

    # Prefer sentences that contain an assertion cue, then retain document order.
    scored: list[tuple[int, int, str]] = []
    for idx, part in enumerate(parts):
        lowered = part.lower()
        cue_count = sum(1 for cue in _IMPORTANT_VERBS if cue in lowered)
        cue_count += sum(1 for cue in ("adalah", "merupakan", "is ", "are ", "associated", "linked") if cue in lowered)
        scored.append((cue_count, idx, part))

    if len(scored) > max_claims:
        chosen = sorted(scored, key=lambda row: (-row[0], row[1]))[:max_claims]
        chosen = sorted(chosen, key=lambda row: row[1])
    else:
        chosen = scored

    results: list[ExtractedClaim] = []
    seen: set[str] = set()
    for _, _, part in chosen:
        normalized = normalize_claim_text(part)
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        index = len(results)
        results.append(
            ExtractedClaim(
                claim_id=_claim_id(normalized, index),
                claim_text=part,
                normalized_claim=normalized,
                claim_type=classify_claim(normalized),
                importance=_importance(normalized),
                topic=_topic(normalized),
            )
        )
    return results
