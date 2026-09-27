from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ValidationLevel = Literal["VALID", "WARNING", "INVALID"]


@dataclass(frozen=True)
class ValidationIssue:
    level: ValidationLevel
    code: str
    message: str


LEVEL_RANK = {"VALID": 0, "WARNING": 1, "INVALID": 2}


def worst_level(issues: list[ValidationIssue]) -> ValidationLevel:
    if not issues:
        return "VALID"
    return max(issues, key=lambda issue: LEVEL_RANK[issue.level]).level
