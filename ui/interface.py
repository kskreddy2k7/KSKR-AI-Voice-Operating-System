"""
KSKR Voice OS – Graphical Interface
-------------------------------------
Built with Tkinter (bundled with Python, no extra install required).

Layout
~~~~~~
┌─────────────────────────────────────────────────────────┐
│  KSKR VOICE OS                           ● LISTENING     │
├─────────────────────────────────────────────────────────┤
│  [Chat / transcript area – scrollable]                   │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  Recognised:  <live text>                                │
│  Response:    <live response>                            │
├─────────────────────────────────────────────────────────┤
│  [Language ▾] [🎤 Start]  [⏹ Stop]  [Enrol Voice]       │
└─────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import font as tkfont
from tkinter import scrolledtext, ttk
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "settings.json"
)

# ---------------------------------------------------------------------------
# Theme colours
# ---------------------------------------------------------------------------
_DARK = {
    "bg":        "#1a1a2e",
    "panel":     "#16213e",
    "accent":    "#0f3460",
    "highlight": "#e94560",
    "text":      "#eaeaea",
    "text_dim":  "#888888",
    "user_msg":  "#4ecca3",
    "bot_msg":   "#e2e2e2",
    "success":   "#4ecca3",
    "warning":   "#f0a500",
    "error":     "#e94560",
    "button_bg": "#0f3460",
    "button_fg": "#eaeaea",
}


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


class KSKRInterface:
    """Tkinter-based GUI for KSKR Voice OS.

    Parameters
    ----------
    on_start_listening:
        Called when the user clicks 'Start'.
    on_stop_listening:
        Called when the user clicks 'Stop'.
    on_language_change:
        Called with the selected language name string.
    on_enrol_voice:
        Called when the user clicks 'Enrol Voice'.
    on_text_command:
        Called when the user submits a typed command.
    """

    def __init__(
        self,
        on_start_listening: Optional[Callable] = None,
        on_stop_listening: Optional[Callable] = None,
        on_language_change: Optional[Callable[[str], None]] = None,
        on_enrol_voice: Optional[Callable] = None,
        on_text_command: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._on_start = on_start_listening or (lambda: None)
        self._on_stop = on_stop_listening or (lambda: None)
        self._on_lang = on_language_change or (lambda l: None)
        self._on_enrol = on_enrol_voice or (lambda: None)
        self._on_text_cmd = on_text_command or (lambda t: None)

        cfg = _load_config()
        ui_cfg = cfg.get("ui", {})
        speech_cfg = cfg.get("speech", {})

        self._languages = list(speech_cfg.get("supported_languages", {
            "English": "en-IN", "Hindi": "hi-IN", "Telugu": "te-IN",
            "Tamil": "ta-IN", "Kannada": "kn-IN",
        }).keys())

        self._title = ui_cfg.get("title", "KSKR Voice OS")
        self._width = ui_cfg.get("width", 900)
        self._height = ui_cfg.get("height", 650)
        self._c = _DARK
        self._update_queue: queue.Queue = queue.Queue()

        self._root: Optional[tk.Tk] = None
        self._status_var: Optional[tk.StringVar] = None
        self._status_color_var: Optional[tk.StringVar] = None
        self._recognised_var: Optional[tk.StringVar] = None
        self._response_var: Optional[tk.StringVar] = None
        self._chat_area: Optional[scrolledtext.ScrolledText] = None
        self._listening = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Build and start the Tk main loop (blocking)."""
        self._root = tk.Tk()
        self._build_ui()
        self._root.after(100, self._process_queue)
        self._root.mainloop()

    def update_status(self, status: str, color: str = "text") -> None:
        """Thread-safe status update."""
        self._update_queue.put(("status", status, color))

    def show_recognised(self, text: str) -> None:
        """Thread-safe update of the recognised-speech label."""
        self._update_queue.put(("recognised", text, ""))

    def show_response(self, text: str) -> None:
        """Thread-safe update of the response label and chat area."""
        self._update_queue.put(("response", text, ""))

    def log_chat(self, speaker: str, text: str) -> None:
        """Append a chat entry (thread-safe)."""
        self._update_queue.put(("chat", speaker, text))

    def show_reminder_popup(self, task: str) -> None:
        """Show a reminder notification popup (thread-safe)."""
        self._update_queue.put(("popup", task, ""))

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = self._root
        assert root is not None
        root.title(self._title)
        root.geometry(f"{self._width}x{self._height}")
        root.configure(bg=self._c["bg"])
        root.resizable(True, True)

        # Fonts
        bold_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        normal_font = tkfont.Font(family="Segoe UI", size=10)
        small_font = tkfont.Font(family="Segoe UI", size=9)
        title_font = tkfont.Font(family="Segoe UI", size=14, weight="bold")

        # ------ HEADER ------
        header = tk.Frame(root, bg=self._c["accent"], height=50)
        header.pack(fill=tk.X, side=tk.TOP)

        tk.Label(
            header, text="⚙  KSKR VOICE OS",
            font=title_font, bg=self._c["accent"], fg=self._c["text"],
        ).pack(side=tk.LEFT, padx=15, pady=10)

        self._status_var = tk.StringVar(value="● IDLE")
        status_lbl = tk.Label(
            header, textvariable=self._status_var,
            font=bold_font, bg=self._c["accent"], fg=self._c["text_dim"],
        )
        status_lbl.pack(side=tk.RIGHT, padx=15, pady=10)
        self._status_label = status_lbl

        # ------ CHAT AREA ------
        chat_frame = tk.Frame(root, bg=self._c["panel"])
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        self._chat_area = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=normal_font,
            bg=self._c["panel"],
            fg=self._c["text"],
            insertbackground=self._c["text"],
            selectbackground=self._c["accent"],
            relief=tk.FLAT,
            padx=10, pady=10,
            state=tk.DISABLED,
        )
        self._chat_area.pack(fill=tk.BOTH, expand=True)
        # Tag for user / bot / system messages
        self._chat_area.tag_config("user",   foreground=self._c["user_msg"], font=bold_font)
        self._chat_area.tag_config("bot",    foreground=self._c["bot_msg"])
        self._chat_area.tag_config("system", foreground=self._c["text_dim"], font=small_font)
        self._chat_area.tag_config("time",   foreground=self._c["text_dim"], font=small_font)

        # ------ STATUS STRIP ------
        status_strip = tk.Frame(root, bg=self._c["bg"], pady=4)
        status_strip.pack(fill=tk.X, padx=10)

        self._recognised_var = tk.StringVar(value="Recognised: —")
        tk.Label(
            status_strip, textvariable=self._recognised_var,
            font=small_font, bg=self._c["bg"], fg=self._c["text_dim"],
            anchor=tk.W,
        ).pack(side=tk.LEFT)

        self._response_var = tk.StringVar(value="")
        tk.Label(
            status_strip, textvariable=self._response_var,
            font=small_font, bg=self._c["bg"], fg=self._c["success"],
            anchor=tk.E,
        ).pack(side=tk.RIGHT)

        # ------ INPUT ROW ------
        input_frame = tk.Frame(root, bg=self._c["bg"], pady=6)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

        self._text_entry = tk.Entry(
            input_frame, font=normal_font,
            bg=self._c["accent"], fg=self._c["text"],
            insertbackground=self._c["text"],
            relief=tk.FLAT,
        )
        self._text_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), ipady=4)
        self._text_entry.bind("<Return>", self._on_entry_submit)

        tk.Button(
            input_frame, text="Send",
            font=normal_font, bg=self._c["highlight"], fg=self._c["text"],
            relief=tk.FLAT, padx=10, cursor="hand2",
            command=self._on_entry_submit,
        ).pack(side=tk.LEFT, padx=(0, 6))

        # ------ CONTROL ROW ------
        ctrl_frame = tk.Frame(root, bg=self._c["bg"], pady=4)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Language selector
        self._lang_var = tk.StringVar(value=self._languages[0])
        lang_cb = ttk.Combobox(
            ctrl_frame, textvariable=self._lang_var,
            values=self._languages, state="readonly", width=12,
        )
        lang_cb.pack(side=tk.LEFT, padx=(0, 8))
        lang_cb.bind("<<ComboboxSelected>>", self._on_lang_change)

        def _btn(parent, text, cmd, color=None):
            return tk.Button(
                parent, text=text, font=normal_font,
                bg=color or self._c["button_bg"],
                fg=self._c["button_fg"],
                relief=tk.FLAT, padx=12, pady=4, cursor="hand2",
                command=cmd,
            )

        self._start_btn = _btn(ctrl_frame, "🎤  Start", self._on_start_click, self._c["success"])
        self._start_btn.pack(side=tk.LEFT, padx=4)

        self._stop_btn = _btn(ctrl_frame, "⏹  Stop", self._on_stop_click, self._c["error"])
        self._stop_btn.pack(side=tk.LEFT, padx=4)
        self._stop_btn.configure(state=tk.DISABLED)

        _btn(ctrl_frame, "🔐  Enrol Voice", self._on_enrol_click).pack(side=tk.LEFT, padx=4)
        _btn(ctrl_frame, "🗑  Clear Chat", self._clear_chat).pack(side=tk.RIGHT, padx=4)

        self._append_system("KSKR Voice OS started. Say a wake word or type a command below.")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_start_click(self) -> None:
        self._start_btn.configure(state=tk.DISABLED)
        self._stop_btn.configure(state=tk.NORMAL)
        self._listening = True
        self.update_status("● LISTENING", "success")
        threading.Thread(target=self._on_start, daemon=True).start()

    def _on_stop_click(self) -> None:
        self._start_btn.configure(state=tk.NORMAL)
        self._stop_btn.configure(state=tk.DISABLED)
        self._listening = False
        self.update_status("● IDLE", "text_dim")
        threading.Thread(target=self._on_stop, daemon=True).start()

    def _on_lang_change(self, event=None) -> None:
        lang = self._lang_var.get()
        self._append_system(f"Language switched to: {lang}")
        threading.Thread(target=lambda: self._on_lang(lang), daemon=True).start()

    def _on_enrol_click(self) -> None:
        self._append_system("Starting voice enrolment…")
        threading.Thread(target=self._on_enrol, daemon=True).start()

    def _on_entry_submit(self, event=None) -> None:
        text = self._text_entry.get().strip()
        if not text:
            return
        self._text_entry.delete(0, tk.END)
        self.log_chat("You", text)
        threading.Thread(target=lambda: self._on_text_cmd(text), daemon=True).start()

    def _clear_chat(self) -> None:
        assert self._chat_area is not None
        self._chat_area.configure(state=tk.NORMAL)
        self._chat_area.delete("1.0", tk.END)
        self._chat_area.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Thread-safe queue processor
    # ------------------------------------------------------------------

    def _process_queue(self) -> None:
        try:
            while True:
                item = self._update_queue.get_nowait()
                kind = item[0]
                if kind == "status":
                    _, msg, color_key = item
                    self._status_var.set(msg)  # type: ignore[union-attr]
                    fg = self._c.get(color_key, self._c["text"])
                    self._status_label.configure(fg=fg)
                elif kind == "recognised":
                    _, text, _ = item
                    self._recognised_var.set(f"Recognised: {text}")  # type: ignore[union-attr]
                elif kind == "response":
                    _, text, _ = item
                    short = text[:80] + ("…" if len(text) > 80 else "")
                    self._response_var.set(f"↳ {short}")  # type: ignore[union-attr]
                    self.log_chat("KSKR", text)
                elif kind == "chat":
                    _, speaker, text = item
                    self._append_chat(speaker, text)
                elif kind == "popup":
                    _, task, _ = item
                    self._show_popup(f"⏰ Reminder: {task}")
        except queue.Empty:
            pass
        if self._root:
            self._root.after(100, self._process_queue)

    def _append_chat(self, speaker: str, text: str) -> None:
        assert self._chat_area is not None
        self._chat_area.configure(state=tk.NORMAL)
        ts = datetime.now().strftime("%H:%M")
        tag = "user" if speaker != "KSKR" else "bot"
        self._chat_area.insert(tk.END, f"\n[{ts}] ", "time")
        self._chat_area.insert(tk.END, f"{speaker}: ", tag)
        self._chat_area.insert(tk.END, f"{text}\n")
        self._chat_area.see(tk.END)
        self._chat_area.configure(state=tk.DISABLED)

    def _append_system(self, text: str) -> None:
        assert self._chat_area is not None
        self._chat_area.configure(state=tk.NORMAL)
        self._chat_area.insert(tk.END, f"\n[SYSTEM] {text}\n", "system")
        self._chat_area.see(tk.END)
        self._chat_area.configure(state=tk.DISABLED)

    def _show_popup(self, message: str) -> None:
        if self._root is None:
            return
        popup = tk.Toplevel(self._root)
        popup.title("Reminder")
        popup.configure(bg=self._c["accent"])
        popup.geometry("350x120")
        popup.attributes("-topmost", True)
        tk.Label(
            popup, text=message,
            font=tkfont.Font(family="Segoe UI", size=11),
            bg=self._c["accent"], fg=self._c["text"],
            wraplength=320,
        ).pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        tk.Button(
            popup, text="OK", command=popup.destroy,
            bg=self._c["highlight"], fg=self._c["text"], relief=tk.FLAT, padx=20,
        ).pack(pady=(0, 15))
        popup.after(10000, popup.destroy)  # auto-close after 10 s
