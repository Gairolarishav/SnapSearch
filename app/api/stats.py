"""
Stats router — GET /api/stats
"""
from fastapi import APIRouter

from app.core.database import count_images

router = APIRouter(tags=["Stats"])


@router.get("/stats")
async def api_stats():
    """Return the total number of images currently indexed."""
    return {"total_indexed": count_images()}
