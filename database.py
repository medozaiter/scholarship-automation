import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "scholarships.db")

class Database:
    """
    Asynchronous SQLite Database Manager for:
    - Scholarship indexing & search caching
    - Student alert subscriptions
    - Channel broadcast logs
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def init_db(self) -> None:
        """Initializes tables and indexes."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scholarships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    institution TEXT,
                    country TEXT,
                    degree TEXT NOT NULL,
                    major TEXT NOT NULL,
                    funding_type TEXT,
                    deadline TEXT,
                    status TEXT,
                    coverage TEXT,
                    requirements TEXT,
                    official_url TEXT UNIQUE NOT NULL,
                    raw_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    cache_key TEXT PRIMARY KEY,
                    results_html TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    degree TEXT NOT NULL,
                    major TEXT NOT NULL,
                    country TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(chat_id, degree, major)
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS channel_broadcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scholarship_url TEXT UNIQUE NOT NULL,
                    broadcast_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await db.commit()
        logger.info(f"Database initialized successfully at {self.db_path}")

    # ==================== SEARCH CACHE ====================

    async def get_cached_search(self, cache_key: str, ttl_hours: int = 24) -> Optional[str]:
        """Retrieves cached search HTML if not expired."""
        cutoff = datetime.utcnow() - timedelta(hours=ttl_hours)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT results_html, created_at FROM search_cache WHERE cache_key = ?",
                (cache_key,)
            )
            row = await cursor.fetchone()
            if row:
                created_at = datetime.fromisoformat(row["created_at"])
                if created_at > cutoff:
                    logger.info(f"Cache HIT for key: {cache_key}")
                    return row["results_html"]
                else:
                    logger.info(f"Cache EXPIRED for key: {cache_key}")
                    await db.execute("DELETE FROM search_cache WHERE cache_key = ?", (cache_key,))
                    await db.commit()
        return None

    async def set_cached_search(self, cache_key: str, results_html: str) -> None:
        """Saves search results HTML into cache."""
        now_str = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO search_cache (cache_key, results_html, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    results_html = excluded.results_html,
                    created_at = excluded.created_at
                """,
                (cache_key, results_html, now_str)
            )
            await db.commit()

    # ==================== SCHOLARSHIPS REPOSITORY ====================

    async def save_scholarship(self, data: Dict[str, Any]) -> bool:
        """Inserts or updates a scholarship entry. Returns True if newly inserted."""
        now_str = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute(
                    """
                    INSERT INTO scholarships (
                        title, institution, country, degree, major,
                        funding_type, deadline, status, coverage,
                        requirements, official_url, raw_content, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(official_url) DO UPDATE SET
                        deadline = excluded.deadline,
                        status = excluded.status,
                        coverage = excluded.coverage,
                        requirements = excluded.requirements,
                        updated_at = excluded.updated_at
                    """,
                    (
                        data.get("title", "Untitled"),
                        data.get("institution", ""),
                        data.get("country", ""),
                        data.get("degree", "Undergraduate"),
                        data.get("major", ""),
                        data.get("funding_type", "Fully Funded"),
                        data.get("deadline", "Check Portal"),
                        data.get("status", "Open Now"),
                        data.get("coverage", ""),
                        data.get("requirements", ""),
                        data["official_url"],
                        data.get("raw_content", ""),
                        now_str,
                        now_str
                    )
                )
                await db.commit()
                # If lastrowid is affected and no update conflict occurred
                return cursor.rowcount > 0
            except Exception as e:
                logger.error(f"Error saving scholarship to DB: {e}")
                return False

    async def get_recent_scholarships(self, degree: str, major: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Queries stored scholarships matching degree and major."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM scholarships
                WHERE degree LIKE ? AND major LIKE ?
                ORDER BY updated_at DESC LIMIT ?
                """,
                (f"%{degree}%", f"%{major}%", limit)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ==================== SUBSCRIPTIONS ====================

    async def add_subscription(self, chat_id: int, degree: str, major: str, country: str) -> bool:
        """Subscribes a student to automated alerts for a given major/degree."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    """
                    INSERT INTO subscriptions (chat_id, degree, major, country)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(chat_id, degree, major) DO UPDATE SET
                        country = excluded.country,
                        created_at = CURRENT_TIMESTAMP
                    """,
                    (chat_id, degree, major, country)
                )
                await db.commit()
                return True
            except Exception as e:
                logger.error(f"Error subscribing user {chat_id}: {e}")
                return False

    async def remove_subscription(self, chat_id: int, major: str) -> bool:
        """Unsubscribes a student from a specific major."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM subscriptions WHERE chat_id = ? AND major = ?",
                (chat_id, major)
            )
            await db.commit()
            return True

    async def get_user_subscriptions(self, chat_id: int) -> List[Dict[str, Any]]:
        """Retrieves active subscriptions for a chat ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM subscriptions WHERE chat_id = ?",
                (chat_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_matching_subscribers(self, degree: str, major: str) -> List[int]:
        """Finds all chat IDs subscribed to a given degree and major."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT DISTINCT chat_id FROM subscriptions WHERE degree LIKE ? AND major LIKE ?",
                (f"%{degree}%", f"%{major}%")
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    # ==================== CHANNEL BROADCASTS ====================

    async def is_broadcasted(self, official_url: str) -> bool:
        """Checks if a scholarship URL was already posted to the public channel."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id FROM channel_broadcasts WHERE scholarship_url = ?",
                (official_url,)
            )
            row = await cursor.fetchone()
            return row is not None

    async def mark_broadcasted(self, official_url: str) -> None:
        """Records that a scholarship was broadcasted."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO channel_broadcasts (scholarship_url) VALUES (?)",
                (official_url,)
            )
            await db.commit()

db = Database()
