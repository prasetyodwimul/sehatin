"""SEHATIN PART 1 no-login core schema.

Revision ID: 20260915_0001
Revises: None
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260915_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nutrition_requests",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("age_months", sa.Integer(), nullable=True),
        sa.Column("age_years", sa.Integer(), nullable=True),
        sa.Column("sex", sa.String(20), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("personalization_status", sa.String(40), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nutrition_requests")),
    )
    op.create_index(op.f("ix_nutrition_requests_stage"), "nutrition_requests", ["stage"], unique=False)

    op.create_table(
        "blood_facilities",
        sa.Column("id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("facility_type", sa.String(80), nullable=False),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("data_source", sa.Text(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blood_facilities")),
    )
    op.create_index(op.f("ix_blood_facilities_name"), "blood_facilities", ["name"], unique=False)
    op.create_index(op.f("ix_blood_facilities_city"), "blood_facilities", ["city"], unique=False)

    op.create_table(
        "evidence_sources",
        sa.Column("id", sa.String(120), nullable=False),
        sa.Column("name", sa.String(220), nullable=False),
        sa.Column("organization", sa.String(220), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(80), nullable=False),
        sa.Column("authority_score", sa.Float(), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=False),
        sa.Column("last_checked", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_sources")),
        sa.UniqueConstraint("url", name=op.f("uq_evidence_sources_url")),
    )
    op.create_index(op.f("ix_evidence_sources_organization"), "evidence_sources", ["organization"], unique=False)
    op.create_index(op.f("ix_evidence_sources_source_type"), "evidence_sources", ["source_type"], unique=False)

    op.create_table(
        "health_claims",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("claim_hash", sa.String(64), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=True),
        sa.Column("result", sa.String(40), nullable=False),
        sa.Column("trust_score", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_health_claims")),
    )
    op.create_index(op.f("ix_health_claims_claim_hash"), "health_claims", ["claim_hash"], unique=False)

    op.create_table(
        "blood_requests",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("blood_type", sa.String(2), nullable=True),
        sa.Column("rhesus", sa.String(1), nullable=True),
        sa.Column("location", sa.String(160), nullable=True),
        sa.Column("facility", sa.String(200), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blood_requests")),
    )

    op.create_table(
        "system_logs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("route", sa.String(240), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_system_logs")),
    )
    op.create_index(op.f("ix_system_logs_event_type"), "system_logs", ["event_type"], unique=False)
    op.create_index(op.f("ix_system_logs_correlation_id"), "system_logs", ["correlation_id"], unique=False)

    op.create_table(
        "nutrition_recommendations",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("category", sa.String(120), nullable=False),
        sa.Column("age_band", sa.String(80), nullable=False),
        sa.Column("personalization_status", sa.String(40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["nutrition_requests.id"], name=op.f("fk_nutrition_recommendations_request_id_nutrition_requests"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nutrition_recommendations")),
    )
    op.create_index(op.f("ix_nutrition_recommendations_request_id"), "nutrition_recommendations", ["request_id"], unique=False)

    op.create_table(
        "blood_inventory",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("facility_id", sa.String(100), nullable=False),
        sa.Column("blood_type", sa.String(2), nullable=False),
        sa.Column("rhesus", sa.String(1), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("blood_type IN ('A','B','AB','O')", name=op.f("ck_blood_inventory_blood_type_valid")),
        sa.CheckConstraint("rhesus IN ('+','-')", name=op.f("ck_blood_inventory_rhesus_valid")),
        sa.CheckConstraint("status IN ('AVAILABLE','LIMITED','EMPTY','UNKNOWN')", name=op.f("ck_blood_inventory_status_valid")),
        sa.CheckConstraint("quantity IS NULL OR quantity >= 0", name=op.f("ck_blood_inventory_quantity_nonnegative")),
        sa.ForeignKeyConstraint(["facility_id"], ["blood_facilities.id"], name=op.f("fk_blood_inventory_facility_id_blood_facilities"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blood_inventory")),
        sa.UniqueConstraint("facility_id", "blood_type", "rhesus", name="blood_inventory_facility_type_rh"),
    )
    op.create_index(op.f("ix_blood_inventory_facility_id"), "blood_inventory", ["facility_id"], unique=False)
    op.create_index(op.f("ix_blood_inventory_blood_type"), "blood_inventory", ["blood_type"], unique=False)
    op.create_index(op.f("ix_blood_inventory_rhesus"), "blood_inventory", ["rhesus"], unique=False)
    op.create_index(op.f("ix_blood_inventory_status"), "blood_inventory", ["status"], unique=False)

    op.create_table(
        "evidence_documents",
        sa.Column("id", sa.String(120), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(160), nullable=False),
        sa.Column("source_id", sa.String(120), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=False),
        sa.Column("evidence_quality", sa.Float(), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("stance_hint", sa.String(16), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["evidence_sources.id"], name=op.f("fk_evidence_documents_source_id_evidence_sources"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_documents")),
    )
    op.create_index(op.f("ix_evidence_documents_topic"), "evidence_documents", ["topic"], unique=False)
    op.create_index(op.f("ix_evidence_documents_source_id"), "evidence_documents", ["source_id"], unique=False)

    op.create_table(
        "claim_evidence",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("claim_id", sa.String(36), nullable=False),
        sa.Column("evidence_document_id", sa.String(120), nullable=False),
        sa.Column("stance", sa.String(16), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("authority_score", sa.Float(), nullable=False),
        sa.Column("evidence_quality_score", sa.Float(), nullable=False),
        sa.Column("recency_score", sa.Float(), nullable=False),
        sa.Column("weighted_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["health_claims.id"], name=op.f("fk_claim_evidence_claim_id_health_claims"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_document_id"], ["evidence_documents.id"], name=op.f("fk_claim_evidence_evidence_document_id_evidence_documents"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_claim_evidence")),
        sa.UniqueConstraint("claim_id", "evidence_document_id", name="claim_evidence_unique_document"),
    )
    op.create_index(op.f("ix_claim_evidence_claim_id"), "claim_evidence", ["claim_id"], unique=False)
    op.create_index(op.f("ix_claim_evidence_evidence_document_id"), "claim_evidence", ["evidence_document_id"], unique=False)


def downgrade() -> None:
    op.drop_table("claim_evidence")
    op.drop_table("evidence_documents")
    op.drop_table("blood_inventory")
    op.drop_table("nutrition_recommendations")
    op.drop_table("system_logs")
    op.drop_table("blood_requests")
    op.drop_table("health_claims")
    op.drop_table("evidence_sources")
    op.drop_table("blood_facilities")
    op.drop_table("nutrition_requests")
