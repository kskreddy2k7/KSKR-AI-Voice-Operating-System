"""
test_microphone.py
------------------
Tests for the SpeechEngine and WakeWordEngine core façades.

These tests do NOT require a physical microphone – all audio I/O is
mocked so they can run in a headless CI environment.

Run with:
    python -m pytest tests/test_microphone.py -v
"""

from __future__ import annotations

import sys
import os
import types
import unittest.mock as mock

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest


# ---------------------------------------------------------------------------
# Helpers: stub out heavy audio dependencies so tests run without hardware
# ---------------------------------------------------------------------------

def _stub_speech_recognition(monkeypatch):
    """Replace the ``speech_recognition`` module with a lightweight stub."""
    sr_stub = types.ModuleType("speech_recognition")
    sr_stub.Microphone = mock.MagicMock()
    sr_stub.Recognizer = mock.MagicMock
    sr_stub.UnknownValueError = Exception
    sr_stub.RequestError = Exception
    monkeypatch.setitem(sys.modules, "speech_recognition", sr_stub)
    return sr_stub


def _stub_pyttsx3(monkeypatch):
    """Replace ``pyttsx3`` with a lightweight stub."""
    pyttsx3_stub = types.ModuleType("pyttsx3")
    engine_mock = mock.MagicMock()
    pyttsx3_stub.init = mock.MagicMock(return_value=engine_mock)
    monkeypatch.setitem(sys.modules, "pyttsx3", pyttsx3_stub)
    return pyttsx3_stub


# ---------------------------------------------------------------------------
# SpeechEngine
# ---------------------------------------------------------------------------

class TestSpeechEngine:
    def test_speak_fallback_to_print(self, monkeypatch, capsys):
        """speak() should fall back to print when TTS is unavailable."""
        from core.speech_engine import SpeechEngine

        engine = SpeechEngine.__new__(SpeechEngine)
        engine._language = "en-IN"
        engine._tts = None       # force TTS unavailable
        engine._recognizer = None

        engine.speak("Hello world")
        captured = capsys.readouterr()
        assert "Hello world" in captured.out

    def test_speak_empty_string(self, monkeypatch, capsys):
        """speak('') should be a no-op."""
        from core.speech_engine import SpeechEngine

        engine = SpeechEngine.__new__(SpeechEngine)
        engine._tts = None
        engine._recognizer = None

        engine.speak("")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_listen_returns_none_without_recognizer(self):
        """listen() should return None gracefully when recognizer is absent."""
        from core.speech_engine import SpeechEngine

        engine = SpeechEngine.__new__(SpeechEngine)
        engine._language = "en-IN"
        engine._recognizer = None

        result = engine.listen()
        assert result is None

    def test_set_language(self):
        """set_language() should update the stored language code."""
        from core.speech_engine import SpeechEngine

        engine = SpeechEngine.__new__(SpeechEngine)
        engine._language = "en-IN"
        engine._recognizer = None
        engine._tts = None

        engine.set_language("hi-IN")
        assert engine.language == "hi-IN"

    def test_set_language_propagates_to_recognizer(self):
        """set_language() should call recognizer.set_language()."""
        from core.speech_engine import SpeechEngine

        engine = SpeechEngine.__new__(SpeechEngine)
        engine._language = "en-IN"
        engine._tts = None
        rec_mock = mock.MagicMock()
        engine._recognizer = rec_mock

        engine.set_language("te-IN")
        rec_mock.set_language.assert_called_once_with("te-IN")

    def test_speak_uses_tts_when_available(self):
        """speak() should call tts.speak() when TTS is available."""
        from core.speech_engine import SpeechEngine

        engine = SpeechEngine.__new__(SpeechEngine)
        engine._language = "en-IN"
        engine._recognizer = None
        tts_mock = mock.MagicMock()
        engine._tts = tts_mock

        engine.speak("Test message")
        tts_mock.speak.assert_called_once_with("Test message")

    def test_listen_delegates_to_recognizer(self):
        """listen() should call recognizer.listen() and return its result."""
        from core.speech_engine import SpeechEngine

        engine = SpeechEngine.__new__(SpeechEngine)
        engine._language = "en-IN"
        engine._tts = None
        rec_mock = mock.MagicMock()
        rec_mock.listen.return_value = "open chrome"
        engine._recognizer = rec_mock

        result = engine.listen(timeout=3)
        assert result == "open chrome"
        rec_mock.listen.assert_called_once_with(timeout=3, phrase_time_limit=15)


# ---------------------------------------------------------------------------
# WakeWordEngine
# ---------------------------------------------------------------------------

class TestWakeWordEngine:
    def test_is_running_false_without_detector(self):
        """is_running should be False when the detector is unavailable."""
        from core.wake_word_engine import WakeWordEngine

        engine = WakeWordEngine.__new__(WakeWordEngine)
        engine._on_wake = None
        engine._detector = None

        assert engine.is_running is False

    def test_start_noop_without_detector(self):
        """start() should not raise when detector is None."""
        from core.wake_word_engine import WakeWordEngine

        engine = WakeWordEngine.__new__(WakeWordEngine)
        engine._on_wake = None
        engine._detector = None

        engine.start()  # should not raise

    def test_stop_noop_without_detector(self):
        """stop() should not raise when detector is None."""
        from core.wake_word_engine import WakeWordEngine

        engine = WakeWordEngine.__new__(WakeWordEngine)
        engine._on_wake = None
        engine._detector = None

        engine.stop()  # should not raise

    def test_start_delegates_to_detector(self):
        """start() should call detector.start()."""
        from core.wake_word_engine import WakeWordEngine

        engine = WakeWordEngine.__new__(WakeWordEngine)
        engine._on_wake = None
        det_mock = mock.MagicMock()
        engine._detector = det_mock

        engine.start()
        det_mock.start.assert_called_once()

    def test_stop_delegates_to_detector(self):
        """stop() should call detector.stop()."""
        from core.wake_word_engine import WakeWordEngine

        engine = WakeWordEngine.__new__(WakeWordEngine)
        engine._on_wake = None
        det_mock = mock.MagicMock()
        engine._detector = det_mock

        engine.stop()
        det_mock.stop.assert_called_once()

    def test_set_wake_words(self):
        """set_wake_words() should update detector.wake_words."""
        from core.wake_word_engine import WakeWordEngine

        engine = WakeWordEngine.__new__(WakeWordEngine)
        engine._on_wake = None
        det_mock = mock.MagicMock()
        det_mock.wake_words = []
        engine._detector = det_mock

        engine.set_wake_words(["Hey KSKR", "OK KSKR"])
        assert "hey kskr" in det_mock.wake_words
        assert "ok kskr" in det_mock.wake_words


# ---------------------------------------------------------------------------
# IntentEngine
# ---------------------------------------------------------------------------

class TestIntentEngine:
    def test_parse_open_app(self):
        from core.intent_engine import IntentEngine

        engine = IntentEngine()
        cmd = engine.parse("open chrome")
        assert cmd.intent == "open_app"

    def test_parse_empty_returns_chat(self):
        from core.intent_engine import IntentEngine

        engine = IntentEngine()
        cmd = engine.parse("")
        assert cmd.intent == "chat"

    def test_parse_fallback_when_parser_unavailable(self):
        from core.intent_engine import IntentEngine

        engine = IntentEngine.__new__(IntentEngine)
        engine._parser = None

        cmd = engine.parse("some random text")
        assert cmd.intent == "chat"

    def test_supported_intents_includes_core_set(self):
        from core.intent_engine import IntentEngine

        engine = IntentEngine()
        intents = engine.supported_intents
        for expected in ("open_app", "search_web", "reminder", "chat", "system"):
            assert expected in intents
