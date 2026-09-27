from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.nutrition import NutritionRequest


class NutritionProgramCreateRequest(BaseModel):
    assessment: NutritionRequest
    consent_to_save: bool
    duration_days: int = Field(default=14, ge=7, le=30)
    goal_key: str | None = Field(default=None, max_length=80)
    display_name: str | None = Field(default=None, max_length=180)


class ProgramGoalResponse(BaseModel):
    id: str | None = None
    goal_key: str
    title: str
    description: str
    baseline: float
    target: float
    actual: float = 0
    unit: str
    measurement_method: str
    duration_days: int
    priority: int
    status: str
    progress_percentage: float = 0
    remaining_gap: float = 0


class CumulativeGoalResponse(BaseModel):
    title: str
    target: float
    actual: float
    unit: str
    progress_percentage: float
    remaining_gap: float
    status: str
    cycles_included: int




class DailyMetricResultResponse(BaseModel):
    task_id: str
    metric_id: str
    target: object | None = None
    actual_result: object | None = None
    unit: str | None = None
    input_type: str
    status: str
    adherence: float | None = None
    completed_at: datetime | None = None
    action_completed: bool = False
    evidence_rule_id: str | None = None
    stage6_engine_version: str | None = None

class ProgramDayResponse(BaseModel):
    id: str
    day_number: int
    focus: str
    status: str
    unlock_at: datetime
    remaining_seconds: int = 0
    recommended_action: str = ""
    meal_guidance: str = ""
    action_details: dict = Field(default_factory=dict)
    meal_guidance_details: dict = Field(default_factory=dict)
    reference_notes: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    checklist_state: list[bool] = Field(default_factory=list)
    food_group_state: list[bool] = Field(default_factory=list)
    has_complaint: bool | None = None
    complaint_note: str | None = None
    completed: bool
    completed_at: datetime | None = None
    locked: bool = False
    missed: bool = False
    meal_label: str | None = None
    meal_notes: str | None = None
    task_results: dict[str, object] = Field(default_factory=dict)
    metric_results: list[DailyMetricResultResponse] = Field(default_factory=list)


class ProgramSummaryResponse(BaseModel):
    id: str
    stage: str
    title: str
    status: str
    duration_days: int
    cycle_number: int = 1
    parent_program_id: str | None = None
    created_at: datetime
    started_at: datetime
    ends_at: datetime
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    current_day: int
    days_completed: int
    completed_tasks: int
    total_tasks: int
    progress_percent: float
    time_elapsed_days: int = 1
    missed_days: int = 0
    inactive_days: int = 0
    last_activity_at: datetime | None = None
    goal: ProgramGoalResponse | None = None
    cumulative_goal: CumulativeGoalResponse | None = None
    adaptive_mode: bool = False
    latest_decision: dict | None = None
    post_block_choice: dict | None = None


class ProgramDetailResponse(ProgramSummaryResponse):
    profile: dict
    assessment_snapshot: dict = Field(default_factory=dict)
    recommendation: dict
    goals: list[ProgramGoalResponse] = Field(default_factory=list)
    days: list[ProgramDayResponse]
    extension_history: list[ProgramSummaryResponse] = Field(default_factory=list)
    rule_version: dict | None = None


class ProgramDayDetailResponse(BaseModel):
    program_id: str
    program_title: str
    program_status: str
    duration_days: int
    current_day: int
    progress_percent: float
    missed_days: int
    inactive_days: int
    last_activity_at: datetime | None = None
    goal: ProgramGoalResponse | None = None
    cumulative_goal: CumulativeGoalResponse | None = None
    day: ProgramDayResponse


class DailyLogRequest(BaseModel):
    day_number: int = Field(ge=1, le=120)
    checklist_state: list[bool] = Field(default_factory=list, max_length=20)
    food_group_state: list[bool] = Field(default_factory=list, max_length=10)
    has_complaint: bool | None = None
    complaint_note: str | None = Field(default=None, max_length=500)
    meal_label: str | None = Field(default=None, max_length=100)
    meal_notes: str | None = Field(default=None, max_length=500)
    task_results: dict[str, object] = Field(default_factory=dict)
    portion: Literal["finished", "partial", "little", "none"] | None = None
    acceptance: Literal["liked", "neutral", "refused"] | None = None
    texture: str | None = Field(default=None, max_length=80)
    new_food: bool | None = None
    reaction: Literal["none", "detected"] | None = None
    reaction_notes: str | None = Field(default=None, max_length=500)
    child_condition: Literal["healthy", "fussy", "sick", "fever", "diarrhea", "severe_teething"] | None = None
    health_condition: Literal["well", "unwell", "reduced_appetite", "nausea", "vomiting", "fever", "diarrhea", "constipation", "fatigue", "dizziness", "pain_discomfort", "difficulty_eating_drinking", "other_concern"] | None = None
    appetite_status: Literal["good", "reduced", "poor"] | None = None
    eating_difficulty: Literal["none", "some", "difficult"] | None = None
    routine_adherence: Literal["yes", "partial", "no"] | None = None
    caregiver_adherence: Literal["yes", "partial", "no"] | None = None
    hydration_status: Literal["good", "reduced", "poor"] | None = None
    eating_support: Literal["independent", "reminder", "assisted"] | None = None
    eating_barrier: Literal["none", "low_appetite", "early_satiety", "chewing", "swallowing", "preparation", "availability", "support", "other"] | None = None
    parent_difficulty: Literal["easy", "somewhat_difficult", "difficult"] | None = None
    available_ingredients: list[str] = Field(default_factory=list, max_length=12)
    budget_context: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class ProgramProgressResponse(BaseModel):
    program_id: str
    days_completed: int
    total_days: int
    completed_tasks: int
    total_tasks: int
    progress_percent: float
    current_day: int
    time_elapsed_days: int = 1
    missed_days: int = 0
    inactive_days: int = 0
    last_activity_at: datetime | None = None
    program_status: str
    completed_at: datetime | None = None
    goals: list[ProgramGoalResponse] = Field(default_factory=list)
    cumulative_goal: CumulativeGoalResponse | None = None
    goal_progress_percent: float = 0


class DailyLogResponse(ProgramProgressResponse):
    saved: bool
    saved_at: datetime
    day_number: int
    day_completed: bool
    day_completed_at: datetime | None = None
    checklist_state: list[bool]
    food_group_state: list[bool] = Field(default_factory=list)
    has_complaint: bool | None = None
    complaint_note: str | None = None
    task_results: dict[str, object] = Field(default_factory=dict)
    metric_results: list[DailyMetricResultResponse] = Field(default_factory=list)
    indicators: dict = Field(default_factory=dict)
    safety: dict = Field(default_factory=dict)
    adaptation: dict = Field(default_factory=dict)
    daily_summary: dict = Field(default_factory=dict)
    next_day_plan: dict | None = None


class ProgramEvaluationResponse(BaseModel):
    program_id: str
    completion_rate: float
    guidance_completion: float
    meal_log_count: int
    summary: str
    details: dict


class ExtensionCreateRequest(BaseModel):
    confirm: bool = False
    preference: Literal["same_goal", "smaller_goal", "different_goal"] = "same_goal"
    difficulty: str | None = Field(default=None, max_length=300)
    goal_key: str | None = Field(default=None, max_length=80)


class ExtensionRecommendationResponse(BaseModel):
    program_id: str
    goal_status: str
    previous_actual: float
    previous_target: float
    remaining_gap: float
    unit: str
    recommended_days: int
    cumulative_actual: float
    cumulative_target: float
    cumulative_progress: float
    why: str
    guidance_adjustments: dict


class BlockReviewResponse(BaseModel):
    program_id: str
    block_number: int | None = None
    duration_days: int | None = None
    block_completed: bool = False
    review_status: str | None = None
    program_progress: dict = Field(default_factory=dict)
    goal_progress: dict = Field(default_factory=dict)
    goal: dict | None = None
    baseline: object | None = None
    current: object | None = None
    metrics: list[dict] = Field(default_factory=list)
    adherence_summary: dict = Field(default_factory=dict)
    trend: dict = Field(default_factory=dict)
    trends: dict = Field(default_factory=dict)
    what_improved: str
    what_remains: str
    safety: dict = Field(default_factory=dict)
    safety_summary: dict = Field(default_factory=dict)
    goal_status: str | None = None
    decision: str
    next_focus: str | None = None
    options: list[str] = Field(default_factory=list)
    can_extend: bool = False
    can_reframe: bool = False
    rule_version: str | None = None
    generated_at: str | None = None
    evaluation_framework: str | None = None


class SafetyReviewRequest(BaseModel):
    confirm: bool = False
    action: Literal["restart_assessment"] = "restart_assessment"
    goal_key: str | None = Field(default=None, max_length=80)


class ProgramStateRequest(BaseModel):
    confirm: bool = False
    recovery_status: Literal["improved", "still_unwell"] | None = None


class CancelProgramRequest(BaseModel):
    confirm: bool = False


class FinalProgramResultResponse(BaseModel):
    program: ProgramSummaryResponse
    cycle: int
    duration_days: int
    goal: ProgramGoalResponse | None = None
    baseline: object | None = None
    target: object | None = None
    actual: object | None = None
    goal_status: str
    goal_achievement_percent: float
    program_completion_percent: float
    program_numbers: dict = Field(default_factory=dict)
    what_accomplished: list[str] = Field(default_factory=list)
    what_changed: str
    what_worked_well: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)
    adaptation_history: list[dict] = Field(default_factory=list)
    trends: dict = Field(default_factory=dict)
    safety_notes: list[str] = Field(default_factory=list)
    next_step: dict = Field(default_factory=dict)
    extension_history: list[ProgramSummaryResponse] = Field(default_factory=list)
    generated_at: datetime
