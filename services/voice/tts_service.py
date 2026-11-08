import os
import uuid
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Tuple, Optional
import edge_tts
from config.settings import settings

logger = logging.getLogger(__name__)

AUDIO_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

class TTSService:
    def __init__(self):
        self.default_urdu_voice = settings.TTS_DEFAULT_VOICE_URDU
        self.default_english_voice = settings.TTS_DEFAULT_VOICE_ENGLISH
        self.default_rate = settings.TTS_RATE
        self.default_pitch = settings.TTS_PITCH

    def select_voice(self, text: str) -> str:
        """Selects suitable female voice based on language detection"""
        # Check for Urdu unicode characters (Arabic script block)
        if any("\u0600" <= c <= "\u06FF" for c in text):
            return self.default_urdu_voice

        # Check for common Roman Urdu words
        roman_urdu_words = [
            "jaan", "meri", "mera", "kaisi", "kaise", "kya", "tum", "aap", "theek",
            "hoon", "hain", "kuch", "bohat", "pyari", "khayal", "rakho", "acha",
            "nahi", "rahi", "raha", "suno", "baba", "shona"
        ]
        text_lower = text.lower()
        matches = sum(1 for w in roman_urdu_words if f" {w} " in f" {text_lower} ")
        if matches >= 2:
            return self.default_urdu_voice
        
        return self.default_english_voice

    async def generate_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Synthesizes speech using Microsoft Edge-TTS and converts to WhatsApp Opus OGG.
        Returns: (mp3_file_path, ogg_file_path, public_filename_base)
        """
        selected_voice = voice or self.select_voice(text)
        speech_rate = rate or self.default_rate
        speech_pitch = pitch or self.default_pitch

        file_id = f"aura_voice_{uuid.uuid4().hex[:10]}"
        mp3_path = AUDIO_DIR / f"{file_id}.mp3"
        ogg_path = AUDIO_DIR / f"{file_id}.ogg"

        # Clean text from emojis / markdown that could disrupt TTS
        clean_text = text.replace("*", "").replace("#", "").replace("_", "")
        # Remove trailing action tokens if any
        clean_text = clean_text.split("[ACTION")[0].strip()

        logger.info("Generating Edge-TTS audio with voice '%s' for text: '%s'...", selected_voice, clean_text[:40])
        communicate = edge_tts.Communicate(
            text=clean_text,
            voice=selected_voice,
            rate=speech_rate,
            pitch=speech_pitch
        )
        await communicate.save(str(mp3_path))

        # Convert to WhatsApp-compliant Opus OGG using FFmpeg
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", str(mp3_path),
                "-c:a", "libopus",
                "-b:a", "32k",
                "-vbr", "on",
                "-ar", "16000",
                "-ac", "1",
                "-application", "voip",
                str(ogg_path)
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                logger.warning("FFmpeg opus conversion had warnings, fallback to mp3: %s", stderr.decode())
                ogg_path = mp3_path
        except Exception as e:
            logger.error("FFmpeg not available or failed conversion: %s. Using mp3.", e)
            ogg_path = mp3_path

        return str(mp3_path), str(ogg_path), file_id

    async def get_available_voices(self):
        """Lists high-quality female voices available in Edge-TTS"""
        return [
            {"id": "ur-PK-UzmaNeural", "name": "Uzma (Urdu - Pakistan)", "gender": "Female", "lang": "ur-PK"},
            {"id": "ur-PK-AsadNeural", "name": "Asad (Urdu - Pakistan)", "gender": "Male", "lang": "ur-PK"},
            {"id": "en-US-AvaNeural", "name": "Ava (English - US, Natural)", "gender": "Female", "lang": "en-US"},
            {"id": "en-US-JennyNeural", "name": "Jenny (English - US, Friendly)", "gender": "Female", "lang": "en-US"},
            {"id": "en-US-EmmaNeural", "name": "Emma (English - US, Soft)", "gender": "Female", "lang": "en-US"},
            {"id": "hi-IN-SwaraNeural", "name": "Swara (Hindi / Roman Urdu)", "gender": "Female", "lang": "hi-IN"},
            {"id": "en-GB-SoniaNeural", "name": "Sonia (English - UK)", "gender": "Female", "lang": "en-GB"}
        ]

tts_service = TTSService()
