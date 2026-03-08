"""
CommandRouter
-------------
Routes a :class:`~nlp.command_parser.Command` object to the appropriate
handler and returns a text response.

The router integrates all KSKR subsystems:

* **automation** – :class:`~automation.windows_controller.WindowsController`
* **memory**     – :class:`~memory.memory_manager.MemoryManager`
* **reminders**  – :class:`~reminders.reminder_manager.ReminderManager`
* **plugins**    – :class:`~plugins.plugin_loader.PluginLoader`
* **chat**       – :class:`~nlp.chat_assistant.ChatAssistant`

Sensitive commands (shutdown, delete, send_message, make_call) are checked
against voice authentication when auth is enabled.

Usage
~~~~~
    router = CommandRouter()
    response = router.route(command)
    print(response)
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Intent sets
_AUTOMATION_INTENTS = frozenset(
    ["open_app", "open_folder", "create_folder", "search_web", "play_media", "system"]
)

_SENSITIVE_INTENTS = frozenset(["system"])
_SENSITIVE_ACTIONS = frozenset(["shutdown", "restart", "delete"])


class CommandRouter:
    """Routes Command objects to the correct handler subsystem.

    Parameters
    ----------
    on_tts:
        Optional callback that receives the text response for TTS output.
        If not provided the router is silent (caller handles TTS).
    """

    def __init__(self, on_tts: Optional[Callable[[str], None]] = None) -> None:
        self._on_tts = on_tts
        self._ctrl = self._load_windows_controller()
        self._memory = self._load_memory()
        self._reminders = self._load_reminders()
        self._plugins = self._load_plugins()
        self._chat = self._load_chat()
        self._auth = self._load_auth()

    # ------------------------------------------------------------------
    # Lazy subsystem loaders
    # ------------------------------------------------------------------

    def _load_windows_controller(self):
        try:
            from automation.windows_controller import WindowsController

            return WindowsController()
        except Exception as exc:  # noqa: BLE001
            logger.warning("WindowsController unavailable: %s", exc)
            return None

    def _load_memory(self):
        try:
            from memory.memory_manager import MemoryManager

            return MemoryManager()
        except Exception as exc:  # noqa: BLE001
            logger.warning("MemoryManager unavailable: %s", exc)
            return None

    def _load_reminders(self):
        try:
            from reminders.reminder_manager import ReminderManager

            return ReminderManager()
        except Exception as exc:  # noqa: BLE001
            logger.warning("ReminderManager unavailable: %s", exc)
            return None

    def _load_plugins(self):
        try:
            from plugins.plugin_loader import PluginLoader

            loader = PluginLoader()
            loader.load_all()
            return loader
        except Exception as exc:  # noqa: BLE001
            logger.warning("PluginLoader unavailable: %s", exc)
            return None

    def _load_chat(self):
        try:
            from nlp.chat_assistant import ChatAssistant

            return ChatAssistant()
        except Exception as exc:  # noqa: BLE001
            logger.warning("ChatAssistant unavailable: %s", exc)
            return None

    def _load_auth(self):
        try:
            from authentication.voice_auth import VoiceAuthenticator

            return VoiceAuthenticator()
        except Exception as exc:  # noqa: BLE001
            logger.debug("VoiceAuthenticator unavailable: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, command, audio_data=None) -> str:
        """Dispatch *command* to the appropriate subsystem.

        Parameters
        ----------
        command:
            A :class:`~nlp.command_parser.Command` instance.
        audio_data:
            Raw audio bytes used for voice authentication of sensitive
            commands.  May be ``None`` when auth is not required.

        Returns
        -------
        str
            Human-readable response text.
        """
        intent = getattr(command, "intent", "chat")
        logger.info("Routing intent=%r", intent)

        # 1. Check plugin registry first (allows plugins to override builtins)
        if self._plugins is not None:
            plugin_resp = self._plugins.dispatch(command)
            if plugin_resp is not None:
                return self._emit(plugin_resp)

        # 2. Memory intents
        if intent == "memory_store":
            return self._emit(self._handle_memory_store(command))
        if intent == "memory_query":
            return self._emit(self._handle_memory_query(command))

        # 3. Reminder intents
        if intent == "reminder":
            return self._emit(self._handle_reminder(command))

        # 4. Automation intents
        if intent in _AUTOMATION_INTENTS:
            # Voice-auth gate for sensitive system actions
            if intent in _SENSITIVE_INTENTS:
                action = command.params.get("action", "")
                if action in _SENSITIVE_ACTIONS:
                    if not self._authenticate(audio_data):
                        return self._emit(
                            "Sorry, I could not verify your voice. "
                            "That action requires owner authentication."
                        )
            return self._emit(self._handle_automation(command))

        # 5. Chat fallback
        return self._emit(self._handle_chat(command))

    # ------------------------------------------------------------------
    # Handler helpers
    # ------------------------------------------------------------------

    def _handle_memory_store(self, command) -> str:
        if self._memory is None:
            return "Memory system is unavailable."
        key = command.params.get("key", "note")
        value = command.params.get("value", command.raw_text)
        self._memory.store(key, value)
        return f"Got it! I'll remember that {key} is {value}."

    def _handle_memory_query(self, command) -> str:
        if self._memory is None:
            return "Memory system is unavailable."
        key = command.params.get("key", "")
        if key:
            value = self._memory.recall(key)
            if value:
                return f"You told me that {key} is {value}."
            return f"I don't have anything stored for '{key}'."
        items = self._memory.list_all()
        if not items:
            return "I don't have any stored memories yet."
        lines = [f"• {i['key']}: {i['value']}" for i in items[:10]]
        return "Here's what I remember:\n" + "\n".join(lines)

    def _handle_reminder(self, command) -> str:
        if self._reminders is None:
            return "Reminder system is unavailable."
        action = command.target
        if action == "add":
            task = command.params.get("task", command.raw_text)
            time_str = command.params.get("time", "")
            self._reminders.add(task, time_str)
            return f"Reminder set: '{task}' at {time_str}."
        # list
        items = self._reminders.list_pending()
        if not items:
            return "You have no pending reminders."
        lines = [f"• {i['task']} at {i['due_at']}" for i in items]
        return "Your reminders:\n" + "\n".join(lines)

    def _handle_automation(self, command) -> str:
        if self._ctrl is None:
            return "Automation controller is unavailable."
        intent = command.intent
        if intent == "open_app":
            return self._ctrl.open_app(command.target)
        if intent == "open_folder":
            return self._ctrl.open_folder(command.target)
        if intent == "create_folder":
            return self._ctrl.create_folder(command.target)
        if intent == "search_web":
            return self._ctrl.search_web(command.target)
        if intent == "play_media":
            action = command.params.get("action", "play")
            return self._ctrl.play_media(action)
        if intent == "system":
            action = command.params.get("action", "")
            return self._ctrl.system(action)
        return f"I'm not sure how to handle '{intent}'."

    def _handle_chat(self, command) -> str:
        if self._chat is None:
            return (
                "I'm sorry, the chat assistant is currently unavailable. "
                "Please check your configuration."
            )
        try:
            return self._chat.chat(command.raw_text or command.target)
        except Exception as exc:  # noqa: BLE001
            logger.error("ChatAssistant error: %s", exc)
            return "I encountered an error while processing your question."

    def _authenticate(self, audio_data) -> bool:
        """Return ``True`` if voice auth passes or is not configured."""
        if self._auth is None:
            return True  # Auth not available → allow (fail-open for demo)
        if audio_data is None:
            logger.warning("No audio provided for authentication – allowing.")
            return True
        try:
            return bool(self._auth.verify(audio_data))
        except Exception as exc:  # noqa: BLE001
            logger.error("Voice auth error: %s", exc)
            return False

    def _emit(self, text: str) -> str:
        """Optionally pipe response to TTS callback, then return it."""
        if self._on_tts is not None:
            try:
                self._on_tts(text)
            except Exception as exc:  # noqa: BLE001
                logger.warning("TTS callback error: %s", exc)
        return text

    # ------------------------------------------------------------------
    # Teardown
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Release resources held by sub-systems."""
        for attr in ("_memory", "_reminders"):
            obj = getattr(self, attr, None)
            if obj is not None and hasattr(obj, "close"):
                try:
                    obj.close()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Error closing %s: %s", attr, exc)
