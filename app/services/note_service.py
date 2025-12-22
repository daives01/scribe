"""Note service for CRUD operations and search."""

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import text
from sqlmodel import Session, func, select

from app.models.note import Note
from app.models.user import UserSettings
from app.services.ollama_service import OllamaService, get_ollama_service
from app.utils.exceptions import NotFoundError
from app.utils.vector import serialize_vector

logger = logging.getLogger(__name__)


class NoteService:
    """Service for note CRUD operations and search."""

    def __init__(self, session: Session):
        """
        Initialize the note service.

        Args:
            session: Database session
        """
        self.session = session

    def create_note(self, user_id: int, audio_path: str | None = None) -> Note:
        """
        Create a new note with pending status.

        Args:
            user_id: Owner user ID
            audio_path: Optional path to saved audio file

        Returns:
            Created Note instance
        """
        note = Note(
            user_id=user_id,
            raw_transcript="",
            audio_path=audio_path,
            processing_status="pending",
        )
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        return note

    def get_note(self, note_id: int, user_id: int) -> Note:
        """
        Get a single note by ID, ensuring user ownership.

        Args:
            note_id: Note ID to fetch
            user_id: Owner user ID for verification

        Returns:
            Note instance

        Raises:
            NotFoundError: If note not found or doesn't belong to user
        """
        note = self.session.get(Note, note_id)
        if not note or note.user_id != user_id:
            raise NotFoundError("Note")
        return note

    def list_notes(
        self, user_id: int, skip: int = 0, limit: int = 50
    ) -> tuple[list[Note], int]:
        """
        List notes for a user with pagination.

        Args:
            user_id: Owner user ID
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (notes list, total count)
        """
        # Get total count
        count_statement = select(func.count()).where(Note.user_id == user_id)
        total = self.session.exec(count_statement).one()

        # Get paginated notes
        statement = (
            select(Note)
            .where(Note.user_id == user_id)
            .order_by(Note.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        notes = list(self.session.exec(statement).all())
        return notes, total

    def update_note(
        self, note_id: int, user_id: int, raw_transcript: str | None = None, tag: str | None = None
    ) -> Note:
        """
        Update a note's content.

        Args:
            note_id: Note ID to update
            user_id: Owner user ID for verification
            raw_transcript: Optional new transcript
            tag: Optional new tag

        Returns:
            Updated Note instance

        Raises:
            NotFoundError: If note not found or doesn't belong to user
        """
        note = self.get_note(note_id, user_id)

        if raw_transcript is not None:
            note.raw_transcript = raw_transcript
            # Mark for re-processing if transcript changed
            note.processing_status = "pending"

        if tag is not None:
            note.tag = tag

        note.updated_at = datetime.now(UTC)
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        return note

    def delete_note(self, note_id: int, user_id: int) -> bool:
        """
        Delete a note and its associated audio file.

        Args:
            note_id: Note ID to delete
            user_id: Owner user ID for verification

        Returns:
            True if deleted

        Raises:
            NotFoundError: If note not found or doesn't belong to user
        """
        note = self.get_note(note_id, user_id)

        # Delete audio file if it exists
        if note.audio_path:
            from pathlib import Path
            audio_path = Path(note.audio_path)
            try:
                if audio_path.exists():
                    audio_path.unlink()
                    logger.info(f"Deleted audio file: {audio_path}")
            except Exception as e:
                logger.error(f"Error deleting audio file {audio_path}: {e}")

        self.session.delete(note)
        self.session.commit()
        return True

    async def search_notes_semantic(
        self, user_id: int, query: str, user_settings: UserSettings, limit: int = 10
    ) -> list[Note]:
        """
        Search notes using vector similarity.

        Args:
            user_id: Owner user ID
            query: Search query text
            user_settings: User's settings for Ollama config
            limit: Maximum results to return

        Returns:
            List of matching notes ordered by relevance
        """
        # Get Ollama service with user's settings
        ollama = get_ollama_service(
            base_url=user_settings.ollama_url,
            model=user_settings.ollama_model,
            embedding_model=user_settings.ollama_embedding_model,
            api_key=user_settings.ollama_api_key,
        )

        # Generate embedding for query
        query_embedding = await ollama.generate_embedding(query)

        # Use raw SQL for vector search with sqlite-vec
        sql = text("""
            SELECT id, raw_transcript, summary, tag, processing_status,
                   error_message, created_at, updated_at, user_id, audio_path, embedding,
                   vec_distance_cosine(embedding, :query_vec) as distance
            FROM notes
            WHERE user_id = :user_id AND embedding IS NOT NULL
            ORDER BY distance ASC
            LIMIT :limit
        """)

        result = self.session.execute(
            sql, {"query_vec": query_embedding, "user_id": user_id, "limit": limit}
        )

        # Convert to Note objects
        notes = []
        for row in result:
            note = Note(
                id=row.id,
                user_id=row.user_id,
                raw_transcript=row.raw_transcript,
                summary=row.summary,
                tag=row.tag,
                processing_status=row.processing_status,
                error_message=row.error_message,
                created_at=row.created_at,
                updated_at=row.updated_at,
                audio_path=row.audio_path,
                embedding=row.embedding,
            )
            notes.append(note)

        return notes

    async def get_similar_notes(
        self, note_id: int, user_id: int, user_settings: UserSettings, limit: int = 5
    ) -> list[Note]:
        """
        Find notes similar to a given note.

        Args:
            note_id: Source note ID
            user_id: Owner user ID
            user_settings: User's settings
            limit: Maximum results to return

        Returns:
            List of similar notes
        """
        # Get the source note
        note = self.get_note(note_id, user_id)
        if not note.embedding:
            return []

        # Use the note's embedding for search
        sql = text("""
            SELECT id, raw_transcript, summary, tag, processing_status,
                   error_message, created_at, updated_at, user_id, audio_path, embedding,
                   vec_distance_cosine(embedding, :query_vec) as distance
            FROM notes
            WHERE user_id = :user_id AND embedding IS NOT NULL AND id != :note_id
            ORDER BY distance ASC
            LIMIT :limit
        """)

        result = self.session.execute(
            sql,
            {
                "query_vec": note.embedding,
                "user_id": user_id,
                "note_id": note_id,
                "limit": limit,
            },
        )

        # Convert to Note objects
        notes = []
        for row in result:
            similar_note = Note(
                id=row.id,
                user_id=row.user_id,
                raw_transcript=row.raw_transcript,
                summary=row.summary,
                tag=row.tag,
                processing_status=row.processing_status,
                error_message=row.error_message,
                created_at=row.created_at,
                updated_at=row.updated_at,
                audio_path=row.audio_path,
                embedding=row.embedding,
            )
            notes.append(similar_note)

        return notes
