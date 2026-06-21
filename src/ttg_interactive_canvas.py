#!/usr/bin/env python3
"""Interactive canvas widget: click select, drag, snap-grid and transform overlay."""

from __future__ import annotations

from pathlib import Path
import tempfile

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QLabel

from ttg_canvas_interaction import CanvasInteractionController, DragMode
from ttg_canvas_tools import ResizeHandle, get_layer, layer_rect
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
        self.interaction = CanvasInteractionController()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(640, 420)
        self.setMouseTracking(True)

    def set_project(self, project: TTGProject | None, selected_layer_id: str | None = None) -> None:
        self.project = project
        self.selected_layer_id = selected_layer_id
        self.interaction.set_project(project)
        if selected_layer_id:
            self.interaction.selection.select(selected_layer_id)
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

    def _project_to_view(self, x: float, y: float) -> tuple[float, float]:
        if self.project is None or self.pixmap() is None:
            return x, y
        pm = self.pixmap()
        x_offset = (self.width() - pm.width()) / 2
        y_offset = (self.height() - pm.height()) / 2
        sx = pm.width() / self.project.canvas.width
        sy = pm.height() / self.project.canvas.height
        return (x_offset + x * sx, y_offset + y * sy)

    def _view_to_project_delta(self, delta: float, axis: str) -> float:
        if self.project is None or self.pixmap() is None:
            return delta
        pm = self.pixmap()
        if axis == "x":
            return delta * self.project.canvas.width / max(1, pm.width())
        return delta * self.project.canvas.height / max(1, pm.height())

    def _handle_points(self) -> dict[ResizeHandle, tuple[float, float]]:
        if self.project is None or not self.selected_layer_id:
            return {}
        try:
            layer = get_layer(self.project, self.selected_layer_id)
        except KeyError:
            return {}
        rect = layer_rect(layer)
        x1, y1 = self._project_to_view(rect.x, rect.y)
        x2, y2 = self._project_to_view(rect.right, rect.bottom)
        cx, cy = self._project_to_view(rect.cx, rect.cy)
        return {
            ResizeHandle.TOP_LEFT: (x1, y1),
            ResizeHandle.TOP: (cx, y1),
            ResizeHandle.TOP_RIGHT: (x2, y1),
            ResizeHandle.RIGHT: (x2, cy),
            ResizeHandle.BOTTOM_RIGHT: (x2, y2),
            ResizeHandle.BOTTOM: (cx, y2),
            ResizeHandle.BOTTOM_LEFT: (x1, y2),
            ResizeHandle.LEFT: (x1, cy),
        }

    def hit_resize_handle(self, view_x: float, view_y: float, radius: float = 10) -> ResizeHandle | None:
        for handle, (hx, hy) in self._handle_points().items():
            if abs(view_x - hx) <= radius and abs(view_y - hy) <= radius:
                return handle
        return None

    def hit_rotate_handle(self, view_x: float, view_y: float, radius: float = 12) -> bool:
        if self.project is None or not self.selected_layer_id:
            return False
        try:
            layer = get_layer(self.project, self.selected_layer_id)
        except KeyError:
            return False
        rect = layer_rect(layer)
        cx, _ = self._project_to_view(rect.cx, rect.cy)
        _, y1 = self._project_to_view(rect.x, rect.y)
        rotate_y = y1 - 34
        return abs(view_x - cx) <= radius and abs(view_y - rotate_y) <= radius

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.project is None:
            return
        x, y = self.canvas_point(event)
        view_x, view_y = event.position().x(), event.position().y()
        additive = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        resize_handle = self.hit_resize_handle(view_x, view_y)
        if resize_handle is not None:
            layer_id = self.interaction.mouse_press(x, y, additive=additive, mode=DragMode.RESIZE, resize_handle=resize_handle)
        elif self.hit_rotate_handle(view_x, view_y):
            layer_id = self.interaction.mouse_press(x, y, additive=additive, mode=DragMode.ROTATE)
        else:
            layer_id = self.interaction.mouse_press(x, y, additive=additive)
        if layer_id:
            self.selected_layer_id = layer_id
            self.layerSelected.emit(layer_id)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.project is None:
            return
        x, y = self.canvas_point(event)
        changed = self.interaction.mouse_move(x, y)
        if changed and self.interaction.active_layer_id():
            layer = get_layer(self.project, self.interaction.active_layer_id())
            self.selected_layer_id = layer.id
            self.layerMoved.emit(layer.id, layer.transform.x, layer.transform.y)
            self.render_preview()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.project is None:
            return
        x, y = self.canvas_point(event)
        changed = self.interaction.mouse_release(x, y)
        if changed and self.interaction.active_layer_id():
            layer = get_layer(self.project, self.interaction.active_layer_id())
            self.selected_layer_id = layer.id
            self.layerMoved.emit(layer.id, layer.transform.x, layer.transform.y)
            self.render_preview()
        self.update()

    def _draw_handle(self, painter: QPainter, x: float, y: float, size: int = 8) -> None:
        half = size // 2
        painter.drawRect(int(x - half), int(y - half), size, size)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        super().paintEvent(event)
        if self.project is None or not self.selected_layer_id or self.pixmap() is None:
            return
        try:
            layer = get_layer(self.project, self.selected_layer_id)
        except KeyError:
            return
        rect = layer_rect(layer)
        x1, y1 = self._project_to_view(rect.x, rect.y)
        x2, y2 = self._project_to_view(rect.right, rect.bottom)
        cx, cy = self._project_to_view(rect.cx, rect.cy)
        painter = QPainter(self)
        pen = QPen(Qt.GlobalColor.cyan)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1))

        for hx, hy in self._handle_points().values():
            self._draw_handle(painter, hx, hy)

        rotate_y = y1 - 34
        painter.drawLine(int(cx), int(y1), int(cx), int(rotate_y))
        painter.drawEllipse(int(cx - 6), int(rotate_y - 6), 12, 12)
