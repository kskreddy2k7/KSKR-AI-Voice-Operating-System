"""
Time & Date Plugin
------------------
Answers questions about the current time and date.

Intent keywords: ``time``, ``date``, ``day``
"""

from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

PLUGIN_NAME = "time_date"
PLUGIN_INTENTS = ["time", "date", "day", "what time", "what day"]


def setup() -> None:
    logger.info("Time/Date plugin loaded.")


def handle(command) -> str:
    raw = command.raw_text.lower()
    now = datetime.now()
    if "time" in raw:
        return f"The current time is {now.strftime('%I:%M %p')}."
    if "date" in raw:
        return f"Today's date is {now.strftime('%A, %B %d, %Y')}."
    if "day" in raw:
        return f"Today is {now.strftime('%A')}."
    return f"It is {now.strftime('%A, %B %d, %Y')} and the time is {now.strftime('%I:%M %p')}."
