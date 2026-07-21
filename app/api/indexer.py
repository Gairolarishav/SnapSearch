"""
Indexer router — manages the background indexing pipeline.

  POST   /api/index/start     — start a new indexing run
  GET    /api/index/progress  — SSE stream of live progress
  GET    /api/index/status    — single-poll status snapshot
  DELETE /api/index/clear     — wipe all index data
"""
import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.database import clear_all
from app.core.indexer import (
    CLIP_INDEX_PATH,
    CLIP_MAP_PATH,
    TEXT_INDEX_PATH,
    TEXT_MAP_PATH,
    run_indexing,
)
from app.core.vector_store import build_index
from app.schemas.indexer import (
    IndexClearResponse,
    IndexRequest,
    IndexStartResponse,
    IndexStatusResponse,
)
from app.services.index_service import index_manager

router = APIRouter(tags=["Indexer"])


@router.post("/start", response_model=IndexStartResponse)
async def api_index_start(req: IndexRequest, request: Request):
    """Start a background indexing run for the given folder."""
    if index_manager.is_running():
        raise HTTPException(status_code=409, detail="Indexing already in progress")
    if not Path(req.folder_path).is_dir():
        raise HTTPException(status_code=400, detail="Folder path does not exist")

    current_run_id = index_manager.get_state()["run_id"]
    new_run_id = current_run_id + 1
    index_manager.update(
        run_id=new_run_id,
        running=True,
        current=0,
        total=0,
        filename="",
        stage="starting",
        percent=0,
        result=None,
        error=None,
    )

    loop = asyncio.get_event_loop()
    app_state = request.app.state

    def run() -> None:
        try:
            index_manager.update(
                stage="loading",
                filename="Loading AI models (first run downloads ~650 MB)…",
            )
            result = run_indexing(req.folder_path, req.force_reindex, index_manager.progress_callback)
            index_manager.reload_indices(app_state)
            index_manager.update(running=False, stage="done", percent=100, result=result)
        except Exception as e:
            index_manager.update(running=False, stage="error", error=str(e) or repr(e))

    loop.run_in_executor(None, run)
    return IndexStartResponse(status="started", run_id=new_run_id)


@router.get("/progress")
async def api_index_progress():
    """Server-Sent Events stream — emits state snapshots every 500 ms until done."""
    async def event_stream():
        while True:
            snapshot = index_manager.get_state()
            yield f"data: {json.dumps(snapshot)}\n\n"
            if not snapshot["running"] and snapshot["stage"] in ("done", "error"):
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/status", response_model=IndexStatusResponse)
async def api_index_status():
    """Single-poll status endpoint (polling fallback for older browsers)."""
    return index_manager.get_state()


@router.delete("/clear", response_model=IndexClearResponse)
async def api_index_clear(request: Request):
    """Wipe all indexed data — DB, FAISS indices, and pickle maps."""
    if index_manager.is_running():
        raise HTTPException(status_code=409, detail="Cannot clear while indexing is running")

    clear_all()

    app_state = request.app.state
    app_state.text_index = build_index(384)
    app_state.text_id_map = []
    app_state.clip_index = build_index(512)
    app_state.clip_id_map = []

    for p in [TEXT_INDEX_PATH, TEXT_MAP_PATH, CLIP_INDEX_PATH, CLIP_MAP_PATH]:
        if p.exists():
            p.unlink()

    return IndexClearResponse(status="cleared")
