from core.intent_engine import IntentEngine


def test_call_contact_intent():
    engine = IntentEngine()
    intent = engine.detect("Call mom")
    assert intent.intent == "call_contact"
    assert intent.params["contact"] == "mom"


def test_send_message_intent():
    engine = IntentEngine()
    intent = engine.detect("Send message to John saying I will be late")
    assert intent.intent == "send_message"
    assert intent.params["contact"] == "john"
    assert "late" in intent.params["message"]


def test_scroll_feed_intent():
    engine = IntentEngine()
    intent = engine.detect("Scroll Instagram")
    assert intent.intent == "scroll_feed"
    assert intent.params["target"] == "instagram"


def test_open_app_on_phone_intent():
    engine = IntentEngine()
    intent = engine.detect("Open WhatsApp on phone")
    assert intent.intent == "open_application"
    assert intent.params["device"] == "phone"


def test_play_media_on_phone_intent():
    engine = IntentEngine()
    intent = engine.detect("Play music on phone")
    assert intent.intent == "play_media"
    assert intent.params["device"] == "phone"