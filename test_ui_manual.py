"""Optional isolated Qt Stop smoke test; every widget operation runs on the Qt thread."""
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from aeris.assistant import AerisAssistant
from aeris.config import AerisConfig
from aeris.core.tts_worker import global_tts
from aeris.models import ActionResult
from aeris.ui.desktop import AerisMainWindow


def verify_stop_button():
    app = QApplication.instance() or QApplication(sys.argv)
    errors = []
    previous_mute = global_tts.muted
    global_tts.muted = True
    with tempfile.TemporaryDirectory(prefix="aeris-manual-ui-") as temporary:
        root = Path(temporary)
        assistant = AerisAssistant(AerisConfig(data_dir=root / "data", allowed_paths=(root,),
            ai_enabled=False, dry_run=True, hands_free=False, coding_workspace=root))
        def slow_execute(action, approval, token=None):
            for _ in range(100):
                token.raise_if_cancelled()
                time.sleep(0.02)
            return ActionResult(True, "Fixture completed")
        assistant.registry.execute = slow_execute
        window = AerisMainWindow(assistant)
        window.show()
        state = [0]
        deadline = time.monotonic() + 8
        def advance():
            try:
                if time.monotonic() >= deadline:
                    raise AssertionError("Fixture shutdown or Stop exceeded deadline")
                if state[0] == 0:
                    window.dashboard.input_field.setText("open notepad")
                    window.dashboard.send_command()
                    state[0] = 1
                elif state[0] == 1 and window.worker.current_token:
                    window.dashboard.stop_btn.click()
                    state[0] = 2
                elif state[0] == 2 and window.worker.current_token is None:
                    assert window.dashboard.chat_history.count() >= 2
                    assert "cancel" in window.dashboard.chat_history.item(1).text().lower()
                    window.close()
                    state[0] = 3
                elif state[0] == 3 and not window.isVisible():
                    timer.stop()
                    app.quit()
            except Exception as exc:
                errors.append(type(exc).__name__)
                window.close()
                if not window.isVisible():
                    timer.stop()
                    app.quit()
        timer = QTimer()
        timer.timeout.connect(advance)
        timer.start(20)
        app.exec()
        assistant.close()
    global_tts.muted = previous_mute
    if errors:
        raise AssertionError("Qt fixture failed: " + ", ".join(errors))
    print("Isolated Qt Stop fixture passed; no device effects or user settings loaded.")


if __name__ == "__main__":
    verify_stop_button()
