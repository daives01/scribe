"""Search and RAG endpoints."""

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, SessionDep, UserSettingsDep
from app.schemas.note import NoteResponse
from app.schemas.search import AskRequest, AskResponse, SearchRequest, SearchResponse
from app.services.note_service import NoteService
from app.services.ollama_service import get_ollama_service

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
    return SearchResponse(
        results=[NoteResponse.model_validate(n) for n in results]
    )


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
    user_settings: UserSettingsDep,
) -> AskResponse:
    """
    Ask a question and get an AI-generated answer based on your notes.

    Uses RAG (Retrieval Augmented Generation) to find relevant notes
    and generate an answer using the configured LLM.
    """
    note_service = NoteService(session)

    # Find relevant notes
    results = await note_service.search_notes_semantic(
        user_id=current_user.id,
        query=request.question,
        user_settings=user_settings,
        limit=5,
    )

    # Filter by tag if specified
    if request.tag_filter:
        results = [n for n in results if n.tag == request.tag_filter]

    # If no relevant notes found
    if not results:
        return AskResponse(
            answer="I couldn't find any relevant notes to answer your question.",
            sources=[],
        )

    # Get answer from LLM
    ollama = get_ollama_service(
        base_url=user_settings.ollama_url,
        model=user_settings.ollama_model,
        embedding_model=user_settings.ollama_embedding_model,
        api_key=user_settings.ollama_api_key,
    )
    answer = await ollama.answer_question(request.question, results)

    return AskResponse(
        answer=answer,
        sources=[NoteResponse.model_validate(n) for n in results],
    )
