from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response


class _RequestTooLarge(Exception):
    pass


class RequestSizeLimitMiddleware:
    """ASGI request-size limiter that also covers streamed/chunked bodies."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_length = headers.get(b"content-length")
        if raw_length is not None:
            try:
                if int(raw_length) > self.max_bytes:
                    response = JSONResponse(
                        status_code=413,
                        content={"error": {"code": "REQUEST_TOO_LARGE", "message": "Ukuran permintaan terlalu besar."}},
                    )
                    await response(scope, receive, send)
                    return
            except ValueError:
                response = JSONResponse(
                    status_code=400,
                    content={"error": {"code": "INVALID_REQUEST", "message": "Header Content-Length tidak valid."}},
                )
                await response(scope, receive, send)
                return

        received_bytes = 0

        async def limited_receive():
            nonlocal received_bytes
            message = await receive()
            if message.get("type") == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_bytes:
                    raise _RequestTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _RequestTooLarge:
            response = JSONResponse(
                status_code=413,
                content={"error": {"code": "REQUEST_TOO_LARGE", "message": "Ukuran permintaan terlalu besar."}},
            )
            await response(scope, receive, send)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Small in-memory fixed-window limiter for a single-process MVP.

    It is intentionally basic. Multi-instance deployment should replace this with
    Redis/API-gateway rate limiting without changing endpoint code.
    """

    def __init__(self, app, requests_per_minute: int):
        super().__init__(app)
        self.limit = requests_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        # Keep health checks usable for orchestration and do not rate-limit preflight.
        if request.url.path == "/health" or request.method == "OPTIONS":
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        key = f"{client}:{request.url.path}"
        now = time.monotonic()
        cutoff = now - 60.0
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= self.limit:
                return JSONResponse(
                    status_code=429,
                    content={"error": {"code": "RATE_LIMITED", "message": "Terlalu banyak permintaan. Coba lagi sebentar."}},
                    headers={"Retry-After": "60"},
                )
            hits.append(now)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, production: bool = False):
        super().__init__(app)
        self.production = production

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'; object-src 'none'; base-uri 'none'"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        if self.production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id[:64]
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """Stricter rate limit for register/login endpoints."""

    def __init__(self, app, requests_per_minute: int):
        super().__init__(app)
        self.limit = requests_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        if request.method != "POST" or request.url.path not in {"/api/auth/login", "/api/auth/register"}:
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        key = f"auth:{client}:{request.url.path}"
        now = time.monotonic()
        cutoff = now - 60.0
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= self.limit:
                return JSONResponse(
                    status_code=429,
                    content={"error": {"code": "AUTH_RATE_LIMITED", "message": "Terlalu banyak percobaan. Tunggu sebentar lalu coba lagi."}},
                    headers={"Retry-After": "60"},
                )
            hits.append(now)
        return await call_next(request)
