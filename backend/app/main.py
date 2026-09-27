import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, blood, health_checker, nutrition, nutrition_program
from app.config import get_settings
from app.database import check_database_connection
from app.security import AuthRateLimitMiddleware, RateLimitMiddleware, RequestIdMiddleware, RequestSizeLimitMiddleware, SecurityHeadersMiddleware

settings = get_settings()
logger = logging.getLogger("sehatin")

app = FastAPI(
    title=settings.app_name,
    description="Trusted Health Ecosystem — public-first health tools with optional authenticated Guided Nutrition persistence.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-Request-ID"],
)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_request_bytes)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)
app.add_middleware(AuthRateLimitMiddleware, requests_per_minute=settings.auth_rate_limit_per_minute)
app.add_middleware(SecurityHeadersMiddleware, production=settings.environment.lower() == "production")
app.add_middleware(RequestIdMiddleware)

app.include_router(auth.router)
app.include_router(nutrition.router)
app.include_router(nutrition_program.router)
app.include_router(blood.router)
app.include_router(health_checker.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else None
    message = first_error.get("msg", "Input tidak valid") if first_error else "Input tidak valid"
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "INVALID_INPUT", "message": message}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        code = str(exc.detail.get("code") or "REQUEST_ERROR")
        message = str(exc.detail.get("message") or "Permintaan tidak dapat diproses")
    else:
        if exc.status_code == 404:
            code = "NOT_FOUND"
        elif exc.status_code == 422:
            code = "INVALID_INPUT"
        else:
            code = "REQUEST_ERROR"
        message = exc.detail if isinstance(exc.detail, str) else "Permintaan tidak dapat diproses"
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": code, "message": message}})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never log request bodies/claims here. Route + exception class are enough for ops.
    logger.exception("Unhandled request error: %s %s [%s]", request.method, request.url.path, exc.__class__.__name__)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Terjadi kesalahan pada server. Silakan coba lagi.",
            }
        },
    )


@app.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "database": "connected" if check_database_connection() else "unavailable",
        "version": app.version,
    }


@app.get("/")
def root() -> dict:
    return {"message": f"{settings.app_name} API — lihat /health dan /docs"}
