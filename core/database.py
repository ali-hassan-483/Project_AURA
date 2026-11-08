"""
DatabaseManager: Supports both SQLite (local dev) and PostgreSQL (Render production).
- If DATABASE_URL env var is set → PostgreSQL (persistent, survives redeploys)
- Otherwise → SQLite (local development only)
"""
import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Fix Render's postgres:// → postgresql:// (psycopg2 requirement)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    try:
        import psycopg2
        import psycopg2.extras
        logger.info("PostgreSQL mode active (persistent storage)")
    except ImportError:
        logger.error("psycopg2 not installed! Run: pip install psycopg2-binary")
        USE_POSTGRES = False
else:
    import sqlite3
    logger.info("SQLite mode active (local dev)")


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        if not USE_POSTGRES:
            from config.settings import settings
            self.db_path = db_path or settings.DATABASE_PATH
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    # ------------------------------------------------------------------ #
    #  Connection helpers
    # ------------------------------------------------------------------ #
    def _get_conn(self):
        if USE_POSTGRES:
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        else:
            conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            return conn

    def _rows_to_dicts(self, rows) -> List[Dict]:
        if USE_POSTGRES:
            return [dict(r) for r in rows]
        return [dict(r) for r in rows]

    def _fetchone_dict(self, cursor) -> Optional[Dict]:
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def _adapt_sql(self, sql: str) -> str:
        """Convert SQLite SQL to PostgreSQL SQL."""
        if not USE_POSTGRES:
            return sql
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        sql = sql.replace("AUTOINCREMENT", "")
        sql = sql.replace("CURRENT_TIMESTAMP", "NOW()")
        sql = sql.replace("datetime('now')", "NOW()")
        # ON CONFLICT upsert is the same in both
        return sql

    def _ph(self, sql: str) -> str:
        """Convert ? placeholders to %s for PostgreSQL."""
        if USE_POSTGRES:
            return sql.replace("?", "%s")
        return sql

    # ------------------------------------------------------------------ #
    #  Schema init
    # ------------------------------------------------------------------ #
    def init_database(self):
        conn = self._get_conn()
        try:
            if USE_POSTGRES:
                cur = conn.cursor()
            else:
                cur = conn.cursor()

            # Users
            cur.execute(self._adapt_sql("""
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
            """))

            # Conversations
            cur.execute(self._adapt_sql("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                message_type TEXT DEFAULT 'text',
                raw_content TEXT NOT NULL,
                translated_content TEXT,
                media_url TEXT,
                tokens_used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """))

            # Memories
            cur.execute(self._adapt_sql("""
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
                UNIQUE (user_id, memory_key)
            );
            """))

            # Character Settings (includes reference_photo_b64 for persistence)
            cur.execute(self._adapt_sql("""
            CREATE TABLE IF NOT EXISTS character_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT DEFAULT 'Aylin',
                age INTEGER DEFAULT 21,
                archetype TEXT DEFAULT 'Loving Companion',
                system_prompt TEXT NOT NULL,
                identity_prompt TEXT NOT NULL,
                negative_prompt TEXT NOT NULL,
                default_voice_urdu TEXT DEFAULT 'ur-PK-UzmaNeural',
                default_voice_english TEXT DEFAULT 'en-US-AvaNeural',
                seed INTEGER DEFAULT 789234,
                reference_photo_b64 TEXT,
                is_active INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """))

            # Add reference_photo_b64 column if upgrading existing DB
            try:
                if USE_POSTGRES:
                    cur.execute("ALTER TABLE character_settings ADD COLUMN IF NOT EXISTS reference_photo_b64 TEXT;")
                else:
                    cur.execute("ALTER TABLE character_settings ADD COLUMN reference_photo_b64 TEXT;")
            except Exception:
                pass  # Column already exists

            # Activity Logs
            cur.execute(self._adapt_sql("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """))

            conn.commit()
        finally:
            conn.close()

        self._seed_character_defaults()
        self._restore_reference_photo()
        logger.info("Database initialized (%s)", "PostgreSQL" if USE_POSTGRES else "SQLite")

    def _seed_character_defaults(self):
        conn = self._get_conn()
        try:
            if USE_POSTGRES:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM character_settings")
            row = cur.fetchone()
            count = row["cnt"] if isinstance(row, dict) else row[0]
            if count == 0:
                persona_path = Path(__file__).resolve().parent.parent / "config" / "persona.json"
                if persona_path.exists():
                    with open(persona_path, "r", encoding="utf-8") as f:
                        p = json.load(f)
                    sql = self._ph(self._adapt_sql("""
                    INSERT INTO character_settings
                    (name, age, archetype, system_prompt, identity_prompt, negative_prompt,
                     default_voice_urdu, default_voice_english, seed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """))
                    cur.execute(sql, (
                        p.get("name", "Aylin"),
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
                    logger.info("Aylin persona seeded into database.")
        except Exception as e:
            logger.error("Seed error: %s", e)
        finally:
            conn.close()

    def _restore_reference_photo(self):
        """On startup, restore reference photo from DB to disk if it exists."""
        try:
            settings = self.get_character_settings()
            b64 = settings.get("reference_photo_b64")
            if b64:
                import base64
                ref_path = Path("static/images/aylin_reference.jpg")
                ref_path.parent.mkdir(parents=True, exist_ok=True)
                with open(ref_path, "wb") as f:
                    f.write(base64.b64decode(b64))
                logger.info("Reference photo restored from database to disk.")
        except Exception as e:
            logger.warning("Could not restore reference photo: %s", e)

    # ------------------------------------------------------------------ #
    #  User Operations
    # ------------------------------------------------------------------ #
    def get_or_create_user(self, phone_number: str, name: Optional[str] = None) -> Dict[str, Any]:
        conn = self._get_conn()
        try:
            if USE_POSTGRES:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cur = conn.cursor()
            cur.execute(self._ph("SELECT * FROM users WHERE phone_number = ?"), (phone_number,))
            row = self._fetchone_dict(cur)
            if row:
                cur.execute(self._ph("UPDATE users SET last_interaction = NOW(), updated_at = NOW() WHERE id = ?") if USE_POSTGRES
                            else "UPDATE users SET last_interaction = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (row["id"],))
                conn.commit()
                return row

            sql = self._ph(self._adapt_sql("""
            INSERT INTO users (phone_number, name, nickname, last_interaction)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """))
            cur.execute(sql, (phone_number, name or "Jaan", name or "Jaan"))
            conn.commit()

            if USE_POSTGRES:
                cur.execute(self._ph("SELECT * FROM users WHERE phone_number = ?"), (phone_number,))
            else:
                cur.execute(self._ph("SELECT * FROM users WHERE id = ?"), (cur.lastrowid,))
            return self._fetchone_dict(cur)
        finally:
            conn.close()

    def update_user(self, user_id: int, **kwargs) -> bool:
        allowed = ["name", "nickname", "language_pref", "relationship_level",
                   "intimacy_score", "timezone", "proactive_enabled"]
        updates, values = [], []
        for k, v in kwargs.items():
            if k in allowed:
                updates.append(f"{k} = {'%s' if USE_POSTGRES else '?'}")
                values.append(v)
        if not updates:
            return False
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = {'%s' if USE_POSTGRES else '?'}"
        conn = self._get_conn()
        try:
            conn.cursor().execute(query, tuple(values))
            conn.commit()
        finally:
            conn.close()
        return True

    def get_all_users(self) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            if USE_POSTGRES:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cur = conn.cursor()
            cur.execute("SELECT * FROM users ORDER BY last_interaction DESC")
            return self._rows_to_dicts(cur.fetchall())
        finally:
            conn.close()

    def delete_user_data(self, user_id: int) -> bool:
        conn = self._get_conn()
        try:
            ph = '%s' if USE_POSTGRES else '?'
            cur = conn.cursor()
            cur.execute(f"DELETE FROM memories WHERE user_id = {ph}", (user_id,))
            cur.execute(f"DELETE FROM conversations WHERE user_id = {ph}", (user_id,))
            cur.execute(f"DELETE FROM users WHERE id = {ph}", (user_id,))
            conn.commit()
        finally:
            conn.close()
        return True

    # ------------------------------------------------------------------ #
    #  Conversation Operations
    # ------------------------------------------------------------------ #
    def add_message(self, user_id: int, sender: str, content: str,
                    message_type: str = "text", media_url: Optional[str] = None,
                    tokens: int = 0) -> int:
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            sql = self._ph(self._adapt_sql("""
            INSERT INTO conversations (user_id, sender, raw_content, message_type, media_url, tokens_used)
            VALUES (?, ?, ?, ?, ?, ?)
            """))
            cur.execute(sql, (user_id, sender, content, message_type, media_url, tokens))
            conn.commit()
            if USE_POSTGRES:
                cur.execute("SELECT lastval()")
                return cur.fetchone()[0]
            return cur.lastrowid
        finally:
            conn.close()

    def get_recent_messages(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            if USE_POSTGRES:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("""
                SELECT * FROM (
                    SELECT * FROM conversations WHERE user_id = %s ORDER BY created_at DESC LIMIT %s
                ) sub ORDER BY created_at ASC
                """, (user_id, limit))
            else:
                cur = conn.cursor()
                cur.execute("""
                SELECT * FROM (
                    SELECT * FROM conversations WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
                ) ORDER BY created_at ASC
                """, (user_id, limit))
            return self._rows_to_dicts(cur.fetchall())
        finally:
            conn.close()

    def get_total_messages_count(self) -> int:
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM conversations")
            row = cur.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    #  Memory Operations
    # ------------------------------------------------------------------ #
    def set_memory(self, user_id: int, category: str, key: str, value: str,
                   importance: int = 3, confidence: float = 1.0) -> bool:
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            if USE_POSTGRES:
                cur.execute("""
                INSERT INTO memories (user_id, category, memory_key, memory_value, importance, confidence, last_accessed_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT(user_id, memory_key) DO UPDATE SET
                    memory_value = EXCLUDED.memory_value,
                    importance = EXCLUDED.importance,
                    confidence = EXCLUDED.confidence,
                    last_accessed_at = NOW()
                """, (user_id, category.lower(), key.strip().lower(), value.strip(), importance, confidence))
            else:
                cur.execute("""
                INSERT INTO memories (user_id, category, memory_key, memory_value, importance, confidence, last_accessed_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, memory_key) DO UPDATE SET
                    memory_value = excluded.memory_value,
                    importance = excluded.importance,
                    confidence = excluded.confidence,
                    last_accessed_at = CURRENT_TIMESTAMP
                """, (user_id, category.lower(), key.strip().lower(), value.strip(), importance, confidence))
            conn.commit()
        finally:
            conn.close()
        return True

    def get_memories_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            if USE_POSTGRES:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cur = conn.cursor()
            cur.execute(self._ph("SELECT * FROM memories WHERE user_id = ? ORDER BY importance DESC, created_at DESC"),
                        (user_id,))
            return self._rows_to_dicts(cur.fetchall())
        finally:
            conn.close()

    def search_relevant_memories(self, user_id: int, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        tokens = [t.lower() for t in query.split() if len(t) > 2]
        conn = self._get_conn()
        try:
            if USE_POSTGRES:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cur = conn.cursor()
            ph = '%s' if USE_POSTGRES else '?'
            if not tokens:
                cur.execute(f"SELECT * FROM memories WHERE user_id = {ph} ORDER BY importance DESC, last_accessed_at DESC LIMIT {ph}",
                            (user_id, limit))
            else:
                like_clauses = " OR ".join([f"memory_key LIKE {ph} OR memory_value LIKE {ph}"] * len(tokens))
                params = [user_id]
                for t in tokens:
                    params.extend([f"%{t}%", f"%{t}%"])
                params.append(limit)
                cur.execute(f"SELECT * FROM memories WHERE user_id = {ph} AND ({like_clauses}) ORDER BY importance DESC LIMIT {ph}",
                            tuple(params))
            results = self._rows_to_dicts(cur.fetchall())

            if len(results) < limit:
                seen = {r["id"] for r in results}
                cur.execute(f"SELECT * FROM memories WHERE user_id = {ph} ORDER BY importance DESC LIMIT {ph}",
                            (user_id, limit))
                for row in self._rows_to_dicts(cur.fetchall()):
                    if row["id"] not in seen and len(results) < limit:
                        results.append(row)
                        seen.add(row["id"])
            return results
        finally:
            conn.close()

    def delete_memory(self, memory_id: int) -> bool:
        conn = self._get_conn()
        try:
            ph = '%s' if USE_POSTGRES else '?'
            cur = conn.cursor()
            cur.execute(f"DELETE FROM memories WHERE id = {ph}", (memory_id,))
            conn.commit()
        finally:
            conn.close()
        return True

    # ------------------------------------------------------------------ #
    #  Character Settings
    # ------------------------------------------------------------------ #
    def get_character_settings(self) -> Dict[str, Any]:
        conn = self._get_conn()
        try:
            if USE_POSTGRES:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cur = conn.cursor()
            cur.execute("SELECT * FROM character_settings WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
            row = self._fetchone_dict(cur)
            return row or {}
        finally:
            conn.close()

    def update_character_settings(self, **kwargs) -> bool:
        allowed = ["name", "age", "archetype", "system_prompt", "identity_prompt",
                   "negative_prompt", "default_voice_urdu", "default_voice_english",
                   "seed", "reference_photo_b64"]
        ph = '%s' if USE_POSTGRES else '?'
        updates, values = [], []
        for k, v in kwargs.items():
            if k in allowed:
                updates.append(f"{k} = {ph}")
                values.append(v)
        if not updates:
            return False
        query = f"UPDATE character_settings SET {', '.join(updates)} WHERE is_active = 1"
        conn = self._get_conn()
        try:
            conn.cursor().execute(query, tuple(values))
            conn.commit()
        finally:
            conn.close()
        return True

    def save_reference_photo_b64(self, b64_string: str) -> bool:
        """Saves reference photo as base64 in DB — survives redeploys."""
        return self.update_character_settings(reference_photo_b64=b64_string)

    # ------------------------------------------------------------------ #
    #  Logs & Metrics
    # ------------------------------------------------------------------ #
    def log_activity(self, event_type: str, details: Dict[str, Any]):
        try:
            conn = self._get_conn()
            ph = '%s' if USE_POSTGRES else '?'
            cur = conn.cursor()
            cur.execute(f"INSERT INTO activity_logs (event_type, details) VALUES ({ph}, {ph})",
                        (event_type, json.dumps(details)))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Failed to log activity: %s", e)

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        conn = self._get_conn()
        try:
            if USE_POSTGRES:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cur = conn.cursor()

            def scalar(sql):
                cur.execute(sql)
                r = cur.fetchone()
                return r[0] if r else 0

            total_users     = scalar("SELECT COUNT(*) FROM users")
            total_messages  = scalar("SELECT COUNT(*) FROM conversations")
            voice_messages  = scalar("SELECT COUNT(*) FROM conversations WHERE message_type = 'voice'")
            image_messages  = scalar("SELECT COUNT(*) FROM conversations WHERE message_type = 'image'")
            total_memories  = scalar("SELECT COUNT(*) FROM memories")

            if USE_POSTGRES:
                cur.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM conversations GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 7
                """)
            else:
                cur.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM conversations GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 7
                """)
            daily_stats = self._rows_to_dicts(cur.fetchall())

            cur.execute("SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 10")
            recent_logs = self._rows_to_dicts(cur.fetchall())

            return {
                "total_users": total_users,
                "total_messages": total_messages,
                "voice_messages": voice_messages,
                "image_messages": image_messages,
                "total_memories": total_memories,
                "daily_stats": daily_stats,
                "recent_logs": recent_logs
            }
        finally:
            conn.close()


db = DatabaseManager()
