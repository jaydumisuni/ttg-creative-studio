#!/usr/bin/env python3
"""Timeline playback preview panel."""

from __future__ import annotations

from pathlib import Path
import tempfile

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QWidget

from ttg_export_service import ExportService
from ttg_project_schema import TTGProject


class PlaybackPanel(QWidget):
    def __init__(self, project_root: str | Path) -> None:
        super().__init__()
        self.project_root = Path(project_root)
        self.project: TTGProject | None = None
        self.time = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.play = QPushButton("Play")
        self.stop = QPushButton("Stop")
        self.label = QLabel("Playback preview is enabled after still preview looks right.")
        controls.addWidget(self.play)
        controls.addWidget(self.stop)
        layout.addLayout(controls)
        layout.addWidget(self.label, 1)
        self.play.clicked.connect(self.start)
        self.stop.clicked.connect(self.stop_playback)

    def set_project(self, project: TTGProject | None) -> None:
        self.project = project
        self.time = 0.0

    def start(self) -> None:
        if self.project is None:
            self.label.setText("Load a project first.")
            return
        self.timer.start(int(1000 / max(1, self.project.canvas.fps)))

    def stop_playback(self) -> None:
        self.timer.stop()

    def tick(self) -> None:
        if self.project is None:
            return
        self.time += 1 / max(1, self.project.canvas.fps)
        if self.time > self.project.canvas.duration:
            self.time = 0.0
        temp = Path(tempfile.gettempdir()) / "ttg_playback_preview.png"
        # Uses current motion renderer through export service path indirectly for still preview.
        ExportService(self.project_root).export_png(self.project, temp)
        pix = QPixmap(str(temp))
        self.label.setPixmap(pix.scaled(self.label.size(), aspectRatioMode=1, transformMode=1))
