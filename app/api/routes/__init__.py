"""API routes module."""

from app.api.routes.auth import router as auth_router
from app.api.routes.notes import router as notes_router
from app.api.routes.search import router as search_router
from app.api.routes.settings import router as settings_router
from app.api.routes.web import router as web_router

__all__ = ["auth_router", "notes_router", "search_router", "settings_router", "web_router"]
