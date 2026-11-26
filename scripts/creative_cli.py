#!/usr/bin/env python3
"""Command-line helper for TTG Creative Studio engine tests."""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_campaign_composer import CampaignBrief, compose_campaign, FORMATS
from ttg_export_service import ExportService
from ttg_intro_builder import IntroBuilder
from ttg_project_schema import TTGProject


def build_intro(args) -> int:
    project = IntroBuilder().build_ttg_intro()
    project.save(args.output)
    print(f"Saved intro project: {args.output}")
    return 0


def export_png(args) -> int:
    project = TTGProject.load(args.project)
    ExportService(ROOT).export_png(project, args.output)
    print(f"Exported PNG: {args.output}")
    return 0


def export_frames(args) -> int:
    project = TTGProject.load(args.project)
    frames = ExportService(ROOT).export_frames(project, args.output_dir)
    print(f"Exported frames: {len(frames)}")
    return 0


def export_mp4(args) -> int:
    project = TTGProject.load(args.project)
    work = Path(args.work_dir) if args.work_dir else Path(tempfile.gettempdir()) / "ttg_cli_mp4"
    ExportService(ROOT).export_mp4(project, args.output, work)
    print(f"Exported MP4: {args.output}")
    return 0


def design_campaign(args) -> int:
    brief = CampaignBrief(
        layout=args.layout,
        brand=args.brand,
        headline=args.headline,
        subhead=args.subhead,
        product_name=args.product,
        cta=args.cta,
        website=args.website,
        accent=args.accent,
        image_path=args.product_image or None,
    )
    files = compose_campaign(brief, Path(args.output_dir))
    for label, path in files.items():
        print(f"{label}: {path}")
    return 0


def donor_interchange(args) -> int:
    """Use existing Studio source/project and specialized donor exchange paths."""
    if args.operation == "export-ora":
        from ttg_openraster_bridge import export_openraster
        source = Path(args.project)
        project = TTGProject.load(source)
        result = export_openraster(
            project, args.output,
            project_root=Path(args.project_root or source.parent),
        )
    elif args.operation == "import-ora":
        from ttg_openraster_bridge import import_openraster
        result = import_openraster(args.source, args.output)
    elif args.operation == "export-otio":
        from ttg_filmcraft_otio_bridge import export_otio
        source = Path(args.project)
        result = export_otio(
            TTGProject.load(source), args.output,
            project_root=Path(args.project_root or source.parent),
        )
    elif args.operation == "import-otio":
        from ttg_filmcraft_otio_bridge import import_otio
        result = import_otio(args.source, args.output)
    elif args.operation == "export-lottie":
        from ttg_effectcraft_lottie_bridge import export_lottie
        result = export_lottie(TTGProject.load(args.project), args.output)
    elif args.operation == "import-lottie":
        from ttg_effectcraft_lottie_bridge import import_lottie
        result = import_lottie(args.source, args.output)
    elif args.operation == "export-svg":
        from ttg_vectorcraft_svg_bridge import export_svg_shapes
        result = export_svg_shapes(TTGProject.load(args.project), args.output)
    elif args.operation == "import-svg":
        from ttg_vectorcraft_svg_bridge import import_svg_shapes
        result = import_svg_shapes(args.source, args.output)
    elif args.operation == "import-lightcraft-raw":
        from ttg_lightcraft_raw_bridge import import_developed_raw
        result = import_developed_raw(args.source, args.preview_png, args.output)
    elif args.operation == "develop-lightcraft-raw":
        from ttg_lightcraft_raw_bridge import develop_with_lightcraft
        result = develop_with_lightcraft(
            args.source, args.output, lightcraft_cli=args.lightcraft_cli,
            exposure=args.exposure,
        )
    elif args.operation == "import-dxf":
        from ttg_cadcraft_dxf_bridge import import_dxf
        result = import_dxf(
            args.source, args.output,
            canvas_width=args.width, canvas_height=args.height,
            units=args.units,
        )
    elif args.operation == "export-dxf":
        from ttg_cadcraft_dxf_bridge import export_dxf
        result = export_dxf(
            TTGProject.load(args.project), args.output, units=args.units,
        )
    elif args.operation == "import-pbr":
        from ttg_material_texture_bridge import import_pbr_export_maps
        result = import_pbr_export_maps(
            args.maps_dir, args.manifest, args.output,
            material_name=args.material_name,
        )
    else:
        raise ValueError("Unknown Studio interchange operation")
    print(json.dumps(asdict(result) if is_dataclass(result) else result, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="TTG Creative Studio CLI")
    sub = parser.add_subparsers(required=True)

    p_intro = sub.add_parser("build-intro")
    p_intro.add_argument("output")
    p_intro.set_defaults(func=build_intro)

    p_png = sub.add_parser("export-png")
    p_png.add_argument("project")
    p_png.add_argument("output")
    p_png.set_defaults(func=export_png)

    p_frames = sub.add_parser("export-frames")
    p_frames.add_argument("project")
    p_frames.add_argument("output_dir")
    p_frames.set_defaults(func=export_frames)

    p_mp4 = sub.add_parser("export-mp4")
    p_mp4.add_argument("project")
    p_mp4.add_argument("output")
    p_mp4.add_argument("--work-dir", default="")
    p_mp4.set_defaults(func=export_mp4)

    p_campaign = sub.add_parser(
        "design-campaign",
        help="Create a portable editable campaign with original offline artwork",
    )
    p_campaign.add_argument("output_dir")
    p_campaign.add_argument("--layout", choices=sorted(FORMATS), default="flagship")
    p_campaign.add_argument("--brand", default="THETECHGUY")
    p_campaign.add_argument("--headline", default="BEYOND THE ORDINARY.")
    p_campaign.add_argument("--subhead", default="Designed to make your next move extraordinary.")
    p_campaign.add_argument("--product", default="NEXT GENERATION")
    p_campaign.add_argument("--cta", default="DISCOVER MORE")
    p_campaign.add_argument("--website", default="thetechguyds.com")
    p_campaign.add_argument("--accent", choices=["aqua", "violet", "amber"], default="aqua")
    p_campaign.add_argument("--product-image", default="")
    p_campaign.set_defaults(func=design_campaign)

    # Interchange is a native Studio capability; no donor executable,
    # external model or paid service is installed by these commands.
    for name in ("export-ora", "export-otio", "export-lottie", "export-svg"):
        sp = sub.add_parser(name, help="Export a Studio project to an open donor format")
        sp.add_argument("project")
        sp.add_argument("output")
        if name != "export-lottie":
            sp.add_argument("--project-root", default="")
        sp.set_defaults(func=donor_interchange, operation=name)
    for name in ("import-ora", "import-otio", "import-lottie", "import-svg"):
        sp = sub.add_parser(name, help="Import supported donor exchange as editable TTG source")
        sp.add_argument("source")
        sp.add_argument("output")
        sp.set_defaults(func=donor_interchange, operation=name)
    sp = sub.add_parser("import-pbr", help="Import verified MaterialCraft/TextureCraft exported PBR maps")
    sp.add_argument("maps_dir")
    sp.add_argument("manifest")
    sp.add_argument("output")
    sp.add_argument("--material-name", required=True)
    sp.set_defaults(func=donor_interchange, operation="import-pbr")

    sp = sub.add_parser("import-lightcraft-raw", help="Import real developed PNG and original RAW as editable Studio source")
    sp.add_argument("source", help="Original camera RAW (preserved unchanged)")
    sp.add_argument("preview_png", help="Actual developed PNG from LightCraft")
    sp.add_argument("output", help="New .ttgstudio.json project")
    sp.set_defaults(func=donor_interchange, operation="import-lightcraft-raw")

    sp = sub.add_parser("develop-lightcraft-raw", help="Use Builder-bundled LightCraft source runtime (no separate installation)")
    sp.add_argument("source", help="Original camera RAW")
    sp.add_argument("output", help="New .ttgstudio.json project")
    sp.add_argument("--lightcraft-cli", help="Optional explicit legacy/laboratory executable; normal mode uses verified Builder bundle")
    sp.add_argument("--exposure", type=float)
    sp.set_defaults(func=donor_interchange, operation="develop-lightcraft-raw")

    sp = sub.add_parser("import-dxf", help="Import bounded CADCraft ASCII 2D DXF")
    sp.add_argument("source")
    sp.add_argument("output")
    sp.add_argument("--width", required=True, type=int)
    sp.add_argument("--height", required=True, type=int)
    sp.add_argument("--units", required=True, choices=["mm", "inch", "unitless"])
    sp.set_defaults(func=donor_interchange, operation="import-dxf")

    sp = sub.add_parser("export-dxf", help="Export bounded native 2D drawing as CADCraft ASCII DXF")
    sp.add_argument("project")
    sp.add_argument("output")
    sp.add_argument("--units", required=True, choices=["mm", "inch", "unitless"])
    sp.set_defaults(func=donor_interchange, operation="export-dxf")

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
