#!/usr/bin/env python3
"""Canvas interaction tools for TTG Creative Studio.

This is the non-UI math/state layer for real canvas editing: select, drag,
resize, rotate and snap. The Qt canvas can call these functions without mixing
geometry logic directly into paint/mouse event code.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import atan2, degrees

from ttg_project_schema import Layer, TTGProject


class CanvasTool(str, Enum):
    SELECT = "select"
    MOVE = "move"
    RESIZE = "resize"
    ROTATE = "rotate"
    HAND = "hand"
    ZOOM = "zoom"


class ResizeHandle(str, Enum):
    TOP_LEFT = "top_left"
    TOP = "top"
    TOP_RIGHT = "top_right"
    RIGHT = "right"
    BOTTOM_RIGHT = "bottom_right"
    BOTTOM = "bottom"
    BOTTOM_LEFT = "bottom_left"
    LEFT = "left"


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def cx(self) -> float:
        return self.x + self.width / 2

    @property
    def cy(self) -> float:
        return self.y + self.height / 2

    def contains(self, x: float, y: float) -> bool:
        return self.x <= x <= self.right and self.y <= y <= self.bottom


@dataclass
class SelectionState:
    layer_ids: list[str]
    active_layer_id: str | None = None
    tool: CanvasTool = CanvasTool.SELECT
    snap_enabled: bool = True
    snap_grid: int = 10

    def select(self, layer_id: str | None, additive: bool = False) -> None:
        if layer_id is None:
            if not additive:
                self.layer_ids.clear()
                self.active_layer_id = None
            return
        if additive:
            if layer_id in self.layer_ids:
                self.layer_ids.remove(layer_id)
            else:
                self.layer_ids.append(layer_id)
        else:
            self.layer_ids = [layer_id]
        self.active_layer_id = layer_id if layer_id in self.layer_ids else (self.layer_ids[-1] if self.layer_ids else None)


def layer_rect(layer: Layer) -> Rect:
    width = float(layer.properties.get("width", layer.properties.get("w", 240)))
    height = float(layer.properties.get("height", layer.properties.get("h", 120)))
    return Rect(float(layer.transform.x), float(layer.transform.y), width * float(layer.transform.scale_x), height * float(layer.transform.scale_y))


def snap(value: float, grid: int = 10) -> float:
    if grid <= 1:
        return value
    return round(value / grid) * grid


def hit_test(project: TTGProject, x: float, y: float) -> str | None:
    for layer in reversed(project.layers):
        if not layer.visible or layer.locked:
            continue
        if layer_rect(layer).contains(x, y):
            return layer.id
    return None


def get_layer(project: TTGProject, layer_id: str) -> Layer:
    for layer in project.layers:
        if layer.id == layer_id:
            return layer
    raise KeyError(layer_id)


def move_layer(layer: Layer, dx: float, dy: float, *, snap_enabled: bool = True, grid: int = 10) -> None:
    nx = float(layer.transform.x) + dx
    ny = float(layer.transform.y) + dy
    layer.transform.x = snap(nx, grid) if snap_enabled else nx
    layer.transform.y = snap(ny, grid) if snap_enabled else ny


def resize_layer(layer: Layer, handle: ResizeHandle, dx: float, dy: float, *, min_size: float = 8, snap_enabled: bool = True, grid: int = 10) -> None:
    rect = layer_rect(layer)
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    if handle in {ResizeHandle.LEFT, ResizeHandle.TOP_LEFT, ResizeHandle.BOTTOM_LEFT}:
        x += dx
        w -= dx
    if handle in {ResizeHandle.RIGHT, ResizeHandle.TOP_RIGHT, ResizeHandle.BOTTOM_RIGHT}:
        w += dx
    if handle in {ResizeHandle.TOP, ResizeHandle.TOP_LEFT, ResizeHandle.TOP_RIGHT}:
        y += dy
        h -= dy
    if handle in {ResizeHandle.BOTTOM, ResizeHandle.BOTTOM_LEFT, ResizeHandle.BOTTOM_RIGHT}:
        h += dy
    w = max(min_size, w)
    h = max(min_size, h)
    if snap_enabled:
        x = snap(x, grid)
        y = snap(y, grid)
        w = max(min_size, snap(w, grid))
        h = max(min_size, snap(h, grid))
    layer.transform.x = x
    layer.transform.y = y
    layer.properties["width"] = w
    layer.properties["height"] = h
    layer.transform.scale_x = 1
    layer.transform.scale_y = 1


def rotate_layer(layer: Layer, center_x: float, center_y: float, pointer_x: float, pointer_y: float, *, snap_enabled: bool = True, step: int = 5) -> None:
    angle = degrees(atan2(pointer_y - center_y, pointer_x - center_x))
    layer.transform.rotation_z = snap(angle, step) if snap_enabled else angle


def selection_bounds(project: TTGProject, layer_ids: list[str]) -> Rect | None:
    rects = [layer_rect(get_layer(project, layer_id)) for layer_id in layer_ids]
    if not rects:
        return None
    left = min(r.x for r in rects)
    top = min(r.y for r in rects)
    right = max(r.right for r in rects)
    bottom = max(r.bottom for r in rects)
    return Rect(left, top, right - left, bottom - top)
