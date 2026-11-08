import logging
import httpx
from typing import List, Dict, Optional
from services.ai.base import BaseLLMProvider
from config.settings import settings

logger = logging.getLogger(__name__)

class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__(name="gemini", model_name=model_name or settings.GEMINI_MODEL)
        self.api_key = api_key or settings.GEMINI_API_KEY

    async def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.75, 
        max_tokens: int = 800
    ) -> str:
        if not await self.is_available():
            raise ValueError("Google Gemini API key is missing or invalid.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        
        # Convert standard OpenAI/Chat format to Gemini contents & system_instruction
        system_instruction = None
        contents = []

        for m in messages:
            role = m["role"]
            content = m["content"]
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": 0.95
            }
        }
        if system_instruction:
            payload["system_instruction"] = system_instruction

        async with httpx.AsyncClient(timeout=35.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.error("Gemini API error (%s): %s", resp.status_code, resp.text)
                raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")
            
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("Gemini returned empty candidate list.")
            
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise RuntimeError("Gemini candidate has no parts.")
            
            return parts[0].get("text", "").strip()
