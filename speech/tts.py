"""
Text-to-Speech (TTS) helper
----------------------------
Converts text to speech using pyttsx3 (offline, cross-platform).
Falls back to a print statement if pyttsx3 is not available.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "settings.json"
)


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh).get("tts", {})
    except Exception:
        return {}


class TextToSpeech:
    """Wraps pyttsx3 with sensible defaults.

    Parameters
    ----------
    rate:    Speech rate in words-per-minute.
    volume:  Volume 0.0–1.0.
    """

    def __init__(
        self,
        rate: Optional[int] = None,
        volume: Optional[float] = None,
    ) -> None:
        cfg = _load_config()
        self._rate = rate or cfg.get("rate", 170)
        self._volume = volume if volume is not None else cfg.get("volume", 1.0)
        self._engine = self._init_engine()

    def speak(self, text: str) -> None:
        """Speak *text* synchronously."""
        if not text:
            return
        logger.info("TTS: '%s'", text[:80])
        if self._engine is None:
            print(f"[KSKR]: {text}")
            return
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as exc:
            logger.error("TTS: speak failed – %s", exc)
            print(f"[KSKR]: {text}")

    def stop(self) -> None:
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_engine(self):
        try:
            import pyttsx3  # type: ignore
            engine = pyttsx3.init()
            engine.setProperty("rate", self._rate)
            engine.setProperty("volume", self._volume)

            # Prefer a female voice if configured
            cfg = _load_config()
            if cfg.get("voice_preference", "female") == "female":
                voices = engine.getProperty("voices")
                for voice in voices:
                    if "female" in voice.name.lower() or "zira" in voice.name.lower():
                        engine.setProperty("voice", voice.id)
                        break

            logger.info("TTS: pyttsx3 engine initialised.")
            return engine
        except ImportError:
            logger.warning("TTS: pyttsx3 not installed – will print responses instead.")
            return None
        except Exception as exc:
            logger.warning("TTS: could not init pyttsx3 – %s", exc)
            return None
