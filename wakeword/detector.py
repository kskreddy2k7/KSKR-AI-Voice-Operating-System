"""
Wake Word Detector
------------------
Listens continuously on the microphone and triggers a callback when one of the
configured wake words is detected.

Strategy
~~~~~~~~
Uses the SpeechRecognition library to capture short audio snippets in a
background thread.  The recognised text is compared against the list of wake
words stored in config/settings.json.  For production use this can be swapped
for a neural wake-word engine (e.g. pvporcupine) without changing the public
interface.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
from typing import Callable, List, Optional

import speech_recognition as sr

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "settings.json"
)


def _load_wake_words() -> List[str]:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        return [w.lower().strip() for w in cfg.get("wake_words", ["hey kskr"])]
    except Exception as exc:
        logger.warning("Could not load settings: %s – using default wake words.", exc)
        return ["hey kskr", "hello assistant"]


class WakeWordDetector:
    """Continuously monitors the microphone and fires *on_detected* when a
    wake word is recognised.

    Parameters
    ----------
    on_detected:
        Callable invoked (in the listener thread) when the wake word fires.
        Receives the matched phrase as its only argument.
    wake_words:
        Override the list of wake words (lower-case strings).  If *None* the
        list is read from ``config/settings.json``.
    energy_threshold:
        Microphone energy threshold forwarded to ``speech_recognition``.
    """

    def __init__(
        self,
        on_detected: Callable[[str], None],
        wake_words: Optional[List[str]] = None,
        energy_threshold: int = 300,
    ) -> None:
        self._on_detected = on_detected
        self._wake_words: List[str] = wake_words if wake_words is not None else _load_wake_words()
        self._energy_threshold = energy_threshold
        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = self._energy_threshold
        self._recognizer.pause_threshold = 0.5
        self._stop_listening: Optional[Callable] = None
        self._running = False
        self._event_queue: queue.Queue = queue.Queue()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background listening loop."""
        if self._running:
            return
        self._running = True
        logger.info("WakeWordDetector: starting – listening for %s", self._wake_words)
        self._stop_listening = self._recognizer.listen_in_background(
            sr.Microphone(), self._audio_callback, phrase_time_limit=4
        )
        # Dispatch thread so callbacks don't block the listener thread
        threading.Thread(target=self._dispatch_loop, daemon=True).start()

    def stop(self) -> None:
        """Stop the background listening loop."""
        self._running = False
        if self._stop_listening:
            self._stop_listening(wait_for_stop=False)
            self._stop_listening = None
        logger.info("WakeWordDetector: stopped.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _audio_callback(self, recognizer: sr.Recognizer, audio: sr.AudioData) -> None:
        """Called by speech_recognition in a background thread for every audio
        chunk captured."""
        try:
            text = recognizer.recognize_google(audio, language="en-IN").lower()
            logger.debug("WakeWordDetector heard: %s", text)
            for wake_word in self._wake_words:
                if wake_word in text:
                    self._event_queue.put(text)
                    break
        except sr.UnknownValueError:
            pass  # No speech detected – normal
        except sr.RequestError as exc:
            logger.warning("WakeWordDetector: recognition service error – %s", exc)

    def _dispatch_loop(self) -> None:
        """Runs in a dedicated thread and dispatches detection events."""
        while self._running:
            try:
                phrase = self._event_queue.get(timeout=1)
                logger.info("WakeWordDetector: wake word detected in '%s'", phrase)
                try:
                    self._on_detected(phrase)
                except Exception:  # noqa: BLE001 – user callback; must not crash the detector
                    logger.error("WakeWordDetector: on_detected callback raised an error", exc_info=True)
            except queue.Empty:
                continue
