#!/usr/bin/env python3
"""
Sai AI Voice Assistant – Installer
====================================
Run this script once to install all dependencies and configure the assistant.

Usage:
    python install.py
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _info(msg: str) -> None:
    print(f"\033[94m[INFO]\033[0m  {msg}")


def _ok(msg: str) -> None:
    print(f"\033[92m[ OK ]\033[0m  {msg}")


def _warn(msg: str) -> None:
    print(f"\033[93m[WARN]\033[0m  {msg}")


def _err(msg: str) -> None:
    print(f"\033[91m[ERR ]\033[0m  {msg}", file=sys.stderr)


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    """Run *cmd* and stream its output to the terminal."""
    result = subprocess.run(cmd, check=False)
    if check and result.returncode != 0:
        _err(f"Command failed (exit {result.returncode}): {' '.join(cmd)}")
        sys.exit(result.returncode)
    return result


def _pip_install(packages: list[str]) -> None:
    """Install *packages* using the current Python's pip."""
    _run([sys.executable, "-m", "pip", "install", "--upgrade", *packages])


# ---------------------------------------------------------------------------
# Installation steps
# ---------------------------------------------------------------------------

def check_python_version() -> None:
    _info("Checking Python version…")
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 9):
        _err(f"Python 3.9+ is required. Found {major}.{minor}.")
        sys.exit(1)
    _ok(f"Python {major}.{minor} detected.")


def upgrade_pip() -> None:
    _info("Upgrading pip…")
    _run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=False)
    _ok("pip upgraded.")


def install_requirements() -> None:
    req_path = Path(__file__).parent / "requirements.txt"
    if not req_path.exists():
        _warn("requirements.txt not found – skipping package install.")
        return
    _info("Installing Python dependencies from requirements.txt…")
    _run([sys.executable, "-m", "pip", "install", "-r", str(req_path)], check=False)
    _ok("Dependencies installed.")


def create_directories() -> None:
    _info("Creating required directories…")
    base = Path(__file__).parent
    dirs = [
        base / "logs",
        base / "memory",
        base / "authentication" / "voice_profiles",
        base / "android_app",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    _ok("Directories ready.")


def check_microphone() -> None:
    _info("Checking microphone availability…")
    try:
        import speech_recognition as sr  # type: ignore
        mics = sr.Microphone.list_microphone_names()
        if mics:
            _ok(f"Found {len(mics)} audio device(s). Default microphone is available.")
        else:
            _warn("No microphone devices detected. Voice input will not work.")
    except Exception as exc:
        _warn(f"Could not list microphones: {exc}")


def configure_settings() -> None:
    _info("Configuring settings…")
    cfg_path = Path(__file__).parent / "config" / "settings.json"
    if not cfg_path.exists():
        _warn("config/settings.json not found – skipping configuration.")
        return

    with open(cfg_path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)

    # Remind about the Android secret key
    android_key = cfg.get("android", {}).get("secret_key", "")
    if android_key == "change_this_secret_key_in_production":
        _warn(
            "Remember to change 'android.secret_key' in config/settings.json "
            "before enabling Android companion mode."
        )

    _ok("Settings verified.")


def print_next_steps() -> None:
    print()
    print("=" * 60)
    print("  Sai AI Voice Assistant – Installation Complete!")
    print("=" * 60)
    print()
    print("  Start the assistant:")
    print("    python main.py             (GUI mode)")
    print("    python main.py --no-gui    (headless CLI mode)")
    print("    python main.py --enrol     (enroll owner voice)")
    print()
    print("  Optional – install Ollama for local AI:")
    print("    https://ollama.com/")
    print("    ollama pull llama3")
    print()
    print("  Optional – enable Android companion:")
    print("    1. Set android.enabled = true in config/settings.json")
    print("    2. Install the Sai Companion APK on your phone")
    print("       (see android_app/README.md for build instructions)")
    print()
    print("  Run tests:")
    print("    python -m pytest tests/ -v")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print()
    print("=" * 60)
    print("  Sai AI Voice Assistant Installer")
    print("=" * 60)
    print(f"  OS      : {platform.system()} {platform.release()}")
    print(f"  Python  : {sys.version.split()[0]}")
    print()

    check_python_version()
    upgrade_pip()
    install_requirements()
    create_directories()
    check_microphone()
    configure_settings()
    print_next_steps()


if __name__ == "__main__":
    main()
