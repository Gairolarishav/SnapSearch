"""
Index service — thread-safe state management and index lifecycle.

Owns the IndexManager singleton that all API routes use to read/update
indexing state and reload FAISS indices into FastAPI app state.
"""
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.indexer import CLIP_INDEX_PATH, CLIP_MAP_PATH, TEXT_INDEX_PATH, TEXT_MAP_PATH
from app.core.vector_store import build_index, load_index


@dataclass
class _IndexState:
    run_id: int = 0
    running: bool = False
    current: int = 0
    total: int = 0
    filename: str = ""
    stage: str = ""
    percent: int = 0
    result: dict | None = None
    error: str | None = None


class IndexManager:
    """
    Thread-safe manager for the background indexing pipeline.

    Provides atomic state updates (via a lock), a progress callback
    for the indexer pipeline, and a helper to reload FAISS indices
    into FastAPI app.state after indexing completes.
    """

    def __init__(self) -> None:
        self._state = _IndexState()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # State access
    # ------------------------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Return a snapshot dict of the current state (thread-safe)."""
        with self._lock:
            s = self._state
            return {
                "run_id": s.run_id,
                "running": s.running,
                "current": s.current,
                "total": s.total,
                "filename": s.filename,
                "stage": s.stage,
                "percent": s.percent,
                "result": s.result,
                "error": s.error,
            }

    def is_running(self) -> bool:
        with self._lock:
            return self._state.running

    def update(self, **kwargs) -> None:
        """Atomically update one or more state fields."""
        with self._lock:
            for k, v in kwargs.items():
                setattr(self._state, k, v)

    # ------------------------------------------------------------------
    # Pipeline callback
    # ------------------------------------------------------------------

    def progress_callback(self, current: int, total: int, filename: str, stage: str) -> None:
        """Called by run_indexing() at each pipeline step."""
        percent = int((current / total) * 100) if total > 0 else 0
        self.update(current=current, total=total, filename=filename, stage=stage, percent=percent)

    # ------------------------------------------------------------------
    # Index lifecycle
    # ------------------------------------------------------------------

    def reload_indices(self, app_state) -> None:
        """
        Load persisted FAISS indices from disk into FastAPI app.state.
        Falls back to empty indices if no persisted data exists yet.
        """
        text_index, text_id_map = load_index(TEXT_INDEX_PATH, TEXT_MAP_PATH)
        clip_index, clip_id_map = load_index(CLIP_INDEX_PATH, CLIP_MAP_PATH)
        app_state.text_index = text_index if text_index is not None else build_index(384)
        app_state.text_id_map = text_id_map if text_id_map else []
        app_state.clip_index = clip_index if clip_index is not None else build_index(512)
        app_state.clip_id_map = clip_id_map if clip_id_map else []


# Module-level singleton — import this everywhere
index_manager = IndexManager()
