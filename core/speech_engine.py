from __future__ import annotations

import logging
from typing import Optional

from speech.recognizer import SpeechRecognizer
from speech.tts import TextToSpeech

logger = logging.getLogger(__name__)


class SpeechEngine:
    """Unified speech I/O wrapper for recognition and TTS."""

    def __init__(self) -> None:
        self._recognizer = SpeechRecognizer()
        self._tts = TextToSpeech()

    def listen_once(self) -> Optional[str]:
        return self._recognizer.listen()

    def speak(self, text: str) -> None:
        logger.info("Sai AI speaking: %s", text[:100])
        self._tts.speak(text)

    def set_language(self, language_name: str) -> bool:
        return self._recognizer.set_language(language_name)
