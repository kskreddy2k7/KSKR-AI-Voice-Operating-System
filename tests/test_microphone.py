import speech_recognition as sr

from speech.recognizer import get_best_microphone


def test_get_best_microphone_returns_index_or_none(monkeypatch):
    monkeypatch.setattr(
        sr.Microphone,
        "list_microphone_names",
        staticmethod(lambda: ["Virtual Output", "USB Microphone", "Line In"]),
    )
    assert get_best_microphone() == 1


def test_get_best_microphone_falls_back_to_default(monkeypatch):
    monkeypatch.setattr(
        sr.Microphone,
        "list_microphone_names",
        staticmethod(lambda: ["Virtual Output", "Speaker"]),
    )
    assert get_best_microphone() is None