from typing import Optional
from fastapi import APIRouter, Cookie, Request
from fastapi.responses import StreamingResponse
from app.utils.events import event_manager
from app.api.routes.web import get_current_user_from_cookie, get_db
from sqlmodel import Session
import asyncio

router = APIRouter(tags=["events"])

@router.get("/api/events")
async def events_endpoint(
    request: Request,
    access_token: Optional[str] = Cookie(default=None),
):
    """SSE endpoint for real-time updates."""
    # We need a session to get the user
    from app.database import engine
    with Session(engine) as session:
        user = await get_current_user_from_cookie(request, session, access_token)
        if not user:
            return StreamingResponse(iter(["event: error\ndata: unauthorized\n\n"]), media_type="text/event-stream")
        user_id = user.id

    return StreamingResponse(
        event_manager.subscribe(user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering for Nginx
        }
    )
