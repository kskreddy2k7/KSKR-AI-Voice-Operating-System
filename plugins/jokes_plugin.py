"""
Jokes Plugin
------------
Returns programming and general jokes.

Intent keywords: ``joke``, ``funny``
"""

from __future__ import annotations

import logging
import random

logger = logging.getLogger(__name__)

PLUGIN_NAME = "jokes"
PLUGIN_INTENTS = ["joke", "funny", "laugh"]

_JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs!",
    "Why do Java developers wear glasses? Because they don't C#.",
    "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
    "How many programmers does it take to change a light bulb? None – it's a hardware problem.",
    "Why did the developer go broke? Because he used up all his cache.",
    "I told a UDP joke. You may or may not get it.",
    "There are 10 types of people: those who understand binary and those who don't.",
    "Debugging is like being the detective in a crime movie where you are also the murderer.",
    "A programmer's partner says: 'Go to the store, get a litre of milk, and if they have eggs, get a dozen.' The programmer returns with 12 litres of milk.",
    "Why do Python programmers prefer snake_case? Because they're always hissing with their editor.",
    "It's not a bug, it's an undocumented feature.",
    "Real programmers count from zero.",
    "Why was the JavaScript developer sad? Because he didn't know how to 'null' his feelings.",
    "I would tell you a joke about recursion, but first I'd have to tell you a joke about recursion.",
]


def setup() -> None:
    logger.info("Jokes plugin loaded.")


def handle(command) -> str:
    return random.choice(_JOKES)
