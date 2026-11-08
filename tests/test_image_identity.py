import unittest
from services.image.identity import IdentityManager
from services.image.scenes import detect_scene_request

class TestImageIdentity(unittest.TestCase):
    def setUp(self):
        self.identity = IdentityManager()

    def test_identity_prompt_composition(self):
        scene = "sitting at the beach in a lovely dress"
        prompt = self.identity.compose_prompt(scene)
        self.assertIn("hazel brown", prompt)
        self.assertIn("beach", prompt)
        self.assertIn("85mm", prompt)

    def test_scene_detection(self):
        key, desc, aspect = detect_scene_request("take a mirror selfie for me")
        self.assertEqual(key, "mirror_selfie")

        key2, desc2, aspect2 = detect_scene_request("send me a picture at the beach")
        self.assertEqual(key2, "beach")

        key3, desc3, aspect3 = detect_scene_request("show me your full outfit")
        self.assertEqual(key3, "outfit")

    def test_seed_anchoring(self):
        seed1 = self.identity.get_generation_seed(0)
        seed2 = self.identity.get_generation_seed(5)
        self.assertEqual(seed2 - seed1, 5)

if __name__ == "__main__":
    unittest.main()
