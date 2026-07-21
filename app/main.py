"""
FastAPI application factory for SnapSearch.

Creates and configures the FastAPI app instance with:
  - Lifespan handler (DB init + FAISS index load on startup)
  - Static file mount
  - All routers registered with correct prefixes
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import images, indexer, search, stats
from app.core.database import init_db
from app.services.index_service import index_manager
from app.web import pages


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB and load persisted FAISS indices into app.state."""
    init_db()
    index_manager.reload_indices(app.state)
    yield
    # (teardown hooks can be added here if needed)


def create_app() -> FastAPI:
    app = FastAPI(
        title="SnapSearch",
        description="AI-powered image & screenshot search — find any image by describing it.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Static assets (CSS, JS)
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # HTML page routes
    app.include_router(pages.router)

    # API routes
    app.include_router(search.router,  prefix="/api")
    app.include_router(indexer.router, prefix="/api/index")
    app.include_router(images.router,  prefix="/api")
    app.include_router(stats.router,   prefix="/api")

    return app


# Module-level app instance — consumed by uvicorn and root main.py
app = create_app()
