"""Note service for CRUD operations and search."""

import logging
from datetime import UTC, datetime

from sqlalchemy import or_, text
from sqlmodel import Session, func, select

from app.models.note import Note
from app.models.user import UserSettings
from app.services.ollama_service import get_ollama_service
from app.utils.exceptions import NotFoundError

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

    def create_note(
        self, user_id: int, raw_transcript: str = "", audio_path: str | None = None
    ) -> Note:
        """
        Create a new note with pending status.

        Args:
            user_id: Owner user ID
            raw_transcript: Initial transcript text (for text notes)
            audio_path: Optional path to saved audio file

        Returns:
            Created Note instance
        """
        note = Note(
            user_id=user_id,
            raw_transcript=raw_transcript,
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
        # Get total count (exclude archived)
        count_statement = select(func.count()).where(
            Note.user_id == user_id,
            Note.archived == False,  # noqa: E712
        )
        total = self.session.exec(count_statement).one()

        # Get paginated notes (exclude archived)
        statement = (
            select(Note)
            .where(Note.user_id == user_id, Note.archived == False)  # noqa: E712
            .order_by(Note.created_at.desc())  # type: ignore
            .offset(skip)
            .limit(limit)
        )
        notes = list(self.session.exec(statement).all())
        return notes, total

    def update_note(
        self,
        note_id: int,
        user_id: int,
        raw_transcript: str | None = None,
        summary: str | None = None,
        tag: str | None = None,
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

        if summary is not None:
            note.summary = summary

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
        logger.info(
            f"Generated search embedding for query '{query}': {len(query_embedding)} bytes"
        )

        # Use raw SQL for vector search with sqlite-vec
        sql = text(
            """
            SELECT id, raw_transcript, summary, tag, processing_status,
                   error_message, created_at, updated_at, user_id, audio_path, embedding,
                   vec_distance_cosine(embedding, :query_vec) as distance
            FROM notes
            WHERE user_id = :user_id
              AND archived = 0
              AND embedding IS NOT NULL
              AND length(embedding) = :vec_len
            ORDER BY distance ASC
            LIMIT :limit
        """
        )

        try:
            # Execute and get rows as mappings
            result = self.session.execute(
                sql,
                {
                    "query_vec": query_embedding,
                    "user_id": user_id,
                    "limit": limit,
                    "vec_len": len(query_embedding),
                },
            )
            rows = result.all()
        except Exception as e:
            logger.error(f"Error executing semantic search SQL: {e}")
            raise e

        # Convert to Note objects
        notes = []
        for row in rows:
            # Note.model_validate handles type conversion (e.g. str -> datetime)
            # and ignores extra fields like 'distance'
            note = Note.model_validate(dict(row._mapping))
            notes.append(note)

        logger.info(f"Semantic search found {len(notes)} results")
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
            logger.warning(f"Note {note_id} has no embedding for similarity search")
            return []

        logger.info(
            f"Finding similar notes for note {note_id}, embedding size: {len(note.embedding)} bytes"
        )

        # Use the note's embedding for search
        sql = text(
            """
            SELECT id, raw_transcript, summary, tag, processing_status,
                   error_message, created_at, updated_at, user_id, audio_path, embedding,
                   vec_distance_cosine(embedding, :query_vec) as distance
            FROM notes
            WHERE user_id = :user_id
              AND archived = 0
              AND embedding IS NOT NULL
              AND id != :note_id
              AND length(embedding) = :vec_len
            ORDER BY distance ASC
            LIMIT :limit
        """
        )

        try:
            result = self.session.execute(
                sql,
                {
                    "query_vec": note.embedding,
                    "user_id": user_id,
                    "note_id": note_id,
                    "limit": limit,
                    "vec_len": len(note.embedding),
                },
            )
            rows = result.all()
        except Exception as e:
            logger.error(f"Error executing similar notes SQL: {e}")
            raise e

        # Convert to Note objects
        notes = []
        for row in rows:
            similar_note = Note.model_validate(dict(row._mapping))
            notes.append(similar_note)

        logger.info(f"Found {len(notes)} similar notes for note {note_id}")
        return notes

    def archive_note(self, note_id: int, user_id: int) -> Note:
        """
        Archive a note (soft delete - hide from recent/search).

        Args:
            note_id: Note ID to archive
            user_id: Owner user ID for verification

        Returns:
            Updated Note instance

        Raises:
            NotFoundError: If note not found or doesn't belong to user
        """
        note = self.get_note(note_id, user_id)
        note.archived = True
        note.updated_at = datetime.now(UTC)
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        return note

    def unarchive_note(self, note_id: int, user_id: int) -> Note:
        """
        Unarchive a note (restore from soft delete).

        Args:
            note_id: Note ID to unarchive
            user_id: Owner user ID for verification

        Returns:
            Updated Note instance

        Raises:
            NotFoundError: If note not found or doesn't belong to user
        """
        note = self.get_note(note_id, user_id)
        note.archived = False
        note.updated_at = datetime.now(UTC)
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        return note

    def list_notes_advanced(
        self,
        user_id: int,
        search: str | None = None,
        tag: str | None = None,
        status: str | None = None,
        include_archived: bool = False,
        archived_only: bool = False,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Note], int]:
        """
        Advanced list with filters, sorting, and pagination.

        Args:
            user_id: Owner user ID
            search: Text search in summary or transcript
            tag: Filter by tag
            status: Filter by processing_status
            include_archived: Include archived notes in results
            archived_only: Show only archived notes
            date_from: Filter by date range start (inclusive)
            date_to: Filter by date range end (inclusive)
            sort_by: Sort column (created_at, updated_at, summary, tag, status)
            sort_order: Sort direction (asc, desc)
            page: Page number (1-indexed)
            per_page: Results per page

        Returns:
            Tuple of (notes list, total count)
        """
        page = max(1, page)
        per_page = min(100, max(1, per_page))
        skip = (page - 1) * per_page

        conditions: list = [Note.user_id == user_id]

        if archived_only:
            conditions.append(Note.archived == True)  # noqa: E712
        elif not include_archived:
            conditions.append(Note.archived == False)  # noqa: E712

        if tag:
            conditions.append(Note.tag == tag)

        if status:
            conditions.append(Note.processing_status == status)

        if search:
            search_term = f"%{search}%"

            conditions.append(
                or_(
                    Note.summary.like(search_term),  # type: ignore[union-attr]
                    Note.raw_transcript.like(search_term),  # type: ignore[union-attr,attr-defined]
                )
            )  # type: ignore[arg-type]

        if date_from:
            conditions.append(Note.created_at >= date_from)

        if date_to:
            conditions.append(Note.created_at <= date_to)

        count_statement = select(func.count()).where(*conditions)
        total = self.session.exec(count_statement).one()

        valid_sort_columns = {
            "created_at": Note.created_at,
            "updated_at": Note.updated_at,
            "summary": Note.summary,
            "tag": Note.tag,
            "status": Note.processing_status,
        }

        sort_column = valid_sort_columns.get(sort_by, Note.created_at)
        sort_attr = (
            sort_column.desc()  # type: ignore[union-attr]
            if sort_order == "desc"
            else sort_column.asc()  # type: ignore[union-attr]
        )

        statement = (
            select(Note)
            .where(*conditions)
            .order_by(sort_attr)
            .offset(skip)
            .limit(per_page)
        )

        notes = list(self.session.exec(statement).all())
        return notes, total

    def bulk_archive_notes(self, note_ids: list[int], user_id: int) -> list[Note]:
        """
        Archive multiple notes.

        Args:
            note_ids: List of note IDs to archive
            user_id: Owner user ID for verification

        Returns:
            List of updated Note instances
        """
        return [
            self.archive_note(note_id, user_id)
            for note_id in note_ids
            if not self._log_note_not_found(note_id, user_id)
        ]

    def bulk_unarchive_notes(self, note_ids: list[int], user_id: int) -> list[Note]:
        """
        Unarchive multiple notes.

        Args:
            note_ids: List of note IDs to unarchive
            user_id: Owner user ID for verification

        Returns:
            List of updated Note instances
        """
        return [
            self.unarchive_note(note_id, user_id)
            for note_id in note_ids
            if not self._log_note_not_found(note_id, user_id)
        ]

    def bulk_delete_notes(self, note_ids: list[int], user_id: int) -> list[int]:
        """
        Delete multiple notes.

        Args:
            note_ids: List of note IDs to delete
            user_id: Owner user ID for verification

        Returns:
            List of deleted note IDs
        """
        deleted_ids = []
        for note_id in note_ids:
            try:
                self.delete_note(note_id, user_id)
                deleted_ids.append(note_id)
            except NotFoundError:
                logger.warning(
                    f"Note {note_id} not found or not owned by user {user_id}"
                )
                continue
        return deleted_ids

    def _log_note_not_found(self, note_id: int, user_id: int) -> bool:
        """
        Check if note exists, log warning if not.

        Args:
            note_id: Note ID to check
            user_id: Owner user ID

        Returns:
            True if note not found, False otherwise
        """
        try:
            self.get_note(note_id, user_id)
            return False
        except NotFoundError:
            logger.warning(f"Note {note_id} not found or not owned by user {user_id}")
            return True
