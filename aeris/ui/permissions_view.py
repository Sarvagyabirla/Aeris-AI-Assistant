"""User-selected scopes, including any accessible drive; no automatic indexing."""
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..access import CAPABILITY_CATEGORIES


class PermissionsView(QWidget):
    def __init__(self, assistant, worker, parent=None):
        super().__init__(parent)
        self.assistant, self.worker = assistant, worker
        self.apply_worker = None
        self._pending_grant = None
        layout = QVBoxLayout(self)
        intro = QLabel('PC-wide access uses explicitly selected folders or drive roots under your normal Windows rights.\nA grant allows relevant requested local work. It never indexes the whole drive or grants cloud sharing. Credential stores, security data, other users’ folders and .git internals stay excluded.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.categories = {}
        for key, label in CAPABILITY_CATEGORIES.items():
            control = QCheckBox(label)
            control.setChecked(key not in assistant.permissions.profile.disabled)
            control.toggled.connect(lambda checked, key=key: self.set_category(key, checked))
            self.categories[key] = control
            layout.addWidget(control)
        layout.addWidget(QLabel('Granted local file / project scopes'))
        self.roots = QListWidget()
        layout.addWidget(self.roots)
        controls = QHBoxLayout()
        grant = QPushButton('Grant folder or drive…')
        grant.clicked.connect(self.choose_root)
        revoke = QPushButton('Revoke selected scope')
        revoke.clicked.connect(self.revoke_selected)
        controls.addWidget(grant)
        controls.addWidget(revoke)
        layout.addLayout(controls)
        self.status = QLabel('')
        self.status.setTextFormat(Qt.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        support = QLabel('Connected controls: configured app launch; selected-window Unicode typing and graceful close; volume/mute and display brightness readback; local files, document batches and reminders.\n\nBrowser operations use the managed adapter; account, screenshot/cloud sharing, sends and installs keep separate approvals. UI Automation and a guarded visual pointer adapter remain unfinished. An app icon indicates launch support only.\n\nDownloads use the separately configured Downloads destination. Broad folder grants do not authorize credential entry, UAC bypass, installations or sending messages.')
        support.setWordWrap(True)
        layout.addWidget(support)
        self.refresh()

    def refresh(self):
        self.roots.clear()
        for root in self.assistant.scope_policy.roots:
            self.roots.addItem(str(root))
        denied = ', '.join(str(root) for root in self.assistant.scope_policy.revoked)
        self.status.setText(self.assistant.scope_policy.error or self.assistant.permissions.profile.error or ('Revoked: ' + denied if denied else 'No revoked scopes.'))

    def set_category(self, category, enabled):
        self.worker.cancel_current()
        self.assistant.permissions.clear_session()
        try:
            self.assistant.permissions.profile.set_enabled(category, enabled)
        except OSError:
            self.assistant.permissions.stop()
            self.status.setText('Access change could not be saved. Emergency Stop is latched; repair writable data storage before resuming.')
            return
        self.refresh()

    def choose_root(self):
        if self.worker.current_token or (self.apply_worker and self.apply_worker.isRunning()):
            self.status.setText('Finish the current task before granting a new scope.')
            return
        selected = QFileDialog.getExistingDirectory(self, 'Grant a folder or accessible drive root')
        if not selected:
            return
        root = Path(selected).resolve()
        message = QMessageBox(self)
        message.setTextFormat(Qt.PlainText)
        message.setWindowTitle('Grant local scope')
        message.setText(f'Allow requested local file and project work in:\n{root}\n\nNo automatic scan or cloud upload. Protected data remains excluded. You can revoke this scope here.')
        message.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        message.setDefaultButton(QMessageBox.No)
        if message.exec() != QMessageBox.Yes:
            return
        self._pending_grant = root
        roots = tuple(dict.fromkeys((*self.assistant.scope_policy.roots, root)))
        self.apply_roots(roots)

    def revoke_selected(self):
        item = self.roots.currentItem()
        if not item:
            return
        root = Path(item.text())
        self.worker.cancel_current()
        self.assistant.permissions.clear_session()
        try:
            self.assistant.scope_policy.revoke(root)
        except OSError:
            self.status.setText('Revoked in this process, but persistence failed. Keep Aeris stopped and repair writable data storage before restart.')
            self.assistant.permissions.stop()
            return
        self.refresh()
        self.status.setText('Scope revoked immediately. Waiting for the current task to settle before saving Settings.')
        def persist():
            if self.window()._closing:
                return
            if self.worker.current_token:
                QTimer.singleShot(50, persist)
                return
            self.apply_roots(self.assistant.scope_policy.roots)
        persist()

    def apply_roots(self, roots):
        from .desktop import SettingsApplyWorker
        if self.window()._closing:
            return
        if self.apply_worker and self.apply_worker.isRunning():
            QTimer.singleShot(50, lambda: self.apply_roots(roots))
            return
        self.apply_worker = SettingsApplyWorker(self.assistant, self.assistant.config.with_overrides(allowed_paths=roots), self)
        self.apply_worker.completed.connect(self.applied)
        self.apply_worker.start()

    def applied(self, success, message):
        if success and self._pending_grant:
            try:
                self.assistant.scope_policy.allow(self._pending_grant)
            except OSError:
                success, message = False, 'Settings saved, but explicit regrant could not be persisted. Revocation remains active.'
        self._pending_grant = None
        self.refresh()
        self.status.setText(message)
