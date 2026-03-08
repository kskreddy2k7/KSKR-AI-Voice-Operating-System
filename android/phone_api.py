"""
Android Phone API
-----------------
Exposes KSKR Voice OS functionality over a lightweight Flask REST API so that
an Android device on the same Wi-Fi network can send commands and receive
responses.

Endpoints
~~~~~~~~~
POST /command
    Body: {"text": "open chrome"}
    Returns: {"response": "Opening Chrome.", "intent": "open_app"}

GET /status
    Returns: {"status": "running", "version": "1.0"}

POST /send_message
    Body: {"contact": "Mom", "message": "On my way"}
    Returns: {"status": "queued"}

GET /reminders
    Returns: {"reminders": [...]}

The server is started in a daemon thread so it does not block the main
application.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from functools import wraps
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "settings.json"
)

__version__ = "1.0.0"


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh).get("android", {})
    except Exception as exc:
        logger.warning("PhoneAPI: could not load config – %s", exc)
        return {}


class PhoneAPI:
    """Lightweight REST API gateway for Android integration.

    Parameters
    ----------
    command_handler:
        Callable that accepts a text command string and returns a response
        string.  This is wired to the main assistant's command pipeline.
    reminder_manager:
        Optional :class:`~reminders.reminder_manager.ReminderManager` so
        reminders can be fetched remotely.
    host / port:
        Network bind address.  Defaults come from ``config/settings.json``.
    secret_key:
        Simple API-key authentication.  Clients must send the header
        ``X-API-Key: <secret_key>``.  Set to empty string to disable.
    """

    def __init__(
        self,
        command_handler: Optional[Callable[[str], str]] = None,
        reminder_manager=None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        secret_key: Optional[str] = None,
    ) -> None:
        cfg = _load_config()
        self._command_handler = command_handler or (lambda t: f"Echo: {t}")
        self._reminder_manager = reminder_manager
        self._host = host or cfg.get("host", "0.0.0.0")
        self._port = port or cfg.get("port", 5050)
        self._secret = secret_key if secret_key is not None else cfg.get("secret_key", "")
        self._app = self._build_app()
        self._server_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the Flask server in a daemon thread."""
        if self._server_thread and self._server_thread.is_alive():
            return
        self._server_thread = threading.Thread(
            target=self._run_server, daemon=True, name="PhoneAPIServer"
        )
        self._server_thread.start()
        logger.info("PhoneAPI: server started on %s:%d", self._host, self._port)

    # ------------------------------------------------------------------
    # Flask app builder
    # ------------------------------------------------------------------

    def _build_app(self):
        try:
            from flask import Flask, request, jsonify  # type: ignore
        except ImportError:
            logger.warning(
                "PhoneAPI: Flask is not installed. "
                "Android integration is disabled. Run: pip install flask"
            )
            return None

        app = Flask("KSKR-PhoneAPI")

        def _auth_required(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                if self._secret:
                    key = request.headers.get("X-API-Key", "")
                    if key != self._secret:
                        return jsonify({"error": "Unauthorised"}), 401
                return fn(*args, **kwargs)
            return wrapper

        @app.route("/status", methods=["GET"])
        def status():
            return jsonify({"status": "running", "version": __version__})

        @app.route("/command", methods=["POST"])
        @_auth_required
        def command():
            data = request.get_json(silent=True) or {}
            text = data.get("text", "").strip()
            if not text:
                return jsonify({"error": "No text provided"}), 400
            try:
                response = self._command_handler(text)
                return jsonify({"response": response})
            except Exception as exc:
                logger.error("PhoneAPI /command error: %s", exc)
                return jsonify({"error": str(exc)}), 500

        @app.route("/reminders", methods=["GET"])
        @_auth_required
        def reminders():
            if self._reminder_manager is None:
                return jsonify({"reminders": []})
            items = self._reminder_manager.list_pending()
            return jsonify({"reminders": items})

        @app.route("/send_message", methods=["POST"])
        @_auth_required
        def send_message():
            data = request.get_json(silent=True) or {}
            contact = data.get("contact", "")
            message = data.get("message", "")
            if not contact or not message:
                return jsonify({"error": "contact and message are required"}), 400
            # Placeholder – real implementation would use Bluetooth/ADB/Tasker
            logger.info("PhoneAPI: send_message → %s: %s", contact, message)
            return jsonify({"status": "queued", "contact": contact})

        return app

    def _run_server(self) -> None:
        if self._app is None:
            return
        try:
            self._app.run(host=self._host, port=self._port, debug=False, use_reloader=False)
        except Exception as exc:
            logger.error("PhoneAPI: server crashed – %s", exc)
