import sys
import threading
from typing import Any

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..assistant import AerisAssistant
from ..models import ActionRequest, PermissionLevel
from ..state import app_store, CancellationToken, CancelledError
import queue
import uuid

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

    def _approval_callback(self, request: ActionRequest, level: PermissionLevel, preview: str) -> bool:
        self._permission_event.clear()
        self.permission_requested.emit(request, level, preview)
        self._permission_event.wait()
        return bool(self._permission_result)

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                cmd_id, text = self.command_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if self._stop_event.is_set():
                break

            token = CancellationToken()
            with self._lock:
                self.current_token = token

            self.status_updated.emit("Thinking...")
            try:
                turn = self.assistant.handle(text, self._approval_callback, token)
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
        layout.addWidget(self.status_label)

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
        self.worker.status_updated.connect(self.status_label.setText)

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
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Settings will go here."))
        layout.addStretch()


class AppGridTab(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.addWidget(QLabel("App shortcuts will go here."), 0, 0)


class AerisMainWindow(QMainWindow):
    def __init__(self, assistant: AerisAssistant):
        super().__init__()
        self.assistant = assistant
        self.worker = AssistantWorker(assistant, self)
        self.worker.start()
        
        self.setWindowTitle("Aeris Assistant")
        self.resize(800, 600)
        self.setup_ui()
        self.setup_styling()
        
    def closeEvent(self, event: Any) -> None:
        self.worker.stop_worker()
        self.worker.wait(2000)
        super().closeEvent(event)
        
    def setup_ui(self) -> None:
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.dashboard = DashboardTab(self.worker)
        self.apps = AppGridTab()
        self.settings = SettingsTab(self.assistant)
        
        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.apps, "Apps & Automation")
        self.tabs.addTab(self.settings, "Settings")
        
        # Connect permission request
        self.worker.permission_requested.connect(self.handle_permission)
        
    def setup_styling(self) -> None:
        # Dark cyan/orange theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1E1E1E;
                color: #FFFFFF;
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
            }
            QTabBar::tab:selected {
                background: #007ACC;
                color: white;
            }
            QLineEdit {
                background: #333333;
                border: 1px solid #555555;
                padding: 6px;
                border-radius: 4px;
            }
            QPushButton {
                background: #007ACC;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #0098FF;
            }
            QListWidget {
                background: #252526;
                border: 1px solid #333333;
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
