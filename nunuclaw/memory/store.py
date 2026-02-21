"""SQLite memory store — user profiles, task history, conversations, scheduled tasks.

All tables from PRD Section 7.4, async via aiosqlite.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_profile (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    detected_role TEXT,
    primary_language TEXT,
    preferred_channel TEXT,
    timezone TEXT DEFAULT 'Asia/Kolkata',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    profile_data JSON
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    original_message TEXT,
    intent TEXT,
    plan JSON,
    status TEXT,
    result TEXT,
    cost_usd REAL DEFAULT 0.0,
    duration_seconds INTEGER DEFAULT 0,
    model_tiers_used TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    key TEXT,
    value TEXT,
    category TEXT,
    source TEXT,
    confidence REAL DEFAULT 0.5,
    created_at TIMESTAMP,
    last_accessed TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    description TEXT,
    cron_expression TEXT,
    task_message TEXT,
    is_active BOOLEAN DEFAULT 1,
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    role TEXT,
    content TEXT,
    channel TEXT,
    timestamp TIMESTAMP
);
"""


class MemoryStore:
    """SQLite-backed memory store for NunuClaw.

    Stores user profiles, task history, learned memories,
    scheduled tasks, and conversation history.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open the database connection and create tables."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.executescript(_SCHEMA)
        await self._db.commit()
        logger.info(f"Memory store connected: {self.db_path}")

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    # ─── User Profiles ───────────────────────────────────────────

    async def get_user(self, user_id: str) -> dict | None:
        """Get a user profile by ID."""
        if not self._db:
            return None
        cursor = await self._db.execute(
            "SELECT * FROM user_profile WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))
        return None

    async def upsert_user(self, user_id: str, **fields) -> None:
        """Create or update a user profile."""
        if not self._db:
            return
        now = datetime.now(timezone.utc).isoformat()
        existing = await self.get_user(user_id)

        if existing:
            sets = ", ".join(f"{k} = ?" for k in fields)
            vals = list(fields.values()) + [now, user_id]
            await self._db.execute(
                f"UPDATE user_profile SET {sets}, updated_at = ? WHERE user_id = ?", vals
            )
        else:
            fields["user_id"] = user_id
            fields["created_at"] = now
            fields["updated_at"] = now
            cols = ", ".join(fields.keys())
            placeholders = ", ".join("?" for _ in fields)
            await self._db.execute(
                f"INSERT INTO user_profile ({cols}) VALUES ({placeholders})",
                list(fields.values()),
            )
        await self._db.commit()

    # ─── Task History ────────────────────────────────────────────

    async def save_task(
        self,
        task_id: str,
        user_id: str,
        message: str,
        intent: str,
        status: str,
        result: str = "",
        cost: float = 0.0,
        duration: int = 0,
    ) -> None:
        """Save a completed task to history."""
        if not self._db:
            return
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            """INSERT OR REPLACE INTO tasks 
               (id, user_id, original_message, intent, status, result, cost_usd, 
                duration_seconds, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, user_id, message, intent, status, result, cost, duration, now, now),
        )
        await self._db.commit()

    async def get_recent_tasks(self, user_id: str, limit: int = 10) -> list[dict]:
        """Get recent tasks for a user."""
        if not self._db:
            return []
        cursor = await self._db.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in rows]

    # ─── Conversation History ────────────────────────────────────

    async def add_conversation(
        self, user_id: str, role: str, content: str, channel: str
    ) -> None:
        """Add a conversation turn."""
        if not self._db:
            return
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "INSERT INTO conversations (user_id, role, content, channel, timestamp) VALUES (?,?,?,?,?)",
            (user_id, role, content, channel, now),
        )
        await self._db.commit()

    async def get_conversation_history(
        self, user_id: str, limit: int = 20
    ) -> list[dict]:
        """Get recent conversation history for a user."""
        if not self._db:
            return []
        cursor = await self._db.execute(
            "SELECT role, content, timestamp FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in reversed(rows)]

    # ─── Persistent Memory ───────────────────────────────────────

    async def remember(
        self, user_id: str, key: str, value: str, category: str = "fact", source: str = "user_stated"
    ) -> None:
        """Store a persistent memory fact."""
        if not self._db:
            return
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            """INSERT INTO memory (user_id, key, value, category, source, confidence, created_at, last_accessed)
               VALUES (?, ?, ?, ?, ?, 1.0, ?, ?)""",
            (user_id, key, value, category, source, now, now),
        )
        await self._db.commit()

    async def recall(self, user_id: str, query: str = "") -> list[dict]:
        """Recall memories for a user, optionally filtered by query."""
        if not self._db:
            return []
        if query:
            cursor = await self._db.execute(
                "SELECT key, value, category FROM memory WHERE user_id = ? AND (key LIKE ? OR value LIKE ?)",
                (user_id, f"%{query}%", f"%{query}%"),
            )
        else:
            cursor = await self._db.execute(
                "SELECT key, value, category FROM memory WHERE user_id = ? ORDER BY last_accessed DESC LIMIT 20",
                (user_id,),
            )
        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in rows]
