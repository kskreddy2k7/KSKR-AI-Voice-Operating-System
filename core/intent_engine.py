from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict

from nlp.command_parser import CommandParser


@dataclass
class AIIntent:
    intent: str
    params: Dict[str, Any]
    raw_text: str


class IntentEngine:
    """Converts natural language into assistant intents."""

    def __init__(self) -> None:
        self._parser = CommandParser()

    def detect(self, text: str) -> AIIntent:
        clean = text.strip()
        lower = clean.lower()

        # Communication intents for Android companion actions.
        m = re.search(r"^(?:call|dial)\s+(.+)$", lower)
        if m:
            return AIIntent(intent="call_contact", params={"contact": m.group(1).strip()}, raw_text=clean)

        m = re.search(r"^open\s+(.+?)\s+(?:on\s+phone|in\s+phone|on\s+mobile)$", lower)
        if m:
            return AIIntent(
                intent="open_application",
                params={"target": m.group(1).strip(), "source_intent": "open_app", "device": "phone"},
                raw_text=clean,
            )

        m = re.search(r"^(?:send\s+(?:a\s+)?)?(?:message|sms|whatsapp)\s+to\s+(.+?)\s+saying\s+(.+)$", lower)
        if m:
            return AIIntent(
                intent="send_message",
                params={"contact": m.group(1).strip(), "message": m.group(2).strip()},
                raw_text=clean,
            )

        m = re.search(r"^(?:scroll|swipe)\s+(.+)$", lower)
        if m:
            return AIIntent(intent="scroll_feed", params={"target": m.group(1).strip()}, raw_text=clean)

        m = re.search(r"^(play|pause)\s+(.+?)\s+(?:on\s+phone|in\s+phone|on\s+mobile)$", lower)
        if m:
            return AIIntent(
                intent="play_media",
                params={"action": m.group(1).strip(), "target": m.group(2).strip(), "device": "phone"},
                raw_text=clean,
            )

        # Reuse existing parser for core desktop skills.
        parsed = self._parser.parse(clean)
        mapping = {
            "open_app": "open_application",
            "search_web": "search_web",
            "play_media": "play_media",
            "system": "system_control",
            "chat": "chat_query",
            "open_folder": "open_application",
            "create_folder": "system_control",
            "reminder": "system_control",
            "memory_store": "chat_query",
            "memory_query": "chat_query",
        }
        return AIIntent(
            intent=mapping.get(parsed.intent, "chat_query"),
            params={"target": parsed.target, "source_intent": parsed.intent, **parsed.params},
            raw_text=clean,
        )
