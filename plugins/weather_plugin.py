"""
Weather Plugin
--------------
Fetches current weather information using the Open-Meteo API (free, no key
required).  Geocoding is performed with the Open-Meteo Geocoding API.

Intent keywords: ``weather``, ``forecast``
"""

from __future__ import annotations

import logging
import urllib.parse
import urllib.request
import json

logger = logging.getLogger(__name__)

PLUGIN_NAME = "weather"
PLUGIN_INTENTS = ["weather", "forecast"]

_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search?name={}&count=1&language=en&format=json"
_WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}"
    "&current_weather=true"
    "&hourly=temperature_2m,relativehumidity_2m,weathercode"
)

_WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


def setup() -> None:
    logger.info("Weather plugin loaded.")


def handle(command) -> str:
    """Handle weather / forecast commands."""
    raw = command.raw_text.lower()

    # Extract city name from the utterance
    city = _extract_city(raw)
    if not city:
        return "Which city would you like the weather for?"

    try:
        lat, lon, resolved = _geocode(city)
    except Exception as exc:
        return f"Sorry, I couldn't find the location '{city}': {exc}"

    try:
        weather = _fetch_weather(lat, lon)
    except Exception as exc:
        return f"Sorry, I couldn't fetch the weather: {exc}"

    temp = weather.get("temperature", "?")
    wind = weather.get("windspeed", "?")
    code = weather.get("weathercode", 0)
    desc = _WMO_CODES.get(code, "Unknown conditions")
    return (
        f"Weather in {resolved}: {desc}. "
        f"Temperature: {temp}°C, Wind speed: {wind} km/h."
    )


def _extract_city(text: str) -> str:
    for kw in ["weather in", "weather for", "forecast for", "forecast in"]:
        idx = text.find(kw)
        if idx != -1:
            return text[idx + len(kw):].strip().rstrip("?.")
    # Fallback: strip known filler words
    for filler in ["what is the weather", "what's the weather", "weather", "forecast"]:
        text = text.replace(filler, "").strip()
    return text.strip().rstrip("?.") or ""


def _geocode(city: str) -> tuple[float, float, str]:
    url = _GEO_URL.format(urllib.parse.quote(city))
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read())
    results = data.get("results")
    if not results:
        raise ValueError("City not found")
    r = results[0]
    return r["latitude"], r["longitude"], r.get("name", city)


def _fetch_weather(lat: float, lon: float) -> dict:
    url = _WEATHER_URL.format(lat=lat, lon=lon)
    with urllib.request.urlopen(url, timeout=5) as resp:
        data = json.loads(resp.read())
    return data.get("current_weather", {})
