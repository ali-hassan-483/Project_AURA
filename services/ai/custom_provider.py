import os
import logging
import httpx
from typing import List, Dict, Optional
from services.ai.base import BaseLLMProvider
from config.settings import settings

logger = logging.getLogger(__name__)

class CustomOpenAICompatibleProvider(BaseLLMProvider):
    """
    Enables the user to plug in ANY custom, private, or third-party AI API
    that follows the standard OpenAI chat completions spec (e.g. DeepSeek,
    Together.ai, vLLM, FastChat, LM Studio, Anyscale, OpenRouter, etc.).
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        super().__init__(name="custom", model_name=model_name or "default-model")
        self.api_key = api_key or os.getenv("CUSTOM_AI_API_KEY", "")
        self.base_url = (base_url or os.getenv("CUSTOM_AI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.endpoint = f"{self.base_url}/chat/completions"

    async def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 3)

    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.75, 
        max_tokens: int = 800
    ) -> str:
        if not await self.is_available():
            raise ValueError("Custom API key is missing or invalid.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(self.endpoint, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error("Custom AI provider error (%s): %s", resp.status_code, resp.text)
                raise RuntimeError(f"Custom AI error {resp.status_code}: {resp.text}")
            
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
