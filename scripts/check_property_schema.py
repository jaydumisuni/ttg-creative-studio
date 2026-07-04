#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_action_engine import ActionEngine
from ttg_property_engine import (
    PropertyEdit,
    add_layer_keyframe,
    apply_property_edits,
    describe_editable_properties,
    evaluate_keyframes,
    list_timeline_clips,
    set_layer_time,
)
from ttg_property_schema import editable_keys_for_layer_type, spec_by_key


def check_schema() -> bool:
    text_keys = editable_keys_for_layer_type("text")
    text3d_keys = editable_keys_for_layer_type("text3d")
    shape_keys = editable_keys_for_layer_type("shape")
    ok = True
    ok = ok and "text" in text_keys
    ok = ok and "size" in text_keys
    ok = ok and "gradient" in text_keys
    ok = ok and "extrude_px" not in text_keys
    ok = ok and "extrude_px" in text3d_keys
    ok = ok and "fill" in shape_keys
    ok = ok and spec_by_key("opacity").min_value == 0.0
    ok = ok and spec_by_key("opacity").max_value == 1.0
    return ok


def check_engine() -> bool:
    action = ActionEngine()
    project = action.new_project("Property Engine Check", "image")
    layer = action.add_text(project, "Start", 10, 20)
    apply_property_edits(project, [
        PropertyEdit(layer.id, "name", "Title"),
        PropertyEdit(layer.id, "transform.x", 120),
        PropertyEdit(layer.id, "transform.y", 240),
        PropertyEdit(layer.id, "transform.opacity", 0.75),
        PropertyEdit(layer.id, "properties.text", "Updated"),
        PropertyEdit(layer.id, "properties.font_size", 64),
        PropertyEdit(layer.id, "effect.style.radius", 18),
    ])
    set_layer_time(project, layer.id, 1.0, 3.5)
    add_layer_keyframe(project, layer.id, "opacity", 1.0, 0.0)
    add_layer_keyframe(project, layer.id, "opacity", 3.0, 1.0)
    desc = describe_editable_properties(layer)
    clips = list_timeline_clips(project)
    halfway = evaluate_keyframes(project, layer.id, "opacity", 2.0)
    return all([
        layer.name == "Title",
        layer.transform.x == 120,
        layer.transform.y == 240,
        layer.transform.opacity == 0.75,
        layer.properties["text"] == "Updated",
        layer.properties["font_size"] == 64,
        layer.effects[0]["id"] == "style",
        layer.effects[0]["radius"] == 18,
        layer.properties["start_time"] == 1.0,
        layer.properties["end_time"] == 3.5,
        len(layer.keyframes["opacity"]) == 2,
        clips[0].layer_id == layer.id,
        halfway == 0.5,
        desc["transform"]["x"] == 120,
    ])


def main() -> int:
    ok = check_schema() and check_engine()
    print("Property schema + engine + timeline check:", "ok" if ok else "not ok")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
