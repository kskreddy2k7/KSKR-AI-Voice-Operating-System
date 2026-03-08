"""
Windows System Controller
-------------------------
Executes OS-level actions on Windows (with graceful no-ops on Linux/macOS for
development/testing purposes).

Actions
~~~~~~~
- open_app      – locate and open installed applications or executables
- open_folder   – open a named or explicit path in Explorer
- create_folder – create a new folder on the Desktop or given path
- search_web    – open the default browser with a search query
- play_media    – control media playback (play/pause, volume …)
- system        – shutdown, restart, sleep, lock, screenshot
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_IS_WINDOWS = platform.system() == "Windows"

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "settings.json"
)

# Well-known application name → typical executable/path on Windows
_APP_MAP: dict[str, str] = {
    "chrome":            "chrome",
    "google chrome":     "chrome",
    "firefox":           "firefox",
    "edge":              "msedge",
    "brave":             "brave",
    "notepad":           "notepad",
    "calculator":        "calc",
    "paint":             "mspaint",
    "word":              "winword",
    "excel":             "excel",
    "powerpoint":        "powerpnt",
    "visual studio code":"code",
    "vs code":           "code",
    "vscode":            "code",
    "pycharm":           "pycharm64",
    "terminal":          "wt",           # Windows Terminal
    "cmd":               "cmd",
    "powershell":        "powershell",
    "task manager":      "taskmgr",
    "file explorer":     "explorer",
    "explorer":          "explorer",
    "spotify":           "spotify",
    "vlc":               "vlc",
    "discord":           "discord",
    "slack":             "slack",
    "zoom":              "zoom",
    "teams":             "teams",
    "outlook":           "outlook",
    "whatsapp":          "whatsapp",
}

# Common special-folder names → environment variables / path fragments
_FOLDER_MAP: dict[str, str] = {
    "desktop":     os.path.join(os.path.expanduser("~"), "Desktop"),
    "documents":   os.path.join(os.path.expanduser("~"), "Documents"),
    "downloads":   os.path.join(os.path.expanduser("~"), "Downloads"),
    "pictures":    os.path.join(os.path.expanduser("~"), "Pictures"),
    "music":       os.path.join(os.path.expanduser("~"), "Music"),
    "videos":      os.path.join(os.path.expanduser("~"), "Videos"),
    "home":        os.path.expanduser("~"),
    "temp":        os.environ.get("TEMP", "/tmp"),
    "appdata":     os.environ.get("APPDATA", ""),
    "program files": os.environ.get("PROGRAMFILES", "C:\\Program Files"),
}


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh).get("automation", {})
    except Exception as exc:
        logger.warning("WindowsController: could not load config – %s", exc)
        return {}


def _open_path(path: str) -> None:
    """Open *path* with the system default handler."""
    if _IS_WINDOWS:
        os.startfile(path)  # type: ignore[attr-defined]
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


class WindowsController:
    """High-level interface for OS automation actions."""

    def __init__(self) -> None:
        self._cfg = _load_config()
        self._search_engine: str = self._cfg.get(
            "search_engine", "https://www.google.com/search?q="
        )

    # ------------------------------------------------------------------
    # Open application
    # ------------------------------------------------------------------

    def open_app(self, app_name: str) -> str:
        """Open an application by name."""
        name_lower = app_name.lower().strip()
        executable = _APP_MAP.get(name_lower, name_lower)

        # If a full path is given, use it directly
        if os.path.isabs(executable) and os.path.exists(executable):
            try:
                subprocess.Popen([executable])
                return f"Opening {app_name}."
            except Exception as exc:
                return f"Could not open {app_name}: {exc}"

        # Try to find the executable on PATH
        found = shutil.which(executable)
        if found:
            try:
                subprocess.Popen([found])
                return f"Opening {app_name}."
            except Exception as exc:
                return f"Could not launch {app_name}: {exc}"

        # Windows-specific: try START command which resolves registered apps
        if _IS_WINDOWS:
            try:
                # Use subprocess.Popen with the Windows START verb via explorer
                # to avoid shell=True injection risks
                subprocess.Popen(["cmd", "/c", "start", "", executable])
                return f"Opening {app_name}."
            except Exception as exc:
                return f"Could not start {app_name}: {exc}"

        return f"Application '{app_name}' not found. Please install it or add it to PATH."

    # ------------------------------------------------------------------
    # Open folder
    # ------------------------------------------------------------------

    def open_folder(self, folder_name: str) -> str:
        """Open a named folder or absolute path in the file manager."""
        name_lower = folder_name.lower().strip()
        path = _FOLDER_MAP.get(name_lower)

        if path is None:
            # Check if it's an absolute path
            if os.path.isabs(folder_name) and os.path.isdir(folder_name):
                path = folder_name
            else:
                # Try Desktop as default location
                desktop = _FOLDER_MAP["desktop"]
                candidate = os.path.join(desktop, folder_name)
                if os.path.isdir(candidate):
                    path = candidate
                else:
                    return (
                        f"Folder '{folder_name}' not found. "
                        "Please specify the full path or a known folder name."
                    )

        try:
            _open_path(path)
            return f"Opening folder: {path}"
        except Exception as exc:
            return f"Could not open folder: {exc}"

    # ------------------------------------------------------------------
    # Create folder
    # ------------------------------------------------------------------

    def create_folder(self, folder_name: str, parent: Optional[str] = None) -> str:
        """Create a new folder.  Defaults to the Desktop."""
        if parent is None:
            parent = _FOLDER_MAP["desktop"]
        new_dir = Path(parent) / folder_name
        try:
            new_dir.mkdir(parents=True, exist_ok=False)
            return f"Folder '{folder_name}' created at {new_dir}."
        except FileExistsError:
            return f"Folder '{folder_name}' already exists at {new_dir}."
        except Exception as exc:
            return f"Could not create folder: {exc}"

    # ------------------------------------------------------------------
    # Web search
    # ------------------------------------------------------------------

    def search_web(self, query: str) -> str:
        """Open the default browser with a Google search for *query*."""
        import urllib.parse
        url = self._search_engine + urllib.parse.quote_plus(query)
        try:
            webbrowser.open(url)
            return f"Searching the web for: {query}"
        except Exception as exc:
            return f"Could not open browser: {exc}"

    # ------------------------------------------------------------------
    # Media control
    # ------------------------------------------------------------------

    def control_media(self, action: str, target: str = "") -> str:
        """Control media playback via keyboard simulation."""
        try:
            import pyautogui  # type: ignore
        except ImportError:
            return "Media control requires pyautogui. Install it with: pip install pyautogui"

        action_map = {
            "play":        lambda: pyautogui.press("playpause"),
            "pause":       lambda: pyautogui.press("playpause"),
            "next":        lambda: pyautogui.press("nexttrack"),
            "prev":        lambda: pyautogui.press("prevtrack"),
            "volume_up":   lambda: pyautogui.press("volumeup"),
            "volume_down": lambda: pyautogui.press("volumedown"),
            "mute":        lambda: pyautogui.press("volumemute"),
        }
        fn = action_map.get(action)
        if fn:
            fn()
            return f"Media: {action}."
        return f"Unknown media action: {action}"

    # ------------------------------------------------------------------
    # System commands
    # ------------------------------------------------------------------

    def system_command(self, action: str, target: str = "") -> str:
        """Execute a system-level command."""
        action = action.lower()

        if action == "shutdown":
            if _IS_WINDOWS:
                subprocess.run(["shutdown", "/s", "/t", "10"], check=False)
                return "Shutting down in 10 seconds. Say 'cancel shutdown' to abort."
            return "Shutdown is only supported on Windows."

        if action == "restart":
            if _IS_WINDOWS:
                subprocess.run(["shutdown", "/r", "/t", "10"], check=False)
                return "Restarting in 10 seconds."
            return "Restart is only supported on Windows."

        if action == "sleep":
            if _IS_WINDOWS:
                subprocess.run(
                    ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                    check=False,
                )
                return "Going to sleep."
            return "Sleep is only supported on Windows."

        if action == "lock":
            if _IS_WINDOWS:
                subprocess.run(
                    ["rundll32.exe", "user32.dll,LockWorkStation"],
                    check=False,
                )
                return "Screen locked."
            return "Lock is only supported on Windows."

        if action == "screenshot":
            try:
                import pyautogui  # type: ignore
                from datetime import datetime

                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = os.path.join(_FOLDER_MAP["desktop"], f"screenshot_{ts}.png")
                pyautogui.screenshot(path)
                return f"Screenshot saved to {path}."
            except ImportError:
                return "Screenshots require pyautogui. Install it with: pip install pyautogui"
            except Exception as exc:
                return f"Screenshot failed: {exc}"

        if action == "close_app" and target:
            if _IS_WINDOWS:
                subprocess.run(
                    ["taskkill", "/F", "/IM", f"{target}.exe", "/T"],
                    check=False,
                )
                return f"Closed {target}."
            return f"close_app is only supported on Windows. Target: {target}"

        return f"Unknown system action: {action}"
