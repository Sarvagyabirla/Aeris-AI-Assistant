import queue
import re as _re
import sys
import threading
import time
import uuid
from typing import Any

from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenu,
    QProgressBar,
    QPushButton,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..activation import extract_addressed_command
from ..assistant import AerisAssistant
from ..integrations.voice import AudioState, VoiceService, VoiceUnavailableError
from ..models import ActionRequest, PermissionLevel
from ..state import CancellationToken, CancelledError, app_store
from .companion import CompanionWindow, ViewPreferences
from .memory_view import MemoryView
from .permissions_view import PermissionsView
from .presence import CharacterWidget, PresenceModel
from .reminders_view import RemindersView
from .tasks_view import TasksView

# Phrases that trigger immediate task interrupt even while a task is active.
_STOP_INTERRUPT = _re.compile(r"^(?:please\s+)?(?:stop|cancel|abort|halt)(?:\s+(?:(?:this|the|current)\s+)?(?:task|command|work))?[.!?]*$", _re.I)


class HandsFreeWorker(QThread):
    transcript = Signal(str)
    readiness = Signal(str)
    def __init__(self, assistant: AerisAssistant, assistant_worker: 'AssistantWorker', parent: QWidget | None = None):
        super().__init__(parent)
        self.assistant = assistant
        self.assistant_worker = assistant_worker
        self._stop_event = threading.Event()
        self.voice = None
        self.push_to_talk = threading.Event()
        self._audio_status = None
        self.passive_enabled = assistant.config.hands_free

    def audio_state(self, state: AudioState, detail: str = ""):
        status = f"Audio: {state.value}" + (f" — {detail}" if detail else "")
        if status != self._audio_status:
            self._audio_status = status
            self.readiness.emit(status)

    def stop(self):
        self._stop_event.set()
        if self.voice:
            self.voice._cancel_flag = True
        self.audio_state(AudioState.DISABLED, "Microphone paused")

    def run(self):
        try:
            self._run_audio()
        except Exception:
            self.audio_state(AudioState.UNAVAILABLE, "Audio processing failed; text input remains available")
        finally:
            # Cached ASR assets are released on the same owner thread after capture stops.
            self.voice = None

    def _run_audio(self):
        try:
            self.voice = VoiceService(
                self.assistant.config.voice_model,
                self.assistant.config.voice_record_seconds,
                self.assistant.config.voice_device,
                self.assistant.config.voice_language,
            )
        except VoiceUnavailableError:
            self.audio_state(AudioState.UNAVAILABLE, "Text input remains available")
            return

        from ..core.tts_worker import global_tts
        capture_generation = [global_tts.playback_generation]
        self.voice.state_listener = self.audio_state
        self.voice.input_allowed = lambda: (
            not self._stop_event.is_set() and not self.assistant.permissions.stopped
            and not global_tts.cleanup_pending
            and not global_tts.speaking.is_set() and time.monotonic() - global_tts.last_output_at >= 0.35
            and capture_generation[0] == global_tts.playback_generation)
        wake_word = self.assistant.config.wake_word.lower()
        self.audio_state(AudioState.DISABLED, "Push to talk is available; assets load from cache only")
        if self.passive_enabled and not self.assistant.permissions.stopped:
            self.audio_state(AudioState.INITIALIZING, "Cached assets only; text input and Stop remain available")
            try:
                self.voice.initialize_cached_model()
            except (VoiceUnavailableError, RuntimeError):
                self.audio_state(AudioState.UNAVAILABLE, "Prepare the configured cached model explicitly; text input remains available")
                return
            if self._stop_event.is_set():
                return
        
        while not self._stop_event.is_set():
            task_active = self.assistant_worker.current_token is not None
            tts_speaking = global_tts.speaking.is_set()
            if self.assistant.permissions.stopped:
                self.push_to_talk.clear()
                self.audio_state(AudioState.DISABLED, "Global Stop active; explicitly Resume in the app")
                self._stop_event.wait(0.1)
                continue
            if global_tts.cleanup_pending:
                self.audio_state(AudioState.UNAVAILABLE, "Speech cleanup is pending; microphone paused. Quit and use Retry cleanup")
                self._stop_event.wait(0.1)
                continue

            addressed = self.push_to_talk.is_set()
            if tts_speaking:
                if addressed:
                    global_tts.stop()
                    self.audio_state(AudioState.INTERRUPTED, "Stopping speech before push to talk")
                else:
                    self.audio_state(AudioState.SPEAKING, "Passive capture paused during AERIS speech; use Push to talk or Stop")
                self._stop_event.wait(0.05)
                continue
            if time.monotonic() - global_tts.last_output_at < 0.35:
                self.audio_state(AudioState.INTERRUPTED, "Waiting for speech playback to settle")
                self._stop_event.wait(0.05)
                continue
            if not self.passive_enabled and not addressed:
                self.audio_state(AudioState.EXECUTING if task_active else AudioState.DISABLED,
                                 "Microphone paused; use Push to talk")
                self._stop_event.wait(0.1)
                continue
            self.push_to_talk.clear()

            try:
                capture_generation[0] = global_tts.playback_generation
                self.voice.begin_session()
                self.audio_state(AudioState.LISTENING if addressed else AudioState.WAKE_STANDBY,
                                 "Push to talk" if addressed else f"Local transcription for '{wake_word}'; not a trained wake detector")
                text = self.voice.listen_once()
                if not text or not self.voice.input_allowed():
                    continue

                addressed_command = extract_addressed_command(text, (wake_word,))
                command = (text if addressed_command is None else addressed_command) if addressed else addressed_command
                if command:
                    self.transcript.emit(text)
                    if _STOP_INTERRUPT.fullmatch(command):
                        self.assistant_worker.cancel_current()
                        self.audio_state(AudioState.INTERRUPTED, "Task cancellation requested")
                    elif task_active or not self.assistant_worker.process_command(command):
                        self.audio_state(AudioState.EXECUTING, "Busy; command not queued. Retry or press Stop")
            except VoiceUnavailableError as exc:
                self.audio_state(AudioState.UNAVAILABLE, str(exc) + " Use text input; Push to talk retries.")
                break
            except Exception:
                self.audio_state(AudioState.UNAVAILABLE, "Audio processing failed; use text input and retry Push to talk")
                break


class AssistantWorker(QThread):
    """Background worker for running the assistant without blocking the UI."""
    response_ready = Signal(str, str)
    permission_requested = Signal(object, object, str)  # request, level, preview
    status_updated = Signal(str)
    permission_invalidated = Signal()
    task_updated = Signal(object)
    turn_completed = Signal(object)

    def __init__(self, assistant: AerisAssistant, parent: QWidget | None = None):
        super().__init__(parent)
        self.assistant = assistant
        self.command_queue: queue.Queue[tuple[str, str]] = queue.Queue(maxsize=1)
        self.current_token: CancellationToken | None = None
        self._lock = threading.Lock()
        self._permission_result: bool | None = None
        self._permission_event = threading.Event()
        self._stop_event = threading.Event()
        self._generation = 0
        self._pending_request_id = None

    def process_command(self, text: str) -> bool:
        """Returns True if accepted, False if busy."""
        command_id = str(uuid.uuid4())
        try:
            with self._lock:
                if self._stop_event.is_set() or self.current_token is not None:
                    return False
                self.command_queue.put_nowait((command_id, text, self._generation))
            return True
        except queue.Full:
            return False

    def cancel_current(self) -> None:
        """Interrupts the currently running command."""
        with self._lock:
            self._generation += 1
            if self.current_token:
                self.current_token.cancel()
        self._permission_result = False
        self._permission_event.set()
        self.permission_invalidated.emit()
        
        from ..core.tts_worker import global_tts
        global_tts.stop()
        
        # Signal any screen monitor to stop
        app_store.set("monitor_cancelled", True)
        self.assistant.followup.clear()
        self.status_updated.emit("Cancellation requested — cleaning up")

        # Clear any pending commands
        try:
            self.command_queue.get_nowait()
        except queue.Empty:
            pass

    def stop_worker(self) -> None:
        self._stop_event.set()
        self.cancel_current()
        try:
            self.command_queue.put_nowait(("stop", "", self._generation))
        except queue.Full:
            pass

    def provide_permission(self, allowed: bool, request_id=None) -> None:
        if request_id != self._pending_request_id or not self.current_token or self.current_token.is_cancelled:
            return
        self._permission_result = allowed
        self._permission_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                cmd_id, text, generation = self.command_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if self._stop_event.is_set():
                break
                
            # Clear monitor cancelled flag for new commands

            token = CancellationToken()
            token.command_id = cmd_id
            token.progress_callback = self.task_updated.emit
            with self._lock:
                if generation != self._generation:
                    continue
                self.current_token = token

            def approval_closure(request: ActionRequest, level: PermissionLevel, preview: str) -> bool:
                if token.is_cancelled or self._stop_event.is_set():
                    return False
                self._permission_event.clear()
                self._permission_result = None
                self._pending_request_id = request.request_id
                self.status_updated.emit("Awaiting permission")
                self.permission_requested.emit(request, level, preview)
                
                while not token.is_cancelled and not self._stop_event.is_set():
                    if self._permission_event.wait(timeout=0.2):
                        break
                
                if token.is_cancelled or self._stop_event.is_set():
                    return False
                self.status_updated.emit('Executing approved task')
                return bool(self._permission_result)

            self.status_updated.emit("Thinking...")
            try:
                turn = self.assistant.handle(text, approval_closure, token)
                self.turn_completed.emit(turn)
                if token.is_cancelled and not turn.results:
                    self.response_ready.emit(text, "Command cancelled.")
                else:
                    self.response_ready.emit(text, turn.reply)
                if not token.is_cancelled and generation == self._generation:
                    from ..core.tts_worker import global_tts
                    global_tts.speak(turn.spoken_summary(), token=token)
            except CancelledError:
                self.response_ready.emit(text, "Command cancelled.")
            except Exception as e:
                self.response_ready.emit(text, f"Error: {e}")
            finally:
                with self._lock:
                    self.current_token = None
                    self._pending_request_id = None
                self.status_updated.emit("Global Stop active — explicitly resume Aeris" if self.assistant.permissions.stopped else "Ready")


class DashboardTab(QWidget):
    def __init__(self, worker: AssistantWorker, parent: QWidget | None = None, presence=None):
        super().__init__(parent)
        self.worker = worker
        self.presence = presence or PresenceModel(self)
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
        self.chat_history.setWordWrap(True)
        body = QHBoxLayout()
        character_panel = QVBoxLayout()
        self.avatar = CharacterWidget(self.presence)
        self.avatar.setMaximumWidth(320)
        character_panel.addWidget(self.avatar, 1)
        self.presence_label = QLabel('Ready for a task')
        self.presence_label.setTextFormat(Qt.PlainText)
        self.presence_label.setWordWrap(True)
        self.metrics_label = QLabel('')
        character_panel.addWidget(self.presence_label)
        character_panel.addWidget(self.metrics_label)
        body.addLayout(character_panel, 1)
        conversation = QVBoxLayout()
        conversation.addWidget(QLabel('Conversation'))
        conversation.addWidget(self.chat_history, 1)
        conversation.addWidget(QLabel('Current task · observed results stay visible after Stop'))
        self.task_steps = QListWidget()
        self.task_steps.setMaximumHeight(110)
        self.task_steps.setWordWrap(True)
        conversation.addWidget(self.task_steps)
        body.addLayout(conversation, 3)
        layout.addLayout(body, 1)
        self.presence.changed.connect(lambda: self.presence_label.setText(self.presence.phase.replace('-', ' ').title() + ' · ' + self.presence.detail))
        self.worker.task_updated.connect(self.show_task)

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
        emergency = QPushButton("Emergency Stop")
        emergency.setToolTip("Blocks all tasks until explicit Resume; separate from cancelling this task")
        def emergency_stop():
            self.worker.assistant.permissions.stop()
            self.worker.cancel_current()
            self.update_status("Global Stop active — explicitly resume Aeris")
        emergency.clicked.connect(emergency_stop)
        input_layout.addWidget(emergency)
        resume = QPushButton("Resume")
        resume.setToolTip("Explicitly release Emergency Stop")
        resume.clicked.connect(lambda: self.worker.process_command("resume Aeris"))
        input_layout.addWidget(resume)
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

    def show_task(self, task):
        self.task_steps.clear()
        for index, step in enumerate(task['steps'], 1):
            suffix = ' · effect uncertain' if step.get('uncertain') else ''
            self.task_steps.addItem(f"{index}. {step['tool'].replace('.', ' / ')} · {step['status']}{suffix}")


class SettingsApplyWorker(QThread):
    completed = Signal(bool, str)

    def __init__(self, assistant, config, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.config = config

    def run(self):
        try:
            self.assistant.apply_settings(self.config)
        except Exception:
            self.completed.emit(False, self.assistant.config.recovery_message or
                                "Settings were not applied. Check credential storage, settings validity and adapter cleanup.")
        else:
            self.completed.emit(True, "Executor/provider settings applied.")


class CleanupWorker(QThread):
    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.cleaned = False

    def run(self):
        from ..core.tts_worker import global_tts
        try:
            tts_cleaned = global_tts.shutdown()
            adapters_cleaned = self.assistant.close()
            self.cleaned = tts_cleaned and adapters_cleaned
        except Exception:
            self.cleaned = False


class SettingsTab(QWidget):
    def __init__(self, assistant: AerisAssistant, parent: QWidget | None = None):
        super().__init__(parent)
        self.assistant = assistant
        layout = QFormLayout(self)
        if self.assistant.config.recovery_message:
            warning = QLabel(self.assistant.config.recovery_message)
            warning.setWordWrap(True)
            layout.addRow(warning)
        
        self.ai_enabled = QCheckBox()
        self.ai_enabled.setChecked(self.assistant.config.ai_enabled)
        layout.addRow("Enable Gemini AI:", self.ai_enabled)
        
        self.dry_run = QCheckBox()
        self.dry_run.setChecked(self.assistant.config.dry_run)
        layout.addRow("Dry Run (Simulation):", self.dry_run)
        self.automation_mode = QComboBox()
        for label, value in [('Assist · preview effects', 'assist'), ('Task Automation · requested goal', 'task'), ('Trusted Routines · reviewed local scope', 'trusted')]:
            self.automation_mode.addItem(label, value)
        self.automation_mode.setCurrentIndex(self.automation_mode.findData(self.assistant.config.automation_mode))
        layout.addRow('Automation mode:', self.automation_mode)
        
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
        self.timezone_name = QLineEdit(self.assistant.config.timezone_name)
        layout.addRow("Reminder timezone:", self.timezone_name)
        
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.clicked.connect(self.save_settings)
        layout.addRow("", self.save_btn)
        self.save_status = QLabel("")
        self.save_status.setWordWrap(True)
        layout.addRow(self.save_status)
        self.apply_worker = None
        
    @Slot()
    def save_settings(self) -> None:
        if self.apply_worker and self.apply_worker.isRunning():
            return
        config = self.assistant.config.with_overrides(
            ai_enabled=self.ai_enabled.isChecked(), dry_run=self.dry_run.isChecked(),
            automation_mode=self.automation_mode.currentData(),
            hands_free=self.hands_free.isChecked(), require_signed_installers=self.require_signed.isChecked(),
            gemini_api_key=self.api_key.text().strip() or None, wake_word=self.wake_word.text().strip() or "aeris",
            timezone_name=self.timezone_name.text().strip() or "Asia/Kolkata")
        
        self.save_btn.setEnabled(False)
        self.save_status.setText("Applying settings — existing mode remains effective until completed")
        self.apply_worker = SettingsApplyWorker(self.assistant, config, self)
        self.apply_worker.completed.connect(self.settings_completed)
        self.apply_worker.start()

    @Slot(bool, str)
    def settings_completed(self, success, message):
        self.save_btn.setEnabled(True)
        self.save_status.setText(message)
        self.dry_run.setChecked(self.assistant.config.dry_run)
        self.ai_enabled.setChecked(self.assistant.config.ai_enabled)
        self.hands_free.setChecked(self.assistant.config.hands_free)
        window = self.window()
        if isinstance(window, AerisMainWindow) and not window._closing:
            window.restart_voice()
            window.mode_label.setText("SIMULATION — no PC changes" if self.assistant.registry.dry_run else "LIVE — real PC actions")


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
        daily_brief_btn.clicked.connect(lambda: self.run_command("daily brief"))
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


class TypingTargetsWorker(QThread):
    completed = Signal(object)

    def __init__(self, desktop, parent=None):
        super().__init__(parent)
        self.desktop = desktop

    def run(self):
        try:
            self.completed.emit(self.desktop.list_typing_targets())
        except Exception:
            self.completed.emit([])


class AerisMainWindow(QMainWindow):
    def __init__(self, assistant: AerisAssistant):
        super().__init__()
        self.assistant = assistant
        self._closing = False
        self._cleanup_worker = None
        self._voice_generation = 0
        self._typing_targets_worker = None
        self._quit_requested = False
        self._tray = None
        self._hotkeys = None
        self._last_worker_status = 'Ready'
        self._last_turn_failed = False
        self._interrupted = False
        self.view_preferences = ViewPreferences(assistant.config.data_dir / 'presentation.json')
        self.presence = PresenceModel(self)
        self.worker = AssistantWorker(assistant, self)
        self.worker.start()
        self.hands_free = HandsFreeWorker(assistant, self.worker, self)
        self.hands_free.passive_enabled = assistant.config.hands_free and not self.view_preferences.values['microphone_muted']
        
        self.setWindowTitle("Aeris Assistant")
        self.resize(1120, 760)
        self.setup_ui()
        self.setup_styling()
        self.setup_presence()
        self.hands_free.transcript.connect(lambda text: self.dashboard.chat_history.addItem("Heard: " + text))
        self.connect_voice_status(self.hands_free)
        self.hands_free.start()
        
    def closeEvent(self, event: Any) -> None:
        if (not self._quit_requested and not self._closing and self.view_preferences.values['close_to_tray']
                and self._tray and self._tray.isVisible()):
            self.hide_to_tray()
            event.ignore()
            return
        if not self._closing:
            self._closing = True
            self._voice_generation += 1
            self.assistant.permissions.stop()
            self.hands_free.stop()
            self.worker.stop_worker()
            self.reminders_view.stop()
        if (self.hands_free.isRunning() or self.worker.isRunning() or self.reminders_view.reading
                or (self._typing_targets_worker and self._typing_targets_worker.isRunning())
                or (self.permissions_view.apply_worker and self.permissions_view.apply_worker.isRunning())
                or (self.settings.apply_worker and self.settings.apply_worker.isRunning())):
            event.ignore()
            self.dashboard.update_status("Closing — waiting for owned workers to finish")
            QTimer.singleShot(100, self.close)
            return
        if self._cleanup_worker is None:
            self._cleanup_worker = CleanupWorker(self.assistant, self)
            self._cleanup_worker.finished.connect(self.close)
            self._cleanup_worker.start()
        if self._cleanup_worker.isRunning():
            event.ignore()
            self.dashboard.update_status("Closing — adapter cleanup pending; window retained safely")
            return
        if not self._cleanup_worker.cleaned:
            event.ignore()
            self.dashboard.update_status("Cleanup failed — window retained. Retry cleanup after checking diagnostics.")
            self.cleanup_retry_btn.show()
            self.show()  # Cleanup failures must remain recoverable even from tray.
            return
        self.presence_timer.stop()
        self.companion.hide()
        if self._tray:
            self._tray.hide()
        if self._hotkeys:
            self._hotkeys.close()
        super().closeEvent(event)

    @Slot()
    def retry_cleanup(self):
        if self._cleanup_worker is not None and self._cleanup_worker.isRunning():
            return
        if self._cleanup_worker is not None:
            self._cleanup_worker.deleteLater()
        self._cleanup_worker = None
        self.cleanup_retry_btn.hide()
        self.close()

    def connect_voice_status(self, voice_worker):
        voice_worker.readiness.connect(lambda text: self.voice_label.setText(text)
                                      if self.hands_free is voice_worker and not self._closing else None)

    def request_push_to_talk(self):
        if self.assistant.permissions.stopped:
            self.voice_label.setText("Audio: disabled — explicitly Resume after Global Stop")
            return
        if not self.hands_free.isRunning() or self.hands_free._stop_event.is_set():
            self.restart_voice(push_to_talk=True)
        else:
            self.hands_free.push_to_talk.set()

    def restart_voice(self, push_to_talk=False):
        if self._closing:
            return
        self._voice_generation += 1
        generation = self._voice_generation
        self.hands_free.stop()
        def restart():
            if self._closing or generation != self._voice_generation:
                return
            if self.hands_free.isRunning():
                QTimer.singleShot(100, restart)
                return
            self.hands_free.voice = None
            self.hands_free.deleteLater()
            self.hands_free = HandsFreeWorker(self.assistant, self.worker, self)
            self.hands_free.passive_enabled = self.assistant.config.hands_free and not self.view_preferences.values['microphone_muted']
            self.hands_free.transcript.connect(lambda text: self.dashboard.chat_history.addItem("Heard: " + text))
            self.connect_voice_status(self.hands_free)
            if push_to_talk:
                self.hands_free.push_to_talk.set()
            self.hands_free.start()
        restart()
        
    def setup_ui(self) -> None:
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.dashboard = DashboardTab(self.worker, presence=self.presence)
        self.apps = AppGridTab(self.worker)
        self.settings = SettingsTab(self.assistant)
        
        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.apps, "Apps & Automation")
        self.tabs.addTab(self.settings, "Settings")
        self.memory_view = MemoryView(self.assistant.memory)
        self.tabs.addTab(self.memory_view, "Local memory")
        self.reminders_view = RemindersView(self.assistant, self.worker, self)
        self.tabs.addTab(self.reminders_view, "Reminders")
        self.tasks_view = TasksView(self.assistant, self.worker, self)
        self.tabs.addTab(self.tasks_view, 'Tasks & routines')
        self.permissions_view = PermissionsView(self.assistant, self.worker, self)
        self.tabs.addTab(self.permissions_view, 'Permissions')
        self.reminders_view.notification.connect(lambda: self.dashboard.chat_history.addItem("Aeris: A reminder is due. Open the Reminders tab to review it."))
        self.mode_label = QLabel("SIMULATION — no PC changes" if self.assistant.registry.dry_run else "LIVE — real PC actions")
        self.voice_label = QLabel("Microphone muted until listening is enabled or push-to-talk is pressed")
        self.voice_label.setWordWrap(True)
        self.dashboard.layout().insertWidget(0, self.mode_label)
        self.dashboard.layout().insertWidget(1, self.voice_label)
        self.cleanup_retry_btn = QPushButton("Retry cleanup and quit")
        self.cleanup_retry_btn.setToolTip("Retry owned adapter cleanup; tasks remain stopped until Aeris closes")
        self.cleanup_retry_btn.clicked.connect(self.retry_cleanup)
        self.cleanup_retry_btn.hide()
        self.dashboard.layout().addWidget(self.cleanup_retry_btn)
        voice_controls = QHBoxLayout()
        ptt = QPushButton("Push to talk")
        ptt.clicked.connect(self.request_push_to_talk)
        speech_mute = QCheckBox("Mute speech")
        from ..core.tts_worker import global_tts
        speech_mute.toggled.connect(lambda muted: setattr(global_tts, "muted", muted))
        mic_mute = QPushButton("Mute microphone")
        mic_mute.clicked.connect(self.mute_microphone)
        mic_enable = QPushButton('Enable saved listening')
        mic_enable.clicked.connect(self.enable_saved_listening)
        voice_controls.addWidget(ptt)
        voice_controls.addWidget(mic_mute)
        voice_controls.addWidget(mic_enable)
        voice_controls.addWidget(speech_mute)
        self.dashboard.layout().addLayout(voice_controls)
        typing_controls = QHBoxLayout()
        self.typing_target_btn = QPushButton("Select task / typing window")
        self.typing_target_btn.setToolTip("Choose one external window before asking Aeris to type; each action still needs confirmation")
        self.typing_target_btn.clicked.connect(self.choose_typing_window)
        self.typing_target_label = QLabel("Typing window: not selected")
        self.typing_target_label.setTextFormat(Qt.PlainText)
        self.typing_target_label.setWordWrap(True)
        typing_controls.addWidget(self.typing_target_btn)
        typing_controls.addWidget(self.typing_target_label, 1)
        self.dashboard.layout().addLayout(typing_controls)
        self.dashboard.stop_btn.clicked.connect(lambda: self.hands_free.voice.cancel_recording() if self.hands_free.voice else None)
        
        # Connect permission request
        self.worker.permission_requested.connect(self.handle_permission)

    def setup_presence(self):
        self.dashboard.avatar.set_reduced_motion(self.view_preferences.values['reduced_motion'])
        self.companion = CompanionWindow(self.presence, self.worker, self.view_preferences)
        self.companion.setStyleSheet(self.styleSheet())
        self.companion.dashboard_requested.connect(self.show_dashboard)
        self.companion.hide_requested.connect(self.hide_to_tray)
        self.companion.mic_btn.clicked.connect(self.request_push_to_talk)
        self.companion.mute_mic_btn.clicked.connect(self.mute_microphone)
        self.companion.stop_btn.clicked.connect(self.cancel_audio_capture)
        self.companion.recovery_available = lambda: bool((self._tray and self._tray.isVisible()) or (self._hotkeys and self._hotkeys.can_restore))
        self.tabs.currentChanged.connect(lambda _: self.dashboard.avatar.sync_animation())
        controls = QHBoxLayout()
        companion_button = QPushButton('Floating companion')
        companion_button.clicked.connect(self.show_companion)
        tray_button = QPushButton('Hide to tray')
        tray_button.clicked.connect(self.hide_to_tray)
        self.reduced_motion = QCheckBox('Reduced motion')
        self.reduced_motion.setChecked(self.view_preferences.values['reduced_motion'])
        self.reduced_motion.toggled.connect(self.set_reduced_motion)
        self.close_to_tray = QCheckBox('Close to tray')
        self.close_to_tray.setChecked(self.view_preferences.values['close_to_tray'])
        self.close_to_tray.toggled.connect(lambda value: self.save_view(close_to_tray=value))
        for widget in (companion_button, tray_button, self.reduced_motion, self.close_to_tray):
            controls.addWidget(widget)
        self.dashboard.layout().addLayout(controls)
        self.worker.status_updated.connect(self.worker_state)
        self.worker.turn_completed.connect(self.turn_finished)
        self.worker.task_updated.connect(self.task_state)
        self.worker.permission_invalidated.connect(lambda: setattr(self, '_interrupted', True))
        # Application shortcuts remain useful when native registration is unavailable.
        self.shortcuts = []
        for sequence, callback in [('Ctrl+Alt+A', self.recover_views), ('Ctrl+Alt+S', self.worker.cancel_current), ('Ctrl+Alt+Space', self.request_push_to_talk)]:
            shortcut = QShortcut(sequence, self)
            shortcut.setContext(Qt.ApplicationShortcut)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)
        if QSystemTrayIcon.isSystemTrayAvailable():
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setPen(QColor('#56d9ed'))
            painter.setFont(QFont('Segoe UI', 21, QFont.Bold))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, 'A')
            painter.end()
            self._tray = QSystemTrayIcon(QIcon(pixmap), self)
            menu = QMenu(self)
            for label, callback in [('Open dashboard / recover clicks', self.recover_views), ('Show companion', self.show_companion),
                                    ('Stop task and speech', self.worker.cancel_current), ('Emergency Stop', self.emergency_stop),
                                    ('Mute microphone', self.mute_microphone), ('Enable saved listening', self.enable_saved_listening), ('Quit Aeris', self.quit_application)]:
                action = QAction(label, menu)
                action.triggered.connect(callback)
                menu.addAction(action)
            self._tray.setContextMenu(menu)
            self._tray.setToolTip('Aeris · Ctrl+Alt+A restore · Ctrl+Alt+S Stop · Ctrl+Alt+Space talk')
            self._tray.activated.connect(lambda reason: self.recover_views() if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick) else None)
            self._tray.show()
        self.presence_timer = QTimer(self)
        self.presence_timer.setInterval(100)
        self.presence_timer.timeout.connect(self.refresh_presence)
        self.presence_timer.start()
        app = QApplication.instance()
        app.screenAdded.connect(self.screen_changed)
        app.screenRemoved.connect(self.screen_changed)
        for screen in app.screens():
            self.observe_screen(screen)
        self.screen_changed()

    def observe_screen(self, screen):
        screen.availableGeometryChanged.connect(self.screen_changed)

    def screen_changed(self, *args):
        if args and hasattr(args[0], 'availableGeometry') and args[0] in QApplication.screens():
            self.observe_screen(args[0])
        self.companion.fit_to_screens([screen.availableGeometry() for screen in QApplication.screens()])

    def save_view(self, **changes):
        try:
            self.view_preferences.save(**changes)
        except OSError:
            self.dashboard.update_status('View preference could not be saved; current view remains usable')

    def set_reduced_motion(self, value):
        self.dashboard.avatar.set_reduced_motion(value)
        self.companion.avatar.set_reduced_motion(value)
        self.save_view(reduced_motion=value)

    def show_companion(self):
        if self._closing:
            return
        self.screen_changed()
        self.companion.show()
        self.hide()
        self.save_view(view='companion')

    def show_dashboard(self):
        if self._closing:
            self.show()
            return
        self.companion.set_click_through(False)
        self.companion.hide()
        self.showNormal()
        self.raise_()
        self.activateWindow()  # Only explicit user restore requests activate.
        geometry = self.companion.geometry()
        self.save_view(view='dashboard', geometry=[geometry.x(), geometry.y(), geometry.width(), geometry.height()])

    def recover_views(self):
        self.show_dashboard()

    def hide_to_tray(self):
        if self._tray and self._tray.isVisible():
            self.companion.set_click_through(False)
            self.companion.hide()
            self.hide()
        else:
            self.showMinimized()  # Always preserve a taskbar recovery path.
            self.companion.hide()

    def quit_application(self):
        geometry = self.companion.geometry()
        self.save_view(geometry=[geometry.x(), geometry.y(), geometry.width(), geometry.height()])
        self._quit_requested = True
        self.companion.hide()
        self.show()
        self.close()

    def emergency_stop(self):
        self.assistant.permissions.stop()
        self.stop_current_task()

    def cancel_audio_capture(self):
        if self.hands_free.voice:
            self.hands_free.voice.cancel_recording()

    def mute_microphone(self):
        self.hands_free.stop()
        self.save_view(microphone_muted=True)

    def enable_saved_listening(self):
        if not self.assistant.config.hands_free:
            self.voice_label.setText('Audio: disabled - opt into Hands-Free in Settings first. Push to talk remains available.')
            return
        self.save_view(microphone_muted=False)
        self.restart_voice()

    def stop_current_task(self):
        self.worker.cancel_current()
        self.cancel_audio_capture()

    def worker_state(self, text):
        self._last_worker_status = text
        if text.startswith('Thinking'):
            self._last_turn_failed = False
            self._interrupted = False
        self.refresh_presence()

    def task_state(self, task):
        self.presence.task = task
        self.refresh_presence()

    def turn_finished(self, turn):
        self._last_turn_failed = turn.status == 'failed'
        self._interrupted = turn.status == 'cancelled'
        self.refresh_presence()
        if self._last_turn_failed and not self.isVisible() and not self.companion.isVisible():
            self.show_dashboard()

    def refresh_presence(self):
        from ..core.tts_worker import global_tts
        audio = self.voice_label.text().split('Audio: ', 1)[-1].split(' ')[0].strip()
        audio_changed = self.presence.audio != audio
        self.presence.audio = audio
        phase, detail = 'idle', 'Ready for a task'
        if self.assistant.permissions.stopped:
            phase, detail = 'interrupted', 'Emergency Stop latched · explicitly Resume'
        elif self._closing:
            phase, detail = 'interrupted', 'Closing · waiting for owned cleanup'
        elif 'Awaiting permission' in self._last_worker_status and self.worker.current_token:
            phase, detail = 'awaiting-permission', 'Review the exact action in the dashboard'
        elif self._interrupted:
            phase, detail = 'interrupted', 'Stop requested · completed effects stay in the transcript'
        elif global_tts.speaking.is_set():
            phase, detail = 'speaking', 'Speaking the observed task result'
        elif self.worker.current_token:
            executing = self.presence.task and any(step['status'] == 'executing' for step in self.presence.task['steps'])
            phase, detail = ('executing', 'Running the current step') if executing else ('thinking', 'Resolving the requested task')
        elif self._last_turn_failed:
            phase, detail = 'error', 'Task failed · review the result before retrying'
        elif audio in {'listening', 'wake_standby', 'wake'}:
            phase, detail = 'listening', 'Microphone active · local transcription'
        elif audio in {'initializing', 'transcribing'}:
            phase, detail = 'thinking', 'Preparing or transcribing local audio'
        elif not self.assistant.config.ai_enabled:
            phase, detail = 'offline', 'Local controls ready · AI disabled'
        self.presence.update_state(phase, detail)
        if audio_changed:
            self.presence.changed.emit()
        # Measured process memory only. No decorative CPU/network/model claims.
        if self.isVisible() and int(time.monotonic()) != getattr(self, '_metrics_second', None):
            self._metrics_second = int(time.monotonic())
            try:
                import psutil
                self.dashboard.metrics_label.setText(f'Aeris process · {psutil.Process().memory_info().rss / 1024**2:.0f} MiB RAM')
            except (ImportError, OSError):
                self.dashboard.metrics_label.setText('Process memory unavailable')

    def changeEvent(self, event):
        super().changeEvent(event)
        if hasattr(self, 'dashboard'):
            self.dashboard.avatar.sync_animation()

    @Slot()
    def choose_typing_window(self):
        if self._closing or (self._typing_targets_worker and self._typing_targets_worker.isRunning()):
            return
        self.typing_target_btn.setEnabled(False)
        self.typing_target_label.setText("Looking for supported visible windows…")
        if self._typing_targets_worker:
            self._typing_targets_worker.deleteLater()
        self._typing_targets_worker = TypingTargetsWorker(self.assistant._desktop, self)
        self._typing_targets_worker.completed.connect(self.typing_targets_ready)
        self._typing_targets_worker.start()

    @Slot(object)
    def typing_targets_ready(self, candidates):
        from PySide6.QtWidgets import QInputDialog
        if self._closing:
            return
        self.typing_target_btn.setEnabled(True)
        if not candidates:
            self.typing_target_label.setText("No supported window found. Open an editor and try again; Windows input support is required.")
            return
        labels = [f"{item['expected_title']} — {item['process_name']} (window {item['window_id']})" for item in candidates]
        choice, accepted = QInputDialog.getItem(self, "Choose typing window",
            "Choose the window and keep its intended text control focused. Every typing request has a separate preview.", labels, 0, False)
        if not accepted:
            self.typing_target_label.setText("Selection cancelled; no new typing target selected")
            return
        candidate = candidates[labels.index(choice)]
        result = self.assistant._desktop.select_typing_target(candidate["window_id"])
        self.typing_target_label.setText(f"Typing window: {candidate['expected_title']}" if result.success else result.message)
        
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
        if (request.request_id != self.worker._pending_request_id or not self.worker.current_token
                or self.worker.current_token.is_cancelled or self._closing):
            return
        self.show_dashboard()
        msg = QMessageBox(self)
        msg.setWindowTitle("Permission Required")
        msg.setTextFormat(Qt.PlainText)
        msg.setText(f"Aeris wants to perform an action:\n\n{preview}")
        if request.tool in {'files.organize', 'files.undo_organization'}:
            args = request.arguments
            manifest = args.get('manifest', [])
            verb = 'Organize' if request.tool == 'files.organize' else 'Restore'
            msg.setText(f'{verb} {len(manifest)} documents?\n\n'
                        f'Folder: {args.get("path", "the selected batch")}\n'
                        'Open Details to review every source and destination. File identities and bytes are bound to this review. '
                        'No existing destination is overwritten. Stop retains completed changes for review; Undo refuses newer edits.')
            msg.setDetailedText('\n'.join(f'{item["source"]}\n  -> {item["destination"]}' for item in manifest))
        if request.tool in {'desktop.close_app', 'desktop.close_current_window'}:
            args = request.arguments
            msg.setText(f"Close {args.get('name')} normally?\n\nWindow: {args.get('expected_title', '')}\n"
                        f"Process: {args.get('process_id')} / window: {args.get('window_id')}\n\n"
                        "The app can show its unsaved-work prompt. Aeris will not force-terminate it.")
        elif request.tool == "desktop.type_text":
            args = request.arguments
            msg.setText(f"Type into {args.get('expected_title', '')}?\n\n"
                        f"Application: {args.get('process_name', '')}\n"
                        f"Window: {args.get('window_id')} / focused control: {args.get('focus_window_id')}\n\n"
                        "Approval restores focus to this selected window. Aeris stops if the window or focused control changes. "
                        "Open Details to review the exact text. Input delivery cannot prove the app accepted the text.")
            msg.setDetailedText(args.get("text", ""))
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        if request.tool == "desktop.type_text":
            msg.button(QMessageBox.Yes).setText("Type into this window")
        
        # In a real app, you might want custom dialogs for emails vs downloads.
        # This uses a simple Yes/No.
        self.worker.permission_invalidated.connect(msg.reject)
        try:
            ret = msg.exec()
        finally:
            self.worker.permission_invalidated.disconnect(msg.reject)
        allowed = ret == QMessageBox.Yes
        if allowed and request.tool == "desktop.type_text":
            token = self.worker.current_token
            allowed = bool(token and not token.is_cancelled and not self._closing
                           and request.request_id == self.worker._pending_request_id
                           and self.assistant._desktop.restore_typing_target(request.arguments, token=token))
            if not allowed:
                self.dashboard.chat_history.addItem("Aeris: Typing target could not be restored safely. Select the window/control again; no text was sent.")
        self.worker.provide_permission(allowed, request.request_id)


def launch_desktop(assistant: AerisAssistant) -> int:
    from .hotkeys import GlobalHotkeys
    from .single_instance import InstanceServer
    app = QApplication(sys.argv)
    window = AerisMainWindow(assistant)
    window._hotkeys = GlobalHotkeys(app, window.recover_views, window.stop_current_task, window.request_push_to_talk)
    window.instance_server = InstanceServer(window.recover_views, window)
    if window.view_preferences.values['view'] == 'companion':
        window.show_companion()
    else:
        window.show()
    return app.exec()
