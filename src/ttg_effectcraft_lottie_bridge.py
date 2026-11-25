"""Small, source-bound Lottie 5.x interchange with EffectCraft-compatible shapes.

Only editable solid rectangle/ellipse shapes and positional keyframes
are represented. Missing transforms, masks, effects or external assets are
explicit errors. Existing native TTG files always remain authoritative.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
import math
from pathlib import Path

from PIL import ImageColor

from ttg_filmcraft_otio_bridge import _safe_write
from ttg_project_schema import CanvasSpec, Keyframe, Layer, TTGProject, Transform

MAX_LOTTIE_BYTES = 2 * 1024 * 1024
MAX_LAYER_COUNT = 128
MAX_FRAMES = 120 * 1800


def _static(v, label):
    if not isinstance(v, dict) or v.get("a") != 0 or "k" not in v:
        raise ValueError(f"Unsupported animated Lottie {label}")
    return v["k"]


def _point(v, label, length):
    if not isinstance(v, list) or len(v) < length:
        raise ValueError(f"Invalid Lottie {label}")
    result = []
    for item in v[:length]:
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
            raise ValueError(f"Nonfinite Lottie {label}")
        result.append(float(item))
    return result


def _lottie_position(layer: Layer, fps: int, width: float, height: float):
    frames = layer.keyframes.get("position")
    if not frames:
        return {"a": 0, "k": [layer.transform.x + width/2,
                              layer.transform.y + height/2, 0]}
    samples = sorted(frames, key=lambda f: f.time)
    if len(samples) < 2 or len(samples) > 256:
        raise ValueError("Lottie export requires 2–256 position keyframes")
    if any(f.time < 0 or f.time * fps > MAX_FRAMES for f in samples):
        raise ValueError("Lottie motion time out of range")
    output = []
    for i, frame in enumerate(samples):
        pos = _point(list(frame.value), "position keyframe", 2)
        data = {
            "t": round(frame.time * fps, 6),
            "s": [pos[0] + width/2, pos[1] + height/2, 0],
        }
        if i != len(samples)-1:
            next_easing = samples[i+1].easing
            if next_easing == "hold":
                data["h"] = 1
            elif next_easing in ("linear", "ease_in_out"):
                defaults = ([0.0, 0.0, 1.0, 1.0] if next_easing == "linear"
                            else [0.42, 0, 0.58, 1])
                data["o"] = {"x": defaults[0], "y": defaults[1]}
                data["i"] = {"x": defaults[2], "y": defaults[3]}
            elif isinstance(next_easing, dict) and next_easing.get("type") == "cubic_bezier":
                handles = _point(list(next_easing.get("handles", [])), "cubic handles", 4)
                if not (0 <= handles[0] <= 1 and 0 <= handles[2] <= 1):
                    raise ValueError("Invalid cubic X handles")
                data["o"] = {"x": handles[0], "y": handles[1]}
                data["i"] = {"x": handles[2], "y": handles[3]}
            else:
                raise ValueError("Unmapped Lottie easing contract")
        output.append(data)
    return {"a": 1, "k": output}


def export_lottie(project: TTGProject, output_path: str | Path) -> dict:
    dest = Path(output_path)
    if dest.suffix.lower() != ".json":
        raise ValueError("Lottie requires a new .json file")
    fps, width, height = project.canvas.fps, project.canvas.width, project.canvas.height
    duration = project.canvas.duration
    if not 1 <= fps <= 120 or width * height > 16_000_000 or duration <= 0 or duration * fps > MAX_FRAMES:
        raise ValueError("Invalid Lottie canvas/time bounds")
    if not project.layers or len(project.layers) > MAX_LAYER_COUNT:
        raise ValueError("Lottie requires bounded shape layers")
    layers = []
    for i, layer in enumerate(reversed(project.layers)):
        if layer.type != "shape" or layer.effects or layer.locked:
            raise ValueError(f"Unsupported EffectCraft/Lottie layer kind or effects: {layer.type}")
        if layer.properties.get("blend_mode", "normal") != "normal":
            raise ValueError("Unmapped Lottie blend mode")
        if set(layer.keyframes) - {"position"}:
            raise ValueError("Unmapped Lottie animated property")
        if layer.transform.rotation_z or layer.transform.rotation_x or layer.transform.rotation_y:
            raise ValueError("Lottie rotation requires a verified renderer path")
        shape_type = layer.properties.get("shape", "rectangle")
        if shape_type not in {"rectangle", "ellipse"}:
            raise ValueError("Unmapped Lottie vector shape")
        w = float(layer.properties.get("width", 200)) * layer.transform.scale_x
        h = float(layer.properties.get("height", 100)) * layer.transform.scale_y
        if not 0 < w <= width or not 0 < h <= height:
            raise ValueError("Lottie shape dimensions invalid")
        color = ImageColor.getcolor(layer.properties.get("fill", "#00E5FF"), "RGBA")
        if color[3] != 255:
            raise ValueError("Lottie transparency must use explicit opacity property")
        if layer.properties.get("outline") or layer.properties.get("glow"):
            raise ValueError("Unsupported Lottie outline/glow")
        spec = {
            "ty": "el" if shape_type == "ellipse" else "rc",
            "nm": shape_type.title(), "d": 1,
            "p": {"a": 0, "k": [0, 0]},
            "s": {"a": 0, "k": [w, h]},
        }
        if shape_type == "rectangle":
            spec["r"] = {"a": 0, "k": 0}
        fill = {
            "ty": "fl", "nm": "Fill", "r": 1,
            "c": {"a": 0, "k": [color[0]/255, color[1]/255, color[2]/255, 1]},
            "o": {"a": 0, "k": 100},
        }
        layer_data = {
            "ddd": 0, "ind": i+1, "ty": 4, "nm": layer.name,
            "sr": 1, "ao": 0, "ip": 0, "op": round(duration * fps),
            "st": 0, "bm": 0,
            "ks": {
                "a": {"a": 0, "k": [0, 0, 0]},
                "p": _lottie_position(layer, fps, w, h),
                "s": {"a": 0, "k": [100, 100, 100]},
                "r": {"a": 0, "k": 0},
                "o": {"a": 0, "k": round(100*layer.transform.opacity, 4)},
            },
            "shapes": [{
                "ty": "gr", "nm": layer.name,
                "it": [spec, fill, {
                    "ty": "tr",
                    "a": {"a": 0, "k": [0, 0]},
                    "p": {"a": 0, "k": [0, 0]},
                    "s": {"a": 0, "k": [100, 100]},
                    "r": {"a": 0, "k": 0},
                    "o": {"a": 0, "k": 100},
                }],
            }],
        }
        if not layer.visible:
            layer_data["hd"] = True
        layers.append(layer_data)
    doc = {"v": "5.12.0", "nm": project.name, "fr": fps,
           "ip": 0, "op": round(duration * fps), "w": width,
           "h": height, "ddd": 0, "assets": [], "layers": layers, "markers": []}
    encoded = (json.dumps(doc, sort_keys=True, indent=2) + "\n").encode()
    if len(encoded) > MAX_LOTTIE_BYTES:
        raise ValueError("Lottie export exceeds budget")
    _safe_write(dest, encoded)
    return {
        "format": "lottie", "output": str(dest), "layers": len(layers),
        "sha256": sha256(encoded).hexdigest(),
        "supported_subset": "solid rectangle/ellipse, static opacity, position keyframes",
    }


def import_lottie(input_file: str | Path, output_project: str | Path) -> dict:
    src, dest = Path(input_file), Path(output_project)
    if not src.is_file() or src.stat().st_size > MAX_LOTTIE_BYTES:
        raise ValueError("Missing or oversized Lottie file")
    if not dest.name.endswith(".ttgstudio.json"):
        raise ValueError("Lottie import requires native Studio project path")
    doc = json.loads(src.read_text(encoding="utf8"))
    if not isinstance(doc, dict) or doc.get("assets") or doc.get("ddd") not in (None, 0):
        raise ValueError("Unsupported Lottie assets or 3D context")
    fps = int(doc.get("fr", 0))
    width = int(doc.get("w", 0))
    height = int(doc.get("h", 0))
    frames = int(doc.get("op", 0))
    if not 1 <= fps <= 120 or not 1 <= width <= 4096 or not 1 <= height <= 4096 or width*height > 16_000_000 or not 1 <= frames <= MAX_FRAMES:
        raise ValueError("Invalid Lottie dimensions or duration")
    raw_layers = doc.get("layers")
    if not isinstance(raw_layers, list) or len(raw_layers) > MAX_LAYER_COUNT:
        raise ValueError("Lottie layers exceed budget")
    project = TTGProject(name=str(doc.get("nm") or src.stem)[:150], project_type="motion")
    project.canvas = CanvasSpec(width=width, height=height, fps=fps,
                                duration=frames/fps, background="#00000000")
    if doc.get("markers"):
        raise ValueError("Lottie markers require mapping to Studio timeline")
    for i, raw in enumerate(reversed(raw_layers)):
        if raw.get("ty") != 4 or raw.get("bm", 0) != 0 or raw.get("tt") or raw.get("masksProperties") or raw.get("ef"):
            raise ValueError("Unsupported masked/blended/effected Lottie layer")
        ks = raw["ks"]
        if _static(ks["a"], "anchor") != [0, 0, 0] or _static(ks["s"], "scale") != [100, 100, 100] or _static(ks["r"], "rotation") != 0:
            raise ValueError("Unsupported Lottie anchor/scale/rotation")
        opacity = float(_static(ks["o"], "opacity"))/100
        if not 0 <= opacity <= 1:
            raise ValueError("Lottie opacity out of range")
        groups = raw.get("shapes")
        if not isinstance(groups, list) or len(groups) != 1 or groups[0].get("ty") != "gr":
            raise ValueError("Only one Lottie shape group supported")
        items = groups[0].get("it")
        if not isinstance(items, list) or len(items) != 3:
            raise ValueError("Unsupported nested Lottie shape")
        geometry, fill, transform = items
        if geometry.get("ty") not in {"el", "rc"} or fill.get("ty") != "fl" or transform.get("ty") != "tr":
            raise ValueError("Unsupported Lottie shape/fill")
        if _static(geometry["p"], "geometry position") != [0, 0]:
            raise ValueError("Offset geometry requires independent mapping")
        size = _point(_static(geometry["s"], "geometry size"), "size", 2)
        if not 0 < size[0] <= width or not 0 < size[1] <= height:
            raise ValueError("Lottie shape dimensions invalid")
        color = _point(_static(fill["c"], "fill color"), "fill color", 3)
        if any(not 0 <= x <= 1 for x in color):
            raise ValueError("Lottie fill outside normalized range")
        if _static(fill["o"], "fill opacity") != 100:
            raise ValueError("Animated fill opacity not mapped")
        if _static(transform["p"], "group position") != [0, 0]:
            raise ValueError("Offset group transform unsupported")
        if _static(transform["s"], "group scale") != [100, 100] or _static(transform["r"], "group rotation") != 0 or _static(transform["o"], "group opacity") != 100:
            raise ValueError("Group transform unsupported")
        pos = ks["p"]
        keyframes = {}
        if pos.get("a") == 0:
            x, y = _point(pos.get("k"), "position", 2)
            x -= size[0]/2
            y -= size[1]/2
        elif pos.get("a") == 1:
            source_keys = pos.get("k")
            if not isinstance(source_keys, list) or not 2 <= len(source_keys) <= 256:
                raise ValueError("Unsupported Lottie keyframe count")
            path = []
            previous = -1
            for key_index, key in enumerate(source_keys):
                stamp = float(key.get("t", -1))
                if not previous < stamp <= frames:
                    raise ValueError("Nonmonotone Lottie keyframe time")
                previous = stamp
                if any(any(abs(v) > 1e-10 for v in _point(key.get(t), t, 3))
                       for t in ("to", "ti") if t in key):
                    raise ValueError("Lottie spatial curve tangents require a qualified adapter")
                px, py = _point(key.get("s"), "keyframe position", 2)
                ease = "linear"
                if key_index:
                    old = source_keys[key_index - 1]
                    if old.get("h") == 1:
                        ease = "hold"
                    elif "o" in old and "i" in old:
                        ease = {
                            "type": "cubic_bezier",
                            "handles": [float(old["o"]["x"]), float(old["o"]["y"]),
                                        float(old["i"]["x"]), float(old["i"]["y"])],
                        }
                path.append(Keyframe(time=stamp/fps,
                                     value=[px-size[0]/2, py-size[1]/2, 0],
                                     easing=ease))
            keyframes["position"] = path
            x, y = path[0].value[:2]
        else:
            raise ValueError("Unknown animated Lottie position contract")
        project.layers.append(Layer(
            id=f"lottie_{i:04d}", type="shape",
            name=str(raw.get("nm") or f"Lottie shape {i}")[:150],
            visible=not raw.get("hd", False),
            transform=Transform(x=x, y=y, opacity=opacity),
            properties={
                "shape": "ellipse" if geometry["ty"] == "el" else "rectangle",
                "width": size[0], "height": size[1],
                "fill": "#" + "".join(f"{round(255*v):02X}" for v in color),
            }, keyframes=keyframes,
        ))
    if dest.exists() or dest.is_symlink():
        raise FileExistsError("Refuse overwrite of native project")
    payload = (json.dumps(project.to_dict(), indent=2) + "\n").encode()
    _safe_write(dest, payload)
    return {"format": "lottie", "output": str(dest),
            "layers": len(project.layers), "sha256": sha256(payload).hexdigest()}
