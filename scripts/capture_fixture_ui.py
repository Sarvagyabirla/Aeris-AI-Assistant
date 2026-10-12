"""Capture the real Qt UI with temporary simulation data; no microphone/network."""
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from aeris.assistant import AerisAssistant
from aeris.config import AerisConfig
from aeris.core.tts_worker import global_tts
from aeris.ui.desktop import AerisMainWindow


def main():
    destination = Path(sys.argv[1]).resolve()
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
        window.resize(1100, 700)
        window.show()
        window.dashboard.input_field.setText("open notepad")
        window.dashboard.send_command()
        deadline = time.monotonic() + 5
        while window.dashboard.chat_history.count() < 2 and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        if window.dashboard.chat_history.count() < 2:
            raise RuntimeError("Fixture command did not finish")
        app.processEvents()
        if not window.grab().save(str(destination)):
            raise RuntimeError("Screenshot could not be saved")
        window.close()
        deadline = time.monotonic() + 5
        while window.isVisible() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        if window.isVisible():
            raise RuntimeError("Fixture UI shutdown did not complete")
    print("Saved offscreen real-widget simulation evidence:", destination)


if __name__ == "__main__":
    main()