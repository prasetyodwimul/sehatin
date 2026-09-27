"""Deterministic pediatric red-flag text detection for Guided Nutrition.

This module does not diagnose disease. It only maps explicit caregiver-reported
phrases to a conservative emergency safety signal used to stop automated
nutrition adaptation. The covered MPASI/Toddler age range (6-59 months) fits
within WHO IMCI's under-5 danger-sign framework.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


WHO_IMCI_SOURCE = {
    "source_name": "WHO Integrated Management of Childhood Illness (IMCI) — General danger signs",
    "source_type": "public_health_guideline",
    "source_url": "https://iris.who.int/bitstream/handle/10665/104772/9789241506823_Module-1_eng.pdf",
    "evidence_level": "WHO guideline",
}

CDC_ALLERGY_SOURCE = {
    "source_name": "CDC — Food Allergies in Schools / emergency allergy guidance",
    "source_type": "public_health_guidance",
    "source_url": "https://www.cdc.gov/school-health-conditions/food-allergies/index.html",
    "evidence_level": "CDC public health guidance",
}


@dataclass(frozen=True)
class RedFlagRule:
    code: str
    label: str
    phrases: tuple[str, ...]
    source: dict[str, str]


# Keep this list intentionally narrow: only explicit danger phrases should cause
# SAFETY_HOLD. Mild symptoms/food refusal/caregiver difficulty stay in the
# adaptive pathway and must not be promoted to an emergency by keyword alone.
RED_FLAG_RULES: tuple[RedFlagRule, ...] = (
    RedFlagRule(
        code="BREATHING_DIFFICULTY",
        label="Kesulitan bernapas / tanda gangguan jalan napas",
        phrases=(
            "sulit bernapas",
            "susah bernapas",
            "kesulitan bernapas",
            "sesak napas",
            "sesak",
            "napas megap megap",
            "nafas megap megap",
            "bibir biru",
            "wajah biru",
        ),
        source=CDC_ALLERGY_SOURCE,
    ),
    RedFlagRule(
        code="AIRWAY_SWELLING",
        label="Pembengkakan yang dapat mengganggu jalan napas",
        phrases=(
            "lidah bengkak",
            "tenggorokan bengkak",
            "sulit menelan",
            "susah menelan",
            "tidak bisa menelan",
        ),
        source=CDC_ALLERGY_SOURCE,
    ),
    RedFlagRule(
        code="CONVULSION",
        label="Kejang",
        phrases=("kejang", "sedang kejang", "kejang kejang"),
        source=WHO_IMCI_SOURCE,
    ),
    RedFlagRule(
        code="ALTERED_CONSCIOUSNESS",
        label="Tidak sadar / sangat sulit dibangunkan",
        phrases=(
            "tidak sadar",
            "pingsan",
            "sulit dibangunkan",
            "susah dibangunkan",
            "tidak merespons",
            "tidak respon",
            "tidak responsif",
        ),
        source=WHO_IMCI_SOURCE,
    ),
    RedFlagRule(
        code="UNABLE_TO_DRINK",
        label="Tidak mampu minum atau menyusu",
        phrases=(
            "tidak bisa minum",
            "tidak dapat minum",
            "tidak mampu minum",
            "tidak bisa menyusu",
            "tidak dapat menyusu",
            "tidak mampu menyusu",
            "tidak bisa menelan cairan",
        ),
        source=WHO_IMCI_SOURCE,
    ),
    RedFlagRule(
        code="VOMITS_EVERYTHING",
        label="Muntah semua asupan",
        phrases=(
            "muntah semua",
            "semua dimuntahkan",
            "muntah setiap minum",
            "muntah setiap makan",
            "setiap minum muntah",
            "setiap makan muntah",
            "tidak bisa menahan cairan",
            "tidak dapat menahan cairan",
        ),
        source=WHO_IMCI_SOURCE,
    ),
)


_NEGATORS = ("tidak", "tidak ada", "tidak pernah", "tidak mengalami", "tanpa", "bukan", "nggak", "gak", "ga")


def normalize_safety_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _is_explicitly_negated(text: str, phrase: str, match_start: int) -> bool:
    """Suppress simple false positives such as 'tidak sesak' or 'tanpa kejang'.

    Phrases whose danger meaning already begins with 'tidak' (for example
    'tidak sadar' or 'tidak bisa minum') are not treated as negated merely
    because their first word is 'tidak'.
    """
    if phrase.startswith("tidak "):
        return False
    prefix = text[max(0, match_start - 40):match_start].strip()
    return any(prefix.endswith(negator) for negator in _NEGATORS)


def _phrase_match(text: str, phrase: str) -> bool:
    start = 0
    while True:
        index = text.find(phrase, start)
        if index < 0:
            return False
        if not _is_explicitly_negated(text, phrase, index):
            return True
        start = index + len(phrase)


def detect_red_flags(*values: str | None) -> list[dict[str, object]]:
    text = normalize_safety_text(" ".join(value or "" for value in values))
    if not text:
        return []

    matches: list[dict[str, object]] = []
    for rule in RED_FLAG_RULES:
        matched_phrase = next((phrase for phrase in rule.phrases if _phrase_match(text, phrase)), None)
        if not matched_phrase:
            continue
        matches.append(
            {
                "code": rule.code,
                "label": rule.label,
                "matched_phrase": matched_phrase,
                "source": dict(rule.source),
            }
        )
    return matches


def emergency_message(matches: Iterable[dict[str, object]]) -> str:
    labels = [str(item.get("label") or "tanda bahaya") for item in matches]
    detail = ", ".join(labels[:3])
    suffix = f" ({detail})" if detail else ""
    return (
        "Tanda bahaya terdeteksi dari informasi yang Anda masukkan"
        f"{suffix}. Hentikan program untuk saat ini dan segera bawa anak ke IGD/rumah sakit "
        "atau hubungi layanan darurat setempat. SEHATIN tidak dapat memastikan diagnosis."
    )
