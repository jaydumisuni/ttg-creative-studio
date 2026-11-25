"""Restricted VectorCraft/SVG shape interchange with TTG's existing editor.

TTG retains editable shape/diagram layers. No script, external resource,
unmapped path, CSS, gradient, transform or complex vector content is silently
rendered or discarded; those require a separately qualified vector engine.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import math
import re
from xml.etree import ElementTree as ET

from PIL import ImageColor

from ttg_filmcraft_otio_bridge import _safe_write
from ttg_project_schema import CanvasSpec, Layer, Transform, TTGProject

SVG = "http://www.w3.org/2000/svg"
MAX_FILE = 1024 * 1024
MAX_SHAPES = 128


def _number(value, name: str, max_value=4096) -> float:
    if isinstance(value, str) and not re.fullmatch(
        r"(?:\d+(?:\.\d+)?|\.\d+)", value
    ):
        raise ValueError(f"SVG {name} needs plain nonnegative pixel units")
    n = float(value)
    if not math.isfinite(n) or not 0 <= n <= max_value:
        raise ValueError(f"Invalid SVG {name}")
    return n


def _color(value) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"#[0-9a-fA-F]{6}", value
    ):
        raise ValueError("Supported SVG colors require #RRGGBB")
    ImageColor.getrgb(value)
    return value.upper()



def _polyline_points(value: object, width: float, height: float) -> list[list[float]]:
    """Read strictly bounded, untransformed SVG pixel-coordinate polylines."""
    if not isinstance(value,str) or len(value)>8_192:
        raise ValueError("SVG polyline coordinates invalid or oversized")
    if not re.fullmatch(r"\s*(?:\d+(?:\.\d+)?|\.\d+),(?:\d+(?:\.\d+)?|\.\d+)"
                        r"(?:\s+(?:\d+(?:\.\d+)?|\.\d+),(?:\d+(?:\.\d+)?|\.\d+))*\s*",
                        value):
        raise ValueError("SVG polyline needs bounded x,y coordinates")
    items=value.strip().split()
    if not 2<=len(items)<=128:
        raise ValueError("SVG polyline requires 2–128 points")
    points=[]
    for item in items:
        x,y=item.split(",")
        px=_number(x,"polyline x",max_value=width)
        py=_number(y,"polyline y",max_value=height)
        points.append([px,py])
    return points


def _validated_native_line_points(points: object, width: float, height: float) -> list[list[float]]:
    """Bound native editable connector/polyline point budgets for SVG output."""
    if not isinstance(points,list) or not 2<=len(points)<=128:
        raise ValueError("SVG connector requires 2–128 points")
    rows=[]
    for p in points:
        if not isinstance(p,(list,tuple)) or len(p)!=2:
            raise ValueError("SVG connector point is not a 2D coordinate")
        if any(isinstance(v,bool) or not isinstance(v,(float,int,str)) for v in p):
            raise ValueError("SVG connector point requires numeric coordinates")
        rows.append([_number(p[0],"x",max_value=width),
                     _number(p[1],"y",max_value=height)])
    return rows

def _layer_rect(idx, x, y, width, height, fill, *, rounded=0):
    if width <= 0 or height <= 0:
        raise ValueError("Zero-size SVG shape unsupported")
    return Layer(
        id=f"svg_{idx:04d}", type="shape", name=f"SVG rectangle {idx}",
        transform=Transform(x=x, y=y),
        properties={
            "shape": "rectangle", "width": width, "height": height,
            "fill": fill, "radius": rounded,
        },
    )


def import_svg_shapes(source: str | Path, destination: str | Path) -> dict:
    p, output = Path(source), Path(destination)
    if p.suffix.lower() != ".svg" or not p.is_file() or p.stat().st_size > MAX_FILE:
        raise ValueError("Missing or oversized .svg input")
    if not output.name.endswith(".ttgstudio.json"):
        raise ValueError("SVG requires a new native TTG project destination")
    raw = p.read_bytes()
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("SVG DTD or entity declaration forbidden")
    tree = ET.fromstring(raw)
    if tree.tag not in {"svg", f"{{{SVG}}}svg"}:
        raise ValueError("SVG document required")
    if any(k in tree.attrib for k in ("style", "onload")):
        raise ValueError("SVG script/style attributes unsupported")
    width = _number(tree.get("width"), "width")
    height = _number(tree.get("height"), "height")
    if not width or not height or width*height > 4_000_000:
        raise ValueError("SVG canvas outside bounds")
    vb = tree.get("viewBox")
    if vb is not None:
        pts = vb.split()
        if len(pts) != 4 or [_number(k, "viewBox") for k in pts] != [0, 0, width, height]:
            raise ValueError("SVG viewBox transforms unsupported")
    if len(tree) > MAX_SHAPES:
        raise ValueError("SVG shape budget exceeded")
    layers = []
    for idx, el in enumerate(tree):
        tag = el.tag.split("}")[-1]
        if len(el) or any(k.startswith("on") for k in el.attrib):
            raise ValueError("Nested SVG/shaders/scripts not supported")
        if el.get("transform") or el.get("style") or el.get("opacity") or el.get("filter"):
            raise ValueError("SVG transforms, CSS or effects require a vector adapter")
        if tag == "rect":
            if el.get("stroke"):
                raise ValueError("SVG rectangle stroke unsupported")
            x = _number(el.get("x", 0), "x")
            y = _number(el.get("y", 0), "y")
            w = _number(el.get("width"), "width")
            h = _number(el.get("height"), "height")
            rounded = _number(el.get("rx", 0), "corner radius")
            shape = _layer_rect(idx, x, y, w, h, _color(el.get("fill")), rounded=rounded)
        elif tag in {"circle", "ellipse"}:
            if el.get("stroke"):
                raise ValueError("SVG ellipse stroke unsupported")
            cx = _number(el.get("cx"), "cx")
            cy = _number(el.get("cy"), "cy")
            rx = _number(el.get("r") if tag == "circle" else el.get("rx"), "rx")
            ry = rx if tag == "circle" else _number(el.get("ry"), "ry")
            if not rx or not ry:
                raise ValueError("Zero-radius SVG ellipse")
            shape = Layer(
                id=f"svg_{idx:04d}", type="shape", name=f"SVG ellipse {idx}",
                transform=Transform(x=cx-rx, y=cy-ry),
                properties={
                    "shape": "ellipse", "width": 2*rx, "height": 2*ry,
                    "fill": _color(el.get("fill")),
                },
            )
        elif tag in {"line", "polyline"}:
            if el.get("fill") not in (None, "none"):
                raise ValueError("SVG line cannot have a fill")
            if tag == "line":
                points = [
                    [_number(el.get("x1"), "x1", max_value=width),
                     _number(el.get("y1"), "y1", max_value=height)],
                    [_number(el.get("x2"), "x2", max_value=width),
                     _number(el.get("y2"), "y2", max_value=height)],
                ]
            else:
                allowed={"points","stroke","stroke-width","fill","id"}
                if any(key not in allowed for key in el.attrib):
                    raise ValueError("Unsupported SVG polyline stroke/transform attribute")
                points = _polyline_points(el.get("points"),width,height)
            color = _color(el.get("stroke"))
            stroke = _number(el.get("stroke-width", 3), "stroke")
            if not 1 <= stroke <= 64:
                raise ValueError("SVG stroke width out of bounds")
            shape = Layer(
                id=f"svg_{idx:04d}", type="connector_line",
                name=f"SVG connector {idx}",
                properties={"points": points,
                            "stroke_width": round(stroke), "color": color},
            )
        else:
            raise ValueError(f"SVG element {tag} unsupported; refusing flatten")
        layers.append(shape)
    if not layers:
        raise ValueError("SVG document has no supported editable shapes")
    project = TTGProject(name=p.stem, project_type="diagram")
    project.canvas = CanvasSpec(width=round(width), height=round(height),
                                background="#00000000")
    project.layers = layers
    if output.exists() or output.is_symlink():
        raise FileExistsError("Native SVG import cannot overwrite an existing project")
    encoded = (json.dumps(project.to_dict(), indent=2) + "\n").encode()
    _safe_write(output, encoded)
    return {"format":"svg", "output":str(output), "layers":len(layers),
            "sha256":sha256(encoded).hexdigest(), "native_editable_shapes": True}


def export_svg_shapes(project: TTGProject, destination: str | Path) -> dict:
    output = Path(destination)
    if output.suffix.lower() != ".svg":
        raise ValueError("VectorCraft interchange requires .svg output")
    width, height = project.canvas.width, project.canvas.height
    if not 1 <= width <= 4096 or not 1 <= height <= 4096 or width*height > 4_000_000:
        raise ValueError("Canvas too large for bounded SVG export")
    if not project.layers or len(project.layers) > MAX_SHAPES:
        raise ValueError("SVG shape count unsupported")
    root = ET.Element(f"{{{SVG}}}svg", {
        "width": str(width), "height": str(height),
        "viewBox": f"0 0 {width} {height}",
    })
    base = ImageColor.getcolor(project.canvas.background, "RGBA")
    if base[3] not in {0,255}:
        raise ValueError("Partially transparent SVG backgrounds unsupported")
    if base[3] == 255:
        ET.SubElement(root, f"{{{SVG}}}rect", {
            "x": "0", "y": "0", "width": str(width), "height": str(height),
            "fill": "#{:02X}{:02X}{:02X}".format(*base[:3]),
        })
    for layer in project.layers:
        if not layer.visible:
            raise ValueError("Hidden SVG layers need source-preserving interchange")
        if (layer.effects or layer.keyframes or layer.transform.opacity != 1
                or layer.transform.rotation_z or layer.properties.get("blend_mode","normal") != "normal"):
            raise ValueError("Cannot represent effects/animation/blend in basic SVG")
        if layer.type == "shape":
            shape = layer.properties.get("shape", "rectangle")
            fill = _color(layer.properties.get("fill"))
            x, y = layer.transform.x, layer.transform.y
            w = float(layer.properties.get("width", 0)) * layer.transform.scale_x
            h = float(layer.properties.get("height", 0)) * layer.transform.scale_y
            if not (0 <= x <= width and 0 <= y <= height and
                    0 < w <= width and 0 < h <= height):
                raise ValueError("Shape outside basic SVG bounds")
            if layer.properties.get("outline") or layer.properties.get("glow"):
                raise ValueError("SVG shape outline/glow not qualified")
            if shape == "rectangle":
                attrs={"x":str(x),"y":str(y),"width":str(w),"height":str(h),"fill":fill}
                radius=layer.properties.get("radius", 0)
                if radius: attrs["rx"] = str(radius)
                ET.SubElement(root, f"{{{SVG}}}rect", attrs)
            elif shape == "ellipse":
                ET.SubElement(root, f"{{{SVG}}}ellipse", {
                    "cx":str(x+w/2), "cy":str(y+h/2),
                    "rx":str(w/2), "ry":str(h/2), "fill":fill,
                })
            else:
                raise ValueError("Unmapped native shape SVG export")
        elif layer.type == "connector_line":
            points = _validated_native_line_points(
                layer.properties.get("points"),width,height
            )
            color = _color(layer.properties.get("color"))
            weight=_number(layer.properties.get("stroke_width",3),"stroke",max_value=64)
            if not 1<=weight<=64 or round(weight)!=weight:
                raise ValueError("SVG connector stroke needs integral pixels")
            if len(points)==2:
                p1,p2=points
                tag="line"
                coords={"x1":str(p1[0]),"y1":str(p1[1]),
                        "x2":str(p2[0]),"y2":str(p2[1])}
            else:
                tag="polyline"
                coords={"points":" ".join(
                    f"{p[0]},{p[1]}" for p in points)}
            ET.SubElement(root,f"{{{SVG}}}{tag}",{
                **coords,"stroke":color,
                "stroke-width":str(int(weight)),"fill":"none",
            })
        else:
            raise ValueError(f"SVG export refuses unsupported layer {layer.type}")
    encoded = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    if len(encoded) > MAX_FILE:
        raise ValueError("SVG output exceeds byte budget")
    _safe_write(output, encoded)
    return {"format":"svg", "output":str(output),
            "layers":len(project.layers), "sha256":sha256(encoded).hexdigest(),
            "supported_subset":"editable solid shapes and 2–128-point line/polyline connectors"}
