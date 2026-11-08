import unittest
from services.ai.router import AIRouter

class TestAIAndActions(unittest.TestCase):
    def setUp(self):
        self.router = AIRouter()

    def test_parse_actions_with_image(self):
        sample = "Ye lo jaan meri picture! [ACTION:SEND_IMAGE: Aura smiling in cozy cafe holding chai] Kaisi lag rahi hoon?"
        clean_text, img_prompt, has_voice = self.router.parse_actions(sample)
        self.assertEqual(clean_text, "Ye lo jaan meri picture!  Kaisi lag rahi hoon?")
        self.assertEqual(img_prompt, "Aura smiling in cozy cafe holding chai")
        self.assertFalse(has_voice)

    def test_parse_actions_with_voice(self):
        sample = "Suno meri jaan, main voice note bhej rahi hoon [ACTION:SEND_VOICE]"
        clean_text, img_prompt, has_voice = self.router.parse_actions(sample)
        self.assertEqual(clean_text, "Suno meri jaan, main voice note bhej rahi hoon")
        self.assertIsNone(img_prompt)
        self.assertTrue(has_voice)

    def test_offline_fallback_generation(self):
        messages = [
            {"role": "user", "content": "Kaisi ho jaan?"}
        ]
        reply = self.router._generate_offline_fallback(messages)
        self.assertIn("jaan", reply.lower())

    def test_offline_fallback_selfie_request(self):
        messages = [
            {"role": "user", "content": "Send me your selfie"}
        ]
        reply = self.router._generate_offline_fallback(messages)
        self.assertIn("[ACTION:SEND_IMAGE:", reply)

if __name__ == "__main__":
    unittest.main()
