from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from fastapi import UploadFile

from app.config import get_settings


_IMAGE_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "image/jpeg": (b"\xFF\xD8\xFF",),
    "image/png": (b"\x89PNG\r\n\x1A\n",),
    "image/gif": (b"GIF87a", b"GIF89a"),
}

_IMAGE_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "image/jpeg": (".jpg", ".jpeg"),
    "image/png": (".png",),
    "image/gif": (".gif",),
    "image/webp": (".webp",),
}

_DEFAULT_EXTENSION_BY_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def _looks_like_webp(content: bytes) -> bool:
    return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"


def _detect_mime(content: bytes) -> str | None:
    for mime_type, signatures in _IMAGE_SIGNATURES.items():
        for signature in signatures:
            if content.startswith(signature):
                return mime_type
    if _looks_like_webp(content):
        return "image/webp"
    return None


def validate_image_upload(*, filename: str, content_type: str, content: bytes) -> str:
    settings = get_settings()
    max_bytes = max(1, int(settings.image_upload_max_bytes))
    if not content:
        raise HTTPException(status_code=422, detail="Empty file")
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large. Max allowed size is {max_bytes} bytes")

    normalized_content_type = (content_type or "").split(";")[0].strip().lower()
    detected_mime = _detect_mime(content)
    if detected_mime is None:
        raise HTTPException(status_code=422, detail="Unsupported or invalid image content")

    if normalized_content_type and normalized_content_type != detected_mime:
        raise HTTPException(status_code=422, detail="Content type does not match uploaded file")

    suffix = Path(filename or "").suffix.lower()
    allowed_extensions = _IMAGE_EXTENSIONS.get(detected_mime, ())
    if suffix not in allowed_extensions:
        suffix = _DEFAULT_EXTENSION_BY_MIME[detected_mime]

    preview = content[:4096].lower()
    if b"<script" in preview or b"<?php" in preview:
        raise HTTPException(status_code=422, detail="Suspicious file content")

    return suffix


async def read_upload_file_limited(file: UploadFile, *, max_bytes: Optional[int] = None) -> bytes:
    settings = get_settings()
    limit = max_bytes if max_bytes is not None else int(settings.image_upload_max_bytes)
    limit = max(1, limit)
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(status_code=413, detail=f"File too large. Max allowed size is {limit} bytes")
    return content
