"""
Sai AI Voice Assistant - Main Entry Point
=========================================
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import threading
import wave
from concurrent.futures import ThreadPoolExecutor

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(_LOG_DIR, "system.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("sai.main")

from authentication.voice_auth import VoiceAuthenticator
from nlp.chat_assistant import ChatAssistant
from automation.windows_controller import WindowsController
from memory.memory_manager import MemoryManager
from reminders.reminder_manager import ReminderManager
from plugins.plugin_loader import PluginLoader
from android.phone_api import PhoneAPI
from core.speech_engine import SpeechEngine
from core.wake_word_engine import WakeWordEngine
from core.intent_engine import IntentEngine
from router.command_router import CommandRouter


def _load_config() -> dict:
    cfg_path = os.path.join(os.path.dirname(__file__), "config", "settings.json")
    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        logger.warning("Could not load config: %s", exc)
        return {}


class SaiAssistant:
    """Central coordinator for Sai AI Voice Assistant subsystems."""

    def __init__(self, gui=None) -> None:
        self._gui = gui
        self._cfg = _load_config()
        self._active = False
        self._pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sai")

        logger.info("Initialising Sai AI subsystems...")
        self._speech = SpeechEngine()
        self._authenticator = VoiceAuthenticator()
        self._intent_engine = IntentEngine()
        self._chat = ChatAssistant()
        self._controller = WindowsController()
        self._memory = MemoryManager()
        self._plugins = PluginLoader()
        self._plugins.load_all()

        self._reminders = ReminderManager(on_due=self._on_reminder_due)
        self._reminders.start()

        self._wake_engine = WakeWordEngine(on_detected=self._on_wake_word)

        android_cfg = self._cfg.get("android", {})
        if android_cfg.get("enabled", False):
            self._phone_api = PhoneAPI(
                command_handler=self.handle_text_command,
                reminder_manager=self._reminders,
            )
            self._phone_api.start()
        else:
            self._phone_api = None

        self._router = CommandRouter(
            controller=self._controller,
            phone_api=self._phone_api,
            chat=self._chat,
            reminders=self._reminders,
            memory=self._memory,
            plugins=self._plugins,
        )

        logger.info("Sai AI Assistant ready.")

    def start_listening(self) -> None:
        logger.info("Starting wake word engine...")
        self._wake_engine.start()
        self._speak("Sai AI is now listening for wake words.")

    def stop_listening(self) -> None:
        self._wake_engine.stop()
        self._speak("Stopped listening.")

    def handle_text_command(self, text: str) -> str:
        if not text:
            return ""
        logger.info("Processing text command: %s", text)
        ai_intent = self._intent_engine.detect(text)
        logger.info("Detected AI intent: %s", ai_intent)
        response = self._router.route(ai_intent)
        self._speak(response)
        if self._gui:
            self._gui.show_response(response)
        return response

    def set_language(self, language_name: str) -> None:
        self._speech.set_language(language_name)

    def enrol_voice(self) -> None:
        self._speak(
            "Voice enrollment mode. I will record 5 short samples. "
            "After each beep, say your name or a short phrase."
        )
        import speech_recognition as sr
        from speech.recognizer import get_best_microphone

        recognizer = sr.Recognizer()
        mic_index = get_best_microphone()
        wav_paths = []

        for i in range(5):
            self._speak(f"Recording sample {i + 1}. Speak now.")
            if self._gui:
                self._gui.update_status(f"ENROLLING ({i+1}/5)", "warning")
            with sr.Microphone(device_index=mic_index) as src:
                recognizer.adjust_for_ambient_noise(src, duration=0.3)
                try:
                    audio = recognizer.listen(src, timeout=5, phrase_time_limit=5)
                except sr.WaitTimeoutError:
                    continue
            path = os.path.join(tempfile.gettempdir(), f"sai_enrol_{i}.wav")
            with wave.open(path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(audio.sample_width)
                wf.setframerate(audio.sample_rate)
                wf.writeframes(audio.get_wav_data())
            wav_paths.append(path)

        if self._authenticator.enroll(wav_paths):
            self._speak("Voice enrollment successful.")
            if self._gui:
                self._gui.update_status("ENROLLED", "success")
        else:
            self._speak("Voice enrollment failed. Please try again.")

    def shutdown(self) -> None:
        logger.info("Shutting down Sai AI Assistant...")
        self._wake_engine.stop()
        self._reminders.close()
        self._memory.close()
        self._pool.shutdown(wait=False)

    def _on_wake_word(self, phrase: str) -> None:
        if self._active:
            return
        self._active = True
        self._pool.submit(self._handle_activation, phrase)

    def _handle_activation(self, phrase: str) -> None:
        try:
            logger.info("Wake word detected in phrase: %s", phrase)
            if self._gui:
                self._gui.update_status("ACTIVE - listening", "success")

            self._speak("Yes, how can I help?")

            heard_future = self._pool.submit(self._speech.listen_once)
            text = heard_future.result(timeout=20)
            if not text:
                self._speak("I did not catch that. Please try again.")
                return

            if self._gui:
                self._gui.show_recognised(text)
                self._gui.log_chat("You", text)

            intent_future = self._pool.submit(self._intent_engine.detect, text)
            ai_intent = intent_future.result(timeout=8)

            exec_future = self._pool.submit(self._router.route, ai_intent)
            response = exec_future.result(timeout=15)

            self._speak(response)
            if self._gui:
                self._gui.show_response(response)
                self._gui.update_status("LISTENING", "success")
        except Exception as exc:
            logger.error("Activation flow failed: %s", exc)
            self._speak("I hit an error while processing that request.")
        finally:
            self._active = False

    def _on_reminder_due(self, reminder: dict) -> None:
        msg = f"Reminder: {reminder['task']}"
        self._speak(msg)
        if self._gui:
            self._gui.show_reminder_popup(reminder["task"])
            self._gui.log_chat("Sai AI", msg)

    def _speak(self, text: str) -> None:
        logger.info("Speaking: %s", text[:100])
        threading.Thread(target=self._speech.speak, args=(text,), daemon=True).start()


def _run_gui(assistant: SaiAssistant) -> None:
    from ui.interface import SaiInterface

    gui = SaiInterface(
        on_start_listening=assistant.start_listening,
        on_stop_listening=assistant.stop_listening,
        on_language_change=assistant.set_language,
        on_enrol_voice=assistant.enrol_voice,
        on_text_command=assistant.handle_text_command,
    )
    assistant._gui = gui
    gui.run()


def _run_headless(assistant: SaiAssistant) -> None:
    print("\nSai AI Voice Assistant - Headless mode")
    print("Type commands (Ctrl+C to quit):\n")
    assistant.start_listening()
    try:
        while True:
            text = input("You: ").strip()
            if not text:
                continue
            response = assistant.handle_text_command(text)
            print(f"Sai AI: {response}\n")
    except KeyboardInterrupt:
        print("\nBye!")
    finally:
        assistant.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sai AI Voice Assistant")
    parser.add_argument("--no-gui", action="store_true", help="Run in headless CLI mode")
    parser.add_argument("--enrol", action="store_true", help="Enroll owner voice and exit")
    args = parser.parse_args()

    assistant = SaiAssistant()

    if args.enrol:
        assistant.enrol_voice()
        assistant.shutdown()
        return

    if args.no_gui:
        _run_headless(assistant)
    else:
        try:
            _run_gui(assistant)
        except Exception as exc:
            logger.warning("GUI failed (%s) - falling back to headless mode.", exc)
            _run_headless(assistant)
        finally:
            assistant.shutdown()


if __name__ == "__main__":
    main()
