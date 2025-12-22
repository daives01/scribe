"""Search endpoints."""

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, SessionDep, UserSettingsDep
from app.schemas.note import NoteResponse
from app.schemas.search import SearchRequest, SearchResponse
from app.services.note_service import NoteService

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
    user_settings: UserSettingsDep,
) -> SearchResponse:
    """
    Search notes using semantic similarity.

    Returns notes most relevant to the query based on vector embeddings.
    """
    note_service = NoteService(session)
    results = await note_service.search_notes_semantic(
        user_id=current_user.id,
        query=request.query,
        user_settings=user_settings,
        limit=request.limit,
    )
    return SearchResponse(results=[NoteResponse.model_validate(n) for n in results])
