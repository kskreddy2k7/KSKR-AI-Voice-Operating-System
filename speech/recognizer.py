"""
Speech Recognizer
-----------------
Converts microphone audio to text.

Supports multiple Indian languages via the Google Web Speech API.
The language can be changed at runtime (e.g. after the user selects a
language in the UI).
"""

from __future__ import annotations

import json
import logging
import os
from typing import List, Optional

import speech_recognition as sr

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "settings.json"
)

_DEFAULT_LANGUAGES = {
    "English": "en-IN",
    "Hindi": "hi-IN",
    "Telugu": "te-IN",
    "Tamil": "ta-IN",
    "Kannada": "kn-IN",
}


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh).get("speech", {})
    except Exception as exc:
        logger.warning("SpeechRecognizer: could not load config – %s", exc)
        return {}


def list_microphone_devices() -> List[str]:
    """Return all available microphone device names.

    Prints the list to stdout for diagnostic purposes and returns it.
    """
    devices = sr.Microphone.list_microphone_names()
    for idx, name in enumerate(devices):
        print(f"  [{idx}] {name}")
    return devices


class SpeechRecognizer:
    """Records a single utterance from the microphone and returns its text.

    Parameters
    ----------
    language:
        BCP-47 language code, e.g. ``"en-IN"``, ``"hi-IN"``.
    timeout:
        Seconds to wait for speech to begin.
    phrase_time_limit:
        Maximum seconds of speech per utterance.
    energy_threshold:
        Microphone energy level cutoff.
    device_index:
        Microphone device index.  When *None* the system default is used.
    """

    def __init__(
        self,
        language: Optional[str] = None,
        timeout: int = 5,
        phrase_time_limit: int = 8,
        energy_threshold: int = 300,
        device_index: Optional[int] = None,
    ) -> None:
        cfg = _load_config()
        self.language = language or cfg.get("language", "en-IN")
        self.supported_languages: dict = cfg.get("supported_languages", _DEFAULT_LANGUAGES)
        self.timeout = timeout or cfg.get("timeout", 5)
        self.phrase_time_limit = phrase_time_limit or cfg.get("phrase_time_limit", 8)
        self._device_index = device_index

        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = energy_threshold or cfg.get("energy_threshold", 300)
        self._recognizer.pause_threshold = cfg.get("pause_threshold", 0.8)
        self._recognizer.dynamic_energy_threshold = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def listen(
        self,
        timeout: Optional[int] = None,
        phrase_time_limit: Optional[int] = None,
    ) -> Optional[str]:
        """Capture one utterance and return its text, or *None* on failure.

        Parameters
        ----------
        timeout:
            Override the instance-level timeout for this call only.
        phrase_time_limit:
            Override the instance-level phrase_time_limit for this call only.
        """
        effective_timeout = timeout if timeout is not None else self.timeout
        effective_ptl = phrase_time_limit if phrase_time_limit is not None else self.phrase_time_limit

        mic_kwargs: dict = {}
        if self._device_index is not None:
            mic_kwargs["device_index"] = self._device_index

        with sr.Microphone(**mic_kwargs) as source:
            logger.info("SpeechRecognizer: adjusting for ambient noise…")
            self._recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Listening...")
            logger.info(
                "SpeechRecognizer: listening (lang=%s, timeout=%ss)…",
                self.language,
                effective_timeout,
            )
            try:
                audio = self._recognizer.listen(
                    source,
                    timeout=effective_timeout,
                    phrase_time_limit=effective_ptl,
                )
            except sr.WaitTimeoutError:
                logger.debug("SpeechRecognizer: listen timed out (no speech).")
                return None

        return self._transcribe(audio)

    def listen_from_audio(self, audio: sr.AudioData) -> Optional[str]:
        """Transcribe a pre-recorded ``AudioData`` object."""
        return self._transcribe(audio)

    def set_language(self, language_name: str) -> bool:
        """Switch language by human-readable name (e.g. *"Hindi"*).

        Returns *True* if the language was found in the supported list.
        """
        code = self.supported_languages.get(language_name)
        if code:
            self.language = code
            logger.info("SpeechRecognizer: language set to %s (%s)", language_name, code)
            return True
        logger.warning("SpeechRecognizer: unknown language '%s'", language_name)
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transcribe(self, audio: sr.AudioData) -> Optional[str]:
        try:
            text = self._recognizer.recognize_google(audio, language=self.language)
            print(f"Recognized speech: {text}")
            logger.info("SpeechRecognizer: recognised → '%s'", text)
            return text
        except sr.UnknownValueError:
            logger.debug("SpeechRecognizer: could not understand audio.")
            return None
        except sr.RequestError as exc:
            logger.error("SpeechRecognizer: API error – %s", exc)
            return None
