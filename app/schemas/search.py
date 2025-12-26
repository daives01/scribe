"""Search and RAG schemas."""

from pydantic import BaseModel

from app.schemas.note import NoteResponse


class SearchRequest(BaseModel):
    """Schema for semantic search request."""

    query: str
    limit: int = 10


class SearchResultItem(BaseModel):
    """Schema for a single search result with similarity score."""

    note: NoteResponse
    similarity: float


class SearchResponse(BaseModel):
    """Schema for search results."""

    results: list[SearchResultItem]
