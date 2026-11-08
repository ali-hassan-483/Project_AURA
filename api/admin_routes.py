import logging
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Body, UploadFile, File
from core.database import db
from core.security import create_admin_jwt, verify_admin_credentials
from services.ai.router import ai_router
from services.voice.tts_service import tts_service
from services.image.generator import image_service
from services.image.identity import identity_manager
from services.memory.memory_service import memory_service
from config.settings import settings

logger = logging.getLogger(__name__)
admin_router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])

# ---------------- AUTHENTICATION ----------------
@admin_router.post("/login")
async def login(credentials: Dict[str, str] = Body(...)):
    username = credentials.get("username", "")
    password = credentials.get("password", "")

    if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
        token = create_admin_jwt(username)
        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            "username": username
        }
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

# ---------------- METRICS & SYSTEM HEALTH ----------------
@admin_router.get("/metrics")
async def get_metrics(current_user: Dict = Depends(verify_admin_credentials)):
    metrics = db.get_dashboard_metrics()
    providers = await ai_router.get_active_providers()
    metrics["active_providers"] = providers
    metrics["primary_provider"] = ai_router.primary_provider
    metrics["app_version"] = settings.APP_VERSION
    return metrics

# ---------------- USER & CONVERSATIONS ----------------
@admin_router.get("/users")
async def get_users(current_user: Dict = Depends(verify_admin_credentials)):
    return db.get_all_users()

@admin_router.get("/conversations/{user_id}")
async def get_conversations(user_id: int, current_user: Dict = Depends(verify_admin_credentials)):
    return db.get_recent_messages(user_id=user_id, limit=50)

@admin_router.delete("/users/{user_id}/purge")
async def purge_user_data(user_id: int, current_user: Dict = Depends(verify_admin_credentials)):
    """Privacy feature: permanently erases all user conversations, memories, and records"""
    success = db.delete_user_data(user_id)
    return {"success": success, "message": f"User {user_id} and all related data purged permanently."}

# ---------------- LONG-TERM MEMORY ----------------
@admin_router.get("/memories/{user_id}")
async def get_user_memories(user_id: int, current_user: Dict = Depends(verify_admin_credentials)):
    return memory_service.get_all_user_memories(user_id=user_id)

@admin_router.post("/memories")
async def create_memory(data: Dict[str, Any] = Body(...), current_user: Dict = Depends(verify_admin_credentials)):
    user_id = data.get("user_id")
    category = data.get("category", "personal_info")
    key = data.get("key", "").strip()
    value = data.get("value", "").strip()
    importance = int(data.get("importance", 3))

    if not user_id or not key or not value:
        raise HTTPException(status_code=400, detail="Missing required memory fields")

    db.set_memory(user_id, category, key, value, importance)
    return {"success": True, "message": "Memory saved successfully"}

@admin_router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: int, current_user: Dict = Depends(verify_admin_credentials)):
    db.delete_memory(memory_id)
    return {"success": True, "message": "Memory deleted"}

# ---------------- CHARACTER PERSONA SETTINGS ----------------
@admin_router.get("/character")
async def get_character(current_user: Dict = Depends(verify_admin_credentials)):
    return db.get_character_settings()

@admin_router.put("/character")
async def update_character(data: Dict[str, Any] = Body(...), current_user: Dict = Depends(verify_admin_credentials)):
    success = db.update_character_settings(**data)
    return {"success": success, "settings": db.get_character_settings()}

# ---------------- AI PROVIDERS & TESTING ----------------
@admin_router.get("/providers")
async def get_providers(current_user: Dict = Depends(verify_admin_credentials)):
    statuses = await ai_router.get_active_providers()
    return {
        "primary": ai_router.primary_provider,
        "fallbacks": ai_router.fallback_providers,
        "statuses": statuses
    }

@admin_router.post("/providers/set-primary")
async def set_primary_provider(data: Dict[str, str] = Body(...), current_user: Dict = Depends(verify_admin_credentials)):
    provider = data.get("provider")
    if provider in ai_router.providers:
        ai_router.set_primary_provider(provider)
        return {"success": True, "primary": ai_router.primary_provider}
    raise HTTPException(status_code=400, detail="Invalid provider")

# ---------------- VOICE STUDIO ----------------
@admin_router.get("/voice/list")
async def list_voices():
    return await tts_service.get_available_voices()

@admin_router.post("/voice/preview")
async def preview_voice(data: Dict[str, str] = Body(...)):
    text = data.get("text", "Hello jaan, I'm Aylin! How are you?")
    voice = data.get("voice", settings.TTS_DEFAULT_VOICE_URDU)
    rate = data.get("rate", "+0%")
    pitch = data.get("pitch", "+0Hz")

    mp3_path, ogg_path, file_id = await tts_service.generate_speech(text, voice=voice, rate=rate, pitch=pitch)
    return {
        "audio_url": f"/static/audio/{file_id}.mp3",
        "voice": voice,
        "text": text
    }

# ---------------- IMAGE GENERATOR STUDIO ----------------
@admin_router.post("/image/generate")
async def generate_image(data: Dict[str, Any] = Body(...)):
    prompt = data.get("prompt", "taking a sweet selfie smiling")
    seed_offset = int(data.get("seed_offset", 0))

    file_path, filename, composed_prompt = await image_service.generate_character_image(
        scene_hint=prompt,
        seed_offset=seed_offset
    )
    return {
        "image_url": f"/static/images/generated/{filename}",
        "composed_prompt": composed_prompt,
        "filename": filename
    }

# ---------------- REFERENCE PHOTO UPLOAD ----------------
@admin_router.post("/character/upload-reference")
async def upload_reference_photo(file: UploadFile = File(...)):
    """
    Admin uploads Aylin's reference photo for consistent face generation.
    No auth required since image upload is low-risk and admin-panel-only.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed (jpg/png/webp)")

    image_bytes = await file.read()
    if len(image_bytes) < 500:
        raise HTTPException(status_code=400, detail="Image file is too small or corrupted")

    # Save as Aylin reference
    ref_path = Path("static/images/aylin_reference.jpg")
    ref_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert any format to JPEG using PIL
    try:
        from PIL import Image as PILImage
        import io
        img = PILImage.open(io.BytesIO(image_bytes)).convert("RGB")
        img.save(str(ref_path), "JPEG", quality=95)
    except Exception:
        with open(ref_path, "wb") as f:
            f.write(image_bytes)

    # Update face anchor
    face_description = (
        "RAW photo, (photorealistic:1.4), beautiful 21-year-old South Asian woman, "
        "same exact face as the reference photo, identical facial features, "
        "warm hazel brown almond eyes, long natural wavy dark brown hair, "
        "subtle beauty mark left cheek, soft natural lips, "
        "flawless warm golden skin, real skin texture and pores"
    )
    identity_manager.set_reference_description(face_description)

    return {
        "success": True,
        "message": "Reference photo saved! All future images will use this face.",
        "reference_url": "/static/images/aylin_reference.jpg"
    }

# ---------------- LIVE SIMULATOR / WEB CHAT ----------------
@admin_router.get("/simulator/history")
async def get_simulator_history(phone: str = "+923001234567"):
    """Fetches chat history for the simulator user so previous messages are never lost"""
    user = db.get_or_create_user(phone_number=phone)
    messages = db.get_recent_messages(user_id=user["id"], limit=50)
    return {"messages": messages, "user": user}

@admin_router.post("/simulator/chat")
async def simulate_chat(data: Dict[str, Any] = Body(...)):
    """
    Allows developers, users, and mobile apps to chat with Aura directly
    without requiring prior admin login.
    """
    user_message = data.get("message", "").strip()
    user_phone = data.get("phone", "+923001234567")
    user_name = data.get("name", "Simulator User")

    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Get or create simulator user
    user = db.get_or_create_user(phone_number=user_phone, name=user_name)
    user_id = user["id"]

    # Store user message
    db.add_message(user_id=user_id, sender="user", content=user_message, message_type="text")

    # Extract memory
    await memory_service.process_and_store_message(user_id=user_id, user_message=user_message)

    # Context & Generation
    memories = memory_service.get_relevant_memories(user_id=user_id, query=user_message)
    recent = db.get_recent_messages(user_id=user_id, limit=14)
    character = db.get_character_settings()

    prompt_messages = ai_router.build_prompt_context(
        system_prompt=character.get("system_prompt", ""),
        user_info=user,
        memories=memories,
        recent_messages=recent
    )

    raw_response, provider = await ai_router.generate(prompt_messages)
    clean_reply, img_prompt, has_voice = ai_router.parse_actions(raw_response)

    image_url = None
    voice_url = None

    if img_prompt:
        try:
            _, filename, _ = await image_service.generate_character_image(img_prompt)
            image_url = f"/static/images/generated/{filename}"
        except Exception as e:
            logger.error("Simulator image error: %s", e)

    if has_voice:
        try:
            _, _, file_id = await tts_service.generate_speech(clean_reply)
            voice_url = f"/static/audio/{file_id}.mp3"
        except Exception as e:
            logger.error("Simulator voice error: %s", e)

    db.add_message(
        user_id=user_id,
        sender="assistant",
        content=clean_reply,
        message_type="image" if image_url else ("voice" if voice_url else "text"),
        media_url=image_url or voice_url
    )

    return {
        "reply": clean_reply,
        "provider": provider,
        "has_image": bool(image_url),
        "image_url": image_url,
        "image_prompt": img_prompt,
        "has_voice": bool(voice_url),
        "voice_url": voice_url,
        "memories_used": len(memories)
    }
