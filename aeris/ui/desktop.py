import queue
import sys
import threading
import uuid
from typing import Any

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..assistant import AerisAssistant
from ..integrations.voice import VoiceService, VoiceUnavailableError
from ..models import ActionRequest, PermissionLevel
from ..state import CancellationToken, CancelledError, app_store


class HandsFreeWorker(QThread):
    def __init__(self, assistant: AerisAssistant, assistant_worker: 'AssistantWorker', parent: QWidget | None = None):
        super().__init__(parent)
        self.assistant = assistant
        self.assistant_worker = assistant_worker
        self._stop_event = threading.Event()
        self.voice = None

    def stop(self):
        self._stop_event.set()
        if self.voice:
            self.voice._cancel_flag = True

    def run(self):
        if not self.assistant.config.hands_free:
            return
            
        try:
            self.voice = VoiceService(
                self.assistant.config.voice_model,
                self.assistant.config.voice_record_seconds,
                self.assistant.config.voice_device,
                self.assistant.config.voice_language,
            )
        except VoiceUnavailableError:
            return

        wake_word = self.assistant.config.wake_word.lower()
        
        while not self._stop_event.is_set():
            if self.assistant_worker.current_token is not None:
                self._stop_event.wait(timeout=1.0)
                continue
                
            try:
                text = self.voice.listen_once()
                if not text or self._stop_event.is_set():
                    continue
                    
                text_lower = text.lower()
                if wake_word in text_lower:
                    if text_lower.startswith(wake_word):
                        command = text[len(wake_word):].strip()
                        if command and command[0] in ".,!?:;":
                            command = command[1:].strip()
                    else:
                        command = text
                        
                    if command:
                        self.assistant_worker.process_command(command)
            except VoiceUnavailableError:
                break
            except Exception:
                self._stop_event.wait(timeout=2.0)


class AssistantWorker(QThread):
    """Background worker for running the assistant without blocking the UI."""
    response_ready = Signal(str, str)
    permission_requested = Signal(object, object, str)  # request, level, preview
    status_updated = Signal(str)

    def __init__(self, assistant: AerisAssistant, parent: QWidget | None = None):
        super().__init__(parent)
        self.assistant = assistant
        self.command_queue: queue.Queue[tuple[str, str]] = queue.Queue(maxsize=1)
        self.current_token: CancellationToken | None = None
        self._lock = threading.Lock()
        self._permission_result: bool | None = None
        self._permission_event = threading.Event()
        self._stop_event = threading.Event()

    def process_command(self, text: str) -> bool:
        """Returns True if accepted, False if busy."""
        command_id = str(uuid.uuid4())
        try:
            self.command_queue.put_nowait((command_id, text))
            return True
        except queue.Full:
            return False

    def cancel_current(self) -> None:
        """Interrupts the currently running command."""
        with self._lock:
            if self.current_token:
                self.current_token.cancel()
        self._permission_result = False
        self._permission_event.set()
        
        from ..core.tts_worker import global_tts
        global_tts.stop()
        
        # Signal any screen monitor to stop
        app_store.set("monitor_cancelled", True)

        # Clear any pending commands
        try:
            self.command_queue.get_nowait()
        except queue.Empty:
            pass

    def stop_worker(self) -> None:
        self._stop_event.set()
        self.cancel_current()
        try:
            self.command_queue.put_nowait(("stop", ""))
        except queue.Full:
            pass

    def provide_permission(self, allowed: bool) -> None:
        self._permission_result = allowed
        self._permission_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                cmd_id, text = self.command_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if self._stop_event.is_set():
                break
                
            # Clear monitor cancelled flag for new commands
            app_store.set("monitor_cancelled", False)

            token = CancellationToken()
            with self._lock:
                self.current_token = token

            def approval_closure(request: ActionRequest, level: PermissionLevel, preview: str) -> bool:
                if token.is_cancelled or self._stop_event.is_set():
                    return False
                self._permission_event.clear()
                self._permission_result = None
                self.permission_requested.emit(request, level, preview)
                
                while not token.is_cancelled and not self._stop_event.is_set():
                    if self._permission_event.wait(timeout=0.2):
                        break
                
                if token.is_cancelled or self._stop_event.is_set():
                    return False
                return bool(self._permission_result)

            self.status_updated.emit("Thinking...")
            try:
                turn = self.assistant.handle(text, approval_closure, token)
                if token.is_cancelled:
                    self.response_ready.emit(text, "Command cancelled.")
                else:
                    self.response_ready.emit(text, turn.reply)
            except CancelledError:
                self.response_ready.emit(text, "Command cancelled.")
            except Exception as e:
                self.response_ready.emit(text, f"Error: {e}")
            finally:
                with self._lock:
                    self.current_token = None
                self.status_updated.emit("Ready")


class DashboardTab(QWidget):
    def __init__(self, worker: AssistantWorker, parent: QWidget | None = None):
        super().__init__(parent)
        self.worker = worker
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        
        self.task_indicator = QProgressBar()
        self.task_indicator.setRange(0, 1)
        self.task_indicator.setValue(1)
        self.task_indicator.setTextVisible(False)
        self.task_indicator.setFixedHeight(4)
        
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.task_indicator)
        layout.addLayout(status_layout)

        # Chat history
        self.chat_history = QListWidget()
        layout.addWidget(self.chat_history)

        # Input area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a command for Aeris...")
        self.input_field.returnPressed.connect(self.send_command)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_command)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.worker.cancel_current)
        self.stop_btn.setStyleSheet("background-color: #CC0000;")

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        input_layout.addWidget(self.stop_btn)
        layout.addLayout(input_layout)

        # Connect signals
        self.worker.response_ready.connect(self.on_response)
        self.worker.status_updated.connect(self.update_status)

    @Slot(str)
    def update_status(self, text: str) -> None:
        self.status_label.setText(text)
        if text.lower() == "ready":
            self.task_indicator.setRange(0, 1)
            self.task_indicator.setValue(1)
        else:
            self.task_indicator.setRange(0, 0)

    @Slot()
    def send_command(self) -> None:
        text = self.input_field.text().strip()
        if text:
            if self.worker.process_command(text):
                self.chat_history.addItem(f"You: {text}")
                self.input_field.clear()
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Busy", "Aeris is currently busy. Please wait or press Stop.")

    @Slot(str, str)
    def on_response(self, user_input: str, reply: str) -> None:
        self.chat_history.addItem(f"Aeris: {reply}")
        self.chat_history.scrollToBottom()


class SettingsTab(QWidget):
    def __init__(self, assistant: AerisAssistant, parent: QWidget | None = None):
        super().__init__(parent)
        self.assistant = assistant
        layout = QFormLayout(self)
        
        self.ai_enabled = QCheckBox()
        self.ai_enabled.setChecked(self.assistant.config.ai_enabled)
        layout.addRow("Enable Gemini AI:", self.ai_enabled)
        
        self.dry_run = QCheckBox()
        self.dry_run.setChecked(self.assistant.config.dry_run)
        layout.addRow("Dry Run (Simulation):", self.dry_run)
        
        self.hands_free = QCheckBox()
        self.hands_free.setChecked(self.assistant.config.hands_free)
        layout.addRow("Hands-Free Mode:", self.hands_free)
        
        self.require_signed = QCheckBox()
        self.require_signed.setChecked(self.assistant.config.require_signed_installers)
        layout.addRow("Require Signed Installers:", self.require_signed)
        
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setText(self.assistant.config.gemini_api_key or "")
        layout.addRow("Gemini API Key:", self.api_key)
        
        self.wake_word = QLineEdit()
        self.wake_word.setText(self.assistant.config.wake_word)
        layout.addRow("Wake Word:", self.wake_word)
        
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        layout.addRow("", save_btn)
        
    @Slot()
    def save_settings(self) -> None:
        self.assistant.config.ai_enabled = self.ai_enabled.isChecked()
        self.assistant.config.dry_run = self.dry_run.isChecked()
        self.assistant.config.hands_free = self.hands_free.isChecked()
        self.assistant.config.require_signed_installers = self.require_signed.isChecked()
        self.assistant.config.gemini_api_key = self.api_key.text().strip() or None
        self.assistant.config.wake_word = self.wake_word.text().strip() or "aeris"
        
        try:
            self.assistant.config.save()
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")


class AppGridTab(QWidget):
    def __init__(self, worker: AssistantWorker, parent: QWidget | None = None):
        super().__init__(parent)
        self.worker = worker
        layout = QVBoxLayout(self)
        
        routines_label = QLabel("Routines & Workflows")
        routines_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(routines_label)
        
        btn_layout = QHBoxLayout()
        
        daily_brief_btn = QPushButton("Daily Brief")
        daily_brief_btn.clicked.connect(lambda: self.run_command("Read my latest emails and summarize my daily brief"))
        btn_layout.addWidget(daily_brief_btn)
        
        system_health_btn = QPushButton("System Health Check")
        system_health_btn.clicked.connect(lambda: self.run_command("Check system health and status"))
        btn_layout.addWidget(system_health_btn)
        
        clear_temp_btn = QPushButton("Network Test")
        clear_temp_btn.clicked.connect(lambda: self.run_command("Test network connectivity"))
        btn_layout.addWidget(clear_temp_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()

    def run_command(self, cmd: str) -> None:
        if not self.worker.process_command(cmd):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Busy", "Aeris is currently busy. Please wait.")


class AerisMainWindow(QMainWindow):
    def __init__(self, assistant: AerisAssistant):
        super().__init__()
        self.assistant = assistant
        self.worker = AssistantWorker(assistant, self)
        self.worker.start()
        self.hands_free = HandsFreeWorker(assistant, self.worker, self)
        self.hands_free.start()
        
        self.setWindowTitle("Aeris Assistant")
        self.resize(800, 600)
        self.setup_ui()
        self.setup_styling()
        
    def closeEvent(self, event: Any) -> None:
        app_store.set("kill_switch_active", True)
        if hasattr(self, 'hands_free'):
            self.hands_free.stop()
            self.hands_free.quit()
            self.hands_free.wait(2000)
        self.worker.stop_worker()
        self.worker.quit()
        self.worker.wait(2000)
        super().closeEvent(event)
        
    def setup_ui(self) -> None:
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.dashboard = DashboardTab(self.worker)
        self.apps = AppGridTab(self.worker)
        self.settings = SettingsTab(self.assistant)
        
        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.apps, "Apps & Automation")
        self.tabs.addTab(self.settings, "Settings")
        
        # Connect permission request
        self.worker.permission_requested.connect(self.handle_permission)
        
    def setup_styling(self) -> None:
        # Dark cyan theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1E1E1E;
                color: #E0E0E0;
                font-family: 'Segoe UI', Arial;
            }
            QTabWidget::pane {
                border: 1px solid #333333;
            }
            QTabBar::tab {
                background: #2D2D30;
                padding: 8px 16px;
                border: 1px solid #333333;
                border-bottom: none;
                color: #A0A0A0;
            }
            QTabBar::tab:selected {
                background: #00BCD4;
                color: #121212;
                font-weight: bold;
            }
            QLineEdit {
                background: #333333;
                border: 1px solid #555555;
                padding: 6px;
                border-radius: 4px;
                color: white;
            }
            QPushButton {
                background: #008B8B;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #00BCD4;
            }
            QListWidget {
                background: #252526;
                border: 1px solid #333333;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 2px;
                text-align: center;
                color: white;
                background-color: #333333;
            }
            QProgressBar::chunk {
                background-color: #00BCD4;
            }
        """)

    @Slot(object, object, str)
    def handle_permission(self, request: ActionRequest, level: PermissionLevel, preview: str) -> None:
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("Permission Required")
        msg.setText(f"Aeris wants to perform an action:\n\n{preview}")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        
        # In a real app, you might want custom dialogs for emails vs downloads.
        # This uses a simple Yes/No.
        ret = msg.exec()
        self.worker.provide_permission(ret == QMessageBox.Yes)


def launch_desktop(assistant: AerisAssistant) -> int:
    app = QApplication(sys.argv)
    window = AerisMainWindow(assistant)
    window.show()
    return app.exec()
