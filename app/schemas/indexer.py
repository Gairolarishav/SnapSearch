"""
Indexer schemas — request and response models for /api/index/* endpoints.
"""
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class IndexRequest(BaseModel):
    folder_path: str = Field(..., description="Absolute path to the folder containing images")
    force_reindex: bool = Field(
        default=False,
        description="Re-process every image even if already indexed"
    )


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class IndexStartResponse(BaseModel):
    status: str   # "started"
    run_id: int


class FailedFile(BaseModel):
    filename: str
    error: str


class IndexResult(BaseModel):
    added: int
    skipped: int
    failed: int
    total: int
    failed_files: list[FailedFile]
    added_files: list[str] = []
    skipped_files: list[str] = []


class IndexStatusResponse(BaseModel):
    run_id: int
    running: bool
    current: int
    total: int
    filename: str
    stage: str
    percent: int
    result: IndexResult | None = None
    error: str | None = None


class IndexClearResponse(BaseModel):
    status: str   # "cleared"
