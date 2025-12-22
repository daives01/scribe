"""Background processing tasks for notes."""

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlmodel import Session

from app.database import engine
from app.models.note import Note
from app.models.user import UserSettings
from app.services.ollama_service import get_ollama_service
from app.services.transcription_service import transcription_service

logger = logging.getLogger(__name__)


def _get_user_settings(session: Session, user_id: int) -> UserSettings:
    """Get user settings or return defaults."""
    from sqlmodel import select

    statement = select(UserSettings).where(UserSettings.user_id == user_id)
    settings = session.exec(statement).first()
    if not settings:
        # Return default settings
        return UserSettings(user_id=user_id)
    return settings


def process_new_note(note_id: int) -> None:
    """
    Process a newly uploaded note.

    Steps:
    1. Update status to 'transcribing'
    2. Transcribe the audio file
    3. Update status to 'processing'
    4. Generate summary and tag
    5. Generate embedding
    6. Update note with results
    7. Set status to 'completed'

    Args:
        note_id: ID of the note to process
    """
    with Session(engine) as session:
        note = session.get(Note, note_id)
        if not note:
            logger.error(f"Note {note_id} not found for processing")
            return

        try:
            # Step 1: Update status to transcribing
            note.processing_status = "transcribing"
            session.add(note)
            session.commit()

            # Step 2: Transcribe audio
            if note.audio_path and Path(note.audio_path).exists():
                transcript = transcription_service.transcribe_file(note.audio_path)
                note.raw_transcript = transcript
            elif not note.raw_transcript:
                raise ValueError("No audio file or transcript available")

            # Step 3: Update status to processing
            note.processing_status = "processing"
            session.add(note)
            session.commit()

            # Get user settings for AI processing
            user_settings = _get_user_settings(session, note.user_id)
            ollama = get_ollama_service(
                base_url=user_settings.ollama_url,
                model=user_settings.ollama_model,
                api_key=user_settings.ollama_api_key,
            )

            # Step 4: Generate summary and tag
            available_tags = json.loads(user_settings.custom_tags)

            # Run async operations in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                summary_result = loop.run_until_complete(
                    ollama.generate_summary_and_tag(note.raw_transcript, available_tags)
                )
                note.summary = summary_result.get("summary")
                note.tag = summary_result.get("tag")

                # Step 5: Generate embedding
                embedding = loop.run_until_complete(
                    ollama.generate_embedding(note.raw_transcript)
                )
                note.embedding = embedding
            finally:
                loop.close()

            # Step 6: Update status to completed
            note.processing_status = "completed"
            note.error_message = None
            note.updated_at = datetime.now(UTC)
            session.add(note)
            session.commit()

            logger.info(f"Successfully processed note {note_id}")

        except Exception as e:
            logger.exception(f"Failed to process note {note_id}: {e}")
            note.processing_status = "failed"
            note.error_message = str(e)
            note.updated_at = datetime.now(UTC)
            session.add(note)
            session.commit()


def reprocess_note(note_id: int) -> None:
    """
    Reprocess an existing note (skip transcription).

    Used when a note's transcript is updated and needs new
    summary, tag, and embedding.

    Args:
        note_id: ID of the note to reprocess
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
            # Update status to processing
            note.processing_status = "processing"
            session.add(note)
            session.commit()

            # Get user settings for AI processing
            user_settings = _get_user_settings(session, note.user_id)
            ollama = get_ollama_service(
                base_url=user_settings.ollama_url,
                model=user_settings.ollama_model,
                api_key=user_settings.ollama_api_key,
            )

            # Get available tags
            available_tags = json.loads(user_settings.custom_tags)

            # Run async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Generate new summary and tag
                summary_result = loop.run_until_complete(
                    ollama.generate_summary_and_tag(note.raw_transcript, available_tags)
                )
                note.summary = summary_result.get("summary")
                note.tag = summary_result.get("tag")

                # Generate new embedding
                embedding = loop.run_until_complete(
                    ollama.generate_embedding(note.raw_transcript)
                )
                note.embedding = embedding
            finally:
                loop.close()

            # Update status to completed
            note.processing_status = "completed"
            note.error_message = None
            note.updated_at = datetime.now(UTC)
            session.add(note)
            session.commit()

            logger.info(f"Successfully reprocessed note {note_id}")

        except Exception as e:
            logger.exception(f"Failed to reprocess note {note_id}: {e}")
            note.processing_status = "failed"
            note.error_message = str(e)
            note.updated_at = datetime.now(UTC)
            session.add(note)
            session.commit()
