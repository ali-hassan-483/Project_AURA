import sqlite3
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for high concurrency
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def init_database(self):
        """Initializes tables and migrations"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT UNIQUE NOT NULL,
                name TEXT,
                nickname TEXT,
                language_pref TEXT DEFAULT 'roman_urdu',
                relationship_level INTEGER DEFAULT 1,
                intimacy_score INTEGER DEFAULT 50,
                timezone TEXT DEFAULT 'UTC',
                proactive_enabled INTEGER DEFAULT 1,
                last_interaction TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # Conversations Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                message_type TEXT DEFAULT 'text',
                raw_content TEXT NOT NULL,
                translated_content TEXT,
                media_url TEXT,
                tokens_used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            """)

            # Memories Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT DEFAULT 'personal',
                memory_key TEXT NOT NULL,
                memory_value TEXT NOT NULL,
                importance INTEGER DEFAULT 3,
                confidence REAL DEFAULT 1.0,
                last_accessed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE (user_id, memory_key)
            );
            """)

            # Character Settings Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT DEFAULT 'Aura',
                age INTEGER DEFAULT 21,
                archetype TEXT DEFAULT 'Loving Companion',
                system_prompt TEXT NOT NULL,
                identity_prompt TEXT NOT NULL,
                negative_prompt TEXT NOT NULL,
                default_voice_urdu TEXT DEFAULT 'ur-PK-UzmaNeural',
                default_voice_english TEXT DEFAULT 'en-US-AvaNeural',
                seed INTEGER DEFAULT 789234,
                is_active INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # Activity Logs Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # AI Provider Settings / Overrides Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS provider_configs (
                provider_name TEXT PRIMARY KEY,
                is_enabled INTEGER DEFAULT 1,
                priority INTEGER DEFAULT 1,
                model_name TEXT,
                api_key TEXT,
                base_url TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            conn.commit()

        # Seed character defaults from persona.json if empty
        self._seed_character_defaults()
        logger.info("Database initialized successfully at %s", self.db_path)

    def _seed_character_defaults(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM character_settings")
            count = cursor.fetchone()[0]
            if count == 0:
                persona_path = Path(__file__).resolve().parent.parent / "config" / "persona.json"
                if persona_path.exists():
                    try:
                        with open(persona_path, "r", encoding="utf-8") as f:
                            p = json.load(f)
                        cursor.execute("""
                        INSERT INTO character_settings 
                        (name, age, archetype, system_prompt, identity_prompt, negative_prompt, default_voice_urdu, default_voice_english, seed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            p.get("name", "Aura"),
                            p.get("age", 21),
                            p.get("archetype", "Loving Companion"),
                            p.get("system_prompt", ""),
                            p.get("appearance", {}).get("identity_anchor", ""),
                            p.get("appearance", {}).get("negative_prompt", ""),
                            "ur-PK-UzmaNeural",
                            "en-US-AvaNeural",
                            p.get("appearance", {}).get("seed", 789234)
                        ))
                        conn.commit()
                        logger.info("Default Aura character persona seeded into database.")
                    except Exception as e:
                        logger.error("Error seeding persona: %s", e)

    # ---------------- USER OPERATIONS ----------------
    def get_or_create_user(self, phone_number: str, name: Optional[str] = None) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE phone_number = ?", (phone_number,))
            row = cursor.fetchone()
            if row:
                cursor.execute("""
                UPDATE users SET last_interaction = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
                """, (row["id"],))
                conn.commit()
                return dict(row)
            
            # Create new user
            cursor.execute("""
            INSERT INTO users (phone_number, name, nickname, last_interaction)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (phone_number, name or "Jaan", name or "Jaan"))
            conn.commit()
            user_id = cursor.lastrowid
            
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return dict(cursor.fetchone())

    def update_user(self, user_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        allowed_fields = [
            "name", "nickname", "language_pref", "relationship_level", 
            "intimacy_score", "timezone", "proactive_enabled"
        ]
        updates = []
        values = []
        for k, v in kwargs.items():
            if k in allowed_fields:
                updates.append(f"{k} = ?")
                values.append(v)
        if not updates:
            return False
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)}, updated_at = ? WHERE id = ?"
        with self.get_connection() as conn:
            conn.execute(query, tuple(values))
            conn.commit()
        return True

    def get_all_users(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY last_interaction DESC")
            return [dict(row) for row in cursor.fetchall()]

    def delete_user_data(self, user_id: int) -> bool:
        """Deletes all messages, memories, and profile for a user (Privacy compliant)"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        return True

    # ---------------- CONVERSATION OPERATIONS ----------------
    def add_message(self, user_id: int, sender: str, content: str, 
                    message_type: str = "text", media_url: Optional[str] = None, 
                    tokens: int = 0) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO conversations (user_id, sender, raw_content, message_type, media_url, tokens_used)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, sender, content, message_type, media_url, tokens))
            conn.commit()
            return cursor.lastrowid

    def get_recent_messages(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM (
                SELECT * FROM conversations 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ) ORDER BY created_at ASC
            """, (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]

    def get_total_messages_count(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM conversations")
            return cursor.fetchone()[0]

    # ---------------- MEMORY OPERATIONS ----------------
    def set_memory(self, user_id: int, category: str, key: str, value: str, 
                   importance: int = 3, confidence: float = 1.0) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO memories (user_id, category, memory_key, memory_value, importance, confidence, last_accessed_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, memory_key) DO UPDATE SET
                memory_value = excluded.memory_value,
                importance = excluded.importance,
                confidence = excluded.confidence,
                last_accessed_at = CURRENT_TIMESTAMP
            """, (user_id, category.lower(), key.strip().lower(), value.strip(), importance, confidence))
            conn.commit()
            return True

    def get_memories_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM memories WHERE user_id = ? ORDER BY importance DESC, created_at DESC
            """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]

    def search_relevant_memories(self, user_id: int, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        """Retrieves top memories matching keywords and highest importance"""
        tokens = [t.lower() for t in query.split() if len(t) > 2]
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if not tokens:
                cursor.execute("""
                SELECT * FROM memories WHERE user_id = ? 
                ORDER BY importance DESC, last_accessed_at DESC LIMIT ?
                """, (user_id, limit))
            else:
                like_clauses = " OR ".join(["memory_key LIKE ? OR memory_value LIKE ?"] * len(tokens))
                params = []
                for t in tokens:
                    params.extend([f"%{t}%", f"%{t}%"])
                params.insert(0, user_id)
                params.append(limit)
                sql = f"""
                SELECT * FROM memories 
                WHERE user_id = ? AND ({like_clauses})
                ORDER BY importance DESC, created_at DESC LIMIT ?
                """
                cursor.execute(sql, tuple(params))
            
            results = [dict(row) for row in cursor.fetchall()]
            
            # If search yielded fewer than desired, backfill with top important memories
            if len(results) < limit:
                existing_ids = {r["id"] for r in results}
                cursor.execute("""
                SELECT * FROM memories WHERE user_id = ? 
                ORDER BY importance DESC LIMIT ?
                """, (user_id, limit))
                for row in cursor.fetchall():
                    if row["id"] not in existing_ids and len(results) < limit:
                        results.append(dict(row))
                        existing_ids.add(row["id"])

            return results

    def delete_memory(self, memory_id: int) -> bool:
        with self.get_connection() as conn:
            conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return True

    # ---------------- CHARACTER SETTINGS ----------------
    def get_character_settings(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM character_settings WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {}

    def update_character_settings(self, **kwargs) -> bool:
        allowed = [
            "name", "age", "archetype", "system_prompt", "identity_prompt",
            "negative_prompt", "default_voice_urdu", "default_voice_english", "seed"
        ]
        updates = []
        values = []
        for k, v in kwargs.items():
            if k in allowed:
                updates.append(f"{k} = ?")
                values.append(v)
        if not updates:
            return False
        values.append(datetime.now(timezone.utc).isoformat())
        with self.get_connection() as conn:
            conn.execute(f"UPDATE character_settings SET {', '.join(updates)}, updated_at = ? WHERE is_active = 1", tuple(values))
            conn.commit()
            return True

    # ---------------- LOGS & METRICS ----------------
    def log_activity(self, event_type: str, details: Dict[str, Any]):
        try:
            with self.get_connection() as conn:
                conn.execute("""
                INSERT INTO activity_logs (event_type, details) VALUES (?, ?)
                """, (event_type, json.dumps(details)))
                conn.commit()
        except Exception as e:
            logger.error("Failed to log activity: %s", e)

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM conversations")
            total_messages = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM conversations WHERE message_type = 'voice'")
            voice_messages = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM conversations WHERE message_type = 'image'")
            image_messages = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM memories")
            total_memories = cursor.fetchone()[0]

            cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count 
            FROM conversations 
            GROUP BY DATE(created_at) 
            ORDER BY date DESC LIMIT 7
            """)
            daily_stats = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
            SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 10
            """)
            recent_logs = [dict(row) for row in cursor.fetchall()]

            return {
                "total_users": total_users,
                "total_messages": total_messages,
                "voice_messages": voice_messages,
                "image_messages": image_messages,
                "total_memories": total_memories,
                "daily_stats": daily_stats,
                "recent_logs": recent_logs
            }

db = DatabaseManager()
