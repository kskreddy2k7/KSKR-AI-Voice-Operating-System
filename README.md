# Sai AI Voice Assistant

Sai AI Voice Assistant is an advanced, modular voice assistant for desktop automation and Android companion control.

## Wake Words
- Hey Sai
- Hello Sai
- Ok Sai

## Primary Capabilities
- Natural-language command understanding
- Computer control (apps, browser search, media, system actions)
- Android companion actions (call, message, feed scroll)
- Conversational AI responses
- Reminder and memory support
- Continuous wake-word listening

## Architecture

```text
Microphone Input
  -> Wake Word Detection
  -> Speech Recognition
  -> Intent Detection
  -> Command Router
  -> Execution Engine
  -> Device Control
```

## Current Project Structure

```text
sai-ai-assistant/
main.py
core/
  speech_engine.py
  wake_word_engine.py
  intent_engine.py
router/
  command_router.py
automation/
  windows_controller.py
plugins/
  plugin_loader.py
memory/
  memory_manager.py
reminders/
  reminder_manager.py
android/
  phone_api.py
ui/
  interface.py
config/
  settings.json
logs/
  system.log
tests/
  test_microphone.py
  test_commands.py
README.md
requirements.txt
```

## Android Companion
Sai Companion is exposed through the REST API module `android/phone_api.py`.
It includes helpers for:
- calling contacts
- sending messages
- opening mobile apps
- scrolling feeds
- controlling media

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Example Interactions
- "Hey Sai, open Chrome" -> "Opening Chrome"
- "Send message to Mom saying I will be late" -> "Message sent"
- "Scroll Instagram" -> assistant triggers feed scroll action
- "What is machine learning?" -> conversational answer
