#!/usr/bin/env python3
"""G6 proof: previously-unseen prompts, guarded generation and editable import.

Fixtures test wiring and safety only; simulated provider pixels are NOT
evidence of real inference or photorealism. No charges/network/model installs.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ttg_professional_image_production import (
    ProfessionalImagePipeline, ProfessionalProductionError, choose_quality,
    SCHEMA, MAX_ATTEMPTS,
)
from ttg_online_image_provider import APPROVAL, build_generation_input
from ttg_project_schema import TTGProject

checks = []
def require(ok: bool, msg: str):
    if not ok:raise AssertionError(msg)
    checks.append(msg)

UNSEEN = [
    ("Architectural photo of a glass atrium with sunlight, believable marble floors", "photoreal"),
    ("Commercial product photograph of a watch with crisp steel reflections", "photoreal"),
    ("Natural portrait photograph of two people at a cafe, anatomically correct hands", "photoreal"),
    ("Photorealistic logo on a satin-black shopfront sign with tiny lettering", "brand_pro"),
    ("A landscape at dawn featuring snow, fog and three mountain cabins", "photoreal"),
    ("A food photograph of a plated avocado sandwich with glass of tea", "photoreal"),
    ("Business card mockup on textured desk with embossed brand name", "brand_pro"),
    ("A macro photograph of a precision CNC mechanism with oily gears", "photoreal"),
    ("Contemporary bedroom interior with folded white linens and warm lighting", "photoreal"),
    ("Product packaging on retail shelf with precise brand typography and labels", "brand_pro"),
    ("Portrait photo of three friends sitting at a restaurant table, five objects", "photoreal"),
]

def main():
    previous=os.environ.pop("REPLICATE_API_TOKEN",None)
    paid=os.environ.pop("TTG_STUDIO_ENABLE_PAID_IMAGE",None)
    try:
        with tempfile.TemporaryDirectory(prefix="ttg-g6-professional-") as work:
            area=Path(work)
            engine=ProfessionalImagePipeline(area)
            for prompt, expected in UNSEEN:
                result=engine.plan(prompt)
                require(result["state"]=="planned_not_generated" and
                        result["quality"]==expected and result["actual_neural_pixels_produced"] is False,
                        "Unseen prompt planned honestly: "+expected)
                model,payload=build_generation_input({
                    "quality":expected,"prompt":prompt,"aspect_ratio":"4:3"
                })
                require(result["model"]==model and "prompt" in payload,
                        "Selected the actual existing provider input contract")
            require(choose_quality("Artwork for brand logo","photoreal")=="photoreal",
                    "Explicit quality override wins against heuristics")
            require(engine.plan("Simple yellow bicycle")["quality"]=="photoreal",
                    "Unknown instruction selects neural photographic route")
            require(engine.plan("Professional tech logo")["quality"]=="brand_pro",
                    "Unknown branding instruction selects semantic text-capable route")
            require(engine.plan("Single tree")["provider_readiness"]=="credentials_required",
                    "Provider discovery recognizes missing credentials")
            require(not list(area.iterdir()),"Planning did not create fake images or spend money")
            try:
                engine.submit(name="unapproved",prompt="Photograph a bicycle")
                raise AssertionError("Paid no-consent request accepted")
            except ProfessionalProductionError as e:
                require("approval" in str(e).lower(),"Per-job billing approval blocks submissions")
            try:
                engine.submit(name="no_token",prompt="Photograph a bicycle",paid_approval=APPROVAL)
                raise AssertionError("Paid no-token request accepted")
            except Exception as e:
                require("token" in str(e).lower() or "credential" in str(e).lower(),
                        "No credential means no real provider call")
            require(not list(area.iterdir()),"Unavailable provider left no false completion files")
            subprocess.run([
                sys.executable,"-B",str(ROOT/"src/ttg_creative_studio/cli.py"),
                "--catalog",
            ],cwd=ROOT,capture_output=True,text=True,check=True,timeout=20)
            job={
                "jobId":"qa1","task":"studio_produce_photoreal",
                "output":str(area/"new_photo.png"),
                "options":{"instruction":"Original hotel lobby photograph",
                           "phase":"plan"},
            }
            path=area/"job.json"
            path.write_text(json.dumps(job))
            cli=subprocess.run([
                sys.executable,"-B",str(ROOT/"src/ttg_creative_studio/cli.py"),
                "--job",str(path),
            ],cwd=ROOT,capture_output=True,text=True,timeout=20)
            require(cli.returncode==0 and json.loads(cli.stdout)["status"]=="planned_not_generated",
                    "Shared Studio job CLI accepts neural-production planning")
            path.unlink()
            # Exercise *existing* top-level Production Director entrypoint,
            # not only a newly introduced specialist task.
            job["task"]="studio_produce"
            path.write_text(json.dumps(job))
            auto=subprocess.run([
                sys.executable,"-B",str(ROOT/"src/ttg_creative_studio/cli.py"),
                "--job",str(path),
            ],cwd=ROOT,capture_output=True,text=True,timeout=20)
            require(auto.returncode==0 and
                    json.loads(auto.stdout)["meta"]["selected_route"]=="neural_photo" and
                    json.loads(auto.stdout)["status"]=="planned_not_generated",
                    "Original Production Director auto-routes unfamiliar hotel prompt to real provider plan")
            path.unlink()
            # Explicitly synthetic provider fixture: tests real-image
            # decoder and the native project handoff, NOT generative quality.
            id="g6fixture0123456789"
            submission={
                "provider":"replicate","model":"black-forest-labs/flux-2-pro",
                "prediction_id":id,"status":"starting",
            }
            with patch("ttg_professional_image_production.submit_image",return_value=submission):
                ticket=engine.submit(name="fixture",prompt="Hotel room photograph",
                                     paid_approval=APPROVAL)
            require(ticket["state"]=="submitted" and not (area/"fixture.png").exists(),
                    "Provider submission is distinct from a completed image")
            with patch("ttg_professional_image_production.image_status",
                       return_value={"status":"processing"}):
                status=engine.inspect("fixture")
            require(status["state"]=="provider_processing" and not status["real_output_verified"],
                    "Processing prediction cannot claim generated pixels")
            with patch("ttg_professional_image_production.image_status",
                       return_value={"status":"succeeded"}):
                with patch("ttg_professional_image_production.download_image",
                           side_effect=lambda _id,dest: simulated_png(_id,Path(dest))):
                    receipt=engine.complete(ticket_name="fixture")
            require(receipt["state"]=="visual_review_required" and
                    receipt["actual_neural_pixels_produced"] is True,
                    "Provider fixture reaches visual-review state, never automatic acceptance")
            require(receipt["accepted"] is False and
                    receipt["semantic_inspection"]["state"]=="unverified_without_local_vision",
                    "No unsupported semantic claims or quality acceptance")
            require(receipt["sha256"]==hashlib.sha256((area/"fixture.png").read_bytes()).hexdigest(),
                    "Verified downloaded PNG SHA256 retained")
            project=TTGProject.load(area/"fixture.ttgstudio.json")
            require(len(project.layers)==1 and project.layers[0].type=="image" and
                    project.assets[0].sha256==receipt["sha256"],
                    "Generated raster is editable Studio layer with traceable asset")
            require(project.layers[0].properties["source_model"]==submission["model"],
                    "Original provider model identity is preserved in editable layer")
            require(project.canvas.width==256 and project.canvas.height==192,
                    "Native project matches physical decoded provider dimensions")
            try:
                engine.complete(ticket_name="fixture")
                raise AssertionError("Repeated completion accepted")
            except ProfessionalProductionError:
                require(True,"Completed job cannot be silently overwritten")
            # Genuine completed candidates can start separately approved
            # corrections; never submit a retry without explicit consent.
            with patch("ttg_professional_image_production.submit_image",
                       return_value={**submission,"prediction_id":"g6fixture2222222222"}):
                follow=engine.submit(name="revision2",prompt="Improve lighting",
                                     previous_ticket="fixture",paid_approval=APPROVAL)
            require(follow["attempt"]==2 and follow["model"]==submission["model"],
                    "Completed visual review permits a separately approved correction")
            pending=json.loads((area/"revision2.prediction.json").read_text())
            require(pending["state"]=="submitted","Pending revision has not passed visual review")
            with patch("ttg_professional_image_production.image_status",
                       return_value={"status":"processing"}):
                try:
                    engine.submit(name="bad_revision",prompt="Different design",previous_ticket="revision2",
                                  paid_approval=APPROVAL)
                    raise AssertionError("Revision submitted while previous job processing")
                except ProfessionalProductionError:
                    require(True,"New paid correction blocked while previous provider job processes")
            require(not (area/"bad_revision.prediction.json").exists(),
                    "Blocked revision created no ticket")
    finally:
        if previous is not None:os.environ["REPLICATE_API_TOKEN"]=previous
        if paid is not None:os.environ["TTG_STUDIO_ENABLE_PAID_IMAGE"]=paid
    print(json.dumps({"status":"PASS","checks":len(checks),
                      "real_provider_inference":"NOT_TESTED",
                      "mock_images_are_not_evidence":True},indent=2))


def simulated_png(prediction_id: str, destination: Path) -> dict:
    Image.new("RGB",(256,192),(40,65,99)).save(destination,"PNG")
    raw=destination.read_bytes()
    return {"path":str(destination),"sha256":hashlib.sha256(raw).hexdigest(),
            "width":256,"height":192,"prediction_id":prediction_id}


if __name__=="__main__":
    main()
