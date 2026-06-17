#!/usr/bin/env python3
"""Interactive canvas widget: click select, drag, snap-grid and bounds overlay."""

from __future__ import annotations

from pathlib import Path
import tempfile

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QLabel

from ttg_canvas_selection import CanvasSelection
from ttg_export_service import ExportService
from ttg_project_schema import TTGProject


class InteractiveCanvas(QLabel):
    layerSelected = pyqtSignal(str)
    layerMoved = pyqtSignal(str, float, float)

    def __init__(self, project_root: str | Path) -> None:
        super().__init__("Canvas")
        self.project_root = Path(project_root)
        self.project: TTGProject | None = None
        self.selected_layer_id: str | None = None
        self.snap_enabled = True
        self.grid_size = 10
        self.drag_start: QPoint | None = None
        self.drag_layer_start: tuple[float, float] | None = None
        self.selector = CanvasSelection()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(640, 420)
        self.setMouseTracking(True)

    def set_project(self, project: TTGProject | None, selected_layer_id: str | None = None) -> None:
        self.project = project
        self.selected_layer_id = selected_layer_id
        self.render_preview()

    def render_preview(self) -> None:
        if self.project is None:
            self.setText("No project")
            return
        temp_dir = Path(tempfile.gettempdir()) / "ttg_interactive_canvas"
        temp_dir.mkdir(parents=True, exist_ok=True)
        path = temp_dir / "canvas.png"
        ExportService(self.project_root).export_png(self.project, path)
        self.setPixmap(QPixmap(str(path)).scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def canvas_point(self, event: QMouseEvent) -> tuple[float, float]:
        if self.project is None or self.pixmap() is None:
            return (event.position().x(), event.position().y())
        pm = self.pixmap()
        x_offset = (self.width() - pm.width()) / 2
        y_offset = (self.height() - pm.height()) / 2
        sx = self.project.canvas.width / max(1, pm.width())
        sy = self.project.canvas.height / max(1, pm.height())
        return ((event.position().x() - x_offset) * sx, (event.position().y() - y_offset) * sy)

    def snap(self, value: float) -> float:
        if not self.snap_enabled:
            return value
        return round(value / self.grid_size) * self.grid_size

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.project is None:
            return
        x, y = self.canvas_point(event)
        layer_id = self.selector.hit_test(self.project, x, y)
        if layer_id:
            self.selected_layer_id = layer_id
            self.layerSelected.emit(layer_id)
            layer = next(layer for layer in self.project.layers if layer.id == layer_id)
            self.drag_start = event.pos()
            self.drag_layer_start = (layer.transform.x, layer.transform.y)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.project is None or not self.selected_layer_id or self.drag_start is None or self.drag_layer_start is None:
            return
        pm = self.pixmap()
        if pm is None:
            return
        dx_view = event.pos().x() - self.drag_start.x()
        dy_view = event.pos().y() - self.drag_start.y()
        sx = self.project.canvas.width / max(1, pm.width())
        sy = self.project.canvas.height / max(1, pm.height())
        new_x = self.snap(self.drag_layer_start[0] + dx_view * sx)
        new_y = self.snap(self.drag_layer_start[1] + dy_view * sy)
        self.layerMoved.emit(self.selected_layer_id, new_x, new_y)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.drag_start = None
        self.drag_layer_start = None

    def paintEvent(self, event) -> None:  # noqa: ANN001
        super().paintEvent(event)
        if self.project is None or not self.selected_layer_id or self.pixmap() is None:
            return
        bounds = None
        for b in self.selector.all_bounds(self.project):
            if b.layer_id == self.selected_layer_id:
                bounds = b
                break
        if bounds is None:
            return
        pm = self.pixmap()
        x_offset = (self.width() - pm.width()) / 2
        y_offset = (self.height() - pm.height()) / 2
        sx = pm.width() / self.project.canvas.width
        sy = pm.height() / self.project.canvas.height
        painter = QPainter(self)
        pen = QPen(Qt.GlobalColor.cyan)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(int(x_offset + bounds.x * sx), int(y_offset + bounds.y * sy), int(bounds.width * sx), int(bounds.height * sy))
