"""Scribe API - Main Application."""

from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes.auth import router as auth_router
from app.api.routes.events import router as events_router
from app.api.routes.notes import router as notes_router
from app.api.routes.search import router as search_router
from app.api.routes.settings import router as settings_router
from app.api.routes.web import router as web_router
from app.config import settings
from app.database import create_db_and_tables
from app import scheduler
from app.services.ollama_service import OllamaService


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db_and_tables()
    Path("uploads").mkdir(exist_ok=True)

    jobstore = SQLAlchemyJobStore(url=settings.database_url)
    scheduler_instance = AsyncIOScheduler(jobstores={"default": jobstore})
    scheduler_instance.start()

    # Update the module-level scheduler so other modules can use it
    scheduler.scheduler = scheduler_instance

    yield
    scheduler_instance.shutdown()
    scheduler.scheduler = None


app = FastAPI(
    title=settings.app_name,
    description="A self-hosted voice note application with AI transcription and semantic search",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include API routers
app.include_router(auth_router)
app.include_router(events_router)
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
    ollama = OllamaService()
    ollama_connected = await ollama.check_connection()

    # Database is connected if we reached this point
    db_connected = True

    return {
        "status": "ok",
        "ollama_connected": ollama_connected,
        "db_connected": db_connected,
    }
