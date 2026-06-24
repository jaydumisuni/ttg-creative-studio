#!/usr/bin/env python3
"""Build a TTG Creative Studio ad project from an asset folder.

This is the real Creative Studio workflow test target: given a folder of images,
create an editable .ttgstudio.json project with scene layers, captions, timing
metadata and export settings. The UI/renderer can then open and improve it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_project_schema import Asset, CanvasSpec, Keyframe, Layer, TTGProject, Transform, new_id

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def discover_images(asset_dir: Path) -> list[Path]:
    return sorted(path for path in asset_dir.rglob("*") if path.suffix.lower() in IMAGE_EXTS and path.is_file())


def build_ad_project(asset_dir: Path, output: Path, title: str = "TTG Events Ad") -> TTGProject:
    images = discover_images(asset_dir)
    if not images:
        raise SystemExit(f"No images found in {asset_dir}")

    project = TTGProject(name=title, project_type="motion")
    project.canvas = CanvasSpec(width=1080, height=1920, fps=30, duration=max(8.0, len(images) * 1.4), background="#050614")
    project.export.update({"format": "mp4", "quality": "1080x1920", "codec": "h264", "workflow": "ad_from_assets"})
    project.export.setdefault("creative_studio_test", {})["source_asset_dir"] = str(asset_dir)

    for index, image in enumerate(images):
        asset_id = new_id("asset")
        project.assets.append(Asset(id=asset_id, kind="image", name=image.stem, path=str(image)))
        start = round(index * 1.4, 2)
        end = round(start + 1.25, 2)
        layer = Layer(
            id=new_id("scene"),
            type="image",
            name=f"Scene {index + 1}: {image.stem}",
            transform=Transform(x=90, y=210, opacity=1),
            properties={
                "asset": asset_id,
                "path": str(image),
                "width": 900,
                "height": 1280,
                "fit": "contain",
                "scene_index": index,
                "start_time": start,
                "end_time": end,
                "motion": "push_in" if index % 2 == 0 else "slide_up",
                "shadow": True,
                "glow": True,
            },
            keyframes={
                "opacity": [Keyframe(start, 0.0), Keyframe(start + 0.18, 1.0), Keyframe(end - 0.18, 1.0), Keyframe(end, 0.0)],
                "scale_x": [Keyframe(start, 0.96), Keyframe(end, 1.04)],
                "scale_y": [Keyframe(start, 0.96), Keyframe(end, 1.04)],
            },
        )
        project.layers.append(layer)

    project.layers.append(Layer(
        id="ad_title",
        type="text3d",
        name="Ad Title",
        transform=Transform(x=90, y=70),
        properties={
            "text": "THETECHGUY DIGITAL EVENTS",
            "width": 900,
            "height": 90,
            "font_size": 54,
            "gradient": True,
            "gradient_start": "#BC13FE",
            "gradient_end": "#00E5FF",
            "glow": True,
            "stroke_width": 3,
        },
    ))
    project.layers.append(Layer(
        id="ad_cta",
        type="text",
        name="Call To Action",
        transform=Transform(x=110, y=1740),
        properties={
            "text": "Create invites • Manage guests • Share events",
            "width": 860,
            "height": 80,
            "font_size": 38,
            "color": "#F7FAFF",
            "glow": True,
        },
    ))
    project.audio_markers.extend([
        {"time": 0.0, "name": "intro hit"},
        {"time": 1.4, "name": "scene change"},
        {"time": project.canvas.duration - 1.0, "name": "final CTA"},
    ])
    output.parent.mkdir(parents=True, exist_ok=True)
    project.save(output)
    return project


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("asset_dir", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "ttg_ad_from_assets.ttgstudio.json")
    parser.add_argument("--title", default="TTG Events Ad")
    args = parser.parse_args()
    project = build_ad_project(args.asset_dir, args.output, args.title)
    print(f"Saved Creative Studio ad project: {args.output}")
    print(f"Assets: {len(project.assets)}")
    print(f"Layers: {len(project.layers)}")
    print(f"Duration: {project.canvas.duration:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
