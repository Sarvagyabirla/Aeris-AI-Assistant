"""Connected reminder controls; storage reads run off the Qt event loop."""
from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ReminderReadWorker(QThread):
    snapshot = Signal(object, object, str)

    def __init__(self, store, parent):
        super().__init__(parent)
        self.store = store

    def run(self):
        try:
            self.snapshot.emit(self.store.list_pending()[:100], self.store.list_recent(30), "")
        except Exception:
            self.snapshot.emit([], [], "Reminder storage unavailable. Check diagnostics and retry.")


class RemindersView(QWidget):
    reminder_due = Signal(object)
    notification = Signal()

    def __init__(self, assistant, worker, parent=None):
        super().__init__(parent)
        self.assistant, self.worker = assistant, worker
        self._store = None
        self._reader = None
        self._stopped = False
        self._callback = self.reminder_due.emit
        layout = QVBoxLayout(self)
        self.status = QLabel("Reminders notify here while Aeris runs in LIVE mode. Emergency Stop pauses delivery.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        form = QFormLayout()
        self.message = QLineEdit()
        self.message.setMaxLength(500)
        self.message.setPlaceholderText("Drink water")
        self.when = QLineEdit("in 15 minutes")
        self.when.setMaxLength(200)
        self.when.setPlaceholderText("tomorrow at 9am, or ISO datetime with offset")
        self.recurrence = QComboBox()
        self.recurrence.addItems(["Once", "Daily", "Weekly"])
        form.addRow("Remind me to", self.message)
        form.addRow("When", self.when)
        form.addRow("Repeat", self.recurrence)
        layout.addLayout(form)
        self.create_btn = QPushButton("Set reminder")
        self.create_btn.clicked.connect(self.create)
        layout.addWidget(self.create_btn)
        self.records = QListWidget()
        self.records.setWordWrap(True)
        layout.addWidget(self.records)
        controls = QHBoxLayout()
        for label, callback in (("Refresh", self.refresh), ("Snooze selected 10 min", self.snooze), ("Cancel selected", self.cancel)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addLayout(controls)
        self.reminder_due.connect(self.on_due)
        self.worker.response_ready.connect(lambda *_: self.refresh())
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    @property
    def reading(self):
        return self._reader is not None and self._reader.isRunning()

    def _bind(self):
        store = self.assistant.reminder_store
        if store is not self._store:
            if self._store is not None:
                self._store.off_reminder(self._callback)
            self._store = store
            store.on_reminder(self._callback)
            store.start()

    @Slot()
    def refresh(self):
        if self._stopped or self.reading:
            return
        self._bind()
        if self._reader is not None:
            self._reader.deleteLater()
        self._reader = ReminderReadWorker(self._store, self)
        self._reader.snapshot.connect(self.show_records)
        self._reader.start()

    @Slot(object, object, str)
    def show_records(self, pending, recent, error):
        if self._stopped:
            return
        selected = self.selected_id()
        self.records.clear()
        zone = self.assistant.reminder_store.timezone
        from datetime import datetime
        for record in pending + recent:
            state = "Overdue" if record.get("overdue") else "Due" if record.get("fired_at") else "Pending"
            if record.get("cancelled"):
                state = "Cancelled"
            try:
                time = datetime.fromisoformat(record.get("snoozed_until") or record["fire_at"]).astimezone(zone).strftime("%d %b %H:%M")
            except (TypeError, ValueError):
                time = "Invalid saved time"
            item = QListWidgetItem(f"{state} | {time} | {record['message']}")
            item.setData(Qt.UserRole, record["id"])
            self.records.addItem(item)
            if record["id"] == selected:
                self.records.setCurrentItem(item)
        self.status.setText(error or f"Timezone: {self.assistant.config.timezone_name}. Delivery {'paused (simulation or Emergency Stop)' if not self._store.enabled() else 'active while Aeris is running'}. Closed-app delivery is unavailable.")

    def selected_id(self):
        item = self.records.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _send(self, command):
        if not self.worker.process_command(command):
            self.status.setText("Aeris is busy. Wait for the current task or press Stop, then retry.")

    @Slot()
    def create(self):
        if not self.message.text().strip() or not self.when.text().strip():
            self.status.setText("Enter a reminder and a schedule.")
            return
        repeat = "" if self.recurrence.currentIndex() == 0 else " " + self.recurrence.currentText().lower()
        self._send(f"remind me{repeat} {self.when.text().strip()} to {self.message.text().strip()}")

    @Slot()
    def snooze(self):
        if self.selected_id():
            self._send(f"snooze reminder {self.selected_id()} for 10 minutes")

    @Slot()
    def cancel(self):
        if self.selected_id():
            self._send(f"cancel reminder {self.selected_id()}")

    @Slot(object)
    def on_due(self, _record):
        if not self._stopped and self._store.enabled():
            # No private reminder text enters speech or generic notifications.
            self.notification.emit()
            self.refresh()

    def stop(self):
        self._stopped = True
        self.timer.stop()
        if self._store is not None:
            self._store.off_reminder(self._callback)
