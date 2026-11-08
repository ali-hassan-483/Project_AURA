import logging
import httpx
from typing import Dict, Any, Optional
from config.settings import settings

logger = logging.getLogger(__name__)

class WhatsAppCloudAPI:
    def __init__(
        self,
        token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
        api_version: Optional[str] = None
    ):
        self.token = token or settings.WHATSAPP_TOKEN
        self.phone_number_id = phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID
        self.api_version = api_version or settings.WHATSAPP_API_VERSION
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def is_configured(self) -> bool:
        return bool(self.token and self.phone_number_id)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def mark_message_as_read(self, message_id: str) -> bool:
        """Sends read receipt to WhatsApp for delivered message"""
        if not self.is_configured():
            return False
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=self._headers(), json=payload)
                return resp.status_code == 200
        except Exception as e:
            logger.warning("Failed to mark message read: %s", e)
            return False

    async def send_text_message(self, recipient_phone: str, text: str) -> Dict[str, Any]:
        """Sends text message to WhatsApp user"""
        if not self.is_configured():
            logger.warning("WhatsApp API not configured. Message simulated for %s: %s", recipient_phone, text[:50])
            return {"simulated": True, "status": "sent"}

        url = f"{self.base_url}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_phone,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": text
            }
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)
            if resp.status_code not in [200, 201]:
                logger.error("WhatsApp Send Text Error (%s): %s", resp.status_code, resp.text)
                raise RuntimeError(f"WhatsApp Error: {resp.text}")
            return resp.json()

    async def send_image_message(
        self,
        recipient_phone: str,
        image_url: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sends image with optional caption"""
        if not self.is_configured():
            logger.warning("WhatsApp API not configured. Simulated image sent to %s: %s", recipient_phone, image_url)
            return {"simulated": True, "status": "sent"}

        url = f"{self.base_url}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_phone,
            "type": "image",
            "image": {
                "link": image_url
            }
        }
        if caption:
            payload["image"]["caption"] = caption

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)
            if resp.status_code not in [200, 201]:
                logger.error("WhatsApp Send Image Error (%s): %s", resp.status_code, resp.text)
                raise RuntimeError(f"WhatsApp Error: {resp.text}")
            return resp.json()

    async def send_voice_message(self, recipient_phone: str, audio_url: str) -> Dict[str, Any]:
        """Sends native WhatsApp voice note"""
        if not self.is_configured():
            logger.warning("WhatsApp API not configured. Simulated voice note sent to %s: %s", recipient_phone, audio_url)
            return {"simulated": True, "status": "sent"}

        url = f"{self.base_url}/{self.phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_phone,
            "type": "audio",
            "audio": {
                "link": audio_url
            }
        }
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)
            if resp.status_code not in [200, 201]:
                logger.error("WhatsApp Send Voice Error (%s): %s", resp.status_code, resp.text)
                raise RuntimeError(f"WhatsApp Error: {resp.text}")
            return resp.json()

    async def download_media(self, media_id: str) -> bytes:
        """Retrieves and downloads binary media (e.g. voice notes) from Meta Graph API"""
        if not self.is_configured():
            raise ValueError("WhatsApp API not configured.")

        # Step 1: Get media URL
        url = f"{self.base_url}/{media_id}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            meta_resp = await client.get(url, headers={"Authorization": f"Bearer {self.token}"})
            if meta_resp.status_code != 200:
                raise RuntimeError(f"Failed to fetch media metadata: {meta_resp.text}")
            download_url = meta_resp.json().get("url")

            # Step 2: Download raw binary
            dl_resp = await client.get(download_url, headers={"Authorization": f"Bearer {self.token}"})
            if dl_resp.status_code != 200:
                raise RuntimeError(f"Failed to download media bytes: {dl_resp.status_code}")
            return dl_resp.content

whatsapp_client = WhatsAppCloudAPI()
