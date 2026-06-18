#!/usr/bin/env python3
"""Advanced Mode panel for Photoshop/Canva/Filmora-style controls."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QGridLayout, QLabel, QPushButton, QWidget


class AdvancedModePanel(QWidget):
    effectRequested = pyqtSignal(str)
    templateRequested = pyqtSignal(str)
    previewRequested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        layout = QGridLayout(self)
        layout.addWidget(QLabel("Advanced Mode"), 0, 0, 1, 2)
        buttons = [
            ("Glow", "effect:glow"),
            ("Stroke + Shadow", "effect:stroke_shadow"),
            ("Bevel + Extrude", "effect:bevel_extrude"),
            ("Reflection", "effect:reflection"),
            ("Gradient Chrome", "effect:gradient"),
            ("Premium Text Stack", "effect:premium_text"),
            ("Reference Intro", "template:ttg_reference_intro"),
            ("Preview Still", "preview"),
        ]
        for index, (label, command) in enumerate(buttons, start=1):
            button = QPushButton(label)
            row = (index + 1) // 2
            col = (index + 1) % 2
            layout.addWidget(button, row, col)
            if command.startswith("effect:"):
                button.clicked.connect(lambda _=False, cmd=command: self.effectRequested.emit(cmd.split(":", 1)[1]))
            elif command.startswith("template:"):
                button.clicked.connect(lambda _=False, cmd=command: self.templateRequested.emit(cmd.split(":", 1)[1]))
            else:
                button.clicked.connect(self.previewRequested.emit)
