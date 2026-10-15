#!/usr/bin/env python3
"""Verify committed campaign samples are genuine, portable native Studio projects."""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ttg_campaign_composer import FORMATS
from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_project_schema import TTGProject
from ttg_validation import ProjectValidator

def main() -> int:
    base=ROOT/"examples"/"campaigns"
    report=[]
    for layout in FORMATS:
        folder=base/layout
        manifest=json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
        if manifest["schema"]!="ttg.creative.campaign.v1":
            raise ValueError("Unexpected campaign evidence schema")
        if manifest["layout"]!=layout or manifest["canvas"]!=list(FORMATS[layout][1:]):
            raise ValueError(f"Layout drift in {layout}")
        for relative,digest in manifest["sha256"].items():
            candidate=(folder/relative).resolve()
            if not candidate.is_relative_to(folder.resolve()):
                raise ValueError("Manifest path escapes project")
            if hashlib.sha256(candidate.read_bytes()).hexdigest()!=digest:
                raise ValueError(f"Evidence hash mismatch: {layout}/{relative}")
        with zipfile.ZipFile(folder/"portable-campaign.zip") as archive:
            if sorted(archive.namelist())!=sorted([*manifest["sha256"],"manifest.json"]):
                raise ValueError("Portable archive lost dependencies")
            for relative,digest in manifest["sha256"].items():
                if hashlib.sha256(archive.read(relative)).hexdigest()!=digest:
                    raise ValueError("Portable archive differs from workspace")
        project=TTGProject.load(folder/"campaign.ttgstudio.json")
        if not ProjectValidator().is_valid(project,folder):
            raise ValueError("Committed project failed native validation")
        if len(project.layers)!=manifest["layer_count"]:
            raise ValueError("Lost native editable layers")
        actual=CanvasRenderer(RenderContext(folder)).render(project)
        with Image.open(folder/"campaign.png") as saved:
            if actual.tobytes()!=saved.convert("RGBA").tobytes():
                raise ValueError("Committed render does not match native editable source")
        report.append({"layout":layout,"layers":len(project.layers),"assets":len(project.assets),
                       "canvas":[project.canvas.width,project.canvas.height]})
    print(json.dumps({"status":"PASS","validated_campaigns":report},indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
