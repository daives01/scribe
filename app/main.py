"""Scribe API - Main Application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    auth_router,
    notes_router,
    search_router,
    settings_router,
    web_router,
)
from app.config import settings
from app.database import create_db_and_tables
from app.services.ollama_service import get_ollama_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    create_db_and_tables()

    # Ensure uploads directory exists
    Path("uploads").mkdir(exist_ok=True)

    yield
    # Shutdown (cleanup if needed)


app = FastAPI(
    title=settings.app_name,
    description="A self-hosted voice note application with AI transcription and semantic search",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include API routers
app.include_router(auth_router)
app.include_router(notes_router)
app.include_router(search_router)
app.include_router(settings_router)

# Include web (frontend) router
app.include_router(web_router)


@app.get("/health")
async def health_check() -> dict:
    """
    System health check.

    Returns status of the application and its dependencies.
    """
    # Check Ollama connection
    ollama = get_ollama_service()
    ollama_connected = await ollama.check_connection()

    # Database is connected if we reached this point
    db_connected = True

    return {
        "status": "ok",
        "ollama_connected": ollama_connected,
        "db_connected": db_connected,
    }
