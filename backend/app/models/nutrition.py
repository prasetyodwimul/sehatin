from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_str


class NutritionRequestModel(TimestampMixin, Base):
    __tablename__ = "nutrition_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    stage: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str] = mapped_column(String(20), nullable=False, default="unspecified")
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    personalization_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Privacy-minimized structured snapshot. Free-text notes/medical_context are not persisted.
    request_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class NutritionRecommendationModel(TimestampMixin, Base):
    __tablename__ = "nutrition_recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("nutrition_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    profile_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("nutrition_profiles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    age_band: Mapped[str] = mapped_column(String(80), nullable=False)
    personalization_status: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    result_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
