"""
FastAPI dependency injection helpers.

Import these with Depends() in route handlers where needed.
"""
from fastapi import Request

from app.services.index_service import index_manager as _index_manager


def get_app_state(request: Request):
    """Inject the FastAPI app state (holds loaded FAISS indices)."""
    return request.app.state


def get_index_manager():
    """Inject the shared IndexManager singleton."""
    return _index_manager
