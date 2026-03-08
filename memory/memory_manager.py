"""
Memory Manager
--------------
Stores and retrieves user preferences, facts, and notes using an SQLite
database.

The memory is key-value based with an optional *category* tag so the
assistant can query broad topics (e.g. "what do you know about my hobbies?").
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "settings.json"
)


def _load_db_path() -> str:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh).get("memory", {}).get("db_path", "memory/kskr_memory.db")
    except Exception:
        return "memory/kskr_memory.db"


class MemoryManager:
    """Persistent key-value memory backed by SQLite.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  Directories are created
        automatically.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or _load_db_path()
        os.makedirs(os.path.dirname(os.path.abspath(self._db_path)), exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._create_tables()
        logger.info("MemoryManager: connected to %s", self._db_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(self, key: str, value: str, category: str = "general") -> str:
        """Store or update a memory entry.

        Parameters
        ----------
        key:    The memory key (e.g. ``"favorite language"``).
        value:  The value to store (e.g. ``"Python"``).
        category:  Optional grouping tag.
        Returns the confirmation message.
        """
        key = key.strip().lower()
        value = value.strip()
        category = category.strip().lower()
        now = datetime.now(timezone.utc).isoformat()
        try:
            self._conn.execute(
                """
                INSERT INTO memory (key, value, category, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value      = excluded.value,
                    category   = excluded.category,
                    updated_at = excluded.updated_at
                """,
                (key, value, category, now),
            )
            self._conn.commit()
            logger.info("MemoryManager: stored [%s] = %s", key, value)
            return f"Got it! I'll remember that your {key} is {value}."
        except Exception as exc:
            logger.error("MemoryManager: store failed – %s", exc)
            return "Sorry, I couldn't save that to memory."

    def recall(self, key: str) -> Optional[str]:
        """Look up a memory entry by *key*.  Returns the value or *None*."""
        key = key.strip().lower()
        try:
            cur = self._conn.execute(
                "SELECT value FROM memory WHERE key = ?", (key,)
            )
            row = cur.fetchone()
            if row:
                logger.info("MemoryManager: recalled [%s] = %s", key, row[0])
                return row[0]
            # Fuzzy: look for keys that *contain* the query
            cur = self._conn.execute(
                "SELECT key, value FROM memory WHERE key LIKE ?", (f"%{key}%",)
            )
            rows = cur.fetchall()
            if rows:
                parts = [f"{r[0]}: {r[1]}" for r in rows]
                return "; ".join(parts)
            return None
        except Exception as exc:
            logger.error("MemoryManager: recall failed – %s", exc)
            return None

    def list_all(self, category: Optional[str] = None) -> list[dict]:
        """Return all memories, optionally filtered by *category*."""
        try:
            if category:
                cur = self._conn.execute(
                    "SELECT key, value, category, updated_at FROM memory WHERE category = ? ORDER BY updated_at DESC",
                    (category.lower(),),
                )
            else:
                cur = self._conn.execute(
                    "SELECT key, value, category, updated_at FROM memory ORDER BY updated_at DESC"
                )
            return [
                {"key": r[0], "value": r[1], "category": r[2], "updated_at": r[3]}
                for r in cur.fetchall()
            ]
        except Exception as exc:
            logger.error("MemoryManager: list_all failed – %s", exc)
            return []

    def delete(self, key: str) -> bool:
        """Delete a memory entry by *key*.  Returns *True* if deleted."""
        try:
            cur = self._conn.execute("DELETE FROM memory WHERE key = ?", (key.lower(),))
            self._conn.commit()
            deleted = cur.rowcount > 0
            if deleted:
                logger.info("MemoryManager: deleted [%s]", key)
            return deleted
        except Exception as exc:
            logger.error("MemoryManager: delete failed – %s", exc)
            return False

    def clear_all(self) -> None:
        """Remove all stored memories (irreversible)."""
        self._conn.execute("DELETE FROM memory")
        self._conn.commit()
        logger.info("MemoryManager: all memories cleared.")

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                key         TEXT PRIMARY KEY,
                value       TEXT NOT NULL,
                category    TEXT DEFAULT 'general',
                updated_at  TEXT NOT NULL
            )
            """
        )
        self._conn.commit()
