"""Tests for advanced notes filtering and pagination."""

from datetime import UTC, datetime

from app.services.note_service import NoteService


def test_list_notes_advanced_basic(session, test_user):
    """Test basic list_notes_advanced functionality."""
    note_service = NoteService(session)

    # Create notes
    from app.models import Note

    note1 = Note(
        user_id=test_user.id,
        raw_transcript="Test note 1",
        summary="Meeting about project",
        tag="Work",
        processing_status="completed",
    )
    note2 = Note(
        user_id=test_user.id,
        raw_transcript="Test note 2",
        summary="Grocery list",
        tag="Personal",
        processing_status="completed",
    )
    note3 = Note(
        user_id=test_user.id,
        raw_transcript="Test note 3",
        summary="Another work item",
        tag="Work",
        processing_status="pending",
    )
    session.add_all([note1, note2, note3])
    session.commit()

    notes, total = note_service.list_notes_advanced(user_id=test_user.id)
    assert total == 3
    assert len(notes) == 3


def test_list_notes_advanced_search(session, test_user):
    """Test search functionality in list_notes_advanced."""
    note_service = NoteService(session)

    from app.models import Note

    note1 = Note(
        user_id=test_user.id,
        raw_transcript="Project alpha meeting",
        summary="Meeting about alpha",
        tag="Work",
        processing_status="completed",
    )
    note2 = Note(
        user_id=test_user.id,
        raw_transcript="Beta test results",
        summary="Testing beta",
        tag="Work",
        processing_status="completed",
    )
    note3 = Note(
        user_id=test_user.id,
        raw_transcript="Grocery shopping",
        summary="Buy groceries",
        tag="Personal",
        processing_status="completed",
    )
    session.add_all([note1, note2, note3])
    session.commit()

    notes, total = note_service.list_notes_advanced(
        user_id=test_user.id, search="meeting"
    )
    assert total == 1
    assert len(notes) == 1
    assert "meeting" in notes[0].raw_transcript.lower()


def test_list_notes_advanced_filter_by_tag(session, test_user):
    """Test filtering by tag in list_notes_advanced."""
    note_service = NoteService(session)

    from app.models import Note

    note1 = Note(
        user_id=test_user.id,
        raw_transcript="Work item",
        summary="Work summary",
        tag="Work",
        processing_status="completed",
    )
    note2 = Note(
        user_id=test_user.id,
        raw_transcript="Personal item",
        summary="Personal summary",
        tag="Personal",
        processing_status="completed",
    )
    session.add_all([note1, note2])
    session.commit()

    notes, total = note_service.list_notes_advanced(user_id=test_user.id, tag="Work")
    assert total == 1
    assert len(notes) == 1
    assert notes[0].tag == "Work"


def test_list_notes_advanced_archived_filter(session, test_user):
    """Test archived filter in list_notes_advanced."""
    note_service = NoteService(session)

    from app.models import Note

    note1 = Note(
        user_id=test_user.id,
        raw_transcript="Active note",
        summary="Active summary",
        tag="Work",
        processing_status="completed",
        archived=False,
    )
    note2 = Note(
        user_id=test_user.id,
        raw_transcript="Archived note",
        summary="Archived summary",
        tag="Work",
        processing_status="completed",
        archived=True,
    )
    session.add_all([note1, note2])
    session.commit()

    notes, total = note_service.list_notes_advanced(
        user_id=test_user.id, archived_only=True
    )
    assert total == 1
    assert len(notes) == 1
    assert notes[0].archived is True


def test_list_notes_advanced_sorting(session, test_user):
    """Test sorting in list_notes_advanced."""
    note_service = NoteService(session)

    from app.models import Note

    note1 = Note(
        user_id=test_user.id,
        raw_transcript="Third note",
        summary="Summary C",
        tag="Work",
        processing_status="completed",
        created_at=datetime(2024, 1, 3, tzinfo=UTC),
    )
    note2 = Note(
        user_id=test_user.id,
        raw_transcript="First note",
        summary="Summary A",
        tag="Work",
        processing_status="completed",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    note3 = Note(
        user_id=test_user.id,
        raw_transcript="Second note",
        summary="Summary B",
        tag="Work",
        processing_status="completed",
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
    )
    session.add_all([note1, note2, note3])
    session.commit()

    notes, total = note_service.list_notes_advanced(
        user_id=test_user.id, sort_by="created_at", sort_order="asc"
    )
    assert total == 3
    assert len(notes) == 3
    assert notes[0].summary == "Summary A"
    assert notes[2].summary == "Summary C"
