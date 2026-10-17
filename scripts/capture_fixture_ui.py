"""Capture the real Qt UI with temporary simulation data; no microphone/network."""
import argparse
import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from aeris.assistant import AerisAssistant
from aeris.config import AerisConfig
from aeris.core.tts_worker import global_tts
from aeris.ui.desktop import AerisMainWindow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--view", choices=("dashboard", "reminders", "companion", "tasks", "permissions"), default="dashboard")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args()
    if not 640 <= args.width <= 3840 or not 480 <= args.height <= 2160:
        parser.error("Choose a supported fixture size")
    destination = args.destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    if os.name == "nt":
        font_dir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for name in ("segoeui.ttf", "segoeuib.ttf", "arial.ttf"):
            if (font_dir / name).is_file():
                QFontDatabase.addApplicationFont(str(font_dir / name))
    global_tts.muted = True
    with tempfile.TemporaryDirectory(prefix="aeris-ui-fixture-") as temporary:
        root = Path(temporary)
        assistant = AerisAssistant(AerisConfig(data_dir=root / "data", allowed_paths=(root,),
            dry_run=True, ai_enabled=False, hands_free=False, startup_greeting=False, coding_workspace=root))
        window = AerisMainWindow(assistant)
        window.resize(args.width, args.height)
        window.show()
        window.dashboard.input_field.setText("open notepad")
        window.dashboard.send_command()
        deadline = time.monotonic() + 5
        while window.dashboard.chat_history.count() < 2 and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        if window.dashboard.chat_history.count() < 2:
            raise RuntimeError("Fixture command did not finish")
        deadline = time.monotonic() + 2
        while (window.worker.current_token is not None or "Audio: disabled" not in window.voice_label.text()) and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        if args.view == "reminders":
            assistant.reminder_store.add("Fixture: review study notes", datetime.now(timezone.utc) + timedelta(minutes=30))
            window.tabs.setCurrentWidget(window.reminders_view)
            window.reminders_view.refresh()
            deadline = time.monotonic() + 5
            while window.reminders_view.records.count() == 0 and time.monotonic() < deadline:
                app.processEvents()
                time.sleep(0.01)
            if window.reminders_view.records.count() == 0:
                raise RuntimeError("Fixture reminder did not appear")
        if args.view == 'tasks':
            window.tabs.setCurrentWidget(window.tasks_view)
            window.tasks_view.study_template()
        if args.view == 'permissions':
            window.tabs.setCurrentWidget(window.permissions_view)
        capture = window
        if args.view == 'companion':
            window.show_companion()
            capture = window.companion
        app.processEvents()
        if not capture.grab().save(str(destination)):
            raise RuntimeError("Screenshot could not be saved")
        window.quit_application()
        deadline = time.monotonic() + 5
        while window.isVisible() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        if window.isVisible():
            raise RuntimeError("Fixture UI shutdown did not complete")
    print("Saved offscreen real-widget simulation evidence:", destination)


if __name__ == "__main__":
    main()
