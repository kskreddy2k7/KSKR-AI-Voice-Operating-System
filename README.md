<div align="center">

# 🎙️ Sai AI Voice Assistant

**A next-generation, open-source AI voice assistant for Windows PC and Android**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-53%20passing-brightgreen)](#testing)
[![Demo](https://img.shields.io/badge/Demo-GitHub%20Pages-orange)](https://kskreddy2k7.github.io/KSKR-AI-Voice-Operating-System/)

*Listens continuously · Understands natural language · Controls your PC and Android phone*

</div>

---

## 📖 Overview

**Sai AI** is a fully modular, production-ready voice assistant that works like a modern
assistant (similar to Siri or Google Assistant) — but runs **locally** on your Windows PC.
It uses offline speech recognition, a plugin architecture, SQLite memory, and a REST API
bridge to your Android phone.

### Wake Words
Say any of these to activate:

| Wake Word | Example |
|---|---|
| **Hey Sai** | "Hey Sai, open Chrome" |
| **Hello Sai** | "Hello Sai, what time is it?" |
| **Ok Sai** | "Ok Sai, remind me to study at 7 PM" |

---

## ✨ Features

| Category | Capabilities |
|---|---|
| 🔊 **Wake Word** | Continuous background listening; activates on wake phrase |
| 🌐 **Speech Recognition** | English, Hindi, Telugu, Tamil, Kannada; noise filtering |
| 🧠 **AI Intent Engine** | NLP command parsing + Ollama / OpenAI / offline fallback |
| 🖥️ **Windows Control** | Open apps, folders, browser search, media, system commands |
| 📱 **Android Companion** | SMS, calls, app launch, feed scroll, WhatsApp — over Wi-Fi REST API |
| 🗓️ **Reminders** | Natural-language time parsing; popup + voice alerts |
| 💾 **Memory System** | SQLite-backed facts recalled conversationally |
| 🔐 **Voice Authentication** | Enrol voice print; reject unknown speakers |
| 🧩 **Plugin System** | Drop Python files in `plugins/` — auto-loaded at startup |
| 🖼️ **Desktop GUI** | Dark-mode Tkinter interface with chat log, status, controls |
| ⚡ **Multi-threading** | Separate threads for recognition, AI, and execution |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Microphone Input                      │
└───────────────────────────┬──────────────────────────────┘
                            ↓
          ┌─────────────────────────────────┐
          │     Wake Word Engine            │
          │  (hey sai / hello sai / ok sai) │
          └────────────────┬────────────────┘
                           ↓
          ┌─────────────────────────────────┐
          │     Speech Recognizer           │
          │  (en / hi / te / ta / kn)       │
          └────────────────┬────────────────┘
                           ↓
          ┌─────────────────────────────────┐
          │     Intent Engine (AI / NLP)    │
          │  (Ollama · OpenAI · fallback)   │
          └────────────────┬────────────────┘
                           ↓
          ┌─────────────────────────────────┐
          │        Command Router           │
          └──┬──────────┬──────────┬────────┘
             ↓          ↓          ↓
     ┌───────────┐ ┌─────────┐ ┌──────────────────┐
     │ Windows   │ │ Android │ │ Memory / Reminder │
     │ Controller│ │ REST API│ │ / Chat / Plugins  │
     └───────────┘ └─────────┘ └──────────────────┘
             ↓
     ┌───────────────────────┐
     │  TTS Response + GUI   │
     └───────────────────────┘
```

### Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.9+ |
| Speech Input | `SpeechRecognition` + Google Web Speech API |
| Text-to-Speech | `pyttsx3` (offline) |
| AI / NLP | Ollama (local LLM) · OpenAI GPT · built-in rules |
| Android Bridge | Flask REST API |
| Memory & Reminders | SQLite3 (stdlib) |
| GUI | Tkinter (stdlib) |
| Media / OS Control | `pyautogui` |
| Threading | `ThreadPoolExecutor` |

---

## 📁 Project Structure

```
KSKR-AI-Voice-Operating-System/
├── main.py                    # Entry point
├── install.py                 # One-command installer
├── requirements.txt
├── config/
│   └── settings.json          # All configuration
├── core/
│   ├── speech_engine.py       # Unified speech I/O
│   ├── wake_word_engine.py    # Always-on wake word
│   └── intent_engine.py       # NLP → structured intent
├── router/
│   └── command_router.py      # Intent → execution dispatch
├── automation/
│   └── windows_controller.py  # OS automation
├── android/
│   └── phone_api.py           # REST API for phone companion
├── memory/
│   └── memory_manager.py      # SQLite fact storage
├── reminders/
│   └── reminder_manager.py    # Scheduled reminders
├── plugins/
│   ├── plugin_loader.py       # Auto-loads plugin files
│   ├── weather_plugin.py
│   ├── jokes_plugin.py
│   └── time_plugin.py
├── speech/
│   ├── recognizer.py          # Multi-language recognizer
│   └── tts.py                 # pyttsx3 wrapper
├── wakeword/
│   └── detector.py            # Background listener
├── nlp/
│   ├── command_parser.py      # Rule-based NLP parser
│   └── chat_assistant.py      # Conversational AI
├── authentication/
│   └── voice_auth.py          # Voice-print enrollment/verify
├── ui/
│   └── interface.py           # Tkinter dark-mode GUI
├── tests/
│   ├── test_sai.py
│   ├── test_microphone.py
│   └── test_commands.py
├── android_app/
│   └── README.md              # Android APK build instructions
├── website/
│   ├── index.html             # GitHub Pages demo site
│   ├── style.css
│   └── script.js
└── logs/
    └── system.log
```

---

## 🚀 Installation

### Prerequisites

- Python 3.9 or later
- A working microphone
- Windows (full feature set) or macOS / Linux (development / headless mode)

### Quick install

```bash
# 1. Clone the repository
git clone https://github.com/kskreddy2k7/KSKR-AI-Voice-Operating-System.git
cd KSKR-AI-Voice-Operating-System

# 2. Run the installer (installs all dependencies)
python install.py

# 3. Launch
python main.py              # GUI mode  (recommended)
python main.py --no-gui     # Headless CLI mode
python main.py --enrol      # Enroll your voice first
```

### Manual install (alternative)

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Unix:     source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Optional – Local AI with Ollama

```bash
# Install Ollama from https://ollama.com/
ollama pull llama3
# Then set "ai_chat.provider": "ollama" in config/settings.json
```

---

## 💬 Usage Examples

| You say | Sai AI responds |
|---|---|
| "Hey Sai, open Chrome" | "Opening Chrome." |
| "Search for machine learning tutorials" | Opens browser with search |
| "Create a folder called AI Project" | Creates folder on Desktop |
| "Remind me to study AI at 7 PM" | "Reminder set." — alerts at 7 PM |
| "Remember my favourite language is Python" | "Got it!" (stored in SQLite) |
| "What language do I like?" | "You like Python." |
| "Send message to John saying I will be late" | SMS sent via Android companion |
| "Call Mom" | Phone call initiated |
| "Scroll Instagram" | Feed scroll triggered on phone |
| "What's the weather in Hyderabad?" | Live weather from Open-Meteo API |
| "Tell me a joke" | 😄 |
| "Shutdown the computer" | Shuts down in 10 seconds |
| "Volume up" | Media volume increased |

---

## 📱 Android Companion APK

The **Sai Companion** Android app connects to the PC assistant over a local
Wi-Fi REST API.

### Capabilities
- Send SMS
- Make phone calls
- Open apps
- Scroll social media feeds
- Play / pause music
- Send WhatsApp messages

### Build the APK

1. Open `android_app/` in **Android Studio**.
2. Run **Build → Build APK**.
3. Install the generated APK on your Android phone.
4. Enable Android mode in `config/settings.json`:
   ```json
   "android": { "enabled": true, "port": 5050 }
   ```
5. Start Sai AI, then connect the Sai Companion app to your PC's IP address.

Full build instructions: [`android_app/README.md`](android_app/README.md)

---

## 🧩 Plugin Development

Drop a Python file in the `plugins/` folder.  It will be auto-loaded at startup.

```python
# plugins/my_plugin.py

PLUGIN_NAME    = "my_plugin"
PLUGIN_INTENTS = ["my_keyword"]

def setup() -> None:
    pass  # called once at load time

def handle(command) -> str:
    return "Hello from my plugin!"
```

---

## 🌐 GitHub Pages Demo

Live demo website: **https://kskreddy2k7.github.io/KSKR-AI-Voice-Operating-System/**

The site is in the `website/` folder and can be deployed directly via
**GitHub Pages** (set source to `/(root)` on the `main` branch or point to
the `website/` subfolder).

---

## 🧪 Testing

```bash
python -m pytest tests/ -v
```

53 tests cover:
- NLP command parsing
- Memory store/recall/delete
- Reminder scheduling and callbacks
- Plugin loader
- Chat assistant (offline fallback)
- Windows controller
- Intent engine
- Microphone detection

---

## ⚙️ Configuration

All settings live in `config/settings.json`.

| Key | Description |
|---|---|
| `wake_words` | List of activation phrases |
| `speech.language` | Default language BCP-47 code |
| `ai_chat.provider` | `ollama`, `openai`, or `fallback` |
| `ai_chat.openai_api_key` | OpenAI key (optional) |
| `android.enabled` | Enable Android REST server |
| `android.secret_key` | API key for phone companion |
| `tts.rate` | Speech rate (words per minute) |
| `voice_auth.enabled` | Enable voice authentication |

---

## 🛣️ Future Improvements

- [ ] Offline wake-word model (pvporcupine / openWakeWord)
- [ ] Fully offline speech recognition (Vosk / Whisper)
- [ ] Kotlin-based Sai Companion Android app with full UI
- [ ] macOS and Linux system controller backends
- [ ] Smart home integration (Home Assistant / MQTT)
- [ ] Personality and conversation history persistence
- [ ] Web dashboard for remote control
- [ ] Custom voice model fine-tuning

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
Built with ❤️ and Python &nbsp;·&nbsp;
<a href="https://github.com/kskreddy2k7/KSKR-AI-Voice-Operating-System">GitHub</a> &nbsp;·&nbsp;
<a href="https://kskreddy2k7.github.io/KSKR-AI-Voice-Operating-System/">Demo</a>
</div>
