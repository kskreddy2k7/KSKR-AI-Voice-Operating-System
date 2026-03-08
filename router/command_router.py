from __future__ import annotations

from core.intent_engine import AIIntent
from nlp.command_parser import Command


class CommandRouter:
    """Routes AI intents to the right execution engine."""

    def __init__(self, controller, phone_api, chat, reminders, memory, plugins) -> None:
        self._controller = controller
        self._phone_api = phone_api
        self._chat = chat
        self._reminders = reminders
        self._memory = memory
        self._plugins = plugins

    def route(self, ai_intent: AIIntent) -> str:
        intent = ai_intent.intent
        params = ai_intent.params

        if intent == "open_application":
            source = params.get("source_intent", "")
            target = params.get("target", "")
            if params.get("device") == "phone" and self._phone_api:
                return self._phone_api.open_mobile_app(target)
            if source == "open_folder":
                return self._controller.open_folder(target)
            if source == "create_folder":
                return self._controller.create_folder(target)
            return self._controller.open_app(target)

        if intent == "call_contact":
            contact = params.get("contact", "")
            return self._phone_api.call_contact(contact) if self._phone_api else f"Calling {contact}."

        if intent == "send_message":
            contact = params.get("contact", "")
            message = params.get("message", "")
            return (
                self._phone_api.send_message_to_contact(contact, message)
                if self._phone_api
                else f"Sending message to {contact}."
            )

        if intent == "search_web":
            return self._controller.search_web(params.get("target", ""))

        if intent == "play_media":
            action = params.get("action", "play")
            target = params.get("target", "")
            if params.get("device") == "phone" and self._phone_api:
                return self._phone_api.control_media(action)
            return self._controller.control_media(action, target)

        if intent == "scroll_feed":
            target = params.get("target", "")
            return self._phone_api.scroll_feed(target) if self._phone_api else f"Scrolling {target}."

        if intent == "system_control":
            source = params.get("source_intent", "")
            if source == "system":
                return self._controller.system_command(params.get("action", ""), params.get("target", ""))
            if source == "reminder":
                return self._handle_reminders(params)
            if source == "create_folder":
                return self._controller.create_folder(params.get("target", ""))
            return "System command received."

        if intent == "chat_query":
            source = params.get("source_intent", "")
            if source == "memory_store":
                return self._memory.store(params.get("target", "note"), params.get("value", ""))
            if source == "memory_query":
                key = params.get("target", "")
                value = self._memory.recall(key)
                return f"Your {key} is {value}." if value else f"I do not have saved info about {key}."

            plugin_response = self._plugins.handle(
                Command(intent="chat", target=ai_intent.raw_text, raw_text=ai_intent.raw_text)
            )
            if plugin_response is not None:
                return plugin_response
            return self._chat.chat(ai_intent.raw_text)

        return "I can help with apps, phone actions, and questions. Please try again."

    def _handle_reminders(self, params: dict) -> str:
        target = params.get("target", "")
        if target == "list":
            items = self._reminders.list_today()
            if not items:
                return "You have no reminders for today."
            return "Your reminders: " + "; ".join([f"{r['task']} at {r['due_at']}" for r in items])
        return self._reminders.add(params.get("task", ""), params.get("time", ""))
