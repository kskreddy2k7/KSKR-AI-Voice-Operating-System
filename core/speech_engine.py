"""
SpeechEngine – Core speech façade
-----------------------------------
Provides a single entry-point that wraps:

* :class:`~speech.recognizer.SpeechRecognizer` – microphone → text
* :class:`~speech.tts.TextToSpeech`             – text → audio

This allows the rest of the application (main.py, UI, router) to interact
with speech input/output through one cohesive object without importing from
multiple sub-packages.

Usage
~~~~~
    engine = SpeechEngine()
    engine.speak("Hello! How can I help you?")
    text = engine.listen()           # blocks until speech is captured
    text = engine.listen(timeout=5)  # returns None on timeout/error
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SpeechEngine:
    """High-level speech interface combining recognition and TTS."""

    def __init__(self, language: str = "en-IN") -> None:
        self._language = language
        self._recognizer = self._init_recognizer()
        self._tts = self._init_tts()

    # ------------------------------------------------------------------
    # Initialisation helpers (lazy imports so missing libs don't crash)
    # ------------------------------------------------------------------

    def _init_recognizer(self):
        try:
            from speech.recognizer import SpeechRecognizer

            rec = SpeechRecognizer()
            rec.set_language(self._language)
            return rec
        except Exception as exc:  # noqa: BLE001
            logger.warning("SpeechRecognizer unavailable: %s", exc)
            return None

    def _init_tts(self):
        try:
            from speech.tts import TextToSpeech

            return TextToSpeech()
        except Exception as exc:  # noqa: BLE001
            logger.warning("TextToSpeech unavailable: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def language(self) -> str:
        """BCP-47 language tag currently active (e.g. ``"en-IN"``)."""
        return self._language

    def set_language(self, language_code: str) -> None:
        """Switch recognition language at runtime (e.g. ``"hi-IN"``)."""
        self._language = language_code
        if self._recognizer is not None:
            try:
                self._recognizer.set_language(language_code)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not change recognizer language: %s", exc)

    def speak(self, text: str) -> None:
        """Convert *text* to audio and play it (blocking).

        Falls back to a :func:`print` if TTS is unavailable.
        """
        if not text:
            return
        if self._tts is not None:
            try:
                self._tts.speak(text)
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("TTS speak failed: %s", exc)
        print(f"[KSKR] {text}")

    def listen(self, timeout: int = 5, phrase_time_limit: int = 15) -> Optional[str]:
        """Capture a single utterance from the microphone and return its text.

        Parameters
        ----------
        timeout:
            Seconds to wait for speech to begin before returning ``None``.
        phrase_time_limit:
            Maximum seconds of speech to capture.

        Returns
        -------
        str | None
            Recognised text in lower-case, or ``None`` on error / silence.
        """
        if self._recognizer is None:
            logger.warning("No speech recognizer available – returning None.")
            return None
        try:
            return self._recognizer.listen(
                timeout=timeout, phrase_time_limit=phrase_time_limit
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("listen() error: %s", exc)
            return None

    def listen_once(self) -> Optional[str]:
        """Convenience wrapper around :meth:`listen` with default settings."""
        return self.listen()
