"""
test_commands.py
----------------
Tests for the CommandRouter and the core IntentEngine integration.

These tests exercise the full routing pipeline without requiring
hardware (microphone, speakers) or a network connection.

Run with:
    python -m pytest tests/test_commands.py -v
"""

from __future__ import annotations

import sys
import os
import unittest.mock as mock

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

from nlp.command_parser import Command


# ---------------------------------------------------------------------------
# CommandRouter – unit tests
# ---------------------------------------------------------------------------

class TestCommandRouterChat:
    """Test that unknown / chat intents are forwarded to ChatAssistant."""

    def _make_router_with_mock_chat(self):
        from router.command_router import CommandRouter

        router = CommandRouter.__new__(CommandRouter)
        router._on_tts = None
        router._ctrl = None
        router._memory = None
        router._reminders = None
        router._plugins = None
        router._auth = None
        chat_mock = mock.MagicMock()
        chat_mock.chat.return_value = "Machine learning is a subset of AI."
        router._chat = chat_mock
        return router, chat_mock

    def test_chat_intent_delegated(self):
        router, chat_mock = self._make_router_with_mock_chat()
        cmd = Command(intent="chat", raw_text="what is machine learning")
        response = router.route(cmd)
        chat_mock.chat.assert_called_once_with("what is machine learning")
        assert "machine learning" in response.lower() or isinstance(response, str)

    def test_chat_fallback_when_assistant_unavailable(self):
        from router.command_router import CommandRouter

        router = CommandRouter.__new__(CommandRouter)
        router._on_tts = None
        router._ctrl = None
        router._memory = None
        router._reminders = None
        router._plugins = None
        router._auth = None
        router._chat = None  # unavailable

        cmd = Command(intent="chat", raw_text="tell me a joke")
        response = router.route(cmd)
        assert isinstance(response, str)
        assert len(response) > 0


class TestCommandRouterAutomation:
    """Test that automation intents are dispatched to WindowsController."""

    def _make_router_with_mock_ctrl(self):
        from router.command_router import CommandRouter

        router = CommandRouter.__new__(CommandRouter)
        router._on_tts = None
        router._memory = None
        router._reminders = None
        router._plugins = None
        router._auth = None
        router._chat = None
        ctrl_mock = mock.MagicMock()
        ctrl_mock.open_app.return_value = "Opening Chrome."
        ctrl_mock.search_web.return_value = "Searching the web for Python."
        ctrl_mock.create_folder.return_value = "Folder 'AI' created."
        ctrl_mock.open_folder.return_value = "Opening Downloads."
        ctrl_mock.play_media.return_value = "Playing media."
        ctrl_mock.system.return_value = "Taking screenshot."
        router._ctrl = ctrl_mock
        return router, ctrl_mock

    def test_open_app_routed(self):
        router, ctrl_mock = self._make_router_with_mock_ctrl()
        cmd = Command(intent="open_app", target="chrome", raw_text="open chrome")
        response = router.route(cmd)
        ctrl_mock.open_app.assert_called_once_with("chrome")

    def test_search_web_routed(self):
        router, ctrl_mock = self._make_router_with_mock_ctrl()
        cmd = Command(intent="search_web", target="Python tutorials",
                      raw_text="search python tutorials")
        response = router.route(cmd)
        ctrl_mock.search_web.assert_called_once_with("Python tutorials")

    def test_create_folder_routed(self):
        router, ctrl_mock = self._make_router_with_mock_ctrl()
        cmd = Command(intent="create_folder", target="AI",
                      raw_text="create folder AI")
        response = router.route(cmd)
        ctrl_mock.create_folder.assert_called_once_with("AI")

    def test_open_folder_routed(self):
        router, ctrl_mock = self._make_router_with_mock_ctrl()
        cmd = Command(intent="open_folder", target="downloads",
                      raw_text="open downloads")
        response = router.route(cmd)
        ctrl_mock.open_folder.assert_called_once_with("downloads")

    def test_play_media_routed(self):
        router, ctrl_mock = self._make_router_with_mock_ctrl()
        cmd = Command(intent="play_media", params={"action": "play"},
                      raw_text="play music")
        response = router.route(cmd)
        ctrl_mock.play_media.assert_called_once_with("play")

    def test_system_screenshot_no_auth_needed(self):
        router, ctrl_mock = self._make_router_with_mock_ctrl()
        cmd = Command(intent="system", params={"action": "screenshot"},
                      raw_text="take a screenshot")
        response = router.route(cmd)
        ctrl_mock.system.assert_called_once_with("screenshot")

    def test_ctrl_unavailable_returns_message(self):
        from router.command_router import CommandRouter

        router = CommandRouter.__new__(CommandRouter)
        router._on_tts = None
        router._ctrl = None
        router._memory = None
        router._reminders = None
        router._plugins = None
        router._auth = None
        router._chat = None

        cmd = Command(intent="open_app", target="notepad",
                      raw_text="open notepad")
        response = router.route(cmd)
        assert "unavailable" in response.lower()


class TestCommandRouterMemory:
    """Test memory store and query routing."""

    def _make_router_with_mock_memory(self):
        from router.command_router import CommandRouter

        router = CommandRouter.__new__(CommandRouter)
        router._on_tts = None
        router._ctrl = None
        router._reminders = None
        router._plugins = None
        router._auth = None
        router._chat = None
        mem_mock = mock.MagicMock()
        mem_mock.recall.return_value = "Python"
        mem_mock.list_all.return_value = [{"key": "language", "value": "Python"}]
        router._memory = mem_mock
        return router, mem_mock

    def test_memory_store_calls_store(self):
        router, mem_mock = self._make_router_with_mock_memory()
        cmd = Command(
            intent="memory_store",
            params={"key": "favorite language", "value": "Python"},
            raw_text="my favorite language is Python",
        )
        response = router.route(cmd)
        mem_mock.store.assert_called_once_with("favorite language", "Python")
        assert "python" in response.lower()

    def test_memory_query_calls_recall(self):
        router, mem_mock = self._make_router_with_mock_memory()
        cmd = Command(
            intent="memory_query",
            params={"key": "favorite language"},
            raw_text="what is my favorite language",
        )
        response = router.route(cmd)
        mem_mock.recall.assert_called_once_with("favorite language")
        assert "python" in response.lower()

    def test_memory_query_missing_key_lists_all(self):
        router, mem_mock = self._make_router_with_mock_memory()
        cmd = Command(
            intent="memory_query",
            params={},  # no key
            raw_text="what do you know about me",
        )
        response = router.route(cmd)
        mem_mock.list_all.assert_called_once()

    def test_memory_unavailable_returns_message(self):
        from router.command_router import CommandRouter

        router = CommandRouter.__new__(CommandRouter)
        router._on_tts = None
        router._ctrl = None
        router._memory = None
        router._reminders = None
        router._plugins = None
        router._auth = None
        router._chat = None

        cmd = Command(intent="memory_store", params={"key": "x", "value": "y"})
        response = router.route(cmd)
        assert "unavailable" in response.lower()


class TestCommandRouterReminders:
    """Test reminder routing."""

    def _make_router_with_mock_reminders(self):
        from router.command_router import CommandRouter

        router = CommandRouter.__new__(CommandRouter)
        router._on_tts = None
        router._ctrl = None
        router._memory = None
        router._plugins = None
        router._auth = None
        router._chat = None
        rem_mock = mock.MagicMock()
        rem_mock.list_pending.return_value = [
            {"task": "Study AI", "due_at": "2026-03-08T19:00"}
        ]
        router._reminders = rem_mock
        return router, rem_mock

    def test_reminder_add(self):
        router, rem_mock = self._make_router_with_mock_reminders()
        cmd = Command(
            intent="reminder",
            target="add",
            params={"task": "study AI", "time": "7 PM"},
            raw_text="remind me to study AI at 7 PM",
        )
        response = router.route(cmd)
        rem_mock.add.assert_called_once_with("study AI", "7 PM")
        assert "reminder" in response.lower() or "study ai" in response.lower()

    def test_reminder_list(self):
        router, rem_mock = self._make_router_with_mock_reminders()
        cmd = Command(
            intent="reminder",
            target="list",
            raw_text="what reminders do I have",
        )
        response = router.route(cmd)
        rem_mock.list_pending.assert_called_once()
        assert "study ai" in response.lower()


class TestCommandRouterTtsCallback:
    """Test that the on_tts callback is invoked."""

    def test_tts_callback_called(self):
        from router.command_router import CommandRouter

        spoken = []
        router = CommandRouter.__new__(CommandRouter)
        router._on_tts = lambda t: spoken.append(t)
        router._ctrl = None
        router._memory = None
        router._reminders = None
        router._plugins = None
        router._auth = None
        chat_mock = mock.MagicMock()
        chat_mock.chat.return_value = "Hello there!"
        router._chat = chat_mock

        cmd = Command(intent="chat", raw_text="hello")
        router.route(cmd)
        assert spoken == ["Hello there!"]


class TestCommandRouterAuth:
    """Sensitive commands should fail when voice auth returns False."""

    def test_sensitive_system_blocked_when_auth_fails(self):
        from router.command_router import CommandRouter

        router = CommandRouter.__new__(CommandRouter)
        router._on_tts = None
        ctrl_mock = mock.MagicMock()
        ctrl_mock.system.return_value = "Shutting down."
        router._ctrl = ctrl_mock
        router._memory = None
        router._reminders = None
        router._plugins = None
        router._chat = None
        auth_mock = mock.MagicMock()
        auth_mock.verify.return_value = False
        router._auth = auth_mock

        cmd = Command(
            intent="system",
            params={"action": "shutdown"},
            raw_text="shutdown the computer",
        )
        response = router.route(cmd, audio_data=b"fake_audio")
        # Controller should NOT have been called
        ctrl_mock.system.assert_not_called()
        assert "verify" in response.lower() or "authentication" in response.lower()

    def test_non_sensitive_system_allowed_without_auth(self):
        from router.command_router import CommandRouter

        router = CommandRouter.__new__(CommandRouter)
        router._on_tts = None
        ctrl_mock = mock.MagicMock()
        ctrl_mock.system.return_value = "Screenshot taken."
        router._ctrl = ctrl_mock
        router._memory = None
        router._reminders = None
        router._plugins = None
        router._auth = None
        router._chat = None

        cmd = Command(
            intent="system",
            params={"action": "screenshot"},
            raw_text="take a screenshot",
        )
        response = router.route(cmd)
        ctrl_mock.system.assert_called_once_with("screenshot")


class TestCommandRouterIntegration:
    """End-to-end: parse text with IntentEngine then route."""

    def test_open_chrome_end_to_end(self, monkeypatch, tmp_path):
        from core.intent_engine import IntentEngine
        from router.command_router import CommandRouter

        intent_engine = IntentEngine()
        cmd = intent_engine.parse("open Chrome")
        assert cmd.intent == "open_app"

        router = CommandRouter.__new__(CommandRouter)
        router._on_tts = None
        router._memory = None
        router._reminders = None
        router._plugins = None
        router._auth = None
        router._chat = None
        ctrl_mock = mock.MagicMock()
        ctrl_mock.open_app.return_value = "Opening Chrome."
        router._ctrl = ctrl_mock

        response = router.route(cmd)
        ctrl_mock.open_app.assert_called_once()
        assert isinstance(response, str)

    def test_search_web_end_to_end(self, monkeypatch):
        from core.intent_engine import IntentEngine
        from router.command_router import CommandRouter

        intent_engine = IntentEngine()
        cmd = intent_engine.parse("search python tutorials")
        assert cmd.intent == "search_web"

        router = CommandRouter.__new__(CommandRouter)
        router._on_tts = None
        router._memory = None
        router._reminders = None
        router._plugins = None
        router._auth = None
        router._chat = None
        ctrl_mock = mock.MagicMock()
        ctrl_mock.search_web.return_value = "Searching..."
        router._ctrl = ctrl_mock

        response = router.route(cmd)
        ctrl_mock.search_web.assert_called_once()

    def test_reminder_end_to_end(self, tmp_path):
        from core.intent_engine import IntentEngine
        from router.command_router import CommandRouter

        intent_engine = IntentEngine()
        cmd = intent_engine.parse("remind me to study AI at 7 PM")
        assert cmd.intent == "reminder"
        assert cmd.target == "add"

        router = CommandRouter.__new__(CommandRouter)
        router._on_tts = None
        router._ctrl = None
        router._plugins = None
        router._auth = None
        router._chat = None
        rem_mock = mock.MagicMock()
        rem_mock.list_pending.return_value = []
        router._reminders = rem_mock
        router._memory = None

        response = router.route(cmd)
        rem_mock.add.assert_called_once()
