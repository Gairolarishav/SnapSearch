"""
Search router — POST /api/search
"""
from fastapi import APIRouter, HTTPException, Request

from app.core.clip_embedder import embed_query_clip, load_clip_model
from app.core.database import get_image_by_id
from app.core.embedder import embed_text, load_model
from app.core.vector_store import search
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from app.services.search_service import fuse_scores

router = APIRouter(tags=["Search"])


@router.post("/search", response_model=SearchResponse)
async def api_search(req: SearchRequest, request: Request):
    """
    Search indexed images using a natural-language query.

    Performs hybrid text + CLIP vector search and returns results
    ranked by fused score.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        text_model = load_model()
        clip_model = load_clip_model()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Models not ready: {e}")

    text_vec = embed_text(req.query, text_model)
    clip_vec = embed_query_clip(req.query, clip_model)

    state = request.app.state
    text_hits = search(state.text_index, state.text_id_map, text_vec, req.top_k * 2)
    clip_hits = search(state.clip_index, state.clip_id_map, clip_vec, req.top_k * 2)

    clip_weight = max(0.0, min(1.0, 1.0 - req.text_weight))
    fused = fuse_scores(text_hits, clip_hits, req.text_weight, clip_weight, req.top_k)

    text_ids = {db_id for db_id, _ in text_hits}
    clip_ids = {db_id for db_id, _ in clip_hits}

    results: list[SearchResultItem] = []
    for db_id, score in fused:
        meta = get_image_by_id(db_id)
        if not meta:
            continue
        if db_id in text_ids and db_id in clip_ids:
            match_source = "Both"
        elif db_id in text_ids:
            match_source = "Text"
        else:
            match_source = "CLIP"
        results.append(
            SearchResultItem(
                db_id=db_id,
                score=round(score, 4),
                match_source=match_source,
                path=meta["path"],
                filename=meta["filename"],
                caption=meta["caption"] or "",
                ocr_text=meta["ocr_text"] or "",
                image_type=meta["image_type"],
            )
        )

    return SearchResponse(query=req.query, results=results)
