from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_str, utcnow


class NutritionProfileModel(TimestampMixin, Base):
    __tablename__ = "nutrition_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str] = mapped_column(String(20), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    profile_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class NutritionProgramModel(TimestampMixin, Base):
    __tablename__ = "nutrition_programs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("nutrition_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(36), ForeignKey("nutrition_recommendations.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_program_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("nutrition_programs.id", ondelete="SET NULL"), nullable=True, index=True)
    stage: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="ACTIVE", index=True)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    assessment_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    recommendation_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    program_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NutritionProgramGoalModel(TimestampMixin, Base):
    __tablename__ = "nutrition_program_goals"
    __table_args__ = (UniqueConstraint("program_id", "goal_key", name="program_goal_unique_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    program_id: Mapped[str] = mapped_column(String(36), ForeignKey("nutrition_programs.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_key: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    baseline: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    target: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(80), nullable=False)
    measurement_method: Mapped[str] = mapped_column(String(120), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="NOT_STARTED")
    actual: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    progress_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0)


class NutritionProgramDayModel(TimestampMixin, Base):
    __tablename__ = "nutrition_program_days"
    __table_args__ = (UniqueConstraint("program_id", "day_number", name="program_day_unique_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    program_id: Mapped[str] = mapped_column(String(36), ForeignKey("nutrition_programs.id", ondelete="CASCADE"), nullable=False, index=True)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    focus: Mapped[str] = mapped_column(String(220), nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    meal_guidance: Mapped[str] = mapped_column(Text, nullable=False)
    action_details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    meal_guidance_details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    checklist: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    checklist_state: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    food_group_state: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    has_complaint: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    complaint_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_notes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NutritionMealLogModel(TimestampMixin, Base):
    __tablename__ = "nutrition_meal_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    program_id: Mapped[str] = mapped_column(String(36), ForeignKey("nutrition_programs.id", ondelete="CASCADE"), nullable=False, index=True)
    program_day_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("nutrition_program_days.id", ondelete="SET NULL"), nullable=True, index=True)
    meal_label: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class NutritionEvaluationModel(TimestampMixin, Base):
    __tablename__ = "nutrition_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    program_id: Mapped[str] = mapped_column(String(36), ForeignKey("nutrition_programs.id", ondelete="CASCADE"), nullable=False, index=True)
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False)
    guidance_completion: Mapped[float] = mapped_column(Float, nullable=False)
    meal_log_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class NutritionProgramExtensionModel(TimestampMixin, Base):
    __tablename__ = "nutrition_program_extensions"
    __table_args__ = (UniqueConstraint("extension_program_id", name="uq_nutrition_program_extensions_extension_program_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    original_program_id: Mapped[str] = mapped_column(String(36), ForeignKey("nutrition_programs.id", ondelete="CASCADE"), nullable=False, index=True)
    extension_program_id: Mapped[str] = mapped_column(String(36), ForeignKey("nutrition_programs.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_actual: Mapped[float] = mapped_column(Float, nullable=False)
    previous_target: Mapped[float] = mapped_column(Float, nullable=False)
    remaining_gap: Mapped[float] = mapped_column(Float, nullable=False)
    recommended_days: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    guidance_adjustments: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
