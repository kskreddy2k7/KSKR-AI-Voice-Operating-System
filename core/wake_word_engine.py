from __future__ import annotations

import logging
from typing import Callable, Optional

from wakeword.detector import WakeWordDetector

logger = logging.getLogger(__name__)


class WakeWordEngine:
    """Always-on wake-word engine for Sai AI."""

    def __init__(self, on_detected: Callable[[str], None], wake_words: Optional[list[str]] = None) -> None:
        default_words = ["hey sai", "hello sai", "ok sai"]
        self._detector = WakeWordDetector(on_detected=on_detected, wake_words=wake_words or default_words)

    def start(self) -> None:
        logger.info("WakeWordEngine: starting")
        self._detector.start()

    def stop(self) -> None:
        logger.info("WakeWordEngine: stopping")
        self._detector.stop()
