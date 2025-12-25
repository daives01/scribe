"""Database engine and session management."""

from collections.abc import Generator

import sqlite_vec
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# Create engine with SQLite
connect_args = {"check_same_thread": False}
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=connect_args,
)


def _load_sqlite_vec(dbapi_conn, _connection_record):
    """Load sqlite-vec extension when connection is created."""
    dbapi_conn.enable_load_extension(True)
    sqlite_vec.load(dbapi_conn)
    dbapi_conn.enable_load_extension(False)


# Register event listener to load sqlite-vec on each connection
event.listen(engine, "connect", _load_sqlite_vec)


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Get a database session."""
    with Session(engine) as session:
        yield session
