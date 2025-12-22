import logging

from sqlmodel import Session, select

from app.config import settings
from app.database import engine
from app.models.note import Note
from app.models.user import UserSettings
from app.services.homeassistant_service import get_home_assistant_service

logger = logging.getLogger(__name__)


async def send_note_notification(note_id: int) -> None:
    with Session(engine) as session:
        note = session.get(Note, note_id)
        if not note:
            logger.error(f"Note {note_id} not found")
            return

        user_settings = session.exec(
            select(UserSettings).where(UserSettings.user_id == note.user_id)
        ).first()
        if not user_settings:
            logger.error(f"User settings not found for user {note.user_id}")
            return

        if not all(
            [
                user_settings.homeassistant_url,
                user_settings.homeassistant_token,
                user_settings.homeassistant_device,
            ]
        ):
            logger.warning(f"Home Assistant not configured for user {note.user_id}")
            return

        title = f"Scribe: {note.tag}" if note.tag else "Scribe Note Reminder"
        message = (
            note.summary
            or (
                note.raw_transcript[:200] + "..."
                if len(note.raw_transcript or "") > 200
                else note.raw_transcript
            )
            or "New note reminder"
        )

        # Generate URL for the note
        note_url = f"{settings.base_url}/web/notes/{note_id}"

        try:
            async with get_home_assistant_service(
                str(user_settings.homeassistant_url), user_settings.homeassistant_token
            ) as ha_service:
                await ha_service.send_notification(
                    device=user_settings.homeassistant_device,
                    message=message,
                    title=title,
                    url=note_url,
                )
            logger.info(f"Sent notification for note {note_id}")
        except Exception as e:
            logger.error(f"Failed to send notification for note {note_id}: {e}")
