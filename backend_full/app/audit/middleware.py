import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from jose import JWTError
from app.infrastructure.db.session import SessionLocal
from app.models.models import RequestLog, Terminal, User
from app.audit.context import set_audit_user_id, reset_audit_user_id
from app.security.auth import decode_access_token

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Captures HTTP request metadata for auditing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id)
        terminal_public_id = (request.headers.get("X-Terminal-ID") or "").strip() or None

        with SessionLocal() as lookup_session:
            terminal_id = self._resolve_terminal_id(lookup_session, terminal_public_id)
            user_id = self._resolve_user_id(lookup_session, request)

        audit_user_token = set_audit_user_id(user_id)
        start = time.time()
        try:
            response = await call_next(request)
            duration_ms = int((time.time() - start) * 1000)
            effective_user_id = getattr(request.state, "request_user_id_override", None)
            if effective_user_id is None:
                effective_user_id = user_id
            try:
                with SessionLocal() as session:
                    log_entry = RequestLog(
                        request_id=request_id,
                        method=request.method,
                        path=str(request.url.path),
                        status_code=response.status_code,
                        user_id=effective_user_id,
                        terminal_id=terminal_id,
                        context={
                            "duration_ms": duration_ms,
                            "terminal_public_id": terminal_public_id,
                        },
                    )
                    session.add(log_entry)
                    session.commit()
            except Exception:  # pragma: no cover - logging should never break flow
                logger.warning("request_log_failed", request_id=request_id)
            return response
        finally:
            reset_audit_user_id(audit_user_token)

    @staticmethod
    def _resolve_user_id(session, request: Request) -> int | None:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token:
                try:
                    payload = decode_access_token(token)
                    username = payload.get("sub")
                    if username:
                        user = session.query(User).filter(User.username == username, User.is_active == True).first()  # noqa: E712
                        if user:
                            return user.id
                except JWTError:
                    pass
        return None

    @staticmethod
    def _resolve_terminal_id(session, terminal_public_id: str | None) -> int | None:
        if not terminal_public_id:
            return None
        terminal = session.query(Terminal).filter(Terminal.terminal_id == terminal_public_id).first()
        return terminal.id if terminal else None
