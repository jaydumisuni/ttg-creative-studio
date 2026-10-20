#!/usr/bin/env python3
"""Prove Creative Studio owns resource discovery, routing, render and evidence."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile

from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ttg_production_director import ProductionDirector,ProductionError
from ttg_project_schema import TTGProject,Layer,Transform,Asset

CHECKS=[]

def require(value,reason):
    if not value:raise AssertionError(reason)
    CHECKS.append(reason)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def fixture(root):
    catalog=root/"catalog"
    output=root/"out"
    catalog.mkdir();output.mkdir()
    assets=catalog/"assets"
    assets.mkdir()
    base=Image.new("RGBA",(160,120),(17,24,36,255))
    base.save(assets/"background.png")
    top=Image.new("RGBA",(160,120),(0,0,0,0))
    draw=ImageDraw.Draw(top)
    draw.rectangle((32,42,128,74),fill=(73,177,237,255))
    top.save(assets/"emblem.png")
    expected=Image.alpha_composite(base,top).convert("RGB")
    expected.save(assets/"reference_unmodified.png")
    project=TTGProject(name="Wall Sign Visual Receipt",project_type="image")
    project.canvas.width=160
    project.canvas.height=120
    project.canvas.background="#111824"
    project.assets=[]
    for n in ["background","emblem","reference_unmodified"]:
        p=assets/(n+".png")
        project.assets.append(Asset(id=n,kind="image",name=n,path="assets/"+p.name,
                                    sha256=sha(p),required=True))
    project.layers=[
        Layer(id="bg",type="image",name="architecture",properties={"path":"assets/background.png"}),
        Layer(id="logo",type="image",name="editable logo",properties={"path":"assets/emblem.png"}),
        Layer(id="reference",type="image",name="original hidden for comparison",
              visible=False,properties={"path":"assets/reference_unmodified.png"}),
    ]
    path=catalog/"wall_sign.ttgstudio.json"
    project.save(path)
    return catalog,output,assets/"reference_unmodified.png",path

def main():
    with tempfile.TemporaryDirectory(prefix="studio-own-production-") as directory:
        root=Path(directory)
        catalog,out,reference,project_file=fixture(root)
        director=ProductionDirector([catalog],out)
        discovery=director.discover(reference)
        require(discovery["catalog_projects_checked"]==1,
                "Only approved catalog projects inspected")
        require(len(discovery["eligible_reference_projects"])==1,
                "Studio located existing matching editable project")
        plan=director.produce(instruction="Recreate exact lobby wall logo",
                              reference=reference,exact=True,
                              output_name="studio_recreation",dry_run=True)
        require(plan["state"]=="planned_not_rendered" and
                not list(out.iterdir()),"Planning is side-effect free")
        report=director.produce(instruction="Recreate exact lobby wall logo",
                                reference=reference,exact=True,
                                output_name="studio_recreation")
        require(report["pixel_exact"] and report["state"]=="accepted_exact",
                "Native Studio compositor produced exact requested pixels")
        require(report["render_sha256"]==sha(out/"studio_recreation.png"),
                "Production receipt SHA256 matches actual emitted PNG")
        restored=TTGProject.load(out/"studio_recreation.ttgstudio.json")
        require(len(restored.layers)==3 and not restored.layers[-1].visible,
                "Portably saved project retains editable and hidden reference layers")
        require(all((out/asset.path).is_file() for asset in restored.assets),
                "Portable assets resolve relative to saved project")
        require(len(list((out/"studio_recreation_assets").glob("*.png")))==3,
                "Resource selector copied or hard-linked only three required assets")
        require(json.loads((out/"studio_recreation.receipt.json").read_text())["pixel_exact"],
                "Receipt is durable and objectively checkable")
        try:
            director.produce(instruction="Recreate exact lobby wall logo",
                             reference=reference,exact=True,
                             output_name="studio_recreation")
            require(False,"Output overwrite must be blocked")
        except ProductionError as e:
            require("already exist" in str(e),"Existing artwork never overwritten")
        bad=Image.new("RGB",(160,120),(30,80,40))
        bad.save(catalog/"unrelated.png")
        try:
            director.produce(instruction="Exact scene",reference=catalog/"unrelated.png",
                             exact=True,output_name="bad")
            require(False,"Reference mismatch must reject")
        except ProductionError:
            require(not (out/"bad.png").exists(),"Wrong reference fails without fake output")
        original=project_file.read_text()
        tampered=TTGProject.load(project_file)
        tampered.assets[0].sha256="f"*64
        tampered.save(project_file)
        try:
            director.produce(instruction="Exact scene",reference=reference,
                             exact=True,output_name="corrupt")
            require(False,"Checksum mismatch must reject")
        except ProductionError:
            require(not (out/"corrupt.png").exists(),
                    "Corrupt asset manifest blocks rendering")
        project_file.write_text(original)
        native_plan=director.produce(instruction="Professional THETECHGUY office wall sign",
                                     output_name="native_plan",dry_run=True)
        require(native_plan["mode"]=="studio_native_procedural_scene" and
                not native_plan["verified_assets"],
                "No-model native rendering selected for supported request")
        try:
            director.produce(instruction="Make an arbitrary photo of an elephant eating stars",
                             output_name="unsupported",dry_run=True)
            require(False,"Unsupported scenes must fail closed")
        except ProductionError:
            require(not (out/"unsupported.png").exists(),
                    "Unsupported prompt does not fake neural inference")
        # The same Studio-owned path must also work through the existing
        # generic AI/job CLI; no Hunter session or Ptah Control is involved.
        catalog_cli=subprocess.run(
            [sys.executable,"-B",str(ROOT/"src/ttg_creative_studio/cli.py"),"--catalog"],
            capture_output=True,text=True,timeout=24
        )
        require(catalog_cli.returncode==0 and
                "studio_produce" in json.loads(catalog_cli.stdout)["operations"],
                "Shared Studio tool registry exposes production routing")
        job={
            "jobId":"studio-production-proof",
            "task":"studio_produce",
            "input":str(reference),
            "output":str(out/"through_job_runner.png"),
            "options":{
                "instruction":"Recreate editable wall sign exactly",
                "catalog_roots":[str(catalog)],
                "exact":True,
            },
        }
        path=out/"production.job.json"
        path.write_text(json.dumps(job))
        executed=subprocess.run(
            [sys.executable,"-B",str(ROOT/"src/ttg_creative_studio/cli.py"),
             "--job",str(path),"--result",str(out/"production.result.json")],
            capture_output=True,text=True,timeout=40
        )
        response=json.loads((out/"production.result.json").read_text())
        require(executed.returncode==0 and response["ok"] and
                response["meta"]["pixel_exact"],
                "Existing generic Studio job CLI dispatches actual Studio rendering")
        require(not report["chargeable_provider_used"] and
                not report["hunter_connected"],
                "No paid provider or Hunter involvement")
    print(json.dumps({"status":"PASS","check_count":len(CHECKS),"checks":CHECKS},indent=2))

if __name__=="__main__":
    main()
