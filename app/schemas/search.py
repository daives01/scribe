"""Search and RAG schemas."""

from pydantic import BaseModel

from app.schemas.note import NoteResponse


class SearchRequest(BaseModel):
    """Schema for semantic search request."""

    query: str
    limit: int = 10


class SearchResponse(BaseModel):
    """Schema for search results."""

    results: list[NoteResponse]


class AskRequest(BaseModel):
    """Schema for RAG question request."""

    question: str
    tag_filter: str | None = None


class AskResponse(BaseModel):
    """Schema for RAG answer response."""

    answer: str
    sources: list[NoteResponse]
