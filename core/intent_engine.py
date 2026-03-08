"""
IntentEngine – Core NLP façade
--------------------------------
Wraps :class:`~nlp.command_parser.CommandParser` and provides a thin, stable
interface for the rest of the application to classify natural-language
utterances without importing directly from the ``nlp`` package.

Usage
~~~~~
    engine = IntentEngine()
    cmd = engine.parse("open Chrome")
    print(cmd.intent)   # "open_app"
    print(cmd.target)   # "chrome"
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class IntentEngine:
    """Parses natural-language text into structured :class:`~nlp.command_parser.Command` objects."""

    def __init__(self) -> None:
        self._parser = self._init_parser()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_parser(self):
        try:
            from nlp.command_parser import CommandParser

            return CommandParser()
        except Exception as exc:  # noqa: BLE001
            logger.error("CommandParser unavailable: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, text: str):
        """Parse *text* and return a :class:`~nlp.command_parser.Command`.

        If the underlying parser is unavailable, returns a ``chat`` command
        so the assistant can still respond conversationally.

        Parameters
        ----------
        text:
            Raw utterance from the user (e.g. ``"open chrome"``).

        Returns
        -------
        Command
            A structured command object with at least ``.intent`` set.
        """
        if not text:
            return self._fallback_command("", "chat")

        if self._parser is None:
            logger.warning("Parser not available – routing to chat fallback.")
            return self._fallback_command(text, "chat")

        try:
            return self._parser.parse(text)
        except Exception as exc:  # noqa: BLE001
            logger.error("parse() error: %s", exc)
            return self._fallback_command(text, "chat")

    def _fallback_command(self, text: str, intent: str = "chat"):
        """Create a minimal Command for use when parsing fails."""
        try:
            from nlp.command_parser import Command

            return Command(intent=intent, raw_text=text)
        except Exception:  # noqa: BLE001
            # Last-resort: return a plain object with the required attributes
            class _SimpleCommand:  # pylint: disable=too-few-public-methods
                def __init__(self, intent_, text_):
                    self.intent = intent_
                    self.raw_text = text_
                    self.target = ""
                    self.params = {}
                    self.confidence = 0.0

            return _SimpleCommand(intent, text)

    @property
    def supported_intents(self) -> list[str]:
        """List of intent labels the parser can recognise."""
        return [
            "open_app",
            "open_folder",
            "create_folder",
            "search_web",
            "play_media",
            "reminder",
            "memory_store",
            "memory_query",
            "system",
            "time",
            "date",
            "joke",
            "weather",
            "chat",
        ]
