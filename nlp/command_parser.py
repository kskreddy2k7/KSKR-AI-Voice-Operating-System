"""
NLP Command Parser
------------------
Classifies a natural-language utterance into a structured ``Command`` object
that the automation layer can execute.

The parser uses a rules-first approach (fast, no network dependency) combined
with an optional AI fallback when the intent is ambiguous.

Supported intents
~~~~~~~~~~~~~~~~~
- open_app          – "open Chrome", "launch VS Code"
- open_folder       – "open downloads folder"
- create_folder     – "create folder called AI project"
- search_web        – "search machine learning tutorials"
- play_media        – "play music", "pause video"
- reminder          – "remind me to study at 7 PM"
- memory_store      – "remember that my name is KSKR"
- memory_query      – "what do you know about me?"
- chat              – general question / anything else
- system            – "shutdown", "restart", "volume up"
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Command:
    intent: str
    target: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    confidence: float = 1.0

    def __str__(self) -> str:
        return (
            f"Command(intent={self.intent!r}, target={self.target!r}, "
            f"params={self.params}, confidence={self.confidence:.2f})"
        )


# ---------------------------------------------------------------------------
# Intent rules
# ---------------------------------------------------------------------------

_OPEN_APP_PATTERNS = [
    r"open\s+(.+?)(?:\s+app(?:lication)?)?$",
    r"launch\s+(.+?)(?:\s+app(?:lication)?)?$",
    r"start\s+(.+?)(?:\s+app(?:lication)?)?$",
    r"run\s+(.+?)$",
]

_OPEN_FOLDER_PATTERNS = [
    r"open\s+(?:the\s+)?(.+?)\s+folder$",
    r"go\s+to\s+(?:the\s+)?(.+?)\s+folder$",
    r"navigate\s+to\s+(.+?)$",
]

_CREATE_FOLDER_PATTERNS = [
    r"create\s+(?:a\s+)?folder\s+(?:called|named)\s+(.+)$",
    r"make\s+(?:a\s+)?(?:new\s+)?folder\s+(?:called|named)?\s*(.+)$",
    r"new\s+folder\s+(.+)$",
]

_SEARCH_PATTERNS = [
    r"search\s+(?:for\s+)?(.+)$",
    r"google\s+(.+)$",
    r"look\s+up\s+(.+)$",
    r"find\s+(.+)\s+online$",
]

_MEDIA_PATTERNS = {
    "play":  [r"play\s+(.+)$", r"play\s*$"],
    "pause": [r"pause(?:\s+.+)?$", r"stop(?:\s+music)?$"],
    "next":  [r"next\s+(?:song|track|video)$"],
    "prev":  [r"previous\s+(?:song|track|video)$"],
    "volume_up":   [r"volume\s+up$", r"louder$", r"increase\s+volume$"],
    "volume_down": [r"volume\s+down$", r"quieter$", r"decrease\s+volume$"],
    "mute":  [r"mute(?:\s+.+)?$"],
}

_REMINDER_PATTERNS = [
    r"remind\s+me\s+to\s+(.+?)\s+at\s+(.+)$",
    r"set\s+(?:a\s+)?reminder\s+(?:to\s+)?(.+?)\s+at\s+(.+)$",
    r"remind\s+me\s+(.+?)\s+at\s+(.+)$",
    r"add\s+(?:a\s+)?reminder(?:\s+to\s+(.+))?$",
    r"what\s+(?:tasks|reminders)\s+(?:do\s+i\s+have)?.*$",
    r"list\s+(?:my\s+)?(?:tasks|reminders)$",
]

_MEMORY_STORE_PATTERNS = [
    r"remember\s+that\s+(.+)$",
    r"remember\s+my\s+(.+)\s+is\s+(.+)$",
    r"my\s+(.+?)\s+is\s+(.+)$",
    r"save\s+(?:that\s+)?(.+)$",
    r"note\s+that\s+(.+)$",
]

_MEMORY_QUERY_PATTERNS = [
    r"what\s+(?:is|are)\s+my\s+(.+)\??$",
    r"what\s+(?:do\s+you\s+know|did\s+you\s+remember)\s+about\s+(.+)\??$",
    r"tell\s+me\s+(?:about\s+)?my\s+(.+)$",
    r"recall\s+(.+)$",
    r"what\s+(?:language|song|color|food)\s+do\s+i\s+(?:like|prefer|love)\??$",
]

_SYSTEM_PATTERNS = {
    "shutdown":  [r"shut\s*down(?:\s+(?:the\s+)?(?:computer|pc|system))?$"],
    "restart":   [r"restart(?:\s+(?:the\s+)?(?:computer|pc|system))?$", r"reboot$"],
    "sleep":     [r"sleep(?:\s+(?:the\s+)?(?:computer|pc))?$"],
    "lock":      [r"lock(?:\s+(?:the\s+)?(?:computer|pc|screen))?$"],
    "screenshot":[r"take\s+(?:a\s+)?screenshot$", r"screenshot$"],
    "close_app": [r"close\s+(.+)$", r"quit\s+(.+)$", r"exit\s+(.+)$"],
}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class CommandParser:
    """Converts a raw utterance string into a :class:`Command`."""

    def parse(self, text: str) -> Command:
        """Parse *text* and return the best-matching :class:`Command`."""
        clean = text.lower().strip().rstrip(".")

        # Check each intent category in order of specificity

        cmd = self._try_system(clean, text)
        if cmd:
            return cmd

        cmd = self._try_reminder(clean, text)
        if cmd:
            return cmd

        cmd = self._try_memory_query(clean, text)
        if cmd:
            return cmd

        cmd = self._try_memory_store(clean, text)
        if cmd:
            return cmd

        cmd = self._try_media(clean, text)
        if cmd:
            return cmd

        cmd = self._try_search(clean, text)
        if cmd:
            return cmd

        cmd = self._try_create_folder(clean, text)
        if cmd:
            return cmd

        cmd = self._try_open_folder(clean, text)
        if cmd:
            return cmd

        cmd = self._try_open_app(clean, text)
        if cmd:
            return cmd

        # Fallback → AI chat
        return Command(intent="chat", target=text, raw_text=text, confidence=0.5)

    # ------------------------------------------------------------------
    # Private matchers
    # ------------------------------------------------------------------

    @staticmethod
    def _first_match(patterns: list, text: str):
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m
        return None

    def _try_open_app(self, clean: str, raw: str) -> Optional[Command]:
        m = self._first_match(_OPEN_APP_PATTERNS, clean)
        if m:
            return Command(intent="open_app", target=m.group(1).strip(), raw_text=raw)
        return None

    def _try_open_folder(self, clean: str, raw: str) -> Optional[Command]:
        m = self._first_match(_OPEN_FOLDER_PATTERNS, clean)
        if m:
            return Command(intent="open_folder", target=m.group(1).strip(), raw_text=raw)
        return None

    def _try_create_folder(self, clean: str, raw: str) -> Optional[Command]:
        m = self._first_match(_CREATE_FOLDER_PATTERNS, clean)
        if m:
            return Command(intent="create_folder", target=m.group(1).strip(), raw_text=raw)
        return None

    def _try_search(self, clean: str, raw: str) -> Optional[Command]:
        m = self._first_match(_SEARCH_PATTERNS, clean)
        if m:
            return Command(intent="search_web", target=m.group(1).strip(), raw_text=raw)
        return None

    def _try_media(self, clean: str, raw: str) -> Optional[Command]:
        for action, patterns in _MEDIA_PATTERNS.items():
            m = self._first_match(patterns, clean)
            if m:
                target = m.group(1).strip() if m.lastindex else ""
                return Command(
                    intent="play_media",
                    target=target,
                    params={"action": action},
                    raw_text=raw,
                )
        return None

    def _try_reminder(self, clean: str, raw: str) -> Optional[Command]:
        # List query
        if re.search(r"(what\s+tasks|list\s+(my\s+)?reminders|what\s+reminders)", clean):
            return Command(intent="reminder", target="list", raw_text=raw)
        m = re.search(r"remind\s+me\s+to\s+(.+?)\s+at\s+(.+)$", clean, re.IGNORECASE)
        if m:
            return Command(
                intent="reminder",
                target="add",
                params={"task": m.group(1).strip(), "time": m.group(2).strip()},
                raw_text=raw,
            )
        m = re.search(r"remind\s+me\s+(.+?)\s+at\s+(.+)$", clean, re.IGNORECASE)
        if m:
            return Command(
                intent="reminder",
                target="add",
                params={"task": m.group(1).strip(), "time": m.group(2).strip()},
                raw_text=raw,
            )
        m = re.search(r"add\s+reminder\s+(.+)$", clean, re.IGNORECASE)
        if m:
            return Command(intent="reminder", target="add", params={"task": m.group(1).strip()}, raw_text=raw)
        return None

    def _try_memory_store(self, clean: str, raw: str) -> Optional[Command]:
        # "my X is Y"
        m = re.search(r"my\s+(.+?)\s+is\s+(.+)$", clean, re.IGNORECASE)
        if m:
            return Command(
                intent="memory_store",
                target=m.group(1).strip(),
                params={"value": m.group(2).strip()},
                raw_text=raw,
            )
        m = re.search(r"remember\s+that\s+(.+)$", clean, re.IGNORECASE)
        if m:
            return Command(intent="memory_store", target="note", params={"value": m.group(1).strip()}, raw_text=raw)
        return None

    def _try_memory_query(self, clean: str, raw: str) -> Optional[Command]:
        m = re.search(r"what\s+(?:is|are)\s+my\s+(.+)\??", clean, re.IGNORECASE)
        if m:
            return Command(intent="memory_query", target=m.group(1).strip(), raw_text=raw)
        m = re.search(r"what\s+(?:language|song|color|food)\s+do\s+i\s+(like|prefer|love)", clean, re.IGNORECASE)
        if m:
            # Extract the noun
            noun = re.search(r"what\s+(\w+)\s+do\s+i", clean)
            key = noun.group(1) if noun else "preference"
            return Command(intent="memory_query", target=key, raw_text=raw)
        m = re.search(r"tell\s+me\s+(?:about\s+)?my\s+(.+)$", clean, re.IGNORECASE)
        if m:
            return Command(intent="memory_query", target=m.group(1).strip(), raw_text=raw)
        return None

    def _try_system(self, clean: str, raw: str) -> Optional[Command]:
        for action, patterns in _SYSTEM_PATTERNS.items():
            m = self._first_match(patterns, clean)
            if m:
                target = ""
                if m.lastindex:
                    try:
                        target = m.group(1).strip()
                    except IndexError:
                        pass
                return Command(intent="system", target=target, params={"action": action}, raw_text=raw)
        return None
