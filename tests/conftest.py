"""Pytest configuration and fixtures."""

from collections.abc import Generator
from typing import cast

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.api.deps import get_db
from app.main import app
from app.models import Note, User, UserSettings
from app.services.auth_service import create_access_token, get_password_hash

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite://"


@pytest.fixture(name="engine")
def engine_fixture():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine


@pytest.fixture(name="session")
def session_fixture(engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database override."""

    def get_session_override() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = get_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Create default settings
    settings = UserSettings(user_id=cast(int, user.id))
    session.add(settings)
    session.commit()

    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(test_user: User) -> dict[str, str]:
    """Create authentication headers for test user."""
    token = create_access_token(cast(int, test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="test_note")
def test_note_fixture(session: Session, test_user: User) -> Note:
    """Create a test note."""
    note = Note(
        user_id=cast(int, test_user.id),
        raw_transcript="This is a test note about Python programming.",
        summary="Test Python note",
        tag="Work",
        processing_status="completed",
    )
    session.add(note)
    session.commit()
    session.refresh(note)
    return note
