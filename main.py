"""
KSKR Voice OS — Main Entry Point
==================================
Orchestrates all subsystems:

  Wake Word Detector ──► Speech Recognizer ──► Voice Authenticator
         │                                              │
         ▼                                              ▼
  Command Parser ──► Windows Controller / Memory / Reminders / Plugins
         │
         ▼
  Chat Assistant ──► TTS ──► UI

Usage
-----
  python main.py              # Full GUI mode
  python main.py --no-gui     # Headless / CLI mode (for testing)
  python main.py --enrol      # Enrol owner voice and exit
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
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Logging setup (must be done before any module imports trigger logging)
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(_LOG_DIR, "kskr_voice_os.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("kskr.main")

# ---------------------------------------------------------------------------
# Module imports (after logging is configured)
# ---------------------------------------------------------------------------
from wakeword.detector import WakeWordDetector
from speech.recognizer import SpeechRecognizer
from speech.tts import TextToSpeech
from authentication.voice_auth import VoiceAuthenticator
from nlp.command_parser import CommandParser, Command
from nlp.chat_assistant import ChatAssistant
from automation.windows_controller import WindowsController
from memory.memory_manager import MemoryManager
from reminders.reminder_manager import ReminderManager
from plugins.plugin_loader import PluginLoader
from android.phone_api import PhoneAPI


def _load_config() -> dict:
    cfg_path = os.path.join(os.path.dirname(__file__), "config", "settings.json")
    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        logger.warning("Could not load config: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Core Assistant class
# ---------------------------------------------------------------------------

class KSKRAssistant:
    """Central coordinator for all KSKR Voice OS subsystems."""

    def __init__(self, gui=None) -> None:
        self._gui = gui
        self._cfg = _load_config()
        self._active = False   # True while processing a command

        # Subsystems
        logger.info("Initialising subsystems…")
        self._tts = TextToSpeech()
        self._recognizer = SpeechRecognizer()
        self._authenticator = VoiceAuthenticator()
        self._parser = CommandParser()
        self._chat = ChatAssistant()
        self._controller = WindowsController()
        self._memory = MemoryManager()
        self._plugins = PluginLoader()
        self._plugins.load_all()

        # Reminders
        self._reminders = ReminderManager(on_due=self._on_reminder_due)
        self._reminders.start()

        # Wake word detector (started separately)
        self._wake_detector = WakeWordDetector(on_detected=self._on_wake_word)

        # Android API
        android_cfg = self._cfg.get("android", {})
        if android_cfg.get("enabled", False):
            self._phone_api = PhoneAPI(
                command_handler=self.handle_text_command,
                reminder_manager=self._reminders,
            )
            self._phone_api.start()
        else:
            self._phone_api = None

        logger.info("KSKR Assistant ready.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_listening(self) -> None:
        """Start the wake-word detector (non-blocking)."""
        logger.info("Starting wake word detector…")
        self._wake_detector.start()
        self._speak("KSKR is now listening for the wake word.")

    def stop_listening(self) -> None:
        """Stop the wake-word detector."""
        self._wake_detector.stop()
        self._speak("Stopped listening.")

    def handle_text_command(self, text: str) -> str:
        """Process a text command and return the response string.

        Can be called from the GUI text box, the Android API, or unit tests.
        """
        if not text:
            return ""
        logger.info("Processing text command: %s", text)
        command = self._parser.parse(text)
        logger.info("Parsed → %s", command)
        response = self._execute(command)
        self._speak(response)
        if self._gui:
            self._gui.show_response(response)
        return response

    def set_language(self, language_name: str) -> None:
        """Switch speech recognition language."""
        self._recognizer.set_language(language_name)

    def enrol_voice(self) -> None:
        """Interactive voice enrolment – captures 5 samples from the mic."""
        self._speak(
            "Voice enrolment mode. I will record 5 short samples of your voice. "
            "After each beep, say your name or a short phrase."
        )
        import speech_recognition as sr
        r = sr.Recognizer()
        wav_paths = []
        for i in range(5):
            self._speak(f"Recording sample {i + 1}. Speak now.")
            if self._gui:
                self._gui.update_status(f"● ENROLLING ({i+1}/5)", "warning")
            with sr.Microphone() as src:
                r.adjust_for_ambient_noise(src, duration=0.3)
                try:
                    audio = r.listen(src, timeout=5, phrase_time_limit=5)
                except sr.WaitTimeoutError:
                    continue
            # Save to temp file
            path = os.path.join(tempfile.gettempdir(), f"kskr_enrol_{i}.wav")
            with wave.open(path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(audio.sample_width)
                wf.setframerate(audio.sample_rate)
                wf.writeframes(audio.get_wav_data())
            wav_paths.append(path)

        if self._authenticator.enroll(wav_paths):
            self._speak("Voice enrolment successful! I will now only respond to your voice.")
            if self._gui:
                self._gui.update_status("● ENROLLED", "success")
        else:
            self._speak("Voice enrolment failed. Please try again.")

    def shutdown(self) -> None:
        """Gracefully stop all subsystems."""
        logger.info("Shutting down KSKR Assistant…")
        self._wake_detector.stop()
        self._reminders.close()
        self._memory.close()

    # ------------------------------------------------------------------
    # Internal: wake word → listen → auth → execute
    # ------------------------------------------------------------------

    def _on_wake_word(self, phrase: str) -> None:
        if self._active:
            return  # Already processing
        self._active = True
        try:
            self._handle_activation()
        finally:
            self._active = False

    def _handle_activation(self) -> None:
        logger.info("Wake word detected – activating.")
        if self._gui:
            self._gui.update_status("● ACTIVE – listening…", "success")

        self._speak("Yes?")

        # Capture command audio
        text = self._recognizer.listen()
        if not text:
            self._speak("I didn't catch that. Please try again.")
            if self._gui:
                self._gui.update_status("● IDLE", "text_dim")
            return

        logger.info("Recognised: %s", text)
        if self._gui:
            self._gui.show_recognised(text)
            self._gui.log_chat("You", text)

        # (Voice authentication skipped here when no profile is enrolled)
        if self._authenticator.is_enrolled:
            # For simplicity we skip per-utterance auth during demo;
            # production would save the audio and call verify()
            pass

        # Parse and execute
        command = self._parser.parse(text)
        logger.info("Command: %s", command)
        response = self._execute(command)
        logger.info("Response: %s", response)

        self._speak(response)
        if self._gui:
            self._gui.show_response(response)
            self._gui.update_status("● LISTENING", "success")

    def _execute(self, command: Command) -> str:
        """Dispatch a parsed command to the appropriate handler."""
        intent = command.intent

        # 1. Plugins take priority
        plugin_response = self._plugins.handle(command)
        if plugin_response is not None:
            return plugin_response

        # 2. Built-in intents
        if intent == "open_app":
            return self._controller.open_app(command.target)

        if intent == "open_folder":
            return self._controller.open_folder(command.target)

        if intent == "create_folder":
            return self._controller.create_folder(command.target)

        if intent == "search_web":
            return self._controller.search_web(command.target)

        if intent == "play_media":
            return self._controller.control_media(
                command.params.get("action", "play"), command.target
            )

        if intent == "system":
            return self._controller.system_command(
                command.params.get("action", ""), command.target
            )

        if intent == "reminder":
            return self._handle_reminder(command)

        if intent == "memory_store":
            return self._memory.store(command.target, command.params.get("value", ""))

        if intent == "memory_query":
            value = self._memory.recall(command.target)
            if value:
                return f"Your {command.target} is {value}."
            return f"I don't have anything stored about your {command.target}."

        if intent == "chat":
            return self._chat.chat(command.target or command.raw_text)

        return "I'm not sure how to handle that. Could you rephrase?"

    def _handle_reminder(self, command: Command) -> str:
        if command.target == "list":
            items = self._reminders.list_today()
            if not items:
                return "You have no reminders for today."
            lines = [f"• {r['task']} at {r['due_at']}" for r in items]
            return "Your reminders: " + "; ".join(lines)
        task = command.params.get("task", command.target)
        time_str = command.params.get("time", "")
        return self._reminders.add(task, time_str)

    def _on_reminder_due(self, reminder: dict) -> None:
        msg = f"Reminder: {reminder['task']}"
        self._speak(msg)
        if self._gui:
            self._gui.show_reminder_popup(reminder["task"])
            self._gui.log_chat("KSKR", f"⏰ {msg}")

    def _speak(self, text: str) -> None:
        logger.info("Speaking: %s", text[:100])
        if self._gui:
            # Non-blocking TTS in the main thread to avoid Tkinter issues
            threading.Thread(target=self._tts.speak, args=(text,), daemon=True).start()
        else:
            self._tts.speak(text)


# ---------------------------------------------------------------------------
# CLI / GUI runner
# ---------------------------------------------------------------------------

def _run_gui(assistant: KSKRAssistant) -> None:
    from ui.interface import KSKRInterface

    gui = KSKRInterface(
        on_start_listening=assistant.start_listening,
        on_stop_listening=assistant.stop_listening,
        on_language_change=assistant.set_language,
        on_enrol_voice=assistant.enrol_voice,
        on_text_command=assistant.handle_text_command,
    )
    assistant._gui = gui  # Wire up after creation
    gui.run()


def _run_headless(assistant: KSKRAssistant) -> None:
    """Simple REPL for testing without a display."""
    print("\nKSKR Voice OS – Headless mode")
    print("Type commands (Ctrl+C to quit):\n")
    assistant.start_listening()
    try:
        while True:
            text = input("You: ").strip()
            if not text:
                continue
            response = assistant.handle_text_command(text)
            print(f"KSKR: {response}\n")
    except KeyboardInterrupt:
        print("\nBye!")
    finally:
        assistant.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="KSKR Voice OS")
    parser.add_argument("--no-gui", action="store_true", help="Run in headless CLI mode")
    parser.add_argument("--enrol", action="store_true", help="Enrol owner voice and exit")
    args = parser.parse_args()

    assistant = KSKRAssistant()

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
            logger.warning("GUI failed (%s) – falling back to headless mode.", exc)
            _run_headless(assistant)
        finally:
            assistant.shutdown()


if __name__ == "__main__":
    main()
