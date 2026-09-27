from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any

STAGE6_RULE_VERSION = "daily_result_adherence_v1"

CHOICE_LIKE_INPUTS = {"choice", "rating", "observation", "simple_experience"}
SUPPORTED_INPUT_TYPES = {"count", "boolean", *CHOICE_LIKE_INPUTS}


def _metric_id(task: dict[str, Any]) -> str:
    return str(task.get("metric_id") or task.get("metric") or "").strip().lower()


def _responsive_feeding_value(value: Any) -> bool | None:
    """Normalize only the responsive_feeding boolean contract.

    Stage 8 explicitly fixes the historical inversion for this metric without
    changing boolean semantics for any other metric.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"ya", "yes", "true"}:
            return True
        if normalized in {"tidak", "no", "false"}:
            return False
    return None


def responsive_feeding_adherence(value: Any) -> float | None:
    normalized = _responsive_feeding_value(value)
    if normalized is None:
        return None
    return 100.0 if normalized else 0.0


class DailyResultValidationError(ValueError):
    def __init__(self, task_id: str, message: str):
        super().__init__(message)
        self.task_id = task_id
        self.message = message


@dataclass(frozen=True)
class DailyTaskResult:
    task_id: str
    metric_id: str
    target: Any
    actual_result: Any
    unit: str | None
    input_type: str
    status: str
    adherence: float | None
    completed_at: str | None
    action_completed: bool
    evidence_rule_id: str | None
    stage6_engine_version: str = STAGE6_RULE_VERSION

    def as_dict(self) -> dict[str, Any]:
        # Preserve legacy aliases so existing Stage 7/8 code and historical UI
        # can continue reading the same JSON payload while Stage 6 exposes the
        # explicit result contract requested by the staged architecture.
        legacy_status = {
            "COMPLETED": "ACHIEVED",
            "PARTIAL": "PARTIAL",
            "NOT_STARTED": "NOT_ACHIEVED",
        }.get(self.status, self.status)
        return {
            "task_id": self.task_id,
            "metric_id": self.metric_id,
            "target": self.target,
            "target_value": self.target,
            "actual_result": self.actual_result,
            "actual": self.actual_result,
            "unit": self.unit,
            "target_unit": self.unit,
            "input_type": self.input_type,
            "status": self.status,
            "result_status": legacy_status,
            "adherence": self.adherence,
            "completed_at": self.completed_at,
            "action_completed": self.action_completed,
            "evidence_rule_id": self.evidence_rule_id,
            "rule_id": self.evidence_rule_id,
            "stage6_engine_version": self.stage6_engine_version,
        }


def _task_id(task: dict[str, Any], index: int = 0) -> str:
    return str(task.get("key") or task.get("id") or f"task_{index}")


def _input_type(task: dict[str, Any]) -> str:
    value = str(task.get("input_type") or "").strip().lower()
    # Existing Stage 5 used `rating` as a choice-like historical alias.
    return value


def _allowed_options(task: dict[str, Any]) -> set[str]:
    output: set[str] = set()
    for option in task.get("options") or []:
        if isinstance(option, dict) and option.get("value") is not None:
            output.add(str(option["value"]))
        elif isinstance(option, str):
            output.add(option)
    return output


def validate_actual_result(task: dict[str, Any], result: Any, *, index: int = 0) -> Any:
    task_id = _task_id(task, index)
    input_type = _input_type(task)
    if input_type not in SUPPORTED_INPUT_TYPES:
        raise DailyResultValidationError(task_id, f"Input type '{input_type or 'unknown'}' belum didukung untuk hasil harian.")

    if input_type == "count":
        if result is None or result == "":
            raise DailyResultValidationError(task_id, "Hasil aktual COUNT wajib diisi.")
        if isinstance(result, bool):
            raise DailyResultValidationError(task_id, "Hasil aktual COUNT harus berupa angka, bukan boolean.")
        try:
            value = float(result)
        except (TypeError, ValueError) as exc:
            raise DailyResultValidationError(task_id, "Hasil aktual COUNT harus berupa angka.") from exc
        if not math.isfinite(value):
            raise DailyResultValidationError(task_id, "Hasil aktual COUNT harus berupa angka finite.")
        if value < 0:
            raise DailyResultValidationError(task_id, "Hasil aktual COUNT tidak boleh negatif.")
        # Keep the exact user result. Integral counts are normalized to int only
        # for stable JSON; non-integral numeric values are preserved as float.
        return int(value) if value.is_integer() else value

    if input_type == "boolean":
        if _metric_id(task) == "responsive_feeding":
            normalized = _responsive_feeding_value(result)
            if normalized is None:
                raise DailyResultValidationError(task_id, "Responsive feeding harus diisi Ya/Tidak atau true/false.")
            return normalized
        if not isinstance(result, bool):
            raise DailyResultValidationError(task_id, "Hasil aktual BOOLEAN harus berupa true atau false.")
        return result

    if not isinstance(result, str) or not result.strip():
        raise DailyResultValidationError(task_id, f"Hasil aktual {input_type.upper()} wajib memilih salah satu opsi.")
    normalized = result.strip()
    allowed = _allowed_options(task)
    if allowed and normalized not in allowed:
        raise DailyResultValidationError(task_id, f"Nilai '{normalized}' tidak termasuk opsi yang diizinkan untuk task ini.")
    if not allowed:
        # Observation/experience remain structured. Without configured options,
        # arbitrary free text would break the Stage 6 contract.
        raise DailyResultValidationError(task_id, f"Task {input_type.upper()} belum memiliki options terstruktur.")
    return normalized


def adherence_for_actual(task: dict[str, Any], actual_result: Any) -> float | None:
    input_type = _input_type(task)
    if input_type == "count":
        target_raw = task.get("target_value")
        if isinstance(target_raw, bool) or target_raw is None:
            return None
        try:
            target = float(target_raw)
            actual = float(actual_result)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(target) or not math.isfinite(actual) or target < 0 or actual < 0:
            return None
        if target == 0:
            return 100.0 if actual == 0 else 0.0
        # Product semantics already cap goal achievement at 100%. The original
        # actual result is never capped or overwritten.
        return round(min(100.0, (actual / target) * 100.0), 2)

    if input_type == "boolean":
        if _metric_id(task) == "responsive_feeding":
            return responsive_feeding_adherence(actual_result)
        expected = task.get("target_value")
        if not isinstance(expected, bool):
            return None
        return 100.0 if actual_result is expected else 0.0

    if input_type in CHOICE_LIKE_INPUTS:
        mapping = task.get("adherence_map") or {}
        if str(actual_result) not in mapping:
            # Stage 6 must not invent scores for observation/experience options
            # when the task definition does not provide a mapping.
            return None
        try:
            score = float(mapping[str(actual_result)])
        except (TypeError, ValueError):
            return None
        if not math.isfinite(score):
            return None
        return round(max(0.0, min(100.0, score)), 2)

    return None


def status_for_actual(task: dict[str, Any], actual_result: Any, adherence: float | None) -> str:
    input_type = _input_type(task)
    if input_type == "count":
        try:
            actual = float(actual_result)
            target = float(task.get("target_value"))
        except (TypeError, ValueError):
            return "PARTIAL"
        if target > 0 and actual == 0:
            return "NOT_STARTED"
        if adherence is not None and adherence >= 100:
            return "COMPLETED"
        return "PARTIAL"

    # Boolean false and rejected choices are *recorded results*, not missing
    # values. They therefore remain PARTIAL when the target is not achieved.
    if adherence is not None:
        return "COMPLETED" if adherence >= 100 else "PARTIAL"

    # Structured observations/experiences without an adherence mapping have
    # been successfully captured, but no numeric score is fabricated.
    return "COMPLETED"


def build_daily_task_result(
    task: dict[str, Any],
    result: Any,
    *,
    action_completed: bool,
    saved_at: datetime,
    index: int = 0,
) -> DailyTaskResult:
    actual = validate_actual_result(task, result, index=index)
    adherence = adherence_for_actual(task, actual)
    status = status_for_actual(task, actual, adherence)
    evidence_rule_id = str(task.get("evidence_rule_id") or (task.get("evidence_rule") or {}).get("rule_id") or "") or None
    return DailyTaskResult(
        task_id=_task_id(task, index),
        metric_id=str(task.get("metric_id") or task.get("metric") or "unknown"),
        target=task.get("target_value"),
        actual_result=actual,
        unit=(str(task.get("unit")) if task.get("unit") is not None else None),
        input_type=_input_type(task),
        status=status,
        adherence=adherence,
        completed_at=saved_at.isoformat() if status == "COMPLETED" else None,
        action_completed=bool(action_completed),
        evidence_rule_id=evidence_rule_id,
    )



def evaluate_partial_daily_results(
    tasks: list[dict[str, Any]],
    incoming_results: dict[str, Any],
    checklist_state: list[bool],
    *,
    saved_at: datetime,
    previous_task_results: dict[str, Any] | None = None,
    previous_metric_results: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, float]]:
    """Persist only results that are already filled during a safety stop.

    This is intentionally limited to the pause/hold path. It preserves valid
    Stage 6 records without forcing unfinished tasks to become completed and
    without inventing values/adherence for missing inputs.
    """
    normalized_results: dict[str, Any] = dict(previous_task_results or {})
    metric_by_task = {
        str(row.get("task_id")): dict(row)
        for row in (previous_metric_results or [])
        if row.get("task_id")
    }
    adherence_by_task: dict[str, float] = {}

    for index, task in enumerate(tasks):
        key = _task_id(task, index)
        if key not in incoming_results:
            continue
        raw = incoming_results[key]
        input_type = _input_type(task)
        if raw is None or raw == "":
            continue
        if input_type in CHOICE_LIKE_INPUTS and isinstance(raw, str) and not raw.strip():
            continue
        record = build_daily_task_result(
            task,
            raw,
            action_completed=(checklist_state[index] if index < len(checklist_state) else False),
            saved_at=saved_at,
            index=index,
        )
        normalized_results[key] = record.actual_result
        metric_by_task[key] = record.as_dict()
        if record.adherence is not None:
            adherence_by_task[key] = record.adherence

    ordered_metrics: list[dict[str, Any]] = []
    task_order = [_task_id(task, index) for index, task in enumerate(tasks)]
    for key in task_order:
        if key in metric_by_task:
            ordered_metrics.append(metric_by_task[key])
    for key, row in metric_by_task.items():
        if key not in task_order:
            ordered_metrics.append(row)

    return normalized_results, ordered_metrics, adherence_by_task

def evaluate_daily_results(
    tasks: list[dict[str, Any]],
    incoming_results: dict[str, Any],
    checklist_state: list[bool],
    *,
    saved_at: datetime,
    previous_metric_results: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, float]]:
    normalized_results: dict[str, Any] = {}
    metric_results: list[dict[str, Any]] = []
    adherence_by_task: dict[str, float] = {}
    previous_by_task = {str(row.get("task_id")): row for row in (previous_metric_results or []) if row.get("task_id")}

    for index, task in enumerate(tasks):
        key = _task_id(task, index)
        if key not in incoming_results:
            raise DailyResultValidationError(key, "Hasil aktual untuk task ini belum diisi.")
        record = build_daily_task_result(
            task,
            incoming_results[key],
            action_completed=(checklist_state[index] if index < len(checklist_state) else False),
            saved_at=saved_at,
            index=index,
        )
        normalized_results[key] = record.actual_result
        payload = record.as_dict()
        previous = previous_by_task.get(key)
        if (
            previous
            and payload["status"] == "COMPLETED"
            and previous.get("status") == "COMPLETED"
            and previous.get("actual_result", previous.get("actual")) == payload["actual_result"]
            and previous.get("completed_at")
        ):
            # Re-saving the same logical result must not manufacture a new
            # completion event. Same-day edits that change the actual result
            # still receive a fresh server timestamp when they become complete.
            payload["completed_at"] = previous.get("completed_at")
        metric_results.append(payload)
        if record.adherence is not None:
            adherence_by_task[key] = record.adherence

    return normalized_results, metric_results, adherence_by_task
