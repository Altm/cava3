import hashlib
import hmac
import time
import logging
from typing import Optional
from fastapi import HTTPException, Header
from app.config import get_settings
from app.infrastructure.db.session import SessionLocal
from app.models.models import Terminal

logger = logging.getLogger(__name__)


def _canonical_string(method: str, path: str, timestamp: str, body_hash: str) -> bytes:
    return f"{method.upper()}|{path}|{timestamp}|{body_hash}".encode()


def _hash_body(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _generate_hmac_signature(method: str, path: str, body: str, secret: str, timestamp: str) -> str:
    """Generate HMAC signature for the request"""
    body_hash = hashlib.sha256(body.encode()).hexdigest()
    canonical_string = f"{method.upper()}|{path}|{timestamp}|{body_hash}"
    signature = hmac.new(
        secret.encode(),
        canonical_string.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


def verify_hmac_signature(
    method: str,
    path: str,
    body: bytes,
    terminal_id: str,
    signature: str,
    timestamp: str,
) -> None:
    settings = get_settings()
    logger.info("hmac_verification_start terminal_id=%s path=%s", terminal_id, path)

    with SessionLocal() as session:
        terminal: Optional[Terminal] = session.query(Terminal).filter_by(terminal_id=terminal_id).first()
        if not terminal:
            logger.warning("hmac_terminal_not_found terminal_id=%s", terminal_id)
            raise HTTPException(status_code=401, detail="Invalid terminal")
        if (terminal.status or "").lower() != "active":
            logger.warning("hmac_terminal_inactive terminal_id=%s status=%s", terminal_id, terminal.status)
            raise HTTPException(status_code=401, detail="Terminal is inactive")
        secret = terminal.secret_hash.encode()

    body_hash = _hash_body(body)

    message = _canonical_string(method, path, timestamp, body_hash)

    computed = hmac.new(secret, message, hashlib.sha256).hexdigest()

    now = int(time.time())
    try:
        ts_value = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid timestamp format") from exc
    if abs(now - ts_value) > settings.hmac_clock_skew_seconds:
        logger.warning(
            "hmac_timestamp_out_of_range terminal_id=%s now=%s skew=%s",
            terminal_id,
            now,
            settings.hmac_clock_skew_seconds,
        )
        raise HTTPException(status_code=401, detail="Timestamp out of range")

    if not hmac.compare_digest(computed, signature):
        logger.warning("hmac_invalid_signature terminal_id=%s path=%s", terminal_id, path)
        raise HTTPException(status_code=401, detail="Invalid signature")

    logger.info("hmac_verification_ok terminal_id=%s path=%s", terminal_id, path)


async def hmac_dependency(
    x_terminal_id: str = Header(..., alias="X-Terminal-ID"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
) -> str:
    return x_terminal_id
