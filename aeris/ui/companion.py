"""Presentation preferences and a non-activating, recoverable companion view."""
import json

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QSizeGrip, QVBoxLayout, QWidget

from ..config import _atomic_settings
from .presence import CharacterWidget


class ViewPreferences:
    defaults = {'view': 'dashboard', 'always_on_top': True, 'reduced_motion': False,
                'close_to_tray': False, 'microphone_muted': False, 'geometry': [50, 50, 280, 460]}

    def __init__(self, path):
        self.path = path
        self.values = dict(self.defaults)
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(payload, dict):
                self.values['microphone_muted'] = True
                return
            if 'microphone_muted' in payload and type(payload['microphone_muted']) is not bool:
                self.values['microphone_muted'] = True
            for key in ('always_on_top', 'reduced_motion', 'close_to_tray', 'microphone_muted'):
                if type(payload.get(key)) is bool:
                    self.values[key] = payload[key]
            if payload.get('view') in {'dashboard', 'companion'}:
                self.values['view'] = payload['view']
            geometry = payload.get('geometry')
            if isinstance(geometry, list) and len(geometry) == 4 and all(type(n) is int and abs(n) <= 50000 for n in geometry) and 240 <= geometry[2] <= 900 and 360 <= geometry[3] <= 1200:
                self.values['geometry'] = geometry
        except (OSError, ValueError):
            if path.exists():
                self.values['microphone_muted'] = True

    def save(self, **changes):
        updated = dict(self.values, **changes)
        _atomic_settings(self.path, updated)
        self.values = updated


class CompanionWindow(QWidget):
    dashboard_requested = Signal()
    hide_requested = Signal()

    def __init__(self, model, worker, preferences, parent=None):
        super().__init__(parent, Qt.Tool | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.model, self.worker, self.preferences = model, worker, preferences
        self.click_through = False
        self.recovery_available = lambda: False
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowTitle('Aeris companion')
        self.setMinimumSize(240, 360)
        self.setMaximumSize(900, 1200)
        self.setGeometry(QRect(*preferences.values['geometry']))
        self.setWindowFlag(Qt.WindowStaysOnTopHint, preferences.values['always_on_top'])
        layout = QVBoxLayout(self)
        self.avatar = CharacterWidget(model)
        self.avatar.set_reduced_motion(preferences.values['reduced_motion'])
        layout.addWidget(self.avatar, 1)
        self.state_label = QLabel()
        self.state_label.setTextFormat(Qt.PlainText)
        self.state_label.setWordWrap(True)
        layout.addWidget(self.state_label)
        controls = QHBoxLayout()
        self.mic_btn = QPushButton('Mic / PTT')
        self.stop_btn = QPushButton('Stop')
        self.stop_btn.setStyleSheet('background:#8f3344')
        dashboard = QPushButton('Dashboard')
        self.stop_btn.clicked.connect(worker.cancel_current)
        dashboard.clicked.connect(self.dashboard_requested)
        for button in (self.mic_btn, self.stop_btn, dashboard):
            button.setFocusPolicy(Qt.NoFocus)
            controls.addWidget(button)
        layout.addLayout(controls)
        self.mute_mic_btn = QPushButton('Mute microphone')
        self.mute_mic_btn.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.mute_mic_btn)
        options = QHBoxLayout()
        self.top_check = QCheckBox('On top')
        self.top_check.setChecked(preferences.values['always_on_top'])
        self.top_check.toggled.connect(self.set_on_top)
        self.through_check = QCheckBox('Click through')
        self.through_check.setToolTip('Requires tray or registered Ctrl+Alt+A recovery. Never restored automatically.')
        self.through_check.toggled.connect(self.set_click_through)
        hide = QPushButton('Hide')
        hide.clicked.connect(self.hide_requested)
        for widget in (self.top_check, self.through_check, hide):
            widget.setFocusPolicy(Qt.NoFocus)
            options.addWidget(widget)
        layout.addLayout(options)
        layout.addWidget(QSizeGrip(self), 0, Qt.AlignRight)
        model.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        mode = 'SIMULATION' if self.worker.assistant.registry.dry_run else 'LIVE'
        self.state_label.setText(f'{mode} · {self.model.phase.replace("-", " ").title()}\n{self.model.detail}\nAudio: {self.model.audio}')

    def _change_flag(self, flag, value):
        visible, geometry = self.isVisible(), self.geometry()
        self.setWindowFlag(flag, value)
        self.setGeometry(geometry)
        if visible:
            self.show()

    def set_on_top(self, value):
        self._change_flag(Qt.WindowStaysOnTopHint, value)
        try:
            self.preferences.save(always_on_top=value)
        except OSError:
            self.state_label.setText('View preference could not be saved; current view remains usable.')

    def set_click_through(self, value):
        if value and not self.recovery_available():
            self.through_check.blockSignals(True)
            self.through_check.setChecked(False)
            self.through_check.blockSignals(False)
            self.state_label.setText('Click through requires a working tray or global recovery shortcut.')
            return False
        self.click_through = bool(value)
        self.through_check.blockSignals(True)
        self.through_check.setChecked(value)
        self.through_check.blockSignals(False)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, value)
        self._change_flag(Qt.WindowTransparentForInput, value)
        return True

    def fit_to_screens(self, rectangles):
        if not rectangles:
            return
        current = self.geometry()
        target = next((rect for rect in rectangles if rect.contains(current.center())), rectangles[0])
        width, height = min(current.width(), target.width()), min(current.height(), target.height())
        left = max(target.left(), min(current.left(), target.right() - width + 1))
        top = max(target.top(), min(current.top(), target.bottom() - height + 1))
        self.setGeometry(left, top, width, height)

    def closeEvent(self, event):
        event.ignore()
        self.dashboard_requested.emit()  # Closing an overlay never loses the controller.

    def changeEvent(self, event):
        super().changeEvent(event)
        if hasattr(self, 'avatar'):
            self.avatar.sync_animation()
