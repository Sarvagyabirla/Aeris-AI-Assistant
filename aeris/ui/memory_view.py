"""Bounded, explicit local conversation-history inspection; never sends data."""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MemoryView(QWidget):
    def __init__(self, memory, parent=None):
        super().__init__(parent)
        self.memory = memory
        self.records = []
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Local conversation history — last 100 records. No cloud upload.\n"
                               "Sensitive new interactions are not stored. Project facts/reminders are not yet implemented."))
        self.list = QListWidget()
        layout.addWidget(self.list)
        buttons = QHBoxLayout()
        for label, callback in (("Inspect / refresh", self.refresh), ("Correct selected", self.correct),
                                ("Forget selected", self.forget)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        layout.addLayout(buttons)

    def refresh(self):
        self.records = self.memory.inspect(100)
        self.list.clear()
        for row in self.records:
            self.list.addItem(f"#{row['id']} | {row['role']} | {row['classification']} | {row['created_at']}\n"
                              + row['content'][:2000])

    def selected(self):
        index = self.list.currentRow()
        return self.records[index] if 0 <= index < len(self.records) else None

    def correct(self):
        row = self.selected()
        if not row:
            return
        text, accepted = QInputDialog.getMultiLineText(self, "Correct local record", "Exact replacement:", row['content'])
        if accepted:
            try:
                self.memory.correct(row['id'], text)
                self.refresh()
            except ValueError:
                QMessageBox.warning(self, "Not changed", "Replacement must contain 1–10000 characters.")

    def forget(self):
        row = self.selected()
        if row and QMessageBox.question(self, "Forget record", f"Permanently forget record #{row['id']}?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            self.memory.forget(row['id'])
            self.refresh()