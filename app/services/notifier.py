import httpx
import os

class Notifier:
    def __init__(self, hass_url=None, token=None):
        self.hass_url = hass_url or os.getenv("HASS_URL")
        self.token = token or os.getenv("HASS_TOKEN")

    async def notify(self, title: str, message: str):
        """
        Sends a notification to Home Assistant.
        """
        if not self.hass_url or not self.token:
            print("Home Assistant notification skipped: HASS_URL or HASS_TOKEN not set.")
            return

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "title": title,
            "message": message,
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.hass_url}/api/services/persistent_notification/create",
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
                return True
            except Exception as e:
                print(f"Failed to send notification: {e}")
                return False

notifier = Notifier()

