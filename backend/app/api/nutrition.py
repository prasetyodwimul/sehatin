from fastapi import APIRouter, HTTPException

from app.nutrition_validation import validate_anthropometrics
from app.schemas.nutrition import (
    NutritionAnthropometricValidationRequest,
    NutritionRequest,
    NutritionResponse,
    NutritionValidationResponse,
)
from app.services.nutrition_service import generate_nutrition_recommendation
from app.services.persistence import persist_nutrition_result

router = APIRouter(prefix="/api/nutrition", tags=["nutrition"])


def _validation(payload) -> dict:
    return validate_anthropometrics(
        stage=payload.stage,
        age_months=payload.age_months,
        age_years=payload.age_years,
        sex=payload.sex,
        weight_kg=payload.weight_kg,
        height_cm=payload.height_cm,
    )


@router.post("/validate", response_model=NutritionValidationResponse)
def validate_measurements(payload: NutritionAnthropometricValidationRequest) -> NutritionValidationResponse:
    return NutritionValidationResponse.model_validate(_validation(payload))


@router.post("/recommendation", response_model=NutritionResponse)
def recommendation(payload: NutritionRequest) -> NutritionResponse:
    validation = _validation(payload)
    if not validation["can_process"]:
        raise HTTPException(status_code=422, detail=validation["message"])
    result = generate_nutrition_recommendation(payload, validation=validation)
    persist_nutrition_result(payload, result)
    return result
