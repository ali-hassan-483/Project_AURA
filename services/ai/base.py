from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseLLMProvider(ABC):
    def __init__(self, name: str, model_name: str):
        self.name = name
        self.model_name = model_name

    @abstractmethod
    async def is_available(self) -> bool:
        """Checks if provider has required configuration or is reachable"""
        pass

    @abstractmethod
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.75, 
        max_tokens: int = 800
    ) -> str:
        """Generates reply given message history formatted as [{role, content}]"""
        pass
