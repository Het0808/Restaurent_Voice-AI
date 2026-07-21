"""Correlation ID, rate limiting, and HTTP metrics middleware."""

import re
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from restaurant_voice_ai.auth.api_keys import fingerprint
from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.observability.metrics import metrics
from restaurant_voice_ai.observability.request_context import request_id_context
from restaurant_voice_ai.rate_limit.base import RateLimiter

SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


class OperationsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, settings: Settings, limiter: RateLimiter) -> None:
        super().__init__(app)
        self.settings = settings
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(self.settings.request_id_header, "")
        request_id = incoming if SAFE_REQUEST_ID.fullmatch(incoming) else str(uuid.uuid4())
        token = request_id_context.set(request_id)
        request.state.request_id = request_id
        started = time.perf_counter()
        metrics.active_requests.inc()
        try:
            limited = await self._rate_limit(request, request_id)
            if limited is not None:
                return limited
            response = await call_next(request)
            response.headers[self.settings.request_id_header] = request_id
            return response
        finally:
            duration = time.perf_counter() - started
            route = self._bounded_route(request.url.path)
            status = getattr(
                locals().get("response"),
                "status_code",
                429 if "limited" in locals() and limited else 500,
            )
            metrics.http_requests.labels(request.method, route, f"{int(status) // 100}xx").inc()
            metrics.http_latency.labels(request.method, route).observe(duration)
            metrics.active_requests.dec()
            request_id_context.reset(token)

    async def _rate_limit(self, request: Request, request_id: str) -> Response | None:
        if not self.settings.rate_limit_enabled:
            return None
        path = request.url.path
        if path.endswith("/conversation/message"):
            limit = self.settings.rate_limit_text_requests_per_minute
            scope = "text"
        elif path in {
            self.settings.health_path,
            self.settings.liveness_path,
            self.settings.readiness_path,
        }:
            limit = self.settings.rate_limit_health_requests_per_minute
            scope = "health"
        elif path == self.settings.metrics_path:
            limit = self.settings.rate_limit_health_requests_per_minute
            scope = "metrics"
        else:
            return None
        supplied = request.headers.get(self.settings.api_key_header_name)
        host = request.client.host if request.client else "unknown"
        identity = fingerprint(supplied) if supplied else host
        result = await self.limiter.check(f"{scope}:{identity}", limit, 60)
        if result.allowed:
            return None
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "request_id": request_id,
                    "recoverable": True,
                }
            },
            headers={
                "Retry-After": str(result.reset_after_seconds),
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": str(result.remaining),
                "X-RateLimit-Reset": str(result.reset_after_seconds),
                self.settings.request_id_header: request_id,
            },
        )

    @staticmethod
    def _bounded_route(path: str) -> str:
        if path.startswith("/api/v1/reservations/"):
            return "/api/v1/reservations/{id}"
        return path if len(path) <= 80 else "other"
