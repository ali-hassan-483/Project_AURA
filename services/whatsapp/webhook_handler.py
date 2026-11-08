import os
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from core.database import db
from services.ai.router import ai_router
from services.memory.memory_service import memory_service
from services.voice.tts_service import tts_service
from services.voice.stt_service import stt_service
from services.image.generator import image_service
from services.whatsapp.cloud_api import whatsapp_client
from config.settings import settings

logger = logging.getLogger(__name__)

TEMP_AUDIO_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "temp"
TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

class WebhookHandler:
    def __init__(self):
        self.db = db
        self.ai = ai_router
        self.memory = memory_service
        self.tts = tts_service
        self.stt = stt_service
        self.image = image_service
        self.whatsapp = whatsapp_client

    async def process_incoming_payload(self, payload: Dict[str, Any]):
        """
        Main entry point for incoming WhatsApp Webhook POST events.
        Parses messages and triggers end-to-end processing pipeline.
        """
        entries = payload.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                contacts = value.get("contacts", [])
                
                # Extract contact profile if present
                sender_name = None
                if contacts:
                    sender_name = contacts[0].get("profile", {}).get("name")

                for msg in messages:
                    await self._handle_single_message(msg, sender_name)

    async def _handle_single_message(self, message: Dict[str, Any], sender_name: Optional[str] = None):
        sender_phone = message.get("from")
        message_id = message.get("id")
        msg_type = message.get("type", "text")

        if not sender_phone:
            logger.warning("Received message without sender phone.")
            return

        # 1. Mark message as read on WhatsApp
        if message_id:
            await self.whatsapp.mark_message_as_read(message_id)

        # 2. Identify or create User in Database
        user = self.db.get_or_create_user(phone_number=sender_phone, name=sender_name)
        user_id = user["id"]

        user_text = ""
        is_inbound_voice = False

        # 3. Handle message types (text or voice note)
        if msg_type == "text":
            user_text = message.get("text", {}).get("body", "").strip()
        elif msg_type == "audio":
            is_inbound_voice = True
            audio_id = message.get("audio", {}).get("id")
            if audio_id:
                try:
                    audio_bytes = await self.whatsapp.download_media(audio_id)
                    temp_audio_file = TEMP_AUDIO_DIR / f"inbound_{uuid.uuid4().hex}.ogg"
                    with open(temp_audio_file, "wb") as f:
                        f.write(audio_bytes)
                    
                    # Transcribe using Whisper
                    transcribed, lang = await self.stt.transcribe_audio(str(temp_audio_file))
                    user_text = transcribed
                    if os.path.exists(temp_audio_file):
                        os.remove(temp_audio_file)
                except Exception as e:
                    logger.error("Failed to process inbound voice: %s", e)
                    user_text = "Voice note received (could not transcribe)"
        else:
            # Other unsupported types like location, stickers
            user_text = f"Sent a {msg_type} message"

        if not user_text:
            return

        # 4. Save user message in conversation log
        self.db.add_message(
            user_id=user_id,
            sender="user",
            content=user_text,
            message_type="voice" if is_inbound_voice else "text"
        )

        # 5. Extract and store memories in background
        await self.memory.process_and_store_message(user_id=user_id, user_message=user_text)

        # 6. Retrieve relevant memories & recent conversation context
        memories = self.memory.get_relevant_memories(user_id=user_id, query=user_text, limit=6)
        recent_messages = self.db.get_recent_messages(user_id=user_id, limit=14)
        character = self.db.get_character_settings()

        prompt_messages = self.ai.build_prompt_context(
            system_prompt=character.get("system_prompt", ""),
            user_info=user,
            memories=memories,
            recent_messages=recent_messages
        )

        # 7. Generate AI response
        raw_response, provider_used = await self.ai.generate(prompt_messages)

        # 8. Parse action triggers (Image / Voice)
        clean_reply, image_prompt, is_voice_requested = self.ai.parse_actions(raw_response)
        
        # If user spoke via voice note, automatically reply with voice note too
        should_send_voice = is_voice_requested or is_inbound_voice

        # 9. Execute actions and reply to WhatsApp
        
        # A. If an image is requested
        if image_prompt:
            try:
                local_img_path, filename, _ = await self.image.generate_character_image(image_prompt)
                public_img_url = f"{settings.BASE_URL}/static/images/generated/{filename}"
                await self.whatsapp.send_image_message(
                    recipient_phone=sender_phone,
                    image_url=public_img_url,
                    caption=clean_reply
                )
                self.db.add_message(
                    user_id=user_id,
                    sender="assistant",
                    content=clean_reply,
                    message_type="image",
                    media_url=public_img_url
                )
            except Exception as e:
                logger.error("Error sending image response: %s", e)
                # Fallback to text
                await self.whatsapp.send_text_message(sender_phone, clean_reply)
                self.db.add_message(user_id=user_id, sender="assistant", content=clean_reply)

        # B. If voice note is requested or appropriate
        elif should_send_voice:
            try:
                mp3_path, ogg_path, file_id = await self.tts.generate_speech(clean_reply)
                public_voice_url = f"{settings.BASE_URL}/static/audio/{file_id}.ogg"
                
                # Send text first for clarity, then voice note
                await self.whatsapp.send_text_message(sender_phone, clean_reply)
                await self.whatsapp.send_voice_message(
                    recipient_phone=sender_phone,
                    audio_url=public_voice_url
                )
                self.db.add_message(
                    user_id=user_id,
                    sender="assistant",
                    content=clean_reply,
                    message_type="voice",
                    media_url=public_voice_url
                )
            except Exception as e:
                logger.error("Error sending voice response: %s", e)
                await self.whatsapp.send_text_message(sender_phone, clean_reply)
                self.db.add_message(user_id=user_id, sender="assistant", content=clean_reply)

        # C. Standard text reply
        else:
            await self.whatsapp.send_text_message(sender_phone, clean_reply)
            self.db.add_message(
                user_id=user_id,
                sender="assistant",
                content=clean_reply,
                message_type="text"
            )

        # 10. Update user activity & log
        self.db.log_activity("message_processed", {
            "user_id": user_id,
            "provider": provider_used,
            "has_image": bool(image_prompt),
            "has_voice": bool(should_send_voice)
        })

webhook_handler = WebhookHandler()
