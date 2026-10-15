"""Interactive white-on-black brush mask creator for native image layers."""
from __future__ import annotations

import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout,
)

from ttg_image_lab import read_image, selected_mask


class PaintSurface(QLabel):
    def __init__(self, source: Image.Image) -> None:
        super().__init__()
        self.source = source
        self.setMouseTracking(True)
        self.brush = 32
        self.points: list[list[tuple[int,int]]] = []
        self.current: list[tuple[int,int]] | None = None
        self.setMinimumSize(320, 300)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.refresh()

    def _point(self, pos) -> tuple[int,int]:
        x = round(pos.x()*self.source.width/max(1,self.width()))
        y = round(pos.y()*self.source.height/max(1,self.height()))
        return (max(0,min(self.source.width-1,x)),
                max(0,min(self.source.height-1,y)))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.current = [self._point(event.position().toPoint())]
            self.points.append(self.current)
            self.refresh()

    def mouseMoveEvent(self, event) -> None:
        if self.current is not None:
            self.current.append(self._point(event.position().toPoint()))
            self.refresh()

    def mouseReleaseEvent(self, event) -> None:
        self.current = None

    def mask(self) -> Image.Image:
        return selected_mask(
            self.source.size,
            strokes=[(points, self.brush) for points in self.points],
        ) if self.points else Image.new("L", self.source.size, 0)

    def refresh(self) -> None:
        image = self.source.convert("RGB").resize((max(1,self.width()),max(1,self.height())))
        mask = self.mask().resize(image.size, Image.Resampling.LANCZOS)
        overlay = Image.new("RGB", image.size, "#e35a7a")
        image = Image.composite(
            Image.blend(image,overlay,.55),image,mask
        )
        data = image.tobytes()
        qimage = QImage(data,image.width,image.height,3*image.width,QImage.Format.Format_RGB888)
        self.setPixmap(QPixmap.fromImage(qimage.copy()))


class MaskPainterDialog(QDialog):
    def __init__(self, source_path: Path, parent=None) -> None:
        super().__init__(parent)
        image = read_image(source_path)
        self.setWindowTitle("Brush selection mask · TTG Creative Studio")
        self.resize(660, 640)
        self.surface = PaintSurface(image)
        main = QVBoxLayout(self)
        main.addWidget(QLabel("Paint the region to KEEP visible. Pink strokes mark your selection."))
        main.addWidget(self.surface, 1)
        row = QHBoxLayout()
        row.addWidget(QLabel("Brush size"))
        brush = QSlider(Qt.Orientation.Horizontal)
        brush.setRange(4,256)
        brush.setValue(32)
        brush.valueChanged.connect(lambda size: setattr(self.surface, "brush", size))
        row.addWidget(brush,1)
        undo = QPushButton("Undo Stroke")
        undo.clicked.connect(self._undo)
        row.addWidget(undo)
        clear = QPushButton("Clear")
        clear.clicked.connect(self._clear)
        row.addWidget(clear)
        main.addLayout(row)
        done = QPushButton("Apply Editable Layer Mask")
        done.clicked.connect(self.accept)
        main.addWidget(done)

    def _undo(self) -> None:
        if self.surface.points:
            self.surface.points.pop()
            self.surface.refresh()

    def _clear(self) -> None:
        self.surface.points.clear()
        self.surface.refresh()

    def mask(self) -> Image.Image:
        return self.surface.mask()
