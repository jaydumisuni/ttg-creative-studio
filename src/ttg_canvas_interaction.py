#!/usr/bin/env python3
"""Qt-facing canvas interaction controller.

This keeps mouse-event behavior separate from the canvas widget. The widget only
needs to translate pointer coordinates into project coordinates and call this
controller.
"""

from __future__ import annotations

from dataclasses import dataclass

from ttg_canvas_tools import CanvasTool, SelectionState, get_layer, hit_test, move_layer
from ttg_project_schema import TTGProject


@dataclass
class PointerState:
    start_x: float = 0
    start_y: float = 0
    last_x: float = 0
    last_y: float = 0
    dragging: bool = False
    moved: bool = False


class CanvasInteractionController:
    def __init__(self, project: TTGProject | None = None) -> None:
        self.project = project
        self.selection = SelectionState([])
        self.pointer = PointerState()

    def set_project(self, project: TTGProject | None) -> None:
        self.project = project
        self.selection.select(None)
        self.pointer = PointerState()

    def mouse_press(self, x: float, y: float, *, additive: bool = False) -> str | None:
        self.pointer = PointerState(start_x=x, start_y=y, last_x=x, last_y=y, dragging=True, moved=False)
        if self.project is None:
            return None
        layer_id = hit_test(self.project, x, y)
        self.selection.select(layer_id, additive=additive)
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
        if self.selection.tool in {CanvasTool.SELECT, CanvasTool.MOVE} and self.selection.active_layer_id:
            layer = get_layer(self.project, self.selection.active_layer_id)
            if not layer.locked:
                move_layer(layer, dx, dy, snap_enabled=self.selection.snap_enabled, grid=self.selection.snap_grid)
                return True
        return False

    def mouse_release(self, x: float, y: float) -> bool:
        changed = self.mouse_move(x, y)
        was_dragging = self.pointer.dragging
        self.pointer.dragging = False
        return changed or (was_dragging and self.pointer.moved)

    def active_layer_id(self) -> str | None:
        return self.selection.active_layer_id
