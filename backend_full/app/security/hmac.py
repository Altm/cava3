import hashlib
import hmac
import time
from typing import Optional
from fastapi import HTTPException, Header
from app.config import get_settings
from app.infrastructure.db.session import SessionLocal
from app.models.models import Terminal


def _canonical_string(method: str, path: str, timestamp: str, body_hash: str) -> bytes:
    return f"{method.upper()}|{path}|{timestamp}|{body_hash}".encode()


def _hash_body(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def verify_hmac_signature(
    method: str,
    path: str,
    body: bytes,
    terminal_id: str,
    signature: str,
    timestamp: str,
) -> None:
    settings = get_settings()
    with SessionLocal() as session:
        terminal: Optional[Terminal] = session.query(Terminal).filter_by(terminal_id=terminal_id).first()
        if not terminal:
            raise HTTPException(status_code=401, detail="Invalid terminal")
        secret = terminal.secret_hash.encode()
    body_hash = _hash_body(body)
    message = _canonical_string(method, path, timestamp, body_hash)
    computed = hmac.new(secret, message, hashlib.sha256).hexdigest()
    now = int(time.time())
    if abs(now - int(timestamp)) > settings.hmac_clock_skew_seconds:
        raise HTTPException(status_code=401, detail="Timestamp out of range")
    if not hmac.compare_digest(computed, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


async def hmac_dependency(
    x_terminal_id: str = Header(..., alias="X-Terminal-ID"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
) -> str:
    return x_terminal_id
