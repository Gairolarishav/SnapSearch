"""
Page router — Jinja2 HTML page routes.

  GET /         — Search UI
  GET /indexer  — Indexer UI
"""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def search_page(request: Request):
    """Render the main search interface."""
    return templates.TemplateResponse(request, "index.html")


@router.get("/indexer")
async def indexer_page(request: Request):
    """Render the indexer management interface."""
    return templates.TemplateResponse(request, "indexer.html")
