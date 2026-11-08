import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Project AURA"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    SECRET_KEY: str = Field(default="aura_secret_jwt_key_change_in_production_89324792384729384")
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "aura2026"
    BASE_URL: str = "http://localhost:8000"

    # Database
    DATABASE_PATH: str = str(BASE_DIR / "data" / "aura.db")

    # WhatsApp Business Cloud API
    WHATSAPP_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: str = "aura_verify_token_2026"
    WHATSAPP_APP_SECRET: Optional[str] = None
    WHATSAPP_API_VERSION: str = "v21.0"

    # AI LLM Providers
    PRIMARY_AI_PROVIDER: str = "groq"  # "groq", "gemini", "ollama", "openrouter"
    FALLBACK_AI_PROVIDERS: List[str] = ["gemini", "ollama", "openrouter"]
    
    # Provider Keys (Free Tiers Supported)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"  # Free & powerful on Groq
    
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"      # Free tier on Google AI Studio
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3:latest"
    
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = "meta-llama/llama-3.3-70b-instruct:free"

    # Custom / Dedicated External AI API (Any OpenAI-compatible endpoint)
    CUSTOM_AI_API_KEY: Optional[str] = None
    CUSTOM_AI_BASE_URL: str = "https://api.openai.com/v1"
    CUSTOM_AI_MODEL: str = "gpt-4o-mini"

    # Voice (TTS & STT)
    TTS_DEFAULT_VOICE_URDU: str = "ur-PK-UzmaNeural"
    TTS_DEFAULT_VOICE_ENGLISH: str = "en-US-AvaNeural"
    TTS_DEFAULT_VOICE_HINGLISH: str = "hi-IN-SwaraNeural"
    TTS_RATE: str = "+0%"
    TTS_PITCH: str = "+0Hz"
    
    # STT Engine
    WHISPER_MODEL_SIZE: str = "base"  # "tiny", "base", "small"
    WHISPER_DEVICE: str = "cpu"      # "cpu" or "cuda"

    # Image Generation
    IMAGE_PROVIDER: str = "pollinations"  # "pollinations", "huggingface", "local_sd"
    IMAGE_MODEL: str = "flux"            # "flux", "flux-realism", "turbo"
    IMAGE_SEED: int = 789234
    IMAGE_WIDTH: int = 768
    IMAGE_HEIGHT: int = 1024
    HF_API_KEY: Optional[str] = None

    # Proactive Automation
    PROACTIVE_MESSAGING_ENABLED: bool = True
    PROACTIVE_MIN_INTERVAL_HOURS: int = 4
    PROACTIVE_MORNING_HOUR: int = 9   # 9:00 AM
    PROACTIVE_NIGHT_HOUR: int = 23    # 11:00 PM

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
