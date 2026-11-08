import os
import logging
from pathlib import Path
from typing import Tuple, Optional
from config.settings import settings

logger = logging.getLogger(__name__)

class STTService:
    def __init__(self):
        self._model = None
        self.model_size = settings.WHISPER_MODEL_SIZE
        self.device = settings.WHISPER_DEVICE

    def _get_model(self):
        """Lazy loads faster-whisper model"""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                logger.info("Loading faster-whisper model '%s' on %s...", self.model_size, self.device)
                self._model = WhisperModel(self.model_size, device=self.device, compute_type="int8")
            except Exception as e:
                logger.error("Failed to load faster-whisper: %s. Trying openai-whisper...", e)
                try:
                    import whisper
                    self._model = whisper.load_model(self.model_size)
                except Exception as e2:
                    logger.error("Failed to load any whisper model: %s", e2)
                    raise RuntimeError("Whisper STT model could not be loaded.")
        return self._model

    async def transcribe_audio(self, audio_path: str) -> Tuple[str, str]:
        """
        Transcribes speech from audio file.
        Returns: (transcribed_text, detected_language)
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            model = self._get_model()
            
            # Check if it's faster_whisper or standard whisper
            if hasattr(model, "transcribe"):
                segments, info = model.transcribe(audio_path, beam_size=5)
                text = " ".join([segment.text for segment in segments]).strip()
                lang = getattr(info, "language", "ur")
                logger.info("Transcribed audio successfully: '%s' (Lang: %s)", text, lang)
                return text, lang
            else:
                # Standard whisper
                result = model.transcribe(audio_path)
                return result["text"].strip(), result.get("language", "ur")

        except Exception as e:
            logger.error("Transcription error: %s", e)
            return "Mujhe aapki awaz theek se sunai nahi di jaan, kya aap dobara bhej sakte hain?", "ur"

stt_service = STTService()
