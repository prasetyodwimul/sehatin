from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_str


class BloodFacilityModel(TimestampMixin, Base):
    __tablename__ = "blood_facilities"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    facility_type: Mapped[str] = mapped_column(String(80), nullable=False, default="blood_facility")
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_source: Mapped[str] = mapped_column(Text, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BloodInventoryModel(TimestampMixin, Base):
    __tablename__ = "blood_inventory"
    __table_args__ = (
        UniqueConstraint("facility_id", "blood_type", "rhesus", name="blood_inventory_facility_type_rh"),
        CheckConstraint("blood_type IN ('A','B','AB','O')", name="blood_type_valid"),
        CheckConstraint("rhesus IN ('+','-')", name="rhesus_valid"),
        CheckConstraint("status IN ('AVAILABLE','LIMITED','EMPTY','UNKNOWN')", name="status_valid"),
        CheckConstraint("quantity IS NULL OR quantity >= 0", name="quantity_nonnegative"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    facility_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("blood_facilities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    blood_type: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    rhesus: Mapped[str] = mapped_column(String(1), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BloodRequestModel(TimestampMixin, Base):
    __tablename__ = "blood_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    blood_type: Mapped[str | None] = mapped_column(String(2), nullable=True)
    rhesus: Mapped[str | None] = mapped_column(String(1), nullable=True)
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    facility: Mapped[str | None] = mapped_column(String(200), nullable=True)
    request_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
