"""
Search schemas — request and response models for POST /api/search.
"""
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural-language search query")
    top_k: int = Field(default=9, ge=1, le=50, description="Max results to return")
    text_weight: float = Field(
        default=0.4, ge=0.0, le=1.0,
        description="Weight for text-embedding scores; CLIP weight = 1 - text_weight"
    )


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class SearchResultItem(BaseModel):
    db_id: int
    score: float
    match_source: str          # "Text" | "CLIP" | "Both"
    path: str
    filename: str
    caption: str
    ocr_text: str
    image_type: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
