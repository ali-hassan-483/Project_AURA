import logging
import httpx
from typing import List, Dict, Optional
from services.ai.base import BaseLLMProvider
from config.settings import settings

logger = logging.getLogger(__name__)

class GroqProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__(name="groq", model_name=model_name or settings.GROQ_MODEL)
        self.api_key = api_key or settings.GROQ_API_KEY
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

    async def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.75, 
        max_tokens: int = 800
    ) -> str:
        if not await self.is_available():
            raise ValueError("Groq API key is missing or invalid.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.95
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.endpoint, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error("Groq API error (%s): %s", resp.status_code, resp.text)
                raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text}")
            
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
