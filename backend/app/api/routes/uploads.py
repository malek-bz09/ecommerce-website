"""Product photo uploads (admins only). Files are served back at /api/v1/uploads/<name>."""

import secrets

from fastapi import APIRouter, UploadFile

from app.api.deps import AdminOnly
from app.core.config import get_settings
from app.core.errors import AppError

router = APIRouter(tags=["uploads"], dependencies=[AdminOnly])

# Recognised by the file's first bytes, not its name: anyone can rename virus.exe to photo.jpg
IMAGE_SIGNATURES = {b"\xff\xd8\xff": ".jpg", b"\x89PNG\r\n\x1a\n": ".png", b"RIFF": ".webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@router.post("/admin/uploads", status_code=201)
async def upload_image(file: UploadFile) -> dict[str, str]:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise AppError(413, "The photo must be smaller than 5 MB.")
    extension = next((ext for magic, ext in IMAGE_SIGNATURES.items() if data.startswith(magic)), None)
    if extension == ".webp" and data[8:12] != b"WEBP":  # RIFF is also used by .wav and .avi
        extension = None
    if extension is None:
        raise AppError(415, "Please upload a JPG, PNG or WebP photo.")
    # A random name: no clashes, and nothing the uploader controls ends up in the path
    name = f"{secrets.token_hex(16)}{extension}"
    upload_dir = get_settings().upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / name).write_bytes(data)
    return {"url": f"/api/v1/uploads/{name}"}
