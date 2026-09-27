from __future__ import annotations

import hashlib
import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import session_scope
from app.models import (
    BloodRequestModel,
    ClaimEvidenceModel,
    HealthClaimModel,
    NutritionRecommendationModel,
    NutritionRequestModel,
    SystemLogModel,
)
from app.schemas.health_checker import HealthCheckResponse
from app.schemas.nutrition import NutritionRequest, NutritionResponse

logger = logging.getLogger("sehatin.persistence")


def _enabled() -> bool:
    return get_settings().persistence_enabled


def persist_nutrition_result(request: NutritionRequest, result: NutritionResponse) -> str | None:
    """Persist a public Nutrition assessment only when anonymous personal-data
    persistence has been explicitly enabled.

    Guided Program saves do not use this helper; they are authenticated and
    persisted through the Nutrition Program service. Keeping this gate separate
    prevents PERSISTENCE_ENABLED from silently turning a guest assessment into a
    stored personal record.
    """
    settings = get_settings()
    if not _enabled() or not settings.persist_anonymous_nutrition_personal_data:
        return None
    try:
        with session_scope() as db:
            safe_request = {
                "stage": request.stage,
                "age_months": request.age_months,
                "age_years": request.age_years,
                "sex": request.sex,
                "weight_kg": request.weight_kg,
                "height_cm": request.height_cm,
                "feeding_mode": request.feeding_mode,
                "texture_level": request.texture_level,
                "appetite": request.appetite,
                "meal_frequency": request.meal_frequency,
                "activity_level": request.activity_level,
                "chewing_difficulty": request.chewing_difficulty,
                "swallowing_difficulty": request.swallowing_difficulty,
                "allergy_count": len(request.allergies),
                "restriction_count": len(request.dietary_restrictions),
                "medical_context_present": bool(request.medical_context),
                "has_condition": request.has_condition,
                "conditions": list(request.conditions),
                "other_condition": request.other_condition,
            }
            req_row = NutritionRequestModel(
                stage=request.stage,
                age_months=request.age_months,
                age_years=request.age_years,
                sex=request.sex,
                weight_kg=request.weight_kg,
                height_cm=request.height_cm,
                personalization_status=result.personalization_status,
                request_payload=safe_request,
            )
            db.add(req_row)
            db.flush()
            db.add(
                NutritionRecommendationModel(
                    request_id=req_row.id,
                    category=result.category,
                    age_band=result.age_band,
                    personalization_status=result.personalization_status,
                    summary=result.summary,
                    result_payload=result.model_dump(mode="json"),
                )
            )
            return req_row.id
    except Exception as exc:
        logger.warning("Nutrition persistence skipped: %s", exc.__class__.__name__)
        return None


def persist_blood_request(*, blood_type: str | None, rhesus: str | None, location: str | None, facility: str | None) -> None:
    if not _enabled():
        return
    try:
        with session_scope() as db:
            db.add(
                BloodRequestModel(
                    blood_type=blood_type,
                    rhesus=rhesus,
                    location=location,
                    facility=facility,
                    request_payload={"filtered": any([blood_type, rhesus, location, facility])},
                )
            )
    except Exception as exc:
        logger.warning("Blood request persistence skipped: %s", exc.__class__.__name__)


def persist_health_analysis(claim: str, result: HealthCheckResponse) -> str | None:
    if not _enabled():
        return None
    settings = get_settings()
    try:
        with session_scope() as db:
            claim_hash = hashlib.sha256(claim.encode("utf-8")).hexdigest()
            row = HealthClaimModel(
                claim_hash=claim_hash,
                claim_text=claim if settings.persist_health_claim_text else None,
                result=result.verdict,
                trust_score=result.trust_score,
                confidence=result.evidence_confidence,
                summary=result.explanation,
                reason=result.why_this_result,
            )
            db.add(row)
            db.flush()
            for evidence in result.supporting_evidence + result.contradicting_evidence:
                # Live PubMed records are request-scoped and are not rows in
                # evidence_documents. Persist only curated/database evidence to
                # avoid inventing a local FK for external records.
                if evidence.provider not in {"curated", "database"}:
                    continue
                db.add(
                    ClaimEvidenceModel(
                        claim_id=row.id,
                        evidence_document_id=evidence.id,
                        stance=evidence.stance,
                        relevance_score=evidence.relevance_score,
                        authority_score=evidence.authority_score,
                        evidence_quality_score=evidence.evidence_quality_score,
                        recency_score=evidence.recency_score,
                        weighted_score=evidence.weighted_score,
                    )
                )
            return row.id
    except Exception as exc:
        # A missing seed/document FK must never break public analysis.
        logger.warning("Health analysis persistence skipped: %s", exc.__class__.__name__)
        return None


def record_system_log(*, event_type: str, level: str = "INFO", route: str | None = None, status_code: int | None = None, correlation_id: str | None = None, details: dict | None = None) -> None:
    if not _enabled():
        return
    try:
        with session_scope() as db:
            db.add(
                SystemLogModel(
                    event_type=event_type,
                    level=level,
                    route=route,
                    status_code=status_code,
                    correlation_id=correlation_id,
                    details=details or {},
                )
            )
    except Exception as exc:
        logger.debug("System log persistence skipped: %s", exc.__class__.__name__)
