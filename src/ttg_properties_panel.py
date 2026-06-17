#!/usr/bin/env python3
"""Editable properties panel for TTG Creative Studio."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDoubleSpinBox, QFormLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QWidget

from ttg_project_schema import Layer


class PropertiesPanel(QWidget):
    propertyChanged = pyqtSignal(str, object)

    def __init__(self) -> None:
        super().__init__()
        self.layer: Layer | None = None
        self.layout = QFormLayout(self)
        self.layer_name = QLineEdit()
        self.text = QLineEdit()
        self.x = QDoubleSpinBox(); self.x.setRange(-10000, 10000)
        self.y = QDoubleSpinBox(); self.y.setRange(-10000, 10000)
        self.scale = QDoubleSpinBox(); self.scale.setRange(0.01, 100); self.scale.setSingleStep(0.05)
        self.rotation = QDoubleSpinBox(); self.rotation.setRange(-3600, 3600)
        self.opacity = QDoubleSpinBox(); self.opacity.setRange(0, 1); self.opacity.setSingleStep(0.05)
        self.size = QSpinBox(); self.size.setRange(1, 1000)
        self.color = QLineEdit()
        self.fill = QLineEdit()
        self.apply_button = QPushButton("Apply Properties")
        self.layout.addRow(QLabel("Layer"))
        self.layout.addRow("Name", self.layer_name)
        self.layout.addRow("Text", self.text)
        self.layout.addRow("X", self.x)
        self.layout.addRow("Y", self.y)
        self.layout.addRow("Scale", self.scale)
        self.layout.addRow("Rotation", self.rotation)
        self.layout.addRow("Opacity", self.opacity)
        self.layout.addRow("Size", self.size)
        self.layout.addRow("Color", self.color)
        self.layout.addRow("Fill", self.fill)
        self.layout.addRow(self.apply_button)
        self.apply_button.clicked.connect(self.emit_changes)

    def set_layer(self, layer: Layer | None) -> None:
        self.layer = layer
        enabled = layer is not None
        for widget in [self.layer_name, self.text, self.x, self.y, self.scale, self.rotation, self.opacity, self.size, self.color, self.fill, self.apply_button]:
            widget.setEnabled(enabled)
        if layer is None:
            return
        self.layer_name.setText(layer.name)
        self.text.setText(str(layer.properties.get("text", "")))
        self.x.setValue(layer.transform.x)
        self.y.setValue(layer.transform.y)
        self.scale.setValue(layer.transform.scale_x)
        self.rotation.setValue(layer.transform.rotation_z)
        self.opacity.setValue(layer.transform.opacity)
        self.size.setValue(int(layer.properties.get("size", 72)))
        self.color.setText(str(layer.properties.get("color", "#F7FAFF")))
        self.fill.setText(str(layer.properties.get("fill", "#00E5FF")))

    def emit_changes(self) -> None:
        if self.layer is None:
            return
        self.propertyChanged.emit("name", self.layer_name.text())
        self.propertyChanged.emit("text", self.text.text())
        self.propertyChanged.emit("position", (self.x.value(), self.y.value()))
        self.propertyChanged.emit("scale", self.scale.value())
        self.propertyChanged.emit("rotation", self.rotation.value())
        self.propertyChanged.emit("opacity", self.opacity.value())
        self.propertyChanged.emit("size", self.size.value())
        self.propertyChanged.emit("color", self.color.text())
        self.propertyChanged.emit("fill", self.fill.text())
