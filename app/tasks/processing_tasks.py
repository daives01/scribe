"""Background processing tasks for notes."""

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlmodel import Session, select

from app.database import engine
from app.models.note import Note
from app.models.user import UserSettings
from app.scheduler import scheduler
from app.services.ollama_service import OllamaService
from app.services.transcription_service import transcription_service
from app.tasks.notification_tasks import send_note_notification
from app.utils import get_custom_tags
from app.utils.events import event_manager

logger = logging.getLogger(__name__)


async def _get_user_settings(session: Session, user_id: int) -> UserSettings:
    """Get user settings or return defaults."""
    statement = select(UserSettings).where(UserSettings.user_id == user_id)
    settings = session.exec(statement).first()
    if not settings:
        return UserSettings(user_id=user_id)
    return settings


async def _process_note_ai(note: Note, session: Session):
    """
    Process note with AI (summary, tag, embedding).

    Args:
        note: Note to process
        session: Database session

    Returns:
        Dictionary with summary, tag, notification_timestamp, embedding
    """
    user_settings = await _get_user_settings(session, note.user_id)
    ollama = OllamaService(
        base_url=user_settings.ollama_url,
        model=user_settings.ollama_model,
        embedding_model=user_settings.ollama_embedding_model,
        api_key=user_settings.ollama_api_key,
    )

    available_tags = get_custom_tags(user_settings.custom_tags)

    summary_result = await ollama.generate_summary_and_tag(
        note.raw_transcript, available_tags
    )

    embedding = await ollama.generate_embedding(note.raw_transcript)

    return {
        "summary": summary_result.get("summary"),
        "tag": summary_result.get("tag"),
        "notification_timestamp": summary_result.get("notification_timestamp"),
        "embedding": embedding,
    }


def _schedule_notification_if_needed(note: Note) -> None:
    """Schedule a notification for the note if timestamp is set and in the future."""
    if note.notification_timestamp and note.notification_timestamp > datetime.now():
        try:
            if not scheduler:
                raise RuntimeError("Scheduler not initialized")
            scheduler.add_job(
                send_note_notification,
                "date",
                run_date=note.notification_timestamp,
                args=[note.id],
                id=f"note_notification_{note.id}",
                replace_existing=True,
            )
            logger.info(
                f"Scheduled notification for note {note.id} at {note.notification_timestamp}"
            )
        except Exception as e:
            logger.error(f"Failed to schedule notification for note {note.id}: {e}")


async def process_new_note(note_id: int) -> None:
    """
    Process a newly uploaded note.
    """
    with Session(engine) as session:
        note = session.get(Note, note_id)
        if not note:
            logger.error(f"Note {note_id} not found for processing")
            return

        try:
            note.processing_status = "transcribing"
            session.add(note)
            session.commit()
            await event_manager.broadcast(
                note.user_id, f"note-status-{note.id}", "transcribing"
            )

            if note.audio_path and Path(note.audio_path).exists():
                transcript = await asyncio.to_thread(
                    transcription_service.transcribe_file, note.audio_path
                )
                note.raw_transcript = transcript
            elif not note.raw_transcript:
                raise ValueError("No audio file or transcript available")

            note.processing_status = "processing"
            session.add(note)
            session.commit()
            await event_manager.broadcast(
                note.user_id, f"note-status-{note.id}", "processing"
            )

            ai_result = await _process_note_ai(note, session)
            note.summary = ai_result["summary"]
            note.tag = ai_result["tag"]
            note.notification_timestamp = ai_result["notification_timestamp"]
            note.embedding = ai_result["embedding"]

            note.processing_status = "completed"
            note.error_message = None
            note.updated_at = datetime.now(UTC)
            session.add(note)
            session.commit()

            _schedule_notification_if_needed(note)

            await event_manager.broadcast(
                note.user_id, f"note-status-{note.id}", "completed"
            )
            await event_manager.broadcast(
                note.user_id, f"note-processed-{note.id}", "completed"
            )

            logger.info(f"Successfully processed note {note_id}")

        except Exception as e:
            logger.exception(f"Failed to process note {note_id}: {e}")
            note.processing_status = "failed"
            note.error_message = str(e)
            note.updated_at = datetime.now(UTC)
            session.add(note)
            session.commit()
            await event_manager.broadcast(
                note.user_id, f"note-status-{note.id}", "failed"
            )


async def reprocess_note(note_id: int) -> None:
    """
    Reprocess an existing note (skip transcription).
    """
    with Session(engine) as session:
        note = session.get(Note, note_id)
        if not note:
            logger.error(f"Note {note_id} not found for reprocessing")
            return

        if not note.raw_transcript:
            logger.error(f"Note {note_id} has no transcript to reprocess")
            note.processing_status = "failed"
            note.error_message = "No transcript available"
            session.add(note)
            session.commit()
            return

        try:
            note.processing_status = "processing"
            session.add(note)
            session.commit()
            await event_manager.broadcast(
                note.user_id, f"note-status-{note.id}", "processing"
            )

            ai_result = await _process_note_ai(note, session)
            note.summary = ai_result["summary"]
            note.tag = ai_result["tag"]
            note.notification_timestamp = ai_result["notification_timestamp"]
            note.embedding = ai_result["embedding"]

            note.processing_status = "completed"
            note.error_message = None
            note.updated_at = datetime.now(UTC)
            session.add(note)
            session.commit()

            _schedule_notification_if_needed(note)

            await event_manager.broadcast(
                note.user_id, f"note-status-{note.id}", "completed"
            )
            await event_manager.broadcast(
                note.user_id, f"note-processed-{note.id}", "completed"
            )

            logger.info(f"Successfully reprocessed note {note_id}")

        except Exception as e:
            logger.exception(f"Failed to reprocess note {note_id}: {e}")
            note.processing_status = "failed"
            note.error_message = str(e)
            note.updated_at = datetime.now(UTC)
            session.add(note)
            session.commit()
            await event_manager.broadcast(
                note.user_id, f"note-status-{note.id}", "failed"
            )
