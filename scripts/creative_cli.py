#!/usr/bin/env python3
"""Command-line helper for TTG Creative Studio engine tests."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

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

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
