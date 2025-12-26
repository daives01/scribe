"""Search endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import SessionDep, UserSettingsDep, get_current_user_id
from app.schemas.note import NoteResponse
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from app.services.note_service import NoteService

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    session: SessionDep,
    user_id: Annotated[int, Depends(get_current_user_id)],
    user_settings: UserSettingsDep,
) -> SearchResponse:
    """
    Search notes using semantic similarity.

    Returns notes most relevant to the query based on vector embeddings.
    """
    note_service = NoteService(session)
    notes, similarities = await note_service.search_notes_semantic(
        user_id=user_id,
        query=request.query,
        user_settings=user_settings,
        limit=request.limit,
    )

    result_items = []
    for note, similarity in zip(notes, similarities):
        note_response = NoteResponse.model_validate(note)
        result_items.append(SearchResultItem(note=note_response, similarity=similarity))

    return SearchResponse(results=result_items)
