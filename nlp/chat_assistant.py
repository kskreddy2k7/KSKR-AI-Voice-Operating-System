"""
AI Chat Assistant
-----------------
Handles open-ended conversation using an AI language model.

Supports multiple backends in order of preference:
1. Ollama (local – private, fast, no API key needed)
2. OpenAI GPT (cloud – requires API key)
3. Fallback hard-coded responses for offline demos

The active backend is selected automatically based on availability and
``config/settings.json``.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "settings.json"
)


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh).get("ai_chat", {})
    except Exception as exc:
        logger.warning("ChatAssistant: could not load config – %s", exc)
        return {}


_FALLBACK_RESPONSES = {
    "machine learning": (
        "Machine learning is a subset of AI where systems learn from data to improve "
        "performance on a task without being explicitly programmed."
    ),
    "neural network": (
        "Neural networks are computing systems loosely inspired by the human brain. "
        "They consist of layers of interconnected nodes that process and transform data."
    ),
    "python": (
        "Python is a high-level, interpreted programming language known for its readability "
        "and versatility. It's widely used in data science, AI, web development, and automation."
    ),
    "artificial intelligence": (
        "Artificial Intelligence is the simulation of human intelligence in machines. "
        "It encompasses machine learning, natural language processing, computer vision, and more."
    ),
    "deep learning": (
        "Deep learning is a type of machine learning that uses multi-layered neural networks "
        "to learn representations of data with multiple levels of abstraction."
    ),
}


class ChatAssistant:
    """Conversational AI with automatic backend selection.

    Parameters
    ----------
    system_prompt:
        Override the system prompt used for all conversations.
    """

    def __init__(self, system_prompt: Optional[str] = None) -> None:
        self._cfg = _load_config()
        self._system_prompt = system_prompt or self._cfg.get(
            "system_prompt",
            "You are KSKR, a helpful AI voice assistant for Windows. "
            "Answer concisely and clearly.",
        )
        self._history: List[Dict[str, str]] = []
        self._backend = self._select_backend()
        logger.info("ChatAssistant: using backend '%s'.", self._backend)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(self, user_message: str) -> str:
        """Send *user_message* and return the assistant's reply."""
        self._history.append({"role": "user", "content": user_message})
        if self._backend == "ollama":
            reply = self._ollama_chat(user_message)
        elif self._backend == "openai":
            reply = self._openai_chat()
        else:
            reply = self._fallback_chat(user_message)
        self._history.append({"role": "assistant", "content": reply})
        return reply

    def clear_history(self) -> None:
        """Reset the conversation history."""
        self._history.clear()

    # ------------------------------------------------------------------
    # Backend implementations
    # ------------------------------------------------------------------

    def _select_backend(self) -> str:
        provider = self._cfg.get("provider", "ollama")
        if provider == "ollama" and self._ollama_available():
            return "ollama"
        if provider == "openai" and self._cfg.get("openai_api_key"):
            return "openai"
        # Auto-detect
        if self._ollama_available():
            return "ollama"
        if self._cfg.get("openai_api_key"):
            return "openai"
        logger.info("ChatAssistant: no cloud backend configured – using fallback responses.")
        return "fallback"

    def _ollama_available(self) -> bool:
        url = self._cfg.get("ollama_url", "http://localhost:11434")
        try:
            with urllib.request.urlopen(f"{url}/api/tags", timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _ollama_chat(self, user_message: str) -> str:
        url = self._cfg.get("ollama_url", "http://localhost:11434")
        model = self._cfg.get("ollama_model", "llama3")
        messages = [{"role": "system", "content": self._system_prompt}] + self._history[:-1]
        messages.append({"role": "user", "content": user_message})

        payload = json.dumps(
            {"model": model, "messages": messages, "stream": False}
        ).encode()

        req = urllib.request.Request(
            f"{url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            return data.get("message", {}).get("content", "I'm not sure how to answer that.")
        except Exception as exc:
            logger.error("ChatAssistant: Ollama error – %s", exc)
            return self._fallback_chat(user_message)

    def _openai_chat(self) -> str:
        api_key = self._cfg.get("openai_api_key", "")
        model = self._cfg.get("openai_model", "gpt-3.5-turbo")
        max_tokens = self._cfg.get("max_tokens", 512)

        messages = [{"role": "system", "content": self._system_prompt}] + self._history

        payload = json.dumps(
            {"model": model, "messages": messages, "max_tokens": max_tokens}
        ).encode()

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.error("ChatAssistant: OpenAI error – %s", exc)
            return self._fallback_chat(self._history[-1]["content"] if self._history else "")

    def _fallback_chat(self, user_message: str) -> str:
        msg = user_message.lower()
        for keyword, response in _FALLBACK_RESPONSES.items():
            if keyword in msg:
                return response
        if "joke" in msg:
            return "Why do programmers prefer dark mode? Because light attracts bugs!"
        if "hello" in msg or "hi" in msg:
            return "Hello! I'm KSKR, your AI voice assistant. How can I help you today?"
        if "your name" in msg or "who are you" in msg:
            return "I'm KSKR, your personal AI voice operating system."
        if "thank" in msg:
            return "You're welcome! Is there anything else I can help you with?"
        return (
            "I'm currently running in offline mode. "
            "For full AI capabilities, please set up Ollama or provide an OpenAI API key "
            "in config/settings.json."
        )
