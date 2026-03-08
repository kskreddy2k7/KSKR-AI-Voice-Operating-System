# KSKR Voice OS

> **A next-generation, modular AI Voice Operating System for Windows with Android integration and multi-language Indian language support.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-46%20passing-brightgreen)](#testing)

---

## Overview

**KSKR Voice OS** is a fully modular, extensible AI voice assistant designed to run on Windows computers and communicate with Android devices over Wi-Fi. It behaves as a personal AI operating system—responding only to the owner's registered voice, supporting multiple Indian languages, and automating day-to-day Windows tasks through natural language commands.

The project is structured as a professional portfolio piece, demonstrating real-world software engineering practices: modular architecture, plugin systems, REST API integration, SQLite persistence, and automated tests.

---

## Key Features

| Feature | Description |
|---------|-------------|
| 🎙️ **Wake Word Detection** | Always-on lightweight listener; activates on *"Hey KSKR"* or *"Hello Assistant"* |
| 🗣️ **Multilingual Speech Recognition** | English, Hindi, Telugu, Tamil, Kannada via Google Web Speech API |
| 🔐 **Voice Authentication** | Speaker verification ensures only the registered owner can issue commands |
| 🧠 **AI Command Understanding** | Rule-first NLP parser + AI chat fallback (Ollama/OpenAI) |
| 🖥️ **Windows Automation** | Open/close apps, create folders, search the web, control media |
| 💬 **AI Chat Assistant** | Conversational responses via Ollama (local) or OpenAI GPT |
| 🧩 **Plugin Architecture** | Dynamically load/unload plugins; ships with Weather, Jokes, Time plugins |
| 🗄️ **Personal Memory** | SQLite-backed key-value store for preferences and facts |
| ⏰ **Reminder System** | Create time-based reminders; background poller fires callbacks |
| 📱 **Android Integration** | Flask REST API lets Android apps send commands over Wi-Fi |
| 🖼️ **Graphical Interface** | Dark-themed Tkinter GUI with live transcript, chat history, and controls |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         KSKR Voice OS                               │
│                                                                     │
│  ┌───────────────┐    ┌──────────────────┐    ┌─────────────────┐  │
│  │  Wake Word    │───▶│ Speech Recognizer│───▶│ Voice Auth      │  │
│  │  Detector     │    │ (multilingual)   │    │ (resemblyzer /  │  │
│  └───────────────┘    └──────────────────┘    │  librosa MFCC)  │  │
│                                               └────────┬────────┘  │
│                                                        │           │
│  ┌─────────────────────────────────────────────────────▼─────────┐ │
│  │                    NLP Command Parser                          │ │
│  │  (rules-first, 10 intent types + AI fallback)                 │ │
│  └──────────────────────────────┬────────────────────────────────┘ │
│                                 │                                  │
│         ┌───────────────────────┼───────────────────────┐          │
│         ▼                       ▼                       ▼          │
│  ┌─────────────┐   ┌────────────────────┐   ┌────────────────┐    │
│  │  Windows    │   │  Memory + Reminders│   │ Plugin Loader  │    │
│  │  Controller │   │  (SQLite)          │   │ (dynamic)      │    │
│  └─────────────┘   └────────────────────┘   └────────────────┘    │
│                                                                     │
│  ┌──────────────────┐    ┌────────────────┐    ┌───────────────┐  │
│  │  Chat Assistant  │    │   TTS Engine   │    │  Android API  │  │
│  │  (Ollama/OpenAI) │    │  (pyttsx3)     │    │  (Flask REST) │  │
│  └──────────────────┘    └────────────────┘    └───────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  Tkinter GUI (Dark Theme)                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
kskr-voice-os/
│
├── main.py                        # Entry point – orchestrates all subsystems
│
├── wakeword/
│   └── detector.py                # Wake word detection (background listener)
│
├── speech/
│   ├── recognizer.py              # Multilingual speech-to-text
│   └── tts.py                     # Text-to-speech (pyttsx3)
│
├── authentication/
│   └── voice_auth.py              # Speaker verification (resemblyzer / MFCC)
│
├── nlp/
│   ├── command_parser.py          # Rule-based NLP intent classification
│   └── chat_assistant.py          # AI chat (Ollama / OpenAI / fallback)
│
├── automation/
│   └── windows_controller.py      # Open apps, folders, search, media, system
│
├── memory/
│   └── memory_manager.py          # SQLite key-value personal memory
│
├── reminders/
│   └── reminder_manager.py        # Time-based reminders with background polling
│
├── plugins/
│   ├── plugin_loader.py           # Dynamic plugin discovery and dispatch
│   ├── weather_plugin.py          # Weather via Open-Meteo (no API key)
│   ├── jokes_plugin.py            # Programming jokes
│   └── time_plugin.py             # Current time and date
│
├── android/
│   └── phone_api.py               # Flask REST API for Android integration
│
├── ui/
│   └── interface.py               # Tkinter dark-themed GUI
│
├── config/
│   └── settings.json              # All configuration in one place
│
├── tests/
│   └── test_kskr.py               # 46 unit tests (pytest)
│
├── requirements.txt
└── README.md
```

---

## Installation

### Prerequisites

- **Python 3.10+**
- **Windows 10/11** (recommended for full automation features; core modules work on Linux/macOS)
- A **working microphone**

### 1. Clone the Repository

```bash
git clone https://github.com/kskreddy2k7/KSKR-AI-Voice-Operating-System.git
cd KSKR-AI-Voice-Operating-System
```

### 2. Create a Virtual Environment (recommended)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> **PyAudio on Windows:** If `pip install pyaudio` fails, download the pre-built wheel from [Gohlke's archive](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) or use:
> ```bash
> pip install pipwin && pipwin install pyaudio
> ```

### 4. (Optional) Install Ollama for AI Chat

```bash
# Download from https://ollama.com/download
ollama pull llama3
```

### 5. (Optional) Install resemblyzer for Better Voice Auth

```bash
pip install resemblyzer
```

---

## Configuration

Edit `config/settings.json` to customise the assistant:

```jsonc
{
  "wake_words": ["hey kskr", "hello assistant"],
  "speech": {
    "language": "en-IN"           // Default recognition language
  },
  "voice_auth": {
    "enabled": true,
    "threshold": 0.75             // Cosine-similarity acceptance threshold
  },
  "ai_chat": {
    "provider": "ollama",         // "ollama" | "openai"
    "ollama_model": "llama3",
    "openai_api_key": ""          // Set if using OpenAI
  },
  "android": {
    "enabled": false,             // Set true to start the REST API
    "port": 5050,
    "secret_key": "change_me"
  }
}
```

---

## Usage

### Start with GUI

```bash
python main.py
```

### Start in Headless / CLI Mode

```bash
python main.py --no-gui
```

### Enrol Your Voice (first-time setup)

```bash
python main.py --enrol
```

---

## Example Commands

### App Control
```
"Hey KSKR" → "Open Chrome"
"Hey KSKR" → "Launch Visual Studio Code"
"Hey KSKR" → "Close Spotify"
```

### File System
```
"Hey KSKR" → "Open the Downloads folder"
"Hey KSKR" → "Create a folder called AI Project"
```

### Web Search
```
"Hey KSKR" → "Search machine learning tutorials"
"Hey KSKR" → "Google how to install Python"
```

### Reminders
```
"Hey KSKR" → "Remind me to study AI at 7 PM"
"Hey KSKR" → "What tasks do I have today?"
```

### Personal Memory
```
"Hey KSKR" → "My favorite programming language is Python"
"Hey KSKR" → "What is my favorite programming language?"
```

### AI Conversation
```
"Hey KSKR" → "What is machine learning?"
"Hey KSKR" → "Explain neural networks"
"Hey KSKR" → "Tell me a programming joke"
```

### Media Control
```
"Hey KSKR" → "Play music"
"Hey KSKR" → "Volume up"
"Hey KSKR" → "Pause"
```

### Plugins
```
"Hey KSKR" → "What is the weather in Hyderabad?"
"Hey KSKR" → "What time is it?"
"Hey KSKR" → "Tell me a joke"
```

---

## Android Integration

1. Set `"android": {"enabled": true}` in `config/settings.json`
2. Restart KSKR Voice OS
3. From your Android device (on the same Wi-Fi network), send:

```bash
# Check status
curl http://<PC_IP>:5050/status

# Send a voice command
curl -X POST http://<PC_IP>:5050/command \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your_secret_key" \
     -d '{"text": "open chrome"}'

# Get today's reminders
curl http://<PC_IP>:5050/reminders \
     -H "X-API-Key: your_secret_key"
```

---

## Adding a Custom Plugin

1. Create a file in the `plugins/` directory, e.g. `plugins/email_plugin.py`
2. Define the required contract:

```python
PLUGIN_NAME = "email"
PLUGIN_INTENTS = ["email", "send email", "check email"]

def setup():
    pass  # Called once when loaded

def handle(command):
    # command.raw_text contains the full utterance
    # command.target contains the parsed target
    return "Email feature coming soon!"
```

3. KSKR automatically discovers and loads plugins on startup.

---

## Testing

```bash
python -m pytest tests/ -v
```

Expected output: **46 tests passing** across:
- NLP Command Parser (18 tests)
- Memory Manager (8 tests)
- Time Parser (6 tests)
- Reminder Manager (4 tests)
- Plugin Loader (3 tests)
- Chat Assistant (3 tests)
- Windows Controller (4 tests)

---

## Supported Languages

| Language | Code |
|----------|------|
| English (India) | `en-IN` |
| Hindi | `hi-IN` |
| Telugu | `te-IN` |
| Tamil | `ta-IN` |
| Kannada | `kn-IN` |

Switch languages in the GUI language dropdown or with the command:
> *"Hey KSKR, switch to Hindi"*

---

## Future Improvements

- [ ] **Neural wake-word engine** (pvporcupine) for offline, always-on detection
- [ ] **Multilingual NLP** – extend command parser to handle Hindi/Telugu commands
- [ ] **Android companion app** – native app for full two-way communication
- [ ] **Smart home integration** – MQTT/Home Assistant bridge
- [ ] **Continuous speaker verification** – verify every utterance, not just on demand
- [ ] **Email plugin** – read/send emails via IMAP/SMTP
- [ ] **Calendar plugin** – Google Calendar or Outlook integration
- [ ] **Custom wake word training** – personal wake word model training pipeline
- [ ] **Streaming STT** – real-time transcription with Whisper
- [ ] **Docker support** – containerised deployment

---

## License

This project is released under the [MIT License](LICENSE).

---

## Author

**KSKR** – Built as a professional AI portfolio project demonstrating modular system design, Python best practices, and multi-modal AI integration.

---

*KSKR Voice OS – Your Personal AI, Your Voice, Your Commands.*