#!/usr/bin/env python3
"""Diagram helpers for TTG Creative Studio."""

from __future__ import annotations

from ttg_project_schema import Layer, Transform, new_id


def make_node(label: str, x: float, y: float, width: float = 180, height: float = 90, color: str = "#00E5FF") -> Layer:
    return Layer(
        id=new_id("node"),
        type="diagram_node",
        name=label,
        transform=Transform(x=x, y=y),
        properties={"label": label, "width": width, "height": height, "color": color},
    )


def make_connector(name: str, points: list[list[float]], color: str = "#BC13FE", stroke_width: int = 3) -> Layer:
    return Layer(
        id=new_id("line"),
        type="connector_line",
        name=name,
        properties={"points": points, "color": color, "stroke_width": stroke_width},
    )


def make_measurement(label: str, start: list[float], end: list[float], color: str = "#F7FAFF") -> Layer:
    return Layer(
        id=new_id("measure"),
        type="measurement",
        name=label,
        properties={"points": [start, end], "label": label, "color": color},
    )


def add_basic_isp_diagram(project) -> None:
    modem = make_node("ISP / Starlink", 80, 120)
    router = make_node("Router", 340, 120)
    client = make_node("Client Devices", 600, 120)
    project.layers.extend([
        modem,
        router,
        client,
        make_connector("ISP to Router", [[260, 165], [340, 165]]),
        make_connector("Router to Devices", [[520, 165], [600, 165]]),
    ])


def add_basic_board_callout(project) -> None:
    board = make_node("PCB / Board", 120, 120, 360, 220, "#00E5FF")
    port = make_node("Port", 560, 150, 120, 70, "#BC13FE")
    project.layers.extend([
        board,
        port,
        make_connector("Port Callout", [[480, 190], [560, 185]], "#BC13FE", 3),
        make_measurement("64.8 mm", [120, 370], [480, 370]),
    ])
