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
    logger.info(f"HMAC verification: terminal_id={terminal_id}, path={path}, timestamp={timestamp}")

    with SessionLocal() as session:
        terminal: Optional[Terminal] = session.query(Terminal).filter_by(terminal_id=terminal_id).first()
        if not terminal:
            logger.warning(f"No terminal found with ID: {terminal_id}")
            raise HTTPException(status_code=401, detail="Invalid terminal")

        logger.info(f"Found terminal: {terminal.terminal_id}, secret_hash: {terminal.secret_hash}")
        secret = terminal.secret_hash.encode()

    body_hash = _hash_body(body)
    logger.info(f"Body hash: {body_hash}")

    message = _canonical_string(method, path, timestamp, body_hash)
    logger.info(f"Canonical string: {message.decode()}")

    computed = hmac.new(secret, message, hashlib.sha256).hexdigest()
    logger.info(f"Computed signature: {computed}, provided signature: {signature}")

    now = int(time.time())
    if abs(now - int(timestamp)) > settings.hmac_clock_skew_seconds:
        logger.warning(f"Timestamp out of range: now={now}, timestamp={timestamp}, skew={settings.hmac_clock_skew_seconds}")
        raise HTTPException(status_code=401, detail="Timestamp out of range")

    if not hmac.compare_digest(computed, signature):
        logger.warning(f"Invalid signature: computed={computed}, provided={signature}")
        raise HTTPException(status_code=401, detail="Invalid signature")

    logger.info("HMAC verification successful")


async def hmac_dependency(
    x_terminal_id: str = Header(..., alias="X-Terminal-ID"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
) -> str:
    return x_terminal_id
