#!/usr/bin/env python3
"""Timeline panel with ruler and editable keyframe summary."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPen
from PyQt6.QtWidgets import QListWidget, QVBoxLayout, QWidget

from ttg_project_schema import TTGProject


class TimelineRuler(QWidget):
    timeChanged = pyqtSignal(float)

    def __init__(self) -> None:
        super().__init__()
        self.duration = 8.0
        self.current_time = 0.0
        self.setMinimumHeight(54)

    def set_duration(self, duration: float) -> None:
        self.duration = max(0.1, duration)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        pen = QPen(Qt.GlobalColor.cyan)
        painter.setPen(pen)
        width = max(1, self.width())
        for sec in range(int(self.duration) + 1):
            x = int((sec / self.duration) * width)
            painter.drawLine(x, 0, x, 26)
            painter.drawText(x + 4, 42, f"{sec}s")
        play_x = int((self.current_time / self.duration) * width)
        painter.setPen(QPen(Qt.GlobalColor.magenta, 3))
        painter.drawLine(play_x, 0, play_x, self.height())

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        self.current_time = max(0.0, min(self.duration, (event.position().x() / max(1, self.width())) * self.duration))
        self.timeChanged.emit(self.current_time)
        self.update()


class TimelinePanel(QWidget):
    timeChanged = pyqtSignal(float)
    keyframeSelected = pyqtSignal(str, str, float)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.ruler = TimelineRuler()
        self.list = QListWidget()
        layout.addWidget(self.ruler)
        layout.addWidget(self.list)
        self.ruler.timeChanged.connect(self.timeChanged.emit)
        self.list.itemClicked.connect(self._item_clicked)

    def set_project(self, project: TTGProject | None) -> None:
        self.list.clear()
        if project is None:
            return
        self.ruler.set_duration(project.canvas.duration)
        for layer in project.layers:
            for prop, frames in layer.keyframes.items():
                for frame in frames:
                    self.list.addItem(f"{layer.id}|{prop}|{frame.time}|{layer.name} / {prop} @ {frame.time:.2f}s")

    def _item_clicked(self, item) -> None:  # noqa: ANN001
        raw = item.text().split("|", 3)
        if len(raw) >= 3:
            self.keyframeSelected.emit(raw[0], raw[1], float(raw[2]))
