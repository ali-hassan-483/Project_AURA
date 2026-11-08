import unittest
from fastapi.testclient import TestClient
from main import app
from config.settings import settings
from core.security import verify_whatsapp_signature, create_admin_jwt

class TestWhatsAppWebhook(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")

    def test_webhook_verification_success(self):
        params = {
            "hub.mode": "subscribe",
            "hub.verify_token": settings.WHATSAPP_VERIFY_TOKEN,
            "hub.challenge": "1158201234"
        }
        response = self.client.get("/webhook", params=params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "1158201234")

    def test_webhook_verification_failure(self):
        params = {
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "1158201234"
        }
        response = self.client.get("/webhook", params=params)
        self.assertEqual(response.status_code, 403)

    def test_simulator_chat_endpoint(self):
        token = create_admin_jwt(settings.ADMIN_USERNAME)
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "message": "Hello Aura! Kaisi ho?",
            "phone": "+923000000000",
            "name": "Test User"
        }
        response = self.client.post("/api/admin/simulator/chat", json=payload, headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("reply", data)
        self.assertTrue(len(data["reply"]) > 0)

if __name__ == "__main__":
    unittest.main()
