import asyncio
import unittest
import os
from services.voice.tts_service import TTSService

class TestVoiceTTS(unittest.TestCase):
    def setUp(self):
        self.tts = TTSService()

    def test_voice_selection_urdu(self):
        urdu_text = "Kaisi ho meri jaan? Main theek hoon."
        voice = self.tts.select_voice(urdu_text)
        self.assertEqual(voice, "ur-PK-UzmaNeural")

    def test_voice_selection_english(self):
        english_text = "I am so happy to hear from you today!"
        voice = self.tts.select_voice(english_text)
        self.assertEqual(voice, "en-US-AvaNeural")

    def test_speech_generation_and_opus(self):
        sample_text = "Testing voice synthesis for Project Aura."
        mp3_path, ogg_path, file_id = asyncio.run(self.tts.generate_speech(sample_text))
        
        self.assertTrue(os.path.exists(mp3_path))
        self.assertTrue(os.path.getsize(mp3_path) > 1000)
        self.assertTrue(os.path.exists(ogg_path))
        
        # Cleanup
        try:
            if os.path.exists(mp3_path): os.remove(mp3_path)
            if os.path.exists(ogg_path): os.remove(ogg_path)
        except Exception:
            pass

if __name__ == "__main__":
    unittest.main()
