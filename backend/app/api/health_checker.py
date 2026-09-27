from fastapi import APIRouter, HTTPException, Request

from app.schemas.health_checker import HealthCheckRequest, HealthCheckRunResponse
from app.services.health_checker_service import HealthCheckerError, health_checker_service
from app.services.persistence import persist_health_analysis

router = APIRouter(prefix="/api/health-checker", tags=["health-checker"])


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    return forwarded or (request.client.host if request.client else "anonymous")


def _run(payload: HealthCheckRequest, request: Request) -> HealthCheckRunResponse:
    try:
        health_checker_service.enforce_request_budget(_client_key(request))
        result = health_checker_service.analyze(payload)
    except HealthCheckerError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc

    # Anonymous persistence remains opt-in and stores a hash by default.
    for claim_result in result.claims:
        persist_health_analysis(claim_result.claim, claim_result)
    return result


@router.post("/analyze", response_model=HealthCheckRunResponse)
def analyze(payload: HealthCheckRequest, request: Request) -> HealthCheckRunResponse:
    return _run(payload, request)


@router.post("/analyze-url", response_model=HealthCheckRunResponse)
def analyze_url(payload: HealthCheckRequest, request: Request) -> HealthCheckRunResponse:
    data = payload.model_copy(update={"input_type": "url"})
    return _run(data, request)
