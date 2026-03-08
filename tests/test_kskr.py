"""
Unit tests for KSKR Voice OS subsystems.

Run with:
    python -m pytest tests/ -v
"""

import os
import sys
import json
import sqlite3
import tempfile
import pytest

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ─────────────────────────────────────────────────────────────────────────────
# NLP / Command Parser
# ─────────────────────────────────────────────────────────────────────────────

from nlp.command_parser import CommandParser, Command


@pytest.fixture
def parser():
    return CommandParser()


class TestCommandParser:
    def test_open_app(self, parser):
        cmd = parser.parse("open chrome")
        assert cmd.intent == "open_app"
        assert "chrome" in cmd.target.lower()

    def test_open_app_launch(self, parser):
        cmd = parser.parse("launch Visual Studio Code")
        assert cmd.intent == "open_app"
        assert "visual studio code" in cmd.target.lower()

    def test_search_web(self, parser):
        cmd = parser.parse("search machine learning tutorials")
        assert cmd.intent == "search_web"
        assert "machine learning" in cmd.target.lower()

    def test_google_search(self, parser):
        cmd = parser.parse("google how to learn Python")
        assert cmd.intent == "search_web"
        assert "python" in cmd.target.lower()

    def test_create_folder(self, parser):
        cmd = parser.parse("create a folder called AI project")
        assert cmd.intent == "create_folder"
        assert "ai project" in cmd.target.lower()

    def test_create_folder_make(self, parser):
        cmd = parser.parse("make a new folder named test")
        assert cmd.intent == "create_folder"

    def test_open_folder(self, parser):
        cmd = parser.parse("open the downloads folder")
        assert cmd.intent == "open_folder"
        assert "downloads" in cmd.target.lower()

    def test_reminder_add(self, parser):
        cmd = parser.parse("remind me to study AI at 7 PM")
        assert cmd.intent == "reminder"
        assert cmd.target == "add"
        assert "study ai" in cmd.params["task"].lower()
        assert "7 pm" in cmd.params["time"].lower()

    def test_reminder_list(self, parser):
        cmd = parser.parse("what tasks do I have today")
        assert cmd.intent == "reminder"
        assert cmd.target == "list"

    def test_memory_store(self, parser):
        cmd = parser.parse("my favorite programming language is Python")
        assert cmd.intent == "memory_store"
        assert "python" in cmd.params["value"].lower()

    def test_memory_query(self, parser):
        cmd = parser.parse("what is my favorite programming language")
        assert cmd.intent == "memory_query"

    def test_media_play(self, parser):
        cmd = parser.parse("play music")
        assert cmd.intent == "play_media"
        assert cmd.params["action"] == "play"

    def test_media_pause(self, parser):
        cmd = parser.parse("pause")
        assert cmd.intent == "play_media"
        assert cmd.params["action"] == "pause"

    def test_media_volume_up(self, parser):
        cmd = parser.parse("volume up")
        assert cmd.intent == "play_media"
        assert cmd.params["action"] == "volume_up"

    def test_system_shutdown(self, parser):
        cmd = parser.parse("shutdown the computer")
        assert cmd.intent == "system"
        assert cmd.params["action"] == "shutdown"

    def test_system_screenshot(self, parser):
        cmd = parser.parse("take a screenshot")
        assert cmd.intent == "system"
        assert cmd.params["action"] == "screenshot"

    def test_fallback_chat(self, parser):
        cmd = parser.parse("What is machine learning?")
        assert cmd.intent == "chat"

    def test_chat_general(self, parser):
        cmd = parser.parse("Tell me a joke")
        # Could be caught by joke plugin intent or chat
        assert cmd.intent in ("chat", "joke")


# ─────────────────────────────────────────────────────────────────────────────
# Memory Manager
# ─────────────────────────────────────────────────────────────────────────────

from memory.memory_manager import MemoryManager


@pytest.fixture
def memory(tmp_path):
    db_path = str(tmp_path / "test_memory.db")
    mgr = MemoryManager(db_path=db_path)
    yield mgr
    mgr.close()


class TestMemoryManager:
    def test_store_and_recall(self, memory):
        memory.store("favorite language", "Python")
        result = memory.recall("favorite language")
        assert result == "Python"

    def test_recall_missing(self, memory):
        result = memory.recall("nonexistent_key_xyz")
        assert result is None

    def test_update_existing(self, memory):
        memory.store("color", "blue")
        memory.store("color", "green")
        assert memory.recall("color") == "green"

    def test_list_all(self, memory):
        memory.store("name", "KSKR")
        memory.store("city", "Hyderabad")
        items = memory.list_all()
        assert len(items) >= 2
        keys = [i["key"] for i in items]
        assert "name" in keys
        assert "city" in keys

    def test_delete(self, memory):
        memory.store("temp_key", "temp_value")
        assert memory.recall("temp_key") == "temp_value"
        deleted = memory.delete("temp_key")
        assert deleted is True
        assert memory.recall("temp_key") is None

    def test_delete_nonexistent(self, memory):
        result = memory.delete("does_not_exist")
        assert result is False

    def test_clear_all(self, memory):
        memory.store("k1", "v1")
        memory.store("k2", "v2")
        memory.clear_all()
        assert memory.list_all() == []

    def test_fuzzy_recall(self, memory):
        memory.store("favorite food", "biryani")
        result = memory.recall("food")
        assert result is not None
        assert "biryani" in result


# ─────────────────────────────────────────────────────────────────────────────
# Reminder Manager
# ─────────────────────────────────────────────────────────────────────────────

from reminders.reminder_manager import ReminderManager, _parse_time_str
from datetime import datetime, timedelta


class TestTimeParser:
    def test_am_pm(self):
        t = _parse_time_str("7 PM")
        assert t is not None
        assert t.hour == 19
        assert t.minute == 0

    def test_am_pm_minutes(self):
        t = _parse_time_str("9:30 AM")
        assert t is not None
        assert t.hour == 9
        assert t.minute == 30

    def test_24h(self):
        t = _parse_time_str("14:45")
        assert t is not None
        assert t.hour == 14
        assert t.minute == 45

    def test_midnight_am(self):
        t = _parse_time_str("12 AM")
        assert t is not None
        assert t.hour == 0

    def test_noon_pm(self):
        t = _parse_time_str("12 PM")
        assert t is not None
        assert t.hour == 12

    def test_invalid(self):
        t = _parse_time_str("invalid time string")
        assert t is None


@pytest.fixture
def reminders(tmp_path):
    db_path = str(tmp_path / "test_reminders.db")
    mgr = ReminderManager(db_path=db_path, check_interval=9999)
    yield mgr
    mgr.close()


class TestReminderManager:
    def test_add_and_list(self, reminders):
        reminders.add("Study AI", "23:59")
        items = reminders.list_pending()
        assert len(items) >= 1
        assert any("Study AI" in i["task"] for i in items)

    def test_complete(self, reminders):
        reminders.add("Exercise", "23:59")
        items = reminders.list_pending()
        rid = items[-1]["id"]
        result = reminders.complete(rid)
        assert result is True
        # Should no longer be pending
        still_pending = [i for i in reminders.list_pending() if i["id"] == rid]
        assert still_pending == []

    def test_delete(self, reminders):
        reminders.add("Read book", "23:59")
        items = reminders.list_pending()
        rid = items[-1]["id"]
        reminders.delete(rid)
        still_there = [i for i in reminders.list_pending() if i["id"] == rid]
        assert still_there == []

    def test_due_callback(self, tmp_path):
        """Reminder that is immediately due should trigger the callback."""
        fired = []
        db_path = str(tmp_path / "cb_reminders.db")
        mgr = ReminderManager(
            on_due=lambda r: fired.append(r),
            db_path=db_path,
            check_interval=9999,
        )
        # Insert a reminder that is already overdue
        past = (datetime.now() - timedelta(minutes=5)).isoformat(timespec="minutes")
        mgr._conn.execute(
            "INSERT INTO reminders (task, due_at, done) VALUES (?, ?, 0)",
            ("past task", past),
        )
        mgr._conn.commit()
        mgr._check_due()
        assert len(fired) == 1
        assert fired[0]["task"] == "past task"
        mgr.close()


# ─────────────────────────────────────────────────────────────────────────────
# Plugin Loader
# ─────────────────────────────────────────────────────────────────────────────

from plugins.plugin_loader import PluginLoader


class TestPluginLoader:
    def test_load_bundled_plugins(self):
        """Weather, jokes, and time plugins should load from the plugins dir."""
        loader = PluginLoader()
        loaded = loader.load_all()
        assert len(loaded) > 0

    def test_time_plugin(self):
        from plugins.time_plugin import handle as time_handle
        from nlp.command_parser import Command

        cmd = Command(intent="time", raw_text="what time is it")
        result = time_handle(cmd)
        assert "time" in result.lower() or ":" in result

    def test_jokes_plugin(self):
        from plugins.jokes_plugin import handle as joke_handle
        from nlp.command_parser import Command

        cmd = Command(intent="joke", raw_text="tell me a joke")
        result = joke_handle(cmd)
        assert isinstance(result, str) and len(result) > 10


# ─────────────────────────────────────────────────────────────────────────────
# Chat Assistant (fallback mode – no network required)
# ─────────────────────────────────────────────────────────────────────────────

from nlp.chat_assistant import ChatAssistant


class TestChatAssistant:
    def test_greeting(self):
        chat = ChatAssistant()
        # Force fallback backend
        chat._backend = "fallback"
        resp = chat.chat("hello")
        assert resp
        assert isinstance(resp, str)

    def test_machine_learning_topic(self):
        chat = ChatAssistant()
        chat._backend = "fallback"
        resp = chat.chat("what is machine learning")
        assert "machine learning" in resp.lower() or "learn" in resp.lower()

    def test_history_clears(self):
        chat = ChatAssistant()
        chat._backend = "fallback"
        chat.chat("hello")
        assert len(chat._history) == 2  # user + assistant
        chat.clear_history()
        assert chat._history == []


# ─────────────────────────────────────────────────────────────────────────────
# Windows Controller (no-op tests – avoids launching real processes)
# ─────────────────────────────────────────────────────────────────────────────

from automation.windows_controller import WindowsController


class TestWindowsController:
    def test_create_folder(self, tmp_path):
        ctrl = WindowsController()
        result = ctrl.create_folder("test_folder_kskr", parent=str(tmp_path))
        assert "created" in result.lower() or "test_folder_kskr" in result

    def test_create_folder_already_exists(self, tmp_path):
        ctrl = WindowsController()
        ctrl.create_folder("dupe_folder", parent=str(tmp_path))
        result = ctrl.create_folder("dupe_folder", parent=str(tmp_path))
        assert "already exists" in result.lower()

    def test_open_folder_unknown(self):
        ctrl = WindowsController()
        result = ctrl.open_folder("nonexistent_folder_xyz_kskr")
        assert "not found" in result.lower()

    def test_search_web_builds_url(self, monkeypatch):
        opened_urls = []
        import webbrowser
        monkeypatch.setattr(webbrowser, "open", lambda url: opened_urls.append(url))
        ctrl = WindowsController()
        result = ctrl.search_web("Python tutorials")
        assert "python" in result.lower() or "searching" in result.lower()
        assert len(opened_urls) == 1
        assert "Python" in opened_urls[0] or "python" in opened_urls[0].lower()
