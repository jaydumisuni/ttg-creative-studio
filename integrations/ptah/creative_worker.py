#!/usr/bin/env python3
"""Creative Studio specialist operations for Ptah A05 (no Hunter required).

This module owns creative semantics. Ptah owns the mechanical run and artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

STUDIO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(STUDIO / "src"))
sys.path.insert(0, str(STUDIO / "scripts"))
from PIL import ImageChops
from ttg_action_engine import ActionEngine
from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_project_schema import TTGProject
from build_ad_project_from_assets import build_ad_project
from render_ad_project_contact_sheet import render_contact_sheet

SCHEMA = "ttg.creative.ptah.request.v1"
OPERATIONS = {"scene_edit", "ad_from_assets"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_request(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        raise ValueError("wrong request schema")
    if raw.get("operation") not in OPERATIONS:
        raise ValueError("unsupported operation")
    if not isinstance(raw.get("request_id"), str) or not raw["request_id"].strip():
        raise ValueError("request_id is required")
    return raw


def require_in_workspace(path: Path) -> Path:
    workspace = (STUDIO / ".workspace").resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(workspace):
        raise ValueError(f"input must be in Studio workspace: {resolved}")
    return resolved


def zip_project(out: Path, names: list[str]) -> None:
    with zipfile.ZipFile(out / "project_bundle.zip", "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name in names:
            z.write(out / name, name)


def scene_edit(req: dict, out: Path) -> dict:
    text = str(req.get("text", "THETECHGUY"))
    if not 1 <= len(text) <= 120:
        raise ValueError("text length 1..120 required")
    dx = req.get("move_x", 108)
    if isinstance(dx, bool) or not isinstance(dx, (int, float)) or not 1 <= dx <= 400:
        raise ValueError("move_x must be between 1 and 400")
    engine = ActionEngine()
    project = engine.new_project("TTG Ptah editable scene", "image")
    project.canvas.width = 640
    project.canvas.height = 360
    project.canvas.background = "#182630"
    engine.add_text(project, text, 30, 30)
    shape = engine.add_shape(project, "rectangle", 42, 132)
    renderer = CanvasRenderer(RenderContext(project_root=out))
    renderer.render(project).save(out / "before.png")
    shape.transform.x += float(dx)
    renderer.render(project).save(out / "preview.png")
    project.save(out / "editable.ttgstudio.json")
    zip_project(out, ["editable.ttgstudio.json", "preview.png"])
    return {"outputs": ["editable.ttgstudio.json", "preview.png", "project_bundle.zip"],
            "scene_layers": 2, "input_count": 0}


def ad_from_assets(req: dict, out: Path) -> dict:
    source = require_in_workspace(Path(str(req.get("asset_dir", ""))))
    if not source.is_dir():
        raise ValueError("asset_dir must be an existing directory")
    images = sorted(p for p in source.iterdir()
                    if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
    if not 2 <= len(images) <= 6:
        raise ValueError("ad assets must contain 2..6 images")
    title = str(req.get("title", "TTG Product Campaign"))
    if not 1 <= len(title) <= 100:
        raise ValueError("title length 1..100 required")
    asset_dir = out / "assets"
    asset_dir.mkdir()
    names = []
    source_hashes = {}
    for i, image in enumerate(images):
        if image.is_symlink() or not image.resolve().is_relative_to((STUDIO / ".workspace").resolve()):
            raise ValueError("asset must be a regular file inside Studio workspace")
        name = f"assets/scene_{i + 1:02d}{image.suffix.lower()}"
        dest = out / name
        content = image.read_bytes()
        if len(content) > 15_000_000:
            raise ValueError("asset exceeds bounded 15 MB input")
        from PIL import Image
        with Image.open(image) as loaded:
            loaded.verify()
        dest.write_bytes(content)
        names.append(name)
        source_hashes[str(image)] = hashlib.sha256(content).hexdigest()
    project = build_ad_project(asset_dir, out / "editable.ttgstudio.json", title,
                               workspace=out / "import-workspace")
    title_layers = [x for x in project.layers if x.name == "Ad Title"]
    if len(title_layers) != 1:
        raise ValueError("expected one title layer")
    title_layers[0].properties["text"] = title
    project.save(out / "editable.ttgstudio.json")
    for asset in project.assets:
        asset.path = str(Path("assets") / Path(asset.path).name)
        asset.sha256 = sha(out / asset.path)
    for layer in project.layers:
        if layer.type == "image":
            layer.properties["path"] = str(Path("assets") / Path(layer.properties["path"]).name)
    # Internal original-source paths belong in Ptah evidence, not the portable bundle.
    project.export.setdefault("creative_studio_test", {})["source_asset_dir"] = "assets"
    project.export.setdefault("ptah", {})["portable_bundle"] = True
    project.save(out / "editable.ttgstudio.json")
    # Render from the same portable relative paths that a standalone user receives.
    render_contact_sheet(out / "editable.ttgstudio.json", out / "preview.jpg")
    zip_project(out, ["editable.ttgstudio.json", "preview.jpg", *names])
    return {"outputs": ["editable.ttgstudio.json", "preview.jpg", "project_bundle.zip"],
            "scene_layers": len(images), "input_count": len(images),
            "source_hashes": source_hashes}


def run(request_path: Path, out: Path) -> dict:
    req = read_request(request_path)
    out = require_in_workspace(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("output directory not empty: refusing overwrite or retry")
    out.mkdir(parents=True, exist_ok=True)
    job = scene_edit(req, out) if req["operation"] == "scene_edit" else ad_from_assets(req, out)
    result = {"schema": "ttg.creative.ptah.worker_result.v1",
              "operation": req["operation"], "request_id": req["request_id"], **job}
    (out / "worker_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--request", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    run(a.request, a.output)
