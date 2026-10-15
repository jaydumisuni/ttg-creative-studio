#!/usr/bin/env python3
"""Native image editing controls and optional local-model execution for Studio."""
from __future__ import annotations

import uuid
from pathlib import Path

from PIL import Image, ImageOps
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QSpinBox, QDoubleSpinBox, QVBoxLayout,
)

from ttg_image_lab import ComfyUIBackend, apply_adjustments, read_image


class ImageJob(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, mode: str, prompt: str, checkpoint: str, url: str,
                 source: str, mask: str, output: Path,
                 brightness: float, contrast: float, saturation: float) -> None:
        super().__init__()
        self.mode, self.prompt, self.checkpoint, self.url = mode, prompt, checkpoint, url
        self.source, self.mask, self.output = source, mask, output
        self.brightness, self.contrast, self.saturation = brightness, contrast, saturation

    def run(self) -> None:
        try:
            if self.mode == "enhance":
                if not self.source:
                    raise ValueError("Select a source image for offline enhancement")
                image = apply_adjustments(
                    read_image(self.source), brightness=self.brightness,
                    contrast=self.contrast, saturation=self.saturation,
                    sharpness=1.4,
                )
            else:
                source = read_image(self.source) if self.source else None
                mask = read_image(self.mask).convert("L") if self.mask else None
                if self.mode in ("image2image", "inpaint") and source is None:
                    raise ValueError("Select the source image for the chosen AI operation")
                if self.mode == "inpaint" and mask is None:
                    raise ValueError("Choose a white-on-black inpainting mask")
                if self.mode == "generate":
                    source = None
                    mask = None
                elif self.mode == "image2image":
                    mask = None
                image = ComfyUIBackend(self.url).generate(
                    prompt=self.prompt, checkpoint=self.checkpoint,
                    input_image=source, mask=mask,
                )
            self.output.parent.mkdir(parents=True, exist_ok=True)
            image.save(self.output, "PNG")
            self.done.emit(str(self.output))
        except Exception as exc:
            self.failed.emit(str(exc))


class ImageLabDialog(QDialog):
    completed = pyqtSignal(str)

    def __init__(self, directory: Path, parent=None, source: str = "") -> None:
        super().__init__(parent)
        self.directory = directory
        self.setWindowTitle("Creative Studio · Image Lab")
        self.setMinimumWidth(570)
        self.setStyleSheet("""
            QDialog {background:#101a2b;color:#f1fcff;}
            QLabel {color:#d2e2ed;}
            QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox {
                background:#1c2d42;color:#f9fcff;border:1px solid #47637c;
                border-radius:5px;padding:6px;min-height:22px;
            }
            QPushButton {background:#25485c;color:#ffffff;border:1px solid #4d8790;
                padding:7px;border-radius:5px;}
            QPushButton:hover {background:#236f73;}
        """)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("IMAGE LAB · EDIT, GENERATE & ENHANCE"))
        layout.addWidget(QLabel(
            "Local inference requires a running ComfyUI server and installed checkpoint. "
            "Offline enhancement needs no AI."
        ))
        form = QFormLayout()
        self.mode = QComboBox()
        for label, value in [
            ("Enhance · offline", "enhance"),
            ("AI prompt → image", "generate"),
            ("AI image → image", "image2image"),
            ("AI inpaint / replace selected region", "inpaint"),
        ]:
            self.mode.addItem(label, value)
        self.prompt = QLineEdit("Premium modern product photography, studio lighting")
        self.model = QLineEdit()
        self.model.setPlaceholderText("Actual installed ComfyUI checkpoint filename")
        self.endpoint = QLineEdit("http://127.0.0.1:8188")
        self.source = QLineEdit(source)
        self.source.setPlaceholderText("Optional source image (required for editing)")
        self.mask = QLineEdit()
        self.mask.setPlaceholderText("White = region to replace; black = preserve")
        self.brightness = QDoubleSpinBox()
        self.contrast = QDoubleSpinBox()
        self.saturation = QDoubleSpinBox()
        for field in (self.brightness, self.contrast, self.saturation):
            field.setRange(0.0, 4.0)
            field.setSingleStep(.1)
            field.setValue(1.0)
        form.addRow("Operation", self.mode)
        form.addRow("Prompt", self.prompt)
        form.addRow("ComfyUI checkpoint", self.model)
        form.addRow("Local service", self.endpoint)
        self._browse_row(form, "Source image", self.source)
        self._browse_row(form, "Inpaint mask", self.mask)
        for label, widget in [("Brightness", self.brightness),
                              ("Contrast", self.contrast),
                              ("Saturation", self.saturation)]:
            form.addRow(label, widget)
        layout.addLayout(form)
        self.status = QLabel("Ready. Results become editable image layers.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.start = QPushButton("Create Editable Image")
        self.start.clicked.connect(self.start_job)
        cancel = QPushButton("Close")
        cancel.clicked.connect(self.close)
        buttons.addWidget(self.start)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self.job: ImageJob | None = None

    def _browse_row(self, form: QFormLayout, label: str, field: QLineEdit) -> None:
        from PyQt6.QtWidgets import QWidget
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        button = QPushButton("Browse")
        button.clicked.connect(lambda: self._browse(field))
        row.addWidget(field, 1)
        row.addWidget(button)
        form.addRow(label, container)

    def _browse(self, field: QLineEdit) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, "Open source image", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if name:
            field.setText(name)

    def start_job(self) -> None:
        if self.job is not None and self.job.isRunning():
            return
        name = "edited-" + uuid.uuid4().hex[:12] + ".png"
        self.job = ImageJob(
            str(self.mode.currentData()), self.prompt.text(), self.model.text(),
            self.endpoint.text(), self.source.text(), self.mask.text(),
            self.directory/name, self.brightness.value(),
            self.contrast.value(), self.saturation.value(),
        )
        self.job.done.connect(self._completed)
        self.job.failed.connect(self._failed)
        self.start.setEnabled(False)
        self.status.setText("Processing… external AI jobs may take several minutes.")
        self.job.start()

    def _completed(self, file: str) -> None:
        self.start.setEnabled(True)
        self.status.setText("Created " + Path(file).name + " — imported into Studio.")
        self.completed.emit(file)

    def _failed(self, message: str) -> None:
        self.start.setEnabled(True)
        self.status.setText("Unavailable: " + message)
        QMessageBox.warning(self, "Image Lab", message)

    def closeEvent(self, event) -> None:
        if self.job is not None and self.job.isRunning():
            QMessageBox.information(
                self, "Image Lab", "Wait for the active image job to finish before closing."
            )
            event.ignore()
            return
        super().closeEvent(event)
