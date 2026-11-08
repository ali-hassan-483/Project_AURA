from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class UserModel(BaseModel):
    id: Optional[int] = None
    phone_number: str
    name: Optional[str] = None
    nickname: Optional[str] = None
    language_pref: str = "roman_urdu"
    relationship_level: int = 1
    intimacy_score: int = 50
    timezone: str = "UTC"
    proactive_enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class MessageModel(BaseModel):
    id: Optional[int] = None
    user_id: int
    sender: str  # "user" or "assistant"
    message_type: str = "text"  # "text", "voice", "image"
    raw_content: str
    translated_content: Optional[str] = None
    media_url: Optional[str] = None
    tokens_used: int = 0
    created_at: Optional[datetime] = None

class MemoryModel(BaseModel):
    id: Optional[int] = None
    user_id: int
    category: str  # "personal", "preference", "romantic", "event", "interest", "custom"
    memory_key: str
    memory_value: str
    importance: int = 3  # 1 to 5
    confidence: float = 1.0
    last_accessed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

class CharacterConfigModel(BaseModel):
    id: Optional[int] = None
    name: str = "Aura"
    age: int = 21
    archetype: str = "Loving Companion"
    system_prompt: str
    identity_prompt: str
    negative_prompt: str
    default_voice_urdu: str = "ur-PK-UzmaNeural"
    default_voice_english: str = "en-US-AvaNeural"
    seed: int = 789234
    is_active: bool = True
    updated_at: Optional[datetime] = None

class ActivityLogModel(BaseModel):
    id: Optional[int] = None
    event_type: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    user_phone: str
    message: str
    message_type: str = "text"  # "text" or "voice"
    audio_base64: Optional[str] = None

class ChatResponse(BaseModel):
    user_phone: str
    reply_text: str
    has_image: bool = False
    image_url: Optional[str] = None
    image_prompt: Optional[str] = None
    has_voice: bool = False
    voice_url: Optional[str] = None
    provider_used: str = "unknown"
