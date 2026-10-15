#!/usr/bin/env python3
"""Independent creative-domain verification of saved project and actual output bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

STUDIO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(STUDIO / "src"))
sys.path.insert(0, str(STUDIO / "scripts"))
from PIL import Image, ImageChops
from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_project_schema import TTGProject
from render_ad_project_contact_sheet import render_contact_sheet
from creative_worker import read_request, require_in_workspace


def hash_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_bundle(out: Path, allowed: list[str]) -> None:
    archive = out / "project_bundle.zip"
    with zipfile.ZipFile(archive) as bundle:
        actual = sorted(bundle.namelist())
        assert actual == sorted(allowed), (actual, allowed)
        for member in bundle.infolist():
            p = Path(member.filename)
            assert not p.is_absolute() and ".." not in p.parts
            assert bundle.read(member.filename) == (out / member.filename).read_bytes(), member.filename


def verify_scene(req: dict, out: Path, project: TTGProject) -> dict:
    assert len(project.layers) == 2
    assert [l.type for l in project.layers] == ["text", "shape"]
    assert project.layers[0].properties["text"] == str(req.get("text", "THETECHGUY"))
    dx = float(req.get("move_x", 108))
    assert project.layers[1].transform.x == 42 + dx
    assert project.layers[0].transform.x == 30
    assert project.canvas.width == 640 and project.canvas.height == 360
    rendered = CanvasRenderer(RenderContext(project_root=out)).render(project).convert("RGBA")
    with Image.open(out / "preview.png") as file:
        expected = file.convert("RGBA")
    assert rendered.size == expected.size and rendered.tobytes() == expected.tobytes()
    with Image.open(out / "before.png") as file:
        before = file.convert("RGBA")
    assert ImageChops.difference(before.convert("RGB"), expected.convert("RGB")).getbbox()
    original_x = project.layers[1].transform.x
    project.layers[1].transform.x = 42
    assert CanvasRenderer(RenderContext(project_root=out)).render(project).convert("RGBA").tobytes() == before.tobytes()
    project.layers[1].transform.x = original_x
    assert_bundle(out, ["editable.ttgstudio.json", "preview.png"])
    return {"checks": ["editable_layers", "exact_text", "exact_x_delta", "pixel_replay",
                       "source_render_reconstructed", "bundle_integrity"],
            "registered_files": ["editable.ttgstudio.json", "preview.png", "project_bundle.zip"]}


def verify_ad(req: dict, out: Path, project: TTGProject) -> dict:
    source = require_in_workspace(Path(str(req["asset_dir"])))
    originals = sorted(p for p in source.iterdir()
                       if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
    assert 2 <= len(originals) <= 6
    images = [l for l in project.layers if l.type == "image"]
    assert len(images) == len(originals) == len(project.assets)
    assert project.name == req.get("title", "TTG Product Campaign")
    assert project.project_type == "motion"
    assert len(project.audio_markers) >= 3
    title = [l for l in project.layers if l.name == "Ad Title"]
    assert len(title) == 1 and title[0].properties["text"] == project.name
    assert all("opacity" in layer.keyframes and "scale_x" in layer.keyframes for layer in images)
    assert project.canvas.width == 1080 and project.canvas.height == 1920
    # All relative assets must remain usable when extracted elsewhere.
    for i, (original, asset, layer) in enumerate(zip(originals, project.assets, images, strict=True)):
        relative = Path(asset.path)
        assert not relative.is_absolute() and ".." not in relative.parts
        assert relative.parts[0] == "assets"
        assert layer.properties["path"] == asset.path
        local = (out / relative).resolve()
        assert local.is_relative_to(out.resolve())
        assert hash_of(original) == hash_of(local) == asset.sha256
        assert layer.properties["scene_index"] == i
    archive_names = ["editable.ttgstudio.json", "preview.jpg", *(a.path for a in project.assets)]
    assert_bundle(out, archive_names)
    # Re-render the unchanged portable project independently; this exercises
    # relocation-safe asset resolution in Creative Studio itself.
    with tempfile.TemporaryDirectory(prefix="ptah-creative-verify-", dir=out) as tmp:
        path = Path(tmp) / "verify_scene.ttgstudio.json"
        preview = Path(tmp) / "verify_preview.jpg"
        # Project and its asset directory are copied together to a new location.
        # The copy must behave identically without the old absolute source paths.
        import shutil
        shutil.copy2(out / "editable.ttgstudio.json", path)
        shutil.copytree(out / "assets", Path(tmp) / "assets")
        render_contact_sheet(path, preview)
        with Image.open(preview) as regenerated, Image.open(out / "preview.jpg") as produced:
            assert regenerated.size == produced.size
            assert regenerated.convert("RGB").tobytes() == produced.convert("RGB").tobytes()
    return {"checks": ["scene_count", "asset_digest_reconciliation", "portable_paths",
                       "timeline_keyframes", "title", "audio_markers",
                       "contact_sheet_pixel_replay", "bundle_integrity"],
            "registered_files": ["editable.ttgstudio.json", "preview.jpg", "project_bundle.zip"],
            "scene_count": len(images)}


def verify(request: Path, out: Path) -> dict:
    req = read_request(request)
    out = require_in_workspace(out)
    worker = json.loads((out / "worker_result.json").read_text(encoding="utf-8"))
    assert worker["schema"] == "ttg.creative.ptah.worker_result.v1"
    assert worker["request_id"] == req["request_id"] and worker["operation"] == req["operation"]
    project = TTGProject.load(out / "editable.ttgstudio.json")
    result = verify_scene(req, out, project) if req["operation"] == "scene_edit" else verify_ad(req, out, project)
    assert worker["outputs"] == result["registered_files"]
    digests = {n: hash_of(out / n) for n in result["registered_files"]}
    report = {"schema": "ttg.creative.ptah.verification.v1", "request_id": req["request_id"],
              "operation": req["operation"], "passed": True, "checks": result["checks"],
              "sha256": digests, "registered_files": result["registered_files"],
              "scope": "deterministic project/output correctness, not aesthetic review"}
    (out / "independent_verification.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    verify(a.request, a.output)
