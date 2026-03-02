from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.security.rate_limit import InMemoryRateLimiter


@dataclass(frozen=True)
class _RouteRateLimit:
    key: str
    limit: int


class RateLimitMiddleware(BaseHTTPMiddleware):
    _limiter = InMemoryRateLimiter()
    _uuid_like = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return await call_next(request)

        route_limit = self._resolve_limit(request)
        if route_limit.limit <= 0:
            return await call_next(request)

        client_key = self._client_identity(request=request, trust_forwarded=settings.rate_limit_trust_x_forwarded_for)
        key = f"{route_limit.key}:{request.method}:{self._normalized_path(request.url.path)}:{client_key}"
        result = self._limiter.check(
            key=key,
            limit=route_limit.limit,
            window_seconds=max(1, settings.rate_limit_window_seconds),
        )

        if not result.allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "scope": route_limit.key,
                    "retry_after_seconds": result.retry_after_seconds,
                },
                headers={
                    "Retry-After": str(result.retry_after_seconds),
                    "X-RateLimit-Limit": str(route_limit.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(result.reset_in_seconds),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(route_limit.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_in_seconds)
        return response

    @staticmethod
    def _client_identity(*, request: Request, trust_forwarded: bool) -> str:
        if trust_forwarded:
            forwarded_for = request.headers.get("X-Forwarded-For", "")
            forwarded_ip = forwarded_for.split(",")[0].strip() if forwarded_for else ""
            if forwarded_ip:
                return forwarded_ip
        client_host = request.client.host if request.client else ""
        if client_host:
            return client_host
        return "unknown"

    @staticmethod
    def _resolve_limit(request: Request) -> _RouteRateLimit:
        settings = get_settings()
        path = request.url.path
        if path.startswith("/api/v1/auth/"):
            return _RouteRateLimit(key="auth", limit=settings.rate_limit_auth_per_hour)
        if path.startswith("/api/v1/sales") or path.startswith("/api/v1/simple-catalog/sales"):
            return _RouteRateLimit(key="sales", limit=settings.rate_limit_sales_per_hour)
        return _RouteRateLimit(key="default", limit=settings.rate_limit_default_per_hour)

    @classmethod
    def _normalized_path(cls, path: str) -> str:
        parts = []
        for part in path.split("/"):
            if not part:
                parts.append(part)
                continue
            if part.isdigit():
                parts.append("{id}")
                continue
            if cls._uuid_like.match(part):
                parts.append("{uuid}")
                continue
            parts.append(part)
        return "/".join(parts)
