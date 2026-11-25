"""Cross-capability donor qualification of TTG-native motion and raster blending.

This runs against the real editable project, action engine, canonical project
persistence, timeline renderer, and actual rendered pixel output.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ttg_action_engine import ActionEngine
from ttg_canvas_engine import RenderContext
from ttg_motion_exporter import MotionExporter
from ttg_project_schema import TTGProject
from ttg_timeline_engine import TimelineEngine


def _scene(mode: str):
    action = ActionEngine()
    project = action.new_project("Native Motion + Blend", "motion")
    project.canvas.width = 140
    project.canvas.height = 55
    project.canvas.duration = 1
    project.canvas.fps = 4
    project.canvas.background = "#808080"
    layer = action.add_shape(project, x=0, y=9)
    layer.properties.update({
        "shape": "rectangle", "width": 15, "height": 15,
        "fill": "#808080", "blend_mode": mode,
    })
    action.add_keyframe(project, layer.id, "position", 0.0, [12, 9, 0], "linear")
    action.add_keyframe(
        project, layer.id, "position", 1.0, [99, 9, 0],
        {"type": "cubic_bezier", "handles": [0.8, 0.0, 0.2, 1.0]},
    )
    return project, layer


@pytest.mark.parametrize("mode,expected", [("multiply", 64), ("screen", 192)])
def test_animated_blend_replays_identical_pixels_after_project_roundtrip(
    tmp_path: Path, mode: str, expected: int
) -> None:
    project, layer = _scene(mode)
    engine = MotionExporter(RenderContext(tmp_path))
    frame = engine.render_frame(project, 0.25)
    animated_x = TimelineEngine().apply_to_layer(layer, 0.25).transform.x
    x = int(animated_x) + 3
    assert frame.getpixel((x, 12)) == (expected, expected, expected, 255)

    saved = tmp_path / "native-donor-interchange.ttgstudio.json"
    project.save(saved)
    reopened = TTGProject.load(saved)
    replay = engine.render_frame(reopened, 0.25)
    assert sha256(replay.tobytes()).digest() == sha256(frame.tobytes()).digest()
    assert reopened.layers[0].properties["blend_mode"] == mode
    assert reopened.layers[0].keyframes["position"][1].easing == {
        "type": "cubic_bezier", "handles": [0.8, 0.0, 0.2, 1.0]
    }

    later = engine.render_frame(reopened, 0.75)
    assert later.getpixel((x, 12)) == (128, 128, 128, 255)
    assert later.tobytes() != frame.tobytes()


def test_bad_curve_does_not_append_keyframe_or_modify_layer_blend(tmp_path: Path) -> None:
    project, layer = _scene("multiply")
    before = project.to_dict()
    with pytest.raises(ValueError, match="four finite"):
        ActionEngine().add_keyframe(
            project, layer.id, "position", .5, [45, 9, 0],
            {"type": "cubic_bezier", "handles": [0, "invalid", 1, 1]},
        )
    assert project.to_dict() == before
    result = MotionExporter(RenderContext(tmp_path)).render_frame(project, 0.25)
    assert result.getpixel((18, 12))[3] == 255


def test_legacy_normal_blending_and_linear_motion_remain_unchanged(tmp_path: Path) -> None:
    project, layer = _scene("normal")
    engine = MotionExporter(RenderContext(tmp_path))
    with_mode = engine.render_frame(project, .25)
    layer.properties.pop("blend_mode")
    no_mode = engine.render_frame(project, .25)
    assert sha256(with_mode.tobytes()).digest() == sha256(no_mode.tobytes()).digest()
    assert layer.keyframes["position"][1].easing["type"] == "cubic_bezier"
