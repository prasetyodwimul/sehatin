"""Versioned WHO 2006 child-growth reference loader.

Reference values live in a JSON data file so the evidence layer can be reviewed
and updated independently from validation logic. The dataset is used only for
screening measurement consistency; it is not a diagnostic growth assessment.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).with_name("data") / "who_child_growth_2006_v1.json"


@dataclass(frozen=True)
class ReferenceBand:
    low_3sd: float
    low_2sd: float
    median: float
    high_2sd: float
    high_3sd: float


@lru_cache(maxsize=1)
def _dataset() -> dict:
    with DATA_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


WHO_CHILD_GROWTH_META = _dataset()["metadata"]


def weight_for_age_band(sex: str, age_months: int) -> ReferenceBand | None:
    row = _dataset().get("weight_for_age", {}).get(sex, {}).get(str(age_months))
    return ReferenceBand(**row) if row else None


def _interpolate_bounds(points: list[list[float]], height_cm: float) -> tuple[float, float] | None:
    if not points or height_cm < points[0][0] or height_cm > points[-1][0]:
        return None
    for idx, point in enumerate(points):
        if height_cm == point[0]:
            return float(point[1]), float(point[2])
        if idx == 0:
            continue
        left = points[idx - 1]
        right = point
        if left[0] <= height_cm <= right[0]:
            ratio = (height_cm - left[0]) / (right[0] - left[0])
            low = left[1] + ratio * (right[1] - left[1])
            high = left[2] + ratio * (right[2] - left[2])
            return round(low, 2), round(high, 2)
    return None


def weight_for_length_height_bounds(sex: str, age_months: int, height_cm: float) -> tuple[float, float] | None:
    key = "weight_for_length_bounds" if age_months < 24 else "weight_for_height_bounds"
    table = _dataset().get(key, {}).get(sex, [])
    return _interpolate_bounds(table, height_cm)
