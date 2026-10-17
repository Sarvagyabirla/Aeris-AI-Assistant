"""Original lightweight vector character; rendering owns no assistant effects."""
import math
import time

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget


class PresenceModel(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = 'idle'
        self.detail = 'Ready for a task'
        self.audio = 'disabled'
        self.task = None

    def update_state(self, phase, detail=''):
        if (phase, detail) != (self.phase, self.detail):
            self.phase, self.detail = phase, detail
            self.changed.emit()


COLORS = {'idle': '#56d9ed', 'listening': '#71f3c4', 'thinking': '#6baeff',
          'awaiting-permission': '#ffcc75', 'executing': '#56d9ed', 'speaking': '#bbadff',
          'interrupted': '#ffb16f', 'offline': '#8da4b5', 'error': '#ff697d'}


class CharacterWidget(QWidget):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.reduced_motion = False
        self._started = time.monotonic()
        self.setMinimumSize(160, 220)
        self.setAccessibleName('Aeris animated humanoid; state follows the assistant')
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(33)  # maximum 30 fps; no hidden rendering
        self.animation_timer.timeout.connect(self.update)
        model.changed.connect(self.update)

    def set_reduced_motion(self, value):
        self.reduced_motion = bool(value)
        self.sync_animation()
        self.update()

    def sync_animation(self):
        if self.isVisible() and not self.window().isMinimized() and not self.reduced_motion:
            self.animation_timer.start()
        else:
            self.animation_timer.stop()

    def showEvent(self, event):
        super().showEvent(event)
        self.sync_animation()

    def hideEvent(self, event):
        self.animation_timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        scale = min(self.width() / 260, self.height() / 330)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(scale, scale)
        t = 0 if self.reduced_motion else time.monotonic() - self._started
        color = QColor(COLORS.get(self.model.phase, COLORS['idle']))
        # Quiet vertical hologram grid; no invented telemetry.
        painter.setPen(QPen(QColor('#1b303a'), 1))
        for x in range(-120, 121, 24):
            painter.drawLine(x, -145, x, 140)
        for y in range(-145, 141, 24):
            painter.drawLine(-120, y, 120, y)
        bob = math.sin(t * 1.5) * 2
        painter.translate(0, bob)
        fill = QLinearGradient(0, -120, 0, 130)
        fill.setColorAt(0, QColor('#173d4b'))
        fill.setColorAt(1, QColor('#0d1b26'))
        painter.setPen(QPen(color, 1.5))
        painter.setBrush(fill)
        # Articulated shoulders, forearms, torso and pelvis form a character.
        def plate(points):
            painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in points]))
        reach = math.sin(t * 1.1) * (4 if self.model.phase == 'executing' else 1.5)
        plate([(-30, -29), (-65, -18), (-76, 24), (-58, 29), (-45, 3)])
        plate([(30, -29), (65, -18), (76, 24), (58, 29), (45, 3)])
        plate([(-76, 30), (-60, 34), (-56 + reach, 79), (-70 + reach, 82), (-84, 53)])
        plate([(76, 30), (60, 34), (56 - reach, 79), (70 - reach, 82), (84, 53)])
        plate([(-41, -22), (-23, -36), (23, -36), (41, -22), (30, 56), (0, 75), (-30, 56)])
        plate([(-28, 63), (0, 82), (28, 63), (33, 90), (18, 107), (-18, 107), (-33, 90)])
        plate([(-29, 98), (-6, 106), (-11, 142), (-33, 142)])
        plate([(29, 98), (6, 106), (11, 142), (33, 142)])
        painter.drawLine(-29, -9, 0, 10)
        painter.drawLine(29, -9, 0, 10)
        painter.drawLine(-24, 30, 24, 30)
        # Asymmetric diamond core, distinct from a loading indicator.
        plate([(0, -9), (10, 6), (0, 20), (-7, 6)])
        painter.save()
        gaze = math.sin(t * 0.65) * (5 if self.model.phase in {'idle', 'offline'} else 2)
        painter.translate(gaze, -71)
        painter.rotate(math.sin(t * 0.8) * 3)
        plate([(-25, -40), (-36, -22), (-31, 19), (-14, 32), (14, 32), (31, 19), (36, -22), (25, -40)])
        painter.drawLine(-23, -29, 21, -29)
        painter.drawLine(-29, -16, -16, -9)
        painter.drawLine(29, -16, 16, -9)
        painter.setBrush(color)
        blink = 1 if self.reduced_motion or t % 6 > 0.16 else 0.15
        painter.drawRoundedRect(QRectF(-23 + gaze * .3, -7, 16, 4 * blink), 2, 2)
        painter.drawRoundedRect(QRectF(7 + gaze * .3, -7, 16, 4 * blink), 2, 2)
        # State-driven speech motion, not measured phoneme/lip synchronization.
        mouth = 2 + (abs(math.sin(t * 14)) * 6 if self.model.phase == 'speaking' else 0)
        painter.drawRoundedRect(QRectF(-9, 17, 18, mouth), 2, 2)
        painter.restore()
        painter.setPen(QPen(color, 1))
        painter.setFont(QFont('Segoe UI', 8))
        painter.drawText(QRectF(-120, -163, 240, 18), Qt.AlignCenter, 'A E R I S  /  LOCAL PRESENCE')
        painter.end()
