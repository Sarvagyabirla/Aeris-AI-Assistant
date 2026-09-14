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
from ..state import app_store

class AssistantWorker(QThread):
    """Background worker for running the assistant without blocking the UI."""
    response_ready = Signal(str, str)
    permission_requested = Signal(object, object, str)  # request, level, preview
    status_updated = Signal(str)

    def __init__(self, assistant: AerisAssistant, parent: QWidget | None = None):
        super().__init__(parent)
        self.assistant = assistant
        self.pending_input: str | None = None
        self._lock = threading.Lock()
        self._permission_result: bool | None = None
        self._permission_event = threading.Event()

    def process_command(self, text: str) -> None:
        with self._lock:
            self.pending_input = text
        self.start()

    def provide_permission(self, allowed: bool) -> None:
        self._permission_result = allowed
        self._permission_event.set()

    def _approval_callback(self, request: ActionRequest, level: PermissionLevel, preview: str) -> bool:
        self._permission_event.clear()
        self.permission_requested.emit(request, level, preview)
        self._permission_event.wait()
        return bool(self._permission_result)

    def run(self) -> None:
        with self._lock:
            text = self.pending_input
            self.pending_input = None

        if not text:
            return

        self.status_updated.emit("Thinking...")
        try:
            turn = self.assistant.handle(text, self._approval_callback)
            self.response_ready.emit(text, turn.reply)
        except Exception as e:
            self.response_ready.emit(text, f"Error: {e}")
        finally:
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

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)

        # Connect signals
        self.worker.response_ready.connect(self.on_response)
        self.worker.status_updated.connect(self.status_label.setText)

    @Slot()
    def send_command(self) -> None:
        text = self.input_field.text().strip()
        if text:
            self.chat_history.addItem(f"You: {text}")
            self.input_field.clear()
            self.worker.process_command(text)

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
        
        self.setWindowTitle("Aeris Assistant")
        self.resize(800, 600)
        self.setup_ui()
        self.setup_styling()
        
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
