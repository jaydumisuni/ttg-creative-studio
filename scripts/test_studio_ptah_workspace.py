#!/usr/bin/env python3
"""Real Studio image/video jobs executed from permitted Ptah workspace directory.

This is a physical file/job compatibility test, not a production Ptah Node
admission nor an authenticated A05 process lease. Does not contact providers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from PIL import Image

STUDIO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIO / "src"))
PTAH = Path("/home/kratos/projects/Ptah-space")
SCHEMA = "ttg.studio.ptah-directory-smoke.v1"


def digest(path: Path) -> str:
    hasher=hashlib.sha256()
    with path.open("rb") as f:
        for piece in iter(lambda:f.read(1024*1024),b""):
            hasher.update(piece)
    return hasher.hexdigest()


def run(job: dict, cwd: Path, name: str) -> dict:
    request=cwd/(name+".job.json")
    result=cwd/(name+".result.json")
    if request.exists() or result.exists():
        raise RuntimeError("Refusing to overwrite prior Ptah workspace evidence")
    request.write_text(json.dumps(job,indent=2)+"\n")
    env=os.environ.copy()
    env.pop("REPLICATE_API_TOKEN",None)
    env.pop("TTG_STUDIO_ENABLE_PAID_IMAGE",None)
    env.pop("TTG_STUDIO_ENABLE_PAID_VIDEO",None)
    env.setdefault("QT_QPA_PLATFORM","offscreen")
    p=subprocess.run([sys.executable,"-B",str(STUDIO/"src/ttg_creative_studio/cli.py"),
                      "--job",str(request),"--result",str(result)],
                     cwd=cwd,env=env,capture_output=True,text=True,timeout=100)
    reply=json.loads(result.read_text())
    return {"rc":p.returncode,"reply":reply,"request_sha256":digest(request),
            "receipt_sha256":digest(result)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--workspace",type=Path,default=PTAH/".workspace/scratch/creative-studio-main-20261018")
    args=parser.parse_args()
    target=args.workspace
    allowed=(PTAH/".workspace/scratch").resolve()
    if not PTAH.is_dir() or not (PTAH/"crates/ptah-workspace").is_dir():
        raise RuntimeError("Ptah source checkout and A06 workspace crate unavailable")
    if target.is_symlink():
        raise ValueError("Ptah workspace may not be a symlink")
    absolute=target.resolve()
    if not absolute.is_relative_to(allowed) or absolute==allowed:
        raise ValueError("Workspace must be a child of the approved Ptah scratch root")
    if absolute.exists() and any(absolute.iterdir()):
        raise ValueError("Refusing existing nonempty workspace to avoid storage waste/overwrite")
    absolute.mkdir(parents=True,exist_ok=True)
    from ttg_action_engine import ActionEngine
    from ttg_project_schema import TTGProject
    from ttg_image_lab import apply_adjustments
    path=absolute
    image=path/"source.png"
    Image.new("RGB",(120,80),(36,105,174)).save(image)
    enhanced=path/"enhanced.png"
    apply_adjustments(Image.open(image),brightness=1.2,contrast=1.1).save(enhanced)
    reports=[]
    p=run({"task":"image_info","jobId":"ptah_image_info",
        "input":str(image),"output":str(path/"image_info.json")},path,"image_info")
    assert p["rc"]==0 and p["reply"]["ok"]
    reports.append(("image_info",p))
    p=run({"task":"resize_image","jobId":"ptah_resize",
        "input":str(image),"output":str(path/"resized.png"),
        "options":{"width":60,"height":40}},path,"resize")
    assert p["rc"]==0 and p["reply"]["ok"]
    with Image.open(path/"resized.png") as x: assert x.size==(60,40)
    reports.append(("resize_image",p))
    p=run({"task":"video_capabilities","jobId":"ptah_capabilities"},path,"capabilities")
    assert p["rc"]==0 and p["reply"]["ok"]
    assert p["reply"]["meta"]["generation"]["online"]["state"]=="credentials_required"
    catalog=subprocess.run(
        [sys.executable,"-B",str(STUDIO/"src/ttg_creative_studio/cli.py"),"--catalog"],
        cwd=path,capture_output=True,text=True,timeout=20
    )
    assert catalog.returncode==0
    assert "image_generate_online" in json.loads(catalog.stdout)["operations"]
    reports.append(("capabilities",p))
    p=run({"task":"video_plan","jobId":"ptah_plan","output":str(path/"storyboard.json"),
        "options":{"fps":24,"scenes":[{"description":"Product still","seconds":1},
                        {"description":"Animated brand reveal","seconds":1}]}},path,"video_plan")
    assert p["rc"]==0 and p["reply"]["ok"]
    assert json.loads((path/"storyboard.json").read_text())["status"]=="review_required"
    reports.append(("video_plan",p))
    action=ActionEngine()
    project=action.new_project("Ptah workspace Studio render","motion")
    project.canvas.width=160
    project.canvas.height=90
    project.canvas.fps=4
    project.canvas.duration=.5
    action.add_shape(project,"rectangle",10,10)
    model=path/"editable.ttgstudio.json"
    project.save(model)
    p=run({"task":"video_render","jobId":"ptah_render",
          "input":str(model),"output":str(path/"render.mp4")},path,"video_render")
    assert p["rc"]==0 and p["reply"]["ok"]
    assert (path/"render.mp4").stat().st_size>300
    reports.append(("video_render",p))
    # The two unpaid cloud routes must reject unauthorized requests when
    # executed from a Ptah workspace just as they do directly in Studio.
    for name,job in [
        ("image_cloud_no_approval",{"task":"image_generate_online","options":{"prompt":"A phone"}}),
        ("video_cloud_no_approval",{"task":"video_generate","options":{"prompt":"A phone"}}),
    ]:
        p=run(job,path,name)
        assert p["rc"]!=0 and p["reply"]["ok"] is False
        reports.append((name,p))
    manifest={
        "schema":SCHEMA,"studio_source":str(STUDIO),"workspace":str(path),
        "ptah_checkout":str(PTAH),"ptah_runtime_enrolled":False,
        "ptah_adapter_used":False,
        "evidence_scope":"Studio executable running under Ptah scratch working directory",
        "cloud_calls":0,"model_downloads":0,"reports":[{
            "operation":name,"exit_code":x["rc"],
            "request_sha256":x["request_sha256"],
            "receipt_sha256":x["receipt_sha256"]
        } for name,x in reports],
        "actual_artifacts":[{
            "name":name,"size_bytes":(path/name).stat().st_size,
            "sha256":digest(path/name)
        } for name in ("enhanced.png","resized.png","storyboard.json",
                       "editable.ttgstudio.json","render.mp4")],
    }
    evidence=path/"studio-ptah-workspace-proof.json"
    evidence.write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"status":"PASS","workspace":str(path),
          "checks":len(reports)+len(manifest["actual_artifacts"]),
          "manifest_sha256":digest(evidence),
          "ptah_runtime_enrolled":False,"model_downloads":0},indent=2))


if __name__=="__main__":
    main()
