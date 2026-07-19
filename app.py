import asyncio
import io
import json
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from pydantic import BaseModel

from src.clip_embedder import embed_query_clip, load_clip_model
from src.database import clear_all, count_images, get_image_by_id, init_db
from src.embedder import embed_text, load_model
from src.indexer import CLIP_INDEX_PATH, CLIP_MAP_PATH, TEXT_INDEX_PATH, TEXT_MAP_PATH, run_indexing
from src.vector_store import build_index, load_index, search

load_dotenv()

VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

index_state: dict = {
    "running": False,
    "current": 0,
    "total": 0,
    "filename": "",
    "stage": "",
    "percent": 0,
    "result": None,
    "error": None,
}
_state_lock = threading.Lock()


def _update_state(**kwargs) -> None:
    with _state_lock:
        index_state.update(kwargs)


def _progress_callback(current: int, total: int, filename: str, stage: str) -> None:
    percent = int((current / total) * 100) if total > 0 else 0
    _update_state(current=current, total=total, filename=filename, stage=stage, percent=percent)


def _reload_indices(app_state) -> None:
    text_index, text_id_map = load_index(TEXT_INDEX_PATH, TEXT_MAP_PATH)
    clip_index, clip_id_map = load_index(CLIP_INDEX_PATH, CLIP_MAP_PATH)
    app_state.text_index = text_index if text_index is not None else build_index(384)
    app_state.text_id_map = text_id_map
    app_state.clip_index = clip_index if clip_index is not None else build_index(512)
    app_state.clip_id_map = clip_id_map


def fuse_scores(
    text_results: list,
    clip_results: list,
    text_weight: float = 0.4,
    clip_weight: float = 0.6,
    top_k: int = 9,
) -> list[tuple]:
    scores: dict[int, float] = {}
    if text_results:
        max_t = max(s for _, s in text_results) or 1.0
        for db_id, s in text_results:
            scores[db_id] = scores.get(db_id, 0.0) + text_weight * (s / max_t)
    if clip_results:
        max_c = max(s for _, s in clip_results) or 1.0
        for db_id, s in clip_results:
            scores[db_id] = scores.get(db_id, 0.0) + clip_weight * (s / max_c)
    return sorted(scores.items(), key=lambda x: -x[1])[:top_k]


def _get_text_model():
    """Lazy accessor — loads model on first call."""
    return load_model()


def _get_clip_model():
    """Lazy accessor — loads model on first call."""
    return load_clip_model()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _reload_indices(app.state)
    yield


app = FastAPI(title="SnapSearch", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# --- Page routes ---

@app.get("/")
async def search_page(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/indexer")
async def indexer_page(request: Request):
    return templates.TemplateResponse(request, "indexer.html")


# --- API models ---

class SearchRequest(BaseModel):
    query: str
    top_k: int = 9
    text_weight: float = 0.4


class IndexRequest(BaseModel):
    folder_path: str
    force_reindex: bool = False


# --- Search ---

@app.post("/api/search")
async def api_search(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        text_model = _get_text_model()
        clip_model = _get_clip_model()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Models not ready: {e}")

    text_vec = embed_text(req.query, text_model)
    clip_vec = embed_query_clip(req.query, clip_model)

    text_hits = search(app.state.text_index, app.state.text_id_map, text_vec, req.top_k * 2)
    clip_hits = search(app.state.clip_index, app.state.clip_id_map, clip_vec, req.top_k * 2)

    clip_weight = max(0.0, min(1.0, 1.0 - req.text_weight))
    fused = fuse_scores(text_hits, clip_hits, req.text_weight, clip_weight, req.top_k)

    text_ids = {db_id for db_id, _ in text_hits}
    clip_ids = {db_id for db_id, _ in clip_hits}

    results = []
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
        results.append({
            "db_id": db_id,
            "score": round(score, 4),
            "match_source": match_source,
            "path": meta["path"],
            "filename": meta["filename"],
            "caption": meta["caption"] or "",
            "ocr_text": meta["ocr_text"] or "",
            "image_type": meta["image_type"],
        })

    return {"results": results, "query": req.query}


# --- Indexing ---

@app.post("/api/index/start")
async def api_index_start(req: IndexRequest):
    with _state_lock:
        if index_state["running"]:
            raise HTTPException(status_code=409, detail="Indexing already in progress")
        if not Path(req.folder_path).is_dir():
            raise HTTPException(status_code=400, detail="Folder path does not exist")
        index_state.update({
            "running": True, "current": 0, "total": 0,
            "filename": "", "stage": "starting", "percent": 0,
            "result": None, "error": None,
        })

    loop = asyncio.get_event_loop()

    def run():
        try:
            result = run_indexing(req.folder_path, req.force_reindex, _progress_callback)
            _reload_indices(app.state)
            _update_state(running=False, stage="done", percent=100, result=result)
        except Exception as e:
            _update_state(running=False, stage="error", error=str(e))

    loop.run_in_executor(None, run)
    return {"status": "started"}


@app.get("/api/index/progress")
async def api_index_progress():
    async def event_stream():
        while True:
            with _state_lock:
                snapshot = dict(index_state)
            yield f"data: {json.dumps(snapshot)}\n\n"
            if not snapshot["running"] and snapshot["stage"] in ("done", "error"):
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/index/status")
async def api_index_status():
    with _state_lock:
        return dict(index_state)


@app.delete("/api/index/clear")
async def api_index_clear():
    with _state_lock:
        if index_state["running"]:
            raise HTTPException(status_code=409, detail="Cannot clear while indexing is running")
    clear_all()
    app.state.text_index = build_index(384)
    app.state.text_id_map = []
    app.state.clip_index = build_index(512)
    app.state.clip_id_map = []
    for p in [TEXT_INDEX_PATH, TEXT_MAP_PATH, CLIP_INDEX_PATH, CLIP_MAP_PATH]:
        if Path(p).exists():
            Path(p).unlink()
    return {"status": "cleared"}


# --- Stats ---

@app.get("/api/stats")
async def api_stats():
    return {"total_indexed": count_images()}


# --- Image serving ---

@app.get("/api/image")
async def api_image(path: str, size: int = 300):
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
