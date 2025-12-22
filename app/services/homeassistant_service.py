import logging
from typing import Any, Dict, Optional

import httpx

from app.utils.exceptions import ServiceError

logger = logging.getLogger(__name__)


class HomeAssistantService:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def send_notification(
        self,
        device: str,
        message: str,
        title: Optional[str] = None,
        url: Optional[str] = None,
    ) -> bool:
        api_url = f"{self.base_url}/api/services/notify/mobile_app_{device}"
        payload: Dict[str, Any] = {"message": message}
        if title:
            payload["title"] = title

        # Add URL for clickable notifications
        if url:
            payload["data"] = {
                "url": url,  # iOS
                "clickAction": url,  # Android
            }

        try:
            response = await self.client.post(api_url, json=payload)
            response.raise_for_status()
            logger.info(f"Sent notification to {device}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"HA API error: {e.response.status_code} for device {device}")
            raise ServiceError(f"Home Assistant API error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"HA request error for device {device}: {e}")
            raise ServiceError("Failed to connect to Home Assistant")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            raise ServiceError("Unexpected error")

    async def test_connection(self) -> bool:
        url = f"{self.base_url}/api/"
        try:
            response = await self.client.get(url)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Test connection failed to {url}: {e}")
            return False


def get_home_assistant_service(base_url: str, token: str) -> HomeAssistantService:
    return HomeAssistantService(base_url, token)
