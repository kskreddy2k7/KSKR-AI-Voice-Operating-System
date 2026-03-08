"""
WakeWordEngine – Core wake-word façade
----------------------------------------
Wraps :class:`~wakeword.detector.WakeWordDetector` and exposes a simple
start/stop interface used by the main application loop.

Supported wake phrases (configured in ``config/settings.json``):

* "Hey KSKR"
* "Hello KSKR"
* "OK KSKR"

Usage
~~~~~
    def on_wake(phrase: str) -> None:
        print(f"Wake word detected: {phrase}")

    engine = WakeWordEngine(on_wake=on_wake)
    engine.start()
    # … later …
    engine.stop()
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class WakeWordEngine:
    """Wraps the underlying detector and exposes start / stop / is_running."""

    def __init__(self, on_wake: Optional[Callable[[str], None]] = None) -> None:
        """
        Parameters
        ----------
        on_wake:
            Callback invoked whenever a wake phrase is detected.
            Receives the matched wake-word phrase as its only argument.
        """
        self._on_wake = on_wake
        self._detector = self._init_detector()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_detector(self):
        try:
            from wakeword.detector import WakeWordDetector

            return WakeWordDetector(on_detected=self._on_wake)
        except Exception as exc:  # noqa: BLE001
            logger.warning("WakeWordDetector unavailable: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start listening for wake words in the background."""
        if self._detector is None:
            logger.warning("WakeWordDetector not initialised – cannot start.")
            return
        try:
            self._detector.start()
            logger.info("WakeWordEngine started.")
        except Exception as exc:  # noqa: BLE001
            logger.error("WakeWordEngine.start() failed: %s", exc)

    def stop(self) -> None:
        """Stop the background listener."""
        if self._detector is None:
            return
        try:
            self._detector.stop()
            logger.info("WakeWordEngine stopped.")
        except Exception as exc:  # noqa: BLE001
            logger.error("WakeWordEngine.stop() failed: %s", exc)

    @property
    def is_running(self) -> bool:
        """``True`` if the detector thread is active."""
        if self._detector is None:
            return False
        try:
            return bool(self._detector.is_running)
        except Exception:  # noqa: BLE001
            return False

    def set_wake_words(self, words: list[str]) -> None:
        """Update the wake-word list at runtime.

        Parameters
        ----------
        words:
            List of lower-case phrases (e.g. ``["hey kskr", "ok kskr"]``).
        """
        if self._detector is None:
            logger.warning("Cannot set wake words – detector not initialised.")
            return
        try:
            self._detector.wake_words = [w.lower().strip() for w in words]
            logger.info("Wake words updated to: %s", self._detector.wake_words)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not update wake words: %s", exc)
