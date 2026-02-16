import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from jose import jwt, JWTError
from app.infrastructure.db.session import SessionLocal
from app.models.models import RequestLog, User
from app.config import get_settings
from app.audit.context import set_audit_user_id, reset_audit_user_id

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Captures HTTP request metadata for auditing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id)
        user_id = self._resolve_user_id(request)
        audit_user_token = set_audit_user_id(user_id)
        start = time.time()
        try:
            response = await call_next(request)
            duration_ms = int((time.time() - start) * 1000)
            try:
                with SessionLocal() as session:
                    log_entry = RequestLog(
                        request_id=request_id,
                        method=request.method,
                        path=str(request.url.path),
                        status_code=response.status_code,
                        user_id=user_id,
                        context={"duration_ms": duration_ms},
                    )
                    session.add(log_entry)
                    session.commit()
            except Exception:  # pragma: no cover - logging should never break flow
                logger.warning("request_log_failed", request_id=request_id)
            return response
        finally:
            reset_audit_user_id(audit_user_token)

    @staticmethod
    def _resolve_user_id(request: Request) -> int | None:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:].strip()
        if not token:
            return None

        settings = get_settings()
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        except JWTError:
            return None

        username = payload.get("sub")
        if not username:
            return None

        try:
            with SessionLocal() as session:
                user = session.query(User).filter(User.username == username, User.is_active == True).first()  # noqa: E712
                return user.id if user else None
        except Exception:
            return None
