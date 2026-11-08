import re
import logging
from typing import List, Dict, Any, Optional
from core.database import db

logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self):
        self.db = db

    def extract_memories_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Extracts salient personal facts, preferences, dates, and emotional events.
        Works with both Roman Urdu and English phrases without requiring paid APIs.
        """
        extracted = []
        low = text.lower()

        # 1. Name patterns (English & Roman Urdu)
        name_match = re.search(r"\b(?:my name is|mera naam|call me|mujhe)\s+([A-Za-z]+)\b", text, re.IGNORECASE)
        if name_match:
            val = name_match.group(1).title()
            if val.lower() not in ["batao", "suno", "haan", "nahi", "jaan"]:
                extracted.append({
                    "category": "personal_info",
                    "key": "user_name",
                    "value": val,
                    "importance": 5
                })

        # 2. Favorite things / Pasand (Supports English & Roman Urdu word orders)
        # Roman Urdu order: "mujhe [item] (bohat) pasand hai"
        urdu_fav = re.search(r"\b(?:mujhe|humein)\s+([A-Za-z\s]+?)\s+(?:bohat\s+)?pasand\s+hai\b", text, re.IGNORECASE)
        if urdu_fav:
            item = urdu_fav.group(1).strip()
            if len(item) > 2 and len(item) < 60:
                extracted.append({
                    "category": "preference",
                    "key": f"favorite_{item[:20].replace(' ', '_').lower()}",
                    "value": item,
                    "importance": 4
                })
        else:
            # English order: "my favorite ... is [item]" or "I love [item]"
            fav_match = re.search(r"\b(?:my favou?rite|mera favou?rite|meri pasandeeda|i love|i really like)\s+([^,.\n?!]+)", text, re.IGNORECASE)
            if fav_match:
                item = fav_match.group(1).strip()
                if len(item) > 2 and len(item) < 60:
                    extracted.append({
                        "category": "preference",
                        "key": f"favorite_{item[:20].replace(' ', '_').lower()}",
                        "value": item,
                        "importance": 4
                    })

        # 3. Profession / Work / Studies
        work_match = re.search(r"\b(?:i work as|i am a|i am an|main ek|mera profession|i study|main parhta hoon|main parhti hoon)\s+([^,.\n?!]+)", text, re.IGNORECASE)
        if work_match:
            work = work_match.group(1).strip()
            if len(work) > 2 and len(work) < 50:
                extracted.append({
                    "category": "personal_info",
                    "key": "career_or_education",
                    "value": work,
                    "importance": 4
                })

        # 4. Location / City / Residence
        city_match = re.search(r"\b(?:i live in|main rehta hoon|main rehti hoon|from)\s+([A-Za-z\s]+)(?:mein|me)?\b", text, re.IGNORECASE)
        if city_match:
            city = city_match.group(1).strip()
            if city.lower() not in ["here", "home", "ghar", "wahan"]:
                extracted.append({
                    "category": "personal_info",
                    "key": "location",
                    "value": city.title(),
                    "importance": 3
                })

        # 5. Birthday / Important Dates
        bday_match = re.search(r"\b(?:my birthday is|meri birthday|salgirah)\s+([^,.\n?!]+)", text, re.IGNORECASE)
        if bday_match:
            bday = bday_match.group(1).strip()
            extracted.append({
                "category": "events",
                "key": "birthday",
                "value": bday,
                "importance": 5
            })

        # 6. Relationship & Emotional Milestones
        if any(w in low for w in ["i love you", "tum meri jaan ho", "you are special", "tum meri girlfriend ho"]):
            extracted.append({
                "category": "relationship",
                "key": "relationship_affection",
                "value": "Expressed deep love and affection for Aura",
                "importance": 5
            })

        return extracted

    async def process_and_store_message(self, user_id: int, user_message: str):
        """Extracts facts from inbound user message and stores them in memory store"""
        try:
            memories = self.extract_memories_from_text(user_message)
            for m in memories:
                self.db.set_memory(
                    user_id=user_id,
                    category=m["category"],
                    key=m["key"],
                    value=m["value"],
                    importance=m["importance"]
                )
                logger.info("Saved memory for user %s: [%s] %s -> %s", user_id, m["category"], m["key"], m["value"])
                
                # If name was updated, update user profile as well
                if m["key"] == "user_name":
                    self.db.update_user(user_id, name=m["value"], nickname=m["value"])
        except Exception as e:
            logger.error("Error processing memory: %s", e)

    def get_relevant_memories(self, user_id: int, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        """Pulls memories relevant to the ongoing message exchange"""
        return self.db.search_relevant_memories(user_id=user_id, query=query, limit=limit)

    def get_all_user_memories(self, user_id: int) -> List[Dict[str, Any]]:
        return self.db.get_memories_for_user(user_id=user_id)

    def delete_memory(self, memory_id: int) -> bool:
        return self.db.delete_memory(memory_id=memory_id)

    def add_manual_memory(self, user_id: int, category: str, key: str, value: str, importance: int = 3) -> bool:
        return self.db.set_memory(user_id, category, key, value, importance)

memory_service = MemoryService()
