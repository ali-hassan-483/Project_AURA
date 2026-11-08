import asyncio
import unittest
import os
from pathlib import Path
from core.database import DatabaseManager
from services.memory.memory_service import MemoryService

class TestDatabaseAndMemory(unittest.TestCase):
    def setUp(self):
        import uuid
        self.test_db_path = f"data/test_aura_{uuid.uuid4().hex[:8]}.db"
        self.db = DatabaseManager(self.test_db_path)
        self.memory = MemoryService()
        self.memory.db = self.db

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def test_user_creation_and_retrieval(self):
        user = self.db.get_or_create_user(phone_number="+923001234567", name="Farhan")
        self.assertIsNotNone(user["id"])
        self.assertEqual(user["phone_number"], "+923001234567")
        self.assertEqual(user["name"], "Farhan")

    def test_message_history(self):
        user = self.db.get_or_create_user(phone_number="+923009998888", name="Ali")
        uid = user["id"]
        
        self.db.add_message(uid, "user", "Hello Aura!", "text")
        self.db.add_message(uid, "assistant", "Hello jaan! Kaisi ho?", "text")
        
        messages = self.db.get_recent_messages(uid, limit=10)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["raw_content"], "Hello Aura!")
        self.assertEqual(messages[1]["raw_content"], "Hello jaan! Kaisi ho?")

    def test_memory_extraction_and_search(self):
        user = self.db.get_or_create_user(phone_number="+923005554444", name="Hamza")
        uid = user["id"]

        # Run extraction on sample Roman Urdu text
        text = "Mera naam Hamza hai aur mujhe Biryani bohat pasand hai"
        asyncio.run(self.memory.process_and_store_message(uid, text))

        memories = self.memory.get_relevant_memories(uid, query="biryani")
        self.assertTrue(len(memories) >= 1)
        found_biryani = any("biryani" in m["memory_value"].lower() for m in memories)
        self.assertTrue(found_biryani)

    def test_memory_deletion(self):
        user = self.db.get_or_create_user(phone_number="+923001112222", name="Zubair")
        uid = user["id"]
        self.db.set_memory(uid, "personal", "hobby", "Playing guitar", 4)
        
        memories = self.db.get_memories_for_user(uid)
        self.assertEqual(len(memories), 1)
        
        mem_id = memories[0]["id"]
        self.db.delete_memory(mem_id)
        
        memories_after = self.db.get_memories_for_user(uid)
        self.assertEqual(len(memories_after), 0)

if __name__ == "__main__":
    unittest.main()
