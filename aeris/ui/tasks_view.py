"""Review and run bounded typed workflows, inspect receipts and request Undo."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..routines import ROUTINE_TOOLS, scope_fingerprint
from ..tasks import TaskPlan


class TasksView(QWidget):
    def __init__(self, assistant, worker, parent=None):
        super().__init__(parent)
        self.assistant, self.worker = assistant, worker
        layout = QVBoxLayout(self)
        explanation = QLabel('Reviewed routines run from one text or voice command: “run routine study mode”.\nOnly bounded local steps are supported; mail, installs, shell macros and automatic triggers are excluded. Stop remains available in either view.')
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.routines = QListWidget()
        self.routines.setMaximumHeight(100)
        self.routines.itemClicked.connect(self.select_routine)
        layout.addWidget(self.routines)
        self.name = QLineEdit()
        self.name.setPlaceholderText('Routine name')
        self.commands = QTextEdit()
        self.commands.setPlaceholderText('One supported command per line.\nopen notepad\nset volume to 35\nremind me in 25 minutes to take a study break')
        self.commands.setMaximumHeight(120)
        layout.addWidget(self.name)
        layout.addWidget(self.commands)
        controls = QHBoxLayout()
        for label, callback in [('Study template', self.study_template), ('Review & save routine', self.save_routine),
                                ('Run selected', self.run_selected), ('Disable selected', self.disable_selected), ('Refresh', self.refresh)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addLayout(controls)
        self.status = QLabel('Saving a routine is an explicit review. It never records your general activity.')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)
        layout.addWidget(QLabel('Recent tasks · interrupted work is retained for review and never replayed'))
        self.history = QListWidget()
        self.history.setWordWrap(True)
        layout.addWidget(self.history, 1)
        layout.addWidget(QLabel('Document organization batches'))
        self.batches = QListWidget()
        self.batches.setMaximumHeight(80)
        layout.addWidget(self.batches)
        batch_controls = QHBoxLayout()
        from PySide6.QtWidgets import QFileDialog
        organize = QPushButton('Choose folder & review organization')
        def choose():
            path = QFileDialog.getExistingDirectory(self, 'Select an allowed disposable or working folder')
            if path:
                self.dispatch('organize documents in ' + path)
        organize.clicked.connect(choose)
        undo = QPushButton('Review Undo for selected batch')
        undo.clicked.connect(self.undo_selected)
        batch_controls.addWidget(organize)
        batch_controls.addWidget(undo)
        layout.addLayout(batch_controls)
        worker.turn_completed.connect(lambda _: self.refresh())
        self.refresh()

    def study_template(self):
        self.name.setText('study mode')
        self.commands.setPlainText('open notepad\nset volume to 35\nremind me in 25 minutes to take a study break')

    def select_routine(self, item):
        self.name.setText(item.data(Qt.UserRole))

    def save_routine(self):
        try:
            actions = []
            commands = self.commands.toPlainText().strip().splitlines()
            if not 1 <= len(commands) <= 12:
                raise ValueError('Use one to twelve direct commands.')
            for command in commands:
                plan = self.assistant.router.route(command)
                if not plan or not plan.actions or any(action.tool not in ROUTINE_TOOLS for action in plan.actions):
                    raise ValueError('One command is unsupported. Use local apps, folders, volume, brightness, health or reminders.')
                actions.extend(plan.actions)
            task = TaskPlan.from_actions(actions)
            task.preflight(self.assistant.registry)
            name = self.name.text().strip()
            preview = '\n'.join(f'{index}. {action.preview()}' for index, action in enumerate(actions, 1))
            message = QMessageBox(self)
            message.setWindowTitle('Review bounded routine')
            message.setTextFormat(Qt.PlainText)
            message.setText(f'Save “{name}” for explicit future runs?\n\n{preview}\n\nCurrent folders, app catalog and live/simulation mode are bound to this review. Sensitive actions keep their normal approvals. No automatic trigger is enabled.')
            message.setStandardButtons(QMessageBox.Save | QMessageBox.Cancel)
            message.setDefaultButton(QMessageBox.Cancel)
            if message.exec() != QMessageBox.Save:
                return
            self.assistant.routine_store.save_reviewed(name, task, scope_fingerprint(self.assistant.config))
            self.status.setText('Saved. Say or type: run routine ' + name)
            self.refresh()
        except (ValueError, OSError) as exc:
            self.status.setText(str(exc))

    def dispatch(self, command):
        if not self.worker.process_command(command):
            self.status.setText('A task is active. Finish it or press Stop before starting this workflow.')

    def run_selected(self):
        item = self.routines.currentItem()
        if item:
            self.dispatch('run routine ' + item.data(Qt.UserRole))

    def disable_selected(self):
        item = self.routines.currentItem()
        if item:
            self.assistant.routine_store.disable(item.data(Qt.UserRole))
            self.refresh()

    def undo_selected(self):
        item = self.batches.currentItem()
        if item:
            self.dispatch('undo organization ' + item.data(Qt.UserRole))

    def refresh(self):
        current = self.routines.currentItem()
        selected_name = current.data(Qt.UserRole) if current else None
        self.routines.clear()
        for name, enabled, status, _ in self.assistant.routine_store.records():
            item = QListWidgetItem(f'{name} · {"enabled" if enabled else "disabled"} · {status or "not run"}')
            item.setData(Qt.UserRole, name)
            self.routines.addItem(item)
            if name == selected_name:
                self.routines.setCurrentItem(item)
        self.history.clear()
        for task in self.assistant.task_journal.recent():
            steps = ', '.join(f'{item["tool"]}: {item["status"]}' for item in task['steps'])
            self.history.addItem(task['status'] + ' · ' + steps)
        self.batches.clear()
        for batch_id, status in self.assistant._organization.recent():
            item = QListWidgetItem(f'{batch_id} · {status}')
            item.setData(Qt.UserRole, batch_id)
            self.batches.addItem(item)
