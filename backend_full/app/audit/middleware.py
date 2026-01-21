import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from app.infrastructure.db.session import SessionLocal
from app.models.models import RequestLog

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Captures HTTP request metadata for auditing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)
        try:
            with SessionLocal() as session:
                log_entry = RequestLog(
                    request_id=request_id,
                    method=request.method,
                    path=str(request.url.path),
                    status_code=response.status_code,
                    context={"duration_ms": duration_ms},
                )
                session.add(log_entry)
                session.commit()
        except Exception:  # pragma: no cover - logging should never break flow
            logger.warning("request_log_failed", request_id=request_id)
        return response
