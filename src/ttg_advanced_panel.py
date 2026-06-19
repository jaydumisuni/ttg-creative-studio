#!/usr/bin/env python3
"""Advanced Mode panel for Photoshop/Canva/Filmora-style controls."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QGridLayout, QLabel, QPushButton, QWidget

from ttg_advanced_presets import presets_by_group


class AdvancedModePanel(QWidget):
    effectRequested = pyqtSignal(str)
    templateRequested = pyqtSignal(str)
    previewRequested = pyqtSignal()
    presetRequested = pyqtSignal(str, str)

    def __init__(self) -> None:
        super().__init__()
        layout = QGridLayout(self)
        layout.addWidget(QLabel("Advanced Mode"), 0, 0, 1, 2)

        self.group_combo = QComboBox()
        self.preset_combo = QComboBox()
        self.apply_preset = QPushButton("Apply Preset")
        layout.addWidget(QLabel("Preset Group"), 1, 0)
        layout.addWidget(self.group_combo, 1, 1)
        layout.addWidget(QLabel("Preset"), 2, 0)
        layout.addWidget(self.preset_combo, 2, 1)
        layout.addWidget(self.apply_preset, 3, 0, 1, 2)

        self.presets = presets_by_group()
        self.group_combo.addItems(sorted(self.presets.keys()))
        self.group_combo.currentTextChanged.connect(self._refresh_presets)
        self.apply_preset.clicked.connect(self._emit_preset)
        self._refresh_presets(self.group_combo.currentText())

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
        for index, (label, command) in enumerate(buttons, start=4):
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

    def _refresh_presets(self, group: str) -> None:
        self.preset_combo.clear()
        for preset in self.presets.get(group, []):
            self.preset_combo.addItem(preset.name, preset.id)

    def _find_workspace(self):
        parent = self.parent()
        while parent is not None:
            if parent.__class__.__name__ == "CreativeWorkspace":
                return parent
            parent = parent.parent()
        return None

    def _emit_preset(self) -> None:
        group = self.group_combo.currentText()
        preset_id = self.preset_combo.currentData()
        if not preset_id:
            return
        preset_id = str(preset_id)
        workspace = self._find_workspace()
        if workspace is not None:
            try:
                from ttg_workspace_preset_bridge import apply_advanced_preset

                apply_advanced_preset(workspace, group, preset_id)
                return
            except Exception:
                # Fall back to signal emission so callers/tests can still handle it.
                pass
        self.presetRequested.emit(group, preset_id)
