"""
Image serving router — GET /api/image
"""
import io
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from PIL import Image

router = APIRouter(tags=["Images"])

VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


@router.get("/image")
async def api_image(path: str, size: int = 300):
    """
    Serve a resized thumbnail of an image from disk.

    Args:
        path: Absolute path to the image file.
        size: Max width/height in pixels for the thumbnail (default 300).
    """
    img_path = Path(path).resolve()
    if not img_path.exists() or img_path.suffix.lower() not in VALID_EXTENSIONS:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        img = Image.open(img_path).convert("RGB")
        img.thumbnail((size, size), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        return Response(content=buf.read(), media_type="image/jpeg")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to process image")
