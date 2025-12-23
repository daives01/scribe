"""Tests for notes endpoints."""

from fastapi.testclient import TestClient


def test_list_notes_empty(client: TestClient, auth_headers):
    """Test listing notes when empty."""
    response = client.get("/api/notes", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["notes"] == []
    assert data["total"] == 0


def test_list_notes_with_notes(client: TestClient, auth_headers, test_note):
    """Test listing notes with existing notes."""
    response = client.get("/api/notes", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["notes"]) == 1
    assert data["total"] == 1
    assert data["notes"][0]["raw_transcript"] == test_note.raw_transcript


def test_get_note(client: TestClient, auth_headers, test_note):
    """Test getting a single note."""
    response = client.get(f"/api/notes/{test_note.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_note.id
    assert data["raw_transcript"] == test_note.raw_transcript
    assert data["summary"] == test_note.summary
    assert data["tag"] == test_note.tag


def test_get_note_not_found(client: TestClient, auth_headers):
    """Test getting a non-existent note."""
    response = client.get("/api/notes/99999", headers=auth_headers)
    assert response.status_code == 404


def test_get_note_no_auth(client: TestClient, test_note):
    """Test getting a note without authentication."""
    response = client.get(f"/api/notes/{test_note.id}")
    assert response.status_code == 401


def test_update_note_tag(client: TestClient, auth_headers, test_note):
    """Test updating a note's tag."""
    response = client.patch(
        f"/api/notes/{test_note.id}",
        headers=auth_headers,
        json={"tag": "Personal"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tag"] == "Personal"
    # Transcript should remain unchanged
    assert data["raw_transcript"] == test_note.raw_transcript


def test_update_note_summary(client: TestClient, auth_headers, test_note):
    """Test updating a note's summary."""
    new_summary = "This is an updated summary."
    response = client.patch(
        f"/api/notes/{test_note.id}",
        headers=auth_headers,
        json={"summary": new_summary},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == new_summary
    # Transcript should remain unchanged
    assert data["raw_transcript"] == test_note.raw_transcript


def test_update_note_transcript(client: TestClient, auth_headers, test_note):
    """Test updating a note's transcript."""
    new_transcript = "This is an updated transcript."
    response = client.patch(
        f"/api/notes/{test_note.id}",
        headers=auth_headers,
        json={"raw_transcript": new_transcript},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["raw_transcript"] == new_transcript
    # Status should be pending for reprocessing
    assert data["processing_status"] == "pending"


def test_delete_note(client: TestClient, auth_headers, test_note):
    """Test deleting a note."""
    response = client.delete(f"/api/notes/{test_note.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify note is deleted
    response = client.get(f"/api/notes/{test_note.id}", headers=auth_headers)
    assert response.status_code == 404


def test_delete_note_not_found(client: TestClient, auth_headers):
    """Test deleting a non-existent note."""
    response = client.delete("/api/notes/99999", headers=auth_headers)
    assert response.status_code == 404


def test_pagination(client: TestClient, auth_headers, session, test_user):
    """Test note list pagination."""
    from app.models import Note

    # Create multiple notes
    for i in range(15):
        note = Note(
            user_id=test_user.id,
            raw_transcript=f"Test note {i}",
            processing_status="completed",
        )
        session.add(note)
    session.commit()

    # Test first page
    response = client.get("/api/notes?skip=0&limit=10", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["notes"]) == 10
    assert data["total"] == 15

    # Test second page
    response = client.get("/api/notes?skip=10&limit=10", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["notes"]) == 5
    assert data["total"] == 15
