from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException


@dataclass(frozen=True)
class ParsedQR:
    kind: str  # "ITM" | "BOX"
    uuid: UUID


def parse_qr(qr_code: str) -> ParsedQR:
    """
    Parse QR code in format {PREFIX}:{UUID}.

    Supported prefixes:
    - ITM (serialized unit / bottle)
    - BOX (box)
    """
    if not isinstance(qr_code, str) or ":" not in qr_code:
        raise HTTPException(status_code=422, detail="Invalid QR format")
    prefix, raw_uuid = qr_code.split(":", 1)
    prefix = prefix.strip().upper()
    try:
        parsed_uuid = UUID(raw_uuid.strip())
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid QR UUID") from exc
    if prefix not in {"ITM", "BOX"}:
        raise HTTPException(status_code=422, detail="Unsupported QR prefix")
    return ParsedQR(kind=prefix, uuid=parsed_uuid)

