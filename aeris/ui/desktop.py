from __future__ import annotations

import math
import os
import shutil
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, scrolledtext, simpledialog

from ..assistant import AerisAssistant
from ..integrations.voice import VoiceService
from ..models import ActionRequest, PermissionLevel
from ..router import has_wake_word, strip_wake_word


class AerisAvatar(tk.Canvas):
    """Code-drawn animated AI character inspired by sci-fi HUD interfaces."""

    COLORS = {
        "idle": "#34e7ff",
        "listening": "#42ffb3",
        "thinking": "#9b8cff",
        "working": "#ffb347",
        "speaking": "#6ef7ff",
        "stopped": "#ff4f6d",
        "error": "#ff4f6d",
    }

    def __init__(self, parent: tk.Misc, background: str):
        super().__init__(
            parent,
            bg=background,
            highlightthickness=1,
            highlightbackground="#17384c",
            relief="flat",
            height=390,
        )
        self.state = "idle"
        self.angle = 0.0
        self.phase = 0.0
        self.bind("<Configure>", lambda _event: self._draw())
        self.after(40, self._animate)

    def set_state(self, value: str) -> None:
        self.state = value if value in self.COLORS else "idle"
        self._draw()

    def _animate(self) -> None:
        if not self.winfo_exists():
            return
        self.angle = (self.angle + (3.8 if self.state in {"listening", "working"} else 1.6)) % 360
        self.phase += 0.13
        self._draw()
        self.after(40, self._animate)

    def _draw(self) -> None:
        self.delete("hud")
        width = max(self.winfo_width(), 420)
        height = max(self.winfo_height(), 360)
        cx, cy = width / 2, height / 2 - 5
        color = self.COLORS[self.state]
        pulse = (math.sin(self.phase) + 1) / 2

        for x in range(0, width, 42):
            self.create_line(x, 0, x, height, fill="#0c2230", width=1, tags="hud")
        for y in range(0, height, 42):
            self.create_line(0, y, width, y, fill="#0c2230", width=1, tags="hud")

        for radius, width_px, speed, extent in (
            (150, 2, 1.0, 76),
            (132, 1, -1.4, 54),
            (112, 2, 1.8, 100),
            (92, 1, -2.2, 64),
        ):
            start = self.angle * speed
            for offset in range(0, 360, 90):
                self.create_arc(
                    cx - radius,
                    cy - radius,
                    cx + radius,
                    cy + radius,
                    start=start + offset,
                    extent=extent,
                    style="arc",
                    outline=color,
                    width=width_px,
                    tags="hud",
                )

        scan_radius = 166 + pulse * 8
        self.create_oval(
            cx - scan_radius,
            cy - scan_radius,
            cx + scan_radius,
            cy + scan_radius,
            outline="#15516b",
            width=1,
            tags="hud",
        )
        for offset in (-190, 190):
            self.create_line(
                cx + offset,
                cy - 90,
                cx + offset,
                cy + 90,
                fill="#1a5b75",
                width=2,
                tags="hud",
            )
            self.create_line(
                cx + offset,
                cy - 90,
                cx + (145 if offset < 0 else -145),
                cy - 90,
                fill="#1a5b75",
                width=2,
                tags="hud",
            )

        head = [
            cx - 38,
            cy - 90,
            cx - 52,
            cy - 42,
            cx - 34,
            cy - 5,
            cx,
            cy + 10,
            cx + 34,
            cy - 5,
            cx + 52,
            cy - 42,
            cx + 38,
            cy - 90,
            cx,
            cy - 110,
        ]
        self.create_polygon(head, outline=color, fill="#0a2230", width=3, tags="hud")
        self.create_line(cx - 30, cy - 54, cx - 8, cy - 49, fill=color, width=4, tags="hud")
        self.create_line(cx + 8, cy - 49, cx + 30, cy - 54, fill=color, width=4, tags="hud")
        self.create_line(cx, cy - 40, cx, cy - 14, fill="#25677d", width=2, tags="hud")
        self.create_arc(
            cx - 19,
            cy - 28,
            cx + 19,
            cy - 2,
            start=200,
            extent=140,
            style="arc",
            outline="#25677d",
            width=2,
            tags="hud",
        )

        torso = [
            cx - 18,
            cy + 12,
            cx - 78,
            cy + 48,
            cx - 94,
            cy + 112,
            cx - 42,
            cy + 128,
            cx,
            cy + 112,
            cx + 42,
            cy + 128,
            cx + 94,
            cy + 112,
            cx + 78,
            cy + 48,
            cx + 18,
            cy + 12,
        ]
        self.create_polygon(torso, outline="#27758d", fill="#081b28", width=2, tags="hud")
        core_radius = 22 + pulse * 4
        for extra, ring_color in ((16, "#123b4e"), (9, "#1d637a"), (0, color)):
            radius = core_radius + extra
            self.create_oval(
                cx - radius,
                cy + 67 - radius,
                cx + radius,
                cy + 67 + radius,
                outline=ring_color,
                width=3 if extra == 0 else 2,
                tags="hud",
            )
        self.create_oval(
            cx - 9,
            cy + 58,
            cx + 9,
            cy + 76,
            fill=color,
            outline="",
            tags="hud",
        )

        self.create_text(
            cx,
            height - 24,
            text=f"AERIS CORE // {self.state.upper()}",
            fill=color,
            font=("Consolas", 11, "bold"),
            tags="hud",
        )
        self.create_text(
            18,
            18,
            text="COGNITIVE INTERFACE  •  SECURE LINK",
            anchor="nw",
            fill="#608da1",
            font=("Consolas", 8),
            tags="hud",
        )


class AerisDesktopApp:
    BG = "#03080d"
    PANEL = "#07131d"
    PANEL_ALT = "#0b1e2a"
    BORDER = "#17384c"
    TEXT = "#eafaff"
    MUTED = "#6f98aa"
    ACCENT = "#34e7ff"
    SUCCESS = "#42ffb3"
    WARNING = "#ffb347"
    DANGER = "#ff4f6d"

    def __init__(self, assistant: AerisAssistant):
        self.assistant = assistant
        self.config = assistant.config
        self.voice = VoiceService(
            self.config.voice_model,
            self.config.voice_record_seconds,
            self.config.voice_device,
            self.config.voice_language,
        )
        self.root = tk.Tk()
        self.root.title("Aeris Cognitive Desktop")
        self.root.geometry("1280x800")
        self.root.minsize(1000, 680)
        self.root.configure(bg=self.BG)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        self._busy = False
        self._busy_lock = threading.Lock()
        self._voice_lock = threading.Lock()
        self._closing = threading.Event()
        self._hands_free_enabled = threading.Event()
        self._hands_free_thread: threading.Thread | None = None
        self._fullscreen = False
        self._topmost = False

        self._build()
        self._write("Aeris", "Cognitive desktop online. Say 'Aeris' before a hands-free command.")
        self._set_status("ONLINE", "idle")
        self._update_telemetry()
        self.root.after(350, self._start_services)

    def _panel(self, parent: tk.Misc, **kwargs: object) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=self.PANEL,
            highlightthickness=1,
            highlightbackground=self.BORDER,
            **kwargs,
        )

    def _section_title(self, parent: tk.Misc, text: str) -> tk.Label:
        return tk.Label(
            parent,
            text=text.upper(),
            bg=self.PANEL,
            fg=self.ACCENT,
            font=("Consolas", 9, "bold"),
            anchor="w",
        )

    def _button(
        self,
        parent: tk.Misc,
        text: str,
        command: object,
        background: str | None = None,
        foreground: str | None = None,
        fill: bool = False,
    ) -> tk.Button:
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=background or self.PANEL_ALT,
            fg=foreground or self.TEXT,
            activebackground=self.ACCENT,
            activeforeground="#021014",
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=8,
            font=("Segoe UI Semibold", 9),
            highlightthickness=1,
            highlightbackground=self.BORDER,
        )
        if fill:
            button.configure(anchor="w")
        return button

    def _build(self) -> None:
        header = tk.Frame(self.root, bg=self.BG, padx=18, pady=12)
        header.pack(fill="x")
        brand = tk.Frame(header, bg=self.BG)
        brand.pack(side="left")
        tk.Label(
            brand,
            text="AERIS",
            bg=self.BG,
            fg=self.ACCENT,
            font=("Segoe UI Semibold", 26),
        ).pack(side="left")
        tk.Label(
            brand,
            text="// COGNITIVE DESKTOP SYSTEM",
            bg=self.BG,
            fg=self.MUTED,
            font=("Consolas", 10),
        ).pack(side="left", padx=10, pady=(9, 0))

        header_controls = tk.Frame(header, bg=self.BG)
        header_controls.pack(side="right")
        self.live_var = tk.BooleanVar(value=not self.config.dry_run)
        self.hands_free_var = tk.BooleanVar(value=self.config.hands_free)
        self.live_button = tk.Checkbutton(
            header_controls,
            text="LIVE ACTIONS",
            variable=self.live_var,
            command=self._toggle_live,
            bg=self.BG,
            fg=self.WARNING,
            selectcolor=self.PANEL_ALT,
            activebackground=self.BG,
            activeforeground=self.WARNING,
            font=("Consolas", 9, "bold"),
        )
        self.live_button.pack(side="left", padx=8)
        self.hands_free_button = tk.Checkbutton(
            header_controls,
            text="WAKE LISTENING",
            variable=self.hands_free_var,
            command=self._toggle_hands_free,
            bg=self.BG,
            fg=self.SUCCESS,
            selectcolor=self.PANEL_ALT,
            activebackground=self.BG,
            activeforeground=self.SUCCESS,
            font=("Consolas", 9, "bold"),
        )
        self.hands_free_button.pack(side="left", padx=8)
        self._button(header_controls, "HUD", self._toggle_fullscreen).pack(side="left", padx=3)
        self._button(header_controls, "TOP", self._toggle_topmost).pack(side="left", padx=3)
        self._button(header_controls, "SETTINGS", self._open_settings).pack(side="left", padx=3)

        status_bar = tk.Frame(self.root, bg="#061019", padx=18, pady=7)
        status_bar.pack(fill="x", padx=18)
        self.status_dot = tk.Label(status_bar, text="●", bg="#061019", fg=self.ACCENT, font=("Segoe UI", 10))
        self.status_dot.pack(side="left")
        self.status_label = tk.Label(
            status_bar,
            text="INITIALIZING",
            bg="#061019",
            fg=self.TEXT,
            font=("Consolas", 9, "bold"),
        )
        self.status_label.pack(side="left", padx=8)
        self.mode_label = tk.Label(status_bar, bg="#061019", fg=self.MUTED, font=("Consolas", 9))
        self.mode_label.pack(side="right")

        body = tk.Frame(self.root, bg=self.BG, padx=18, pady=12)
        body.pack(fill="both", expand=True)

        left = self._panel(body, width=218, padx=13, pady=13)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self._section_title(left, "Command deck").pack(fill="x", pady=(0, 10))
        for label, command in (
            ("◉  Screen assist", "look at my screen and tell me the next useful step"),
            ("⌘  Open VS Code", "open vscode"),
            ("⇩  Downloads", "open downloads"),
            ("▣  PC health", "computer health"),
            ("↻  App updates", "list app updates"),
            ("◎  Screenshot", "take a screenshot"),
            ("▶  YouTube", "open youtube"),
        ):
            self._button(
                left,
                label,
                lambda value=command: self._start_command(value),
                fill=True,
            ).pack(fill="x", pady=3)
        self._button(
            left,
            "</>  Build code project",
            self._new_code_project,
            background="#123348",
            foreground=self.ACCENT,
            fill=True,
        ).pack(fill="x", pady=(12, 3))
        tk.Frame(left, bg=self.BORDER, height=1).pack(fill="x", pady=14)
        self._section_title(left, "Safety core").pack(fill="x", pady=(0, 8))
        self._button(left, "■  STOP AERIS", self._stop, self.DANGER, "#16030a", True).pack(
            fill="x", pady=3
        )
        self._button(left, "▷  Resume systems", self._resume, fill=True).pack(fill="x", pady=3)
        self._button(
            left,
            "?  Command guide",
            lambda: self._start_command("offline help"),
            fill=True,
        ).pack(fill="x", pady=3)

        right = self._panel(body, width=244, padx=13, pady=13)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        self._section_title(right, "System telemetry").pack(fill="x", pady=(0, 8))
        self.clock_label = self._metric(right, "LOCAL TIME", "--:--:--")
        self.cpu_label = self._metric(right, "CPU LOAD", "-- %")
        self.memory_label = self._metric(right, "MEMORY", "-- %")
        self.disk_label = self._metric(right, "DISK FREE", "-- GB")
        self.battery_label = self._metric(right, "BATTERY", "--")
        tk.Frame(right, bg=self.BORDER, height=1).pack(fill="x", pady=14)
        self._section_title(right, "Access monitor").pack(fill="x", pady=(0, 8))
        self.mic_access_label = self._access_row(right, "MICROPHONE", "STANDBY")
        self.screen_access_label = self._access_row(right, "SCREEN", "ASK FIRST")
        self.action_access_label = self._access_row(right, "PC ACTIONS", "SAFE MODE")
        self.ai_access_label = self._access_row(
            right,
            "AI CORE",
            "ONLINE" if self.config.ai_enabled and self.config.gemini_api_key else "NOT CONFIGURED",
        )
        tk.Frame(right, bg=self.BORDER, height=1).pack(fill="x", pady=14)
        self._section_title(right, "Protocol").pack(fill="x", pady=(0, 8))
        tk.Label(
            right,
            text=(
                "Say: “Aeris, open Chrome”\n\n"
                "Screen viewing, code writing,\nemail, installs, deletion and\npower actions remain permission-based."
            ),
            justify="left",
            anchor="nw",
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Segoe UI", 9),
        ).pack(fill="x")

        center = tk.Frame(body, bg=self.BG)
        center.pack(side="left", fill="both", expand=True, padx=12)
        self.avatar = AerisAvatar(center, self.PANEL)
        self.avatar.pack(fill="both", expand=True)

        activity_header = tk.Frame(center, bg=self.BG, pady=7)
        activity_header.pack(fill="x")
        tk.Label(
            activity_header,
            text="ACTIVITY STREAM",
            bg=self.BG,
            fg=self.ACCENT,
            font=("Consolas", 9, "bold"),
        ).pack(side="left")
        tk.Label(
            activity_header,
            text="SCREEN CAPTURE IS NEVER CONTINUOUS",
            bg=self.BG,
            fg=self.MUTED,
            font=("Consolas", 8),
        ).pack(side="right")
        self.output = scrolledtext.ScrolledText(
            center,
            height=9,
            wrap="word",
            bg=self.PANEL,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat",
            padx=13,
            pady=10,
            font=("Segoe UI", 9),
            state="disabled",
            highlightthickness=1,
            highlightbackground=self.BORDER,
        )
        self.output.pack(fill="x")
        self.output.tag_configure("user", foreground=self.WARNING, font=("Consolas", 9, "bold"))
        self.output.tag_configure("aeris", foreground=self.ACCENT, font=("Consolas", 9, "bold"))
        self.output.tag_configure("body", foreground=self.TEXT, spacing3=8)

        command_panel = tk.Frame(self.root, bg=self.BG, padx=18, pady=10)
        command_panel.pack(fill="x")
        tk.Label(
            command_panel,
            text=">",
            bg=self.BG,
            fg=self.ACCENT,
            font=("Consolas", 18, "bold"),
        ).pack(side="left", padx=(0, 8))
        self.command_entry = tk.Entry(
            command_panel,
            bg=self.PANEL_ALT,
            fg=self.TEXT,
            insertbackground=self.ACCENT,
            relief="flat",
            font=("Consolas", 11),
            highlightthickness=1,
            highlightbackground=self.BORDER,
            highlightcolor=self.ACCENT,
        )
        self.command_entry.pack(side="left", fill="x", expand=True, ipady=10)
        self.command_entry.bind("<Return>", lambda _event: self._send_text())
        self._button(command_panel, "EXECUTE", self._send_text, self.ACCENT, "#021014").pack(
            side="left", padx=(9, 0)
        )
        self._button(command_panel, "SPEAK", self._listen, self.SUCCESS, "#02140c").pack(
            side="left", padx=(7, 0)
        )
        self.command_entry.focus_set()
        self._refresh_mode_label()

    def _metric(self, parent: tk.Misc, name: str, value: str) -> tk.Label:
        frame = tk.Frame(parent, bg=self.PANEL_ALT, padx=9, pady=7)
        frame.pack(fill="x", pady=3)
        tk.Label(frame, text=name, bg=self.PANEL_ALT, fg=self.MUTED, font=("Consolas", 8)).pack(
            anchor="w"
        )
        label = tk.Label(
            frame,
            text=value,
            bg=self.PANEL_ALT,
            fg=self.ACCENT,
            font=("Consolas", 13, "bold"),
        )
        label.pack(anchor="w")
        return label

    def _access_row(self, parent: tk.Misc, name: str, value: str) -> tk.Label:
        frame = tk.Frame(parent, bg=self.PANEL, pady=4)
        frame.pack(fill="x")
        tk.Label(frame, text=name, bg=self.PANEL, fg=self.MUTED, font=("Consolas", 8)).pack(
            side="left"
        )
        label = tk.Label(frame, text=value, bg=self.PANEL, fg=self.SUCCESS, font=("Consolas", 8, "bold"))
        label.pack(side="right")
        return label

    def _update_telemetry(self) -> None:
        if self._closing.is_set():
            return
        self.clock_label.configure(text=datetime.now().strftime("%H:%M:%S"))
        try:
            import psutil

            self.cpu_label.configure(text=f"{psutil.cpu_percent(interval=None):.0f} %")
            self.memory_label.configure(text=f"{psutil.virtual_memory().percent:.0f} %")
            battery = psutil.sensors_battery()
            if battery:
                suffix = " AC" if battery.power_plugged else ""
                self.battery_label.configure(text=f"{battery.percent:.0f} %{suffix}")
            else:
                self.battery_label.configure(text="DESKTOP")
        except ImportError:
            self.cpu_label.configure(text="N/A")
            self.memory_label.configure(text="N/A")
            self.battery_label.configure(text="N/A")
        try:
            free_gb = shutil.disk_usage(Path.home()).free / (1024**3)
            self.disk_label.configure(text=f"{free_gb:.1f} GB")
        except OSError:
            self.disk_label.configure(text="N/A")
        self.root.after(1500, self._update_telemetry)

    def _start_services(self) -> None:
        if self.config.startup_greeting:
            threading.Thread(target=self._speak_startup, daemon=True).start()
        if self.hands_free_var.get():
            self.root.after(900, self._enable_hands_free)

    def _speak_startup(self) -> None:
        try:
            with self._voice_lock:
                self.voice.speak("Aeris online. All systems ready.")
        except Exception:
            return

    def _enable_hands_free(self) -> None:
        if self._closing.is_set() or not self.hands_free_var.get():
            return
        self._hands_free_enabled.set()
        self.mic_access_label.configure(text="WAKE LISTENING", fg=self.SUCCESS)
        if not self._hands_free_thread or not self._hands_free_thread.is_alive():
            self._hands_free_thread = threading.Thread(target=self._hands_free_loop, daemon=True)
            self._hands_free_thread.start()

    def _toggle_hands_free(self) -> None:
        if self.hands_free_var.get():
            self._write("Aeris", "Wake listening enabled. Say 'Aeris' before your command.")
            self._enable_hands_free()
        else:
            self._hands_free_enabled.clear()
            self.mic_access_label.configure(text="OFF", fg=self.MUTED)
            self._set_status("ONLINE", "idle")
            self._write("Aeris", "Wake listening disabled. The Speak button still works.")

    def _hands_free_loop(self) -> None:
        while not self._closing.is_set():
            if not self._hands_free_enabled.wait(timeout=0.4):
                continue
            with self._busy_lock:
                busy = self._busy
            if busy:
                self._closing.wait(0.25)
                continue
            try:
                self.root.after(0, lambda: self._set_status("WAKE LISTENING", "listening"))
                with self._voice_lock:
                    text = self.voice.listen_once()
            except Exception as exc:
                self._hands_free_enabled.clear()
                message = f"Wake listening stopped safely: {exc}"
                self.root.after(0, lambda value=message: self._hands_free_failed(value))
                return
            with self._busy_lock:
                became_busy = self._busy
            if became_busy or not self._hands_free_enabled.is_set():
                continue
            if text and has_wake_word(text, self.config.wake_word):
                command = strip_wake_word(text, self.config.wake_word)
                self.root.after(
                    0,
                    lambda shown=text, value=command: self._start_detected_command(shown, value),
                )
            else:
                self.root.after(0, lambda: self._set_status("ONLINE • WAKE STANDBY", "idle"))

    def _hands_free_failed(self, message: str) -> None:
        self.hands_free_var.set(False)
        self.mic_access_label.configure(text="UNAVAILABLE", fg=self.DANGER)
        self._write("Aeris", message)
        self._set_status("VOICE UNAVAILABLE", "error")

    def _claim_busy(self) -> bool:
        with self._busy_lock:
            if self._busy:
                return False
            self._busy = True
            return True

    def _release_busy(self) -> None:
        with self._busy_lock:
            self._busy = False

    def _start_detected_command(self, shown_text: str, command_text: str) -> None:
        if not self._claim_busy():
            return
        self._write("You", shown_text)
        self._set_status("THINKING", "thinking")
        threading.Thread(
            target=self._execute,
            args=(command_text or "help",),
            daemon=True,
        ).start()

    def _write(self, speaker: str, message: str) -> None:
        self.output.configure(state="normal")
        tag = "user" if speaker == "You" else "aeris"
        self.output.insert("end", f"{speaker.upper()}\n", tag)
        self.output.insert("end", message.strip() + "\n\n", "body")
        self.output.configure(state="disabled")
        self.output.see("end")

    def _set_status(self, value: str, state: str = "idle") -> None:
        colors = {
            "idle": self.ACCENT,
            "listening": self.SUCCESS,
            "thinking": "#9b8cff",
            "working": self.WARNING,
            "speaking": self.ACCENT,
            "stopped": self.DANGER,
            "error": self.DANGER,
        }
        self.status_label.configure(text=value)
        self.status_dot.configure(fg=colors.get(state, self.ACCENT))
        self.avatar.set_state(state)

    def _refresh_mode_label(self) -> None:
        mode = "LIVE • CONFIRMATIONS ACTIVE" if self.live_var.get() else "SAFE DRY RUN"
        self.mode_label.configure(text=mode)
        self.action_access_label.configure(
            text="LIVE + ASK" if self.live_var.get() else "SAFE MODE",
            fg=self.WARNING if self.live_var.get() else self.SUCCESS,
        )

    def _toggle_live(self) -> None:
        requested = self.live_var.get()
        if requested and not messagebox.askyesno(
            "Enable live actions",
            "Live mode performs real computer actions. Downloads, installs, screen access, files, email and power actions still ask separately. Enable it?",
            parent=self.root,
        ):
            self.live_var.set(False)
            requested = False
        self.assistant.registry.dry_run = not requested
        self._refresh_mode_label()
        self._write("Aeris", "Live actions enabled." if requested else "Safe dry-run mode enabled.")

    def _send_text(self) -> None:
        text = self.command_entry.get().strip()
        if not text:
            return
        self.command_entry.delete(0, "end")
        self._start_command(text)

    def _listen(self) -> None:
        if not self._claim_busy():
            self._write("Aeris", "One operation is already running.")
            return
        self._set_status(f"LISTENING • {self.config.voice_record_seconds} SECONDS", "listening")

        def worker() -> None:
            try:
                with self._voice_lock:
                    text = self.voice.listen_once()
                if not text:
                    self.root.after(0, lambda: self._finish_with_message("I did not hear speech."))
                    return
                self.root.after(0, lambda value=text: self._write("You", value))
                self._execute(text)
            except Exception as exc:
                message = f"Voice failed safely: {exc}"
                self.root.after(0, lambda value=message: self._finish_with_message(value, True))

        threading.Thread(target=worker, daemon=True).start()

    def _start_command(self, text: str) -> None:
        if not self._claim_busy():
            self._write("Aeris", "One operation is already running. Please wait.")
            return
        self._write("You", text)
        self._set_status("THINKING", "thinking")
        threading.Thread(target=self._execute, args=(text,), daemon=True).start()

    def _execute(self, text: str) -> None:
        try:
            self.root.after(0, lambda: self._set_status("EXECUTING", "working"))
            turn = self.assistant.handle(text, self._approval_callback)
            self.root.after(0, lambda value=turn.reply: self._present_response(value))
            try:
                spoken = turn.reply.splitlines()[0][:500]
                self.root.after(0, lambda: self._set_status("SPEAKING", "speaking"))
                with self._voice_lock:
                    self.voice.speak(spoken)
            except Exception:
                pass
            self.root.after(0, self._complete_command)
        except Exception as exc:
            message = f"Command failed safely: {exc}"
            self.root.after(0, lambda value=message: self._finish_with_message(value, True))

    def _finish_with_message(self, message: str, failed: bool = False) -> None:
        self._write("Aeris", message)
        self._complete_command(failed)

    def _present_response(self, message: str) -> None:
        self._write("Aeris", message)

    def _complete_command(self, failed: bool = False) -> None:
        self._release_busy()
        status = "ACTION FAILED" if failed else "ONLINE • WAKE STANDBY"
        self._set_status(status, "error" if failed else "idle")

    def _approval_callback(
        self,
        request: ActionRequest,
        level: PermissionLevel,
        preview: str,
    ) -> bool:
        completed = threading.Event()
        answer = {"approved": False}

        def ask() -> None:
            heading = "Session permission" if level is PermissionLevel.SESSION else "Confirm action"
            details = preview
            if request.tool == "email.send":
                details = (
                    f"To: {request.arguments.get('to')}\n"
                    f"Subject: {request.arguments.get('subject')}\n\n"
                    f"{request.arguments.get('body')}"
                )
            elif request.tool == "vision.inspect_screen":
                details = (
                    "Allow Aeris to capture the currently visible screens for this session?\n\n"
                    f"Question: {request.arguments.get('question')}\n\n"
                    "The screenshot is sent to the configured AI model, is not saved by Aeris, and hidden windows are not accessed."
                )
            elif request.tool == "coding.create_project":
                details = (
                    f"Create a new coding project in:\n{self.config.coding_workspace}\n\n"
                    f"Request: {request.arguments.get('prompt')}\n\n"
                    "Aeris validates text files, never overwrites a project, and does not execute generated code or install dependencies."
                )
            elif request.tool == "downloads.download":
                details = (
                    f"Download from:\n{request.arguments.get('url')}\n\n"
                    f"Save as: {request.arguments.get('filename') or 'website filename'}\n\n"
                    "The file will be saved, scanned when Defender is available, and not run."
                )
            elif request.tool in {
                "packages.install",
                "packages.update",
                "packages.uninstall",
                "packages.install_file",
            }:
                details = (
                    f"Action: {request.tool.replace('packages.', '').replace('_', ' ')}\n"
                    f"Target: {request.arguments.get('package') or request.arguments.get('path', '')}\n\n"
                    "Windows or UAC may show another confirmation."
                )
            elif request.tool == "packages.list_installed":
                details = "Allow Aeris to read the installed-application list for this session?"
            elif request.tool in {"system.shutdown", "system.restart"}:
                details = preview + "\n\nThis uses a 10-second cancellation window."
            answer["approved"] = messagebox.askyesno(heading, details, parent=self.root)
            if request.tool == "vision.inspect_screen":
                self.screen_access_label.configure(
                    text="SESSION GRANTED" if answer["approved"] else "DENIED",
                    fg=self.WARNING if answer["approved"] else self.DANGER,
                )
            completed.set()

        self.root.after(0, ask)
        completed.wait()
        return answer["approved"]

    def _new_code_project(self) -> None:
        request = simpledialog.askstring(
            "Build a code project",
            "What should Aeris build?\nExample: a Python expense tracker with a Tkinter interface",
            parent=self.root,
        )
        if request and request.strip():
            self._start_command(f"write code for {request.strip()}")

    def _stop(self) -> None:
        self.assistant.permissions.stop()
        self._hands_free_enabled.clear()
        self.hands_free_var.set(False)
        self.mic_access_label.configure(text="OFF", fg=self.MUTED)
        self._write("Aeris", "Emergency stop active. PC tools, microphone standby and AI actions are paused.")
        self._set_status("STOPPED", "stopped")

    def _resume(self) -> None:
        self.assistant.permissions.resume()
        self._write("Aeris", "Systems resumed. Enable wake listening when you want hands-free control.")
        self._set_status("ONLINE", "idle")

    def _toggle_fullscreen(self) -> None:
        self._fullscreen = not self._fullscreen
        self.root.attributes("-fullscreen", self._fullscreen)

    def _toggle_topmost(self) -> None:
        self._topmost = not self._topmost
        self.root.attributes("-topmost", self._topmost)
        self._write("Aeris", "HUD pinned above other windows." if self._topmost else "HUD pin disabled.")

    def _open_settings(self) -> None:
        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            example = Path.cwd() / ".env.example"
            if example.exists():
                env_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        if os.name == "nt":
            os.startfile(str(env_path))  # type: ignore[attr-defined]
        else:
            messagebox.showinfo("Settings", str(env_path), parent=self.root)

    def _close(self) -> None:
        self._closing.set()
        self._hands_free_enabled.clear()
        self.assistant.permissions.stop()
        self.assistant.permissions.clear_session()
        self.root.destroy()

    def run(self) -> int:
        self.root.mainloop()
        return 0


def launch_desktop(assistant: AerisAssistant) -> int:
    return AerisDesktopApp(assistant).run()
