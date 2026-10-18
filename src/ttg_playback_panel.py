#!/usr/bin/env python3
"""Timeline playback preview panel."""

from __future__ import annotations

from pathlib import Path
from io import BytesIO

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QWidget

from ttg_canvas_engine import RenderContext
from ttg_motion_exporter import MotionExporter
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
        if self.time >= self.project.canvas.duration:
            self.time = 0.0
        self.seek(self.time)

    def seek(self, seconds: float) -> None:
        if self.project is None:
            return
        self.time = max(0.0, min(self.project.canvas.duration-0.0001, seconds))
        try:
            image = MotionExporter(RenderContext(self.project_root)).render_frame(
                self.project, self.time
            )
            data = BytesIO()
            image.save(data, format="PNG")
            pix = QPixmap()
            if not pix.loadFromData(data.getvalue(), "PNG"):
                raise RuntimeError("Could not display rendered timeline frame")
            self.label.setPixmap(pix.scaled(
                self.label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        except Exception as exc:
            self.stop_playback()
            self.label.setText(f"Playback unavailable: {exc}")
