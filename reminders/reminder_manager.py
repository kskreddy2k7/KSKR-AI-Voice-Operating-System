"""
Reminder Manager
----------------
Stores one-off reminders and periodic tasks in an SQLite database and fires
callbacks when they become due.

Usage
~~~~~
::

    rm = ReminderManager(on_due=lambda r: print(f"Due: {r}"))
    rm.add("Study AI", "19:00")   # "7 PM" or "19:00" or ISO datetime
    rm.start()                    # background check thread
    ...
    rm.stop()
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
import time
from datetime import date, datetime, timedelta
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "settings.json"
)

# Time-string patterns
_TIME_PATTERNS = [
    # "7 PM" / "7:30 PM" / "7:30 am"
    (r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", "%I:%M %p"),
    # "19:00" / "07:30"
    (r"(\d{1,2}):(\d{2})\s*$", "%H:%M"),
    # "19" – bare hour in 24-h
    (r"^(\d{1,2})\s*$", "%H"),
]


def _parse_time_str(time_str: str) -> Optional[datetime]:
    """Convert a natural-language time string to a :class:`datetime` today."""
    s = time_str.strip().lower()

    # Already ISO?
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%H:%M"):
        try:
            t = datetime.strptime(s, fmt)
            if t.year == 1900:
                now = datetime.now()
                t = t.replace(year=now.year, month=now.month, day=now.day)
            return t
        except ValueError:
            pass

    # "h PM" / "h:mm PM"
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", s, re.IGNORECASE)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or "0")
        meridiem = m.group(3).lower()
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        now = datetime.now()
        t = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if t <= now:
            t += timedelta(days=1)
        return t

    # bare 24-h hour
    m = re.match(r"^(\d{1,2})$", s)
    if m:
        now = datetime.now()
        t = now.replace(hour=int(m.group(1)), minute=0, second=0, microsecond=0)
        if t <= now:
            t += timedelta(days=1)
        return t

    return None


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh).get("reminders", {})
    except Exception:
        return {}


class ReminderManager:
    """Manage reminders with SQLite persistence and background polling.

    Parameters
    ----------
    on_due:
        Callback fired when a reminder is due.  Receives the reminder dict.
    db_path:
        Override the SQLite file path.
    check_interval:
        Seconds between due-time checks.
    """

    def __init__(
        self,
        on_due: Optional[Callable[[dict], None]] = None,
        db_path: Optional[str] = None,
        check_interval: Optional[int] = None,
    ) -> None:
        cfg = _load_config()
        self._on_due = on_due or (lambda r: logger.info("Reminder due: %s", r))
        _db = db_path or os.path.join("memory", "kskr_memory.db")
        os.makedirs(os.path.dirname(os.path.abspath(_db)), exist_ok=True)
        self._conn = sqlite3.connect(_db, check_same_thread=False)
        self._create_tables()
        self._check_interval: int = check_interval or cfg.get("check_interval_seconds", 30)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        logger.info("ReminderManager: initialised (interval=%ds).", self._check_interval)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, task: str, time_str: str = "") -> str:
        """Add a new reminder.

        Parameters
        ----------
        task:     Description of the task.
        time_str: Time expression such as ``"7 PM"``, ``"19:00"``, or an ISO
                  datetime string.  If empty the reminder fires immediately.
        Returns a human-readable confirmation string.
        """
        if time_str:
            due_dt = _parse_time_str(time_str)
            if due_dt is None:
                return (
                    f"Sorry, I couldn't parse the time '{time_str}'. "
                    "Please say something like '7 PM' or '19:00'."
                )
            due_iso = due_dt.isoformat(timespec="minutes")
        else:
            due_iso = datetime.now().isoformat(timespec="minutes")

        try:
            self._conn.execute(
                "INSERT INTO reminders (task, due_at, done) VALUES (?, ?, 0)",
                (task, due_iso),
            )
            self._conn.commit()
            logger.info("ReminderManager: added '%s' due %s", task, due_iso)
            return f"Reminder set: '{task}' at {due_iso}."
        except Exception as exc:
            logger.error("ReminderManager: add failed – %s", exc)
            return "Sorry, I couldn't save the reminder."

    def list_pending(self) -> list[dict]:
        """Return all pending (not done) reminders."""
        try:
            cur = self._conn.execute(
                "SELECT id, task, due_at FROM reminders WHERE done = 0 ORDER BY due_at"
            )
            return [{"id": r[0], "task": r[1], "due_at": r[2]} for r in cur.fetchall()]
        except Exception as exc:
            logger.error("ReminderManager: list_pending failed – %s", exc)
            return []

    def list_today(self) -> list[dict]:
        """Return reminders due today."""
        today = date.today().isoformat()
        try:
            cur = self._conn.execute(
                "SELECT id, task, due_at FROM reminders WHERE done = 0 AND due_at LIKE ?",
                (f"{today}%",),
            )
            return [{"id": r[0], "task": r[1], "due_at": r[2]} for r in cur.fetchall()]
        except Exception:
            return []

    def complete(self, reminder_id: int) -> bool:
        """Mark a reminder as done."""
        try:
            self._conn.execute(
                "UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,)
            )
            self._conn.commit()
            return True
        except Exception:
            return False

    def delete(self, reminder_id: int) -> bool:
        """Delete a reminder."""
        try:
            self._conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            self._conn.commit()
            return True
        except Exception:
            return False

    def start(self) -> None:
        """Start the background polling thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="ReminderPoller")
        self._thread.start()
        logger.info("ReminderManager: background poller started.")

    def stop(self) -> None:
        """Stop the background polling thread."""
        self._running = False
        logger.info("ReminderManager: stopped.")

    def close(self) -> None:
        """Stop polling and close the database connection."""
        self.stop()
        self._conn.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _poll_loop(self) -> None:
        while self._running:
            self._check_due()
            time.sleep(self._check_interval)

    def _check_due(self) -> None:
        now_str = datetime.now().isoformat(timespec="minutes")
        try:
            cur = self._conn.execute(
                "SELECT id, task, due_at FROM reminders WHERE done = 0 AND due_at <= ?",
                (now_str,),
            )
            rows = cur.fetchall()
            for row in rows:
                reminder = {"id": row[0], "task": row[1], "due_at": row[2]}
                logger.info("ReminderManager: firing reminder %s", reminder)
                try:
                    self._on_due(reminder)
                except Exception as exc:
                    logger.error("ReminderManager: on_due callback error – %s", exc)
                self.complete(row[0])
        except Exception as exc:
            logger.error("ReminderManager: _check_due error – %s", exc)

    def _create_tables(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                task    TEXT    NOT NULL,
                due_at  TEXT    NOT NULL,
                done    INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self._conn.commit()
