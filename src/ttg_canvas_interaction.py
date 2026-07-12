#!/usr/bin/env python3
"""Qt-facing canvas interaction controller.

This keeps mouse-event behavior separate from the canvas widget. The widget only
needs to translate pointer coordinates into project coordinates and call this
controller.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ttg_canvas_tools import CanvasTool, ResizeHandle, SelectionState, get_layer, hit_test, layer_rect, move_layer, resize_layer, rotate_layer
from ttg_project_schema import TTGProject


class DragMode(str, Enum):
    NONE = "none"
    MOVE = "move"
    RESIZE = "resize"
    ROTATE = "rotate"


@dataclass
class PointerState:
    start_x: float = 0
    start_y: float = 0
    last_x: float = 0
    last_y: float = 0
    dragging: bool = False
    moved: bool = False
    mode: DragMode = DragMode.NONE
    resize_handle: ResizeHandle | None = None
    origin_x: float = 0
    origin_y: float = 0
    origin_width: float = 0
    origin_height: float = 0


class CanvasInteractionController:
    def __init__(self, project: TTGProject | None = None) -> None:
        self.project = project
        self.selection = SelectionState([])
        self.pointer = PointerState()

    def set_project(self, project: TTGProject | None) -> None:
        self.project = project
        self.selection.select(None)
        self.pointer = PointerState()

    def mouse_press(self, x: float, y: float, *, additive: bool = False, mode: DragMode | str | None = None, resize_handle: ResizeHandle | None = None) -> str | None:
        drag_mode = DragMode(mode) if isinstance(mode, str) else (mode or DragMode.NONE)
        self.pointer = PointerState(start_x=x, start_y=y, last_x=x, last_y=y, dragging=True, moved=False, mode=drag_mode, resize_handle=resize_handle)
        if self.project is None:
            return None
        layer_id = self.selection.active_layer_id if drag_mode in {DragMode.RESIZE, DragMode.ROTATE} else hit_test(self.project, x, y)
        self.selection.select(layer_id, additive=additive)
        if self.pointer.mode == DragMode.NONE and layer_id:
            self.pointer.mode = DragMode.MOVE
        if layer_id:
            layer = get_layer(self.project, layer_id)
            rect = layer_rect(layer)
            self.pointer.origin_x = rect.x
            self.pointer.origin_y = rect.y
            self.pointer.origin_width = rect.width
            self.pointer.origin_height = rect.height
        return layer_id

    def mouse_move(self, x: float, y: float) -> bool:
        if not self.pointer.dragging or self.project is None:
            return False
        dx = x - self.pointer.last_x
        dy = y - self.pointer.last_y
        self.pointer.last_x = x
        self.pointer.last_y = y
        if abs(dx) < 0.001 and abs(dy) < 0.001:
            return False
        self.pointer.moved = True
        layer_id = self.selection.active_layer_id
        if not layer_id:
            return False
        layer = get_layer(self.project, layer_id)
        if layer.locked:
            return False
        total_dx = x - self.pointer.start_x
        total_dy = y - self.pointer.start_y
        if self.pointer.mode in {DragMode.MOVE, DragMode.NONE} and self.selection.tool in {CanvasTool.SELECT, CanvasTool.MOVE}:
            layer.transform.x = self.pointer.origin_x
            layer.transform.y = self.pointer.origin_y
            move_layer(layer, total_dx, total_dy, snap_enabled=self.selection.snap_enabled, grid=self.selection.snap_grid)
            return True
        if self.pointer.mode == DragMode.RESIZE and self.pointer.resize_handle is not None:
            layer.transform.x = self.pointer.origin_x
            layer.transform.y = self.pointer.origin_y
            layer.transform.scale_x = 1
            layer.transform.scale_y = 1
            layer.properties["width"] = self.pointer.origin_width
            layer.properties["height"] = self.pointer.origin_height
            resize_layer(layer, self.pointer.resize_handle, total_dx, total_dy, snap_enabled=self.selection.snap_enabled, grid=self.selection.snap_grid)
            return True
        if self.pointer.mode == DragMode.ROTATE:
            rect = layer_rect(layer)
            rotate_layer(layer, rect.cx, rect.cy, x, y, snap_enabled=self.selection.snap_enabled, step=5)
            return True
        return False

    def mouse_release(self, x: float, y: float) -> bool:
        changed = self.mouse_move(x, y)
        was_dragging = self.pointer.dragging
        self.pointer.dragging = False
        self.pointer.mode = DragMode.NONE
        self.pointer.resize_handle = None
        return changed or (was_dragging and self.pointer.moved)

    def active_layer_id(self) -> str | None:
        return self.selection.active_layer_id
