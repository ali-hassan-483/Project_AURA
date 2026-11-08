import logging
import httpx
from typing import List, Dict, Optional
from services.ai.base import BaseLLMProvider
from config.settings import settings

logger = logging.getLogger(__name__)

class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__(name="ollama", model_name=model_name or settings.OLLAMA_MODEL)
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    async def is_available(self) -> bool:
        """Pings local Ollama server tags endpoint to check availability"""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.75, 
        max_tokens: int = 800
    ) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            },
            "stream": False
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.error("Ollama error (%s): %s", resp.status_code, resp.text)
                raise RuntimeError(f"Ollama error {resp.status_code}: {resp.text}")
            
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()
