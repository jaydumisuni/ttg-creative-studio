#!/usr/bin/env python3
"""Standalone image provider qualification. No network calls or billing.

The simulated provider PNG is a protocol fixture, not proof of AI inference.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PIL import Image
from PyQt6.QtWidgets import QApplication,QMessageBox
from ttg_online_image_provider import (
    readiness,submit_image,image_status,image_cancel,download_image,
    VideoProviderError,APPROVAL,validate_public_https,
    compact_reference_image, build_generation_input,
)
from ttg_online_image_dialog import OnlineImageDialog
from ttg_creative_studio.engine.online_image_jobs import run_online_image_job
from ttg_creative_workspace import CreativeWorkspace

passed=[]

def check(ok,label):
    if not ok:raise AssertionError(label)
    passed.append(label)

def denied(run,part):
    try:run()
    except (VideoProviderError,RuntimeError) as error:
        check(part.lower() in str(error).lower(),"Fail-closed: "+part)
    else:raise AssertionError("Unexpectedly allowed "+part)

class Reply:
    def __init__(self,raw):
        self.buf=io.BytesIO(raw)
    def __enter__(self):return self
    def __exit__(self,*args):self.buf.close()
    def read(self,n=-1):return self.buf.read(n)

class Fake:
    def __init__(self,prediction,blob):
        self.prediction=prediction
        self.blob=blob
        self.calls=[]
    def open(self,request,timeout=None):
        self.calls.append((request.get_method(),request.full_url,request.data))
        if request.full_url.startswith("https://replicate.delivery/"):
            return Reply(self.blob)
        return Reply(json.dumps(self.prediction).encode())

def main():
    token=os.environ.pop("REPLICATE_API_TOKEN",None)
    paid=os.environ.pop("TTG_STUDIO_ENABLE_PAID_IMAGE",None)
    try:
        check(readiness()["state"]=="credentials_required",
              "Missing image-cloud credentials reported without network")
        check(readiness()["local_checkpoint_installed_by_studio"] is False,
              "KRATOS image checkpoint not downloaded")
        denied(lambda:submit_image({"prompt":"phone"}),"approval")
        from ttg_online_video_provider import APPROVAL as VIDEO_APPROVAL
        denied(lambda:submit_image({"prompt":"phone","paid_approval":VIDEO_APPROVAL}),
               "approval")
        denied(lambda:submit_image({"prompt":"phone","paid_approval":APPROVAL}),
               "REPLICATE_API_TOKEN")
        denied(lambda:validate_public_https("http://127.0.0.1/bad.png"),"HTTPS")
        denied(lambda:validate_public_https("https://localhost/bad.png"),"HTTPS")
        os.environ["REPLICATE_API_TOKEN"]="fixture-only-no-real-account"
        denied(lambda:submit_image({"prompt":"phone","paid_approval":APPROVAL}),
               "operator")
        os.environ["TTG_STUDIO_ENABLE_PAID_IMAGE"]="1"
        denied(lambda:submit_image({"operation":"remove-all-guardrails","prompt":"phone",
                                     "paid_approval":APPROVAL}),"Unsupported")
        denied(lambda:submit_image({"operation":"edit","prompt":"replace background",
                                     "paid_approval":APPROVAL}),"reference")
        with tempfile.TemporaryDirectory(prefix="studio-cloud-image-") as temp:
            image=Image.new("RGB",(64,48),(42,78,150))
            data=io.BytesIO()
            image.save(data,format="PNG")
            blob=data.getvalue()
            prediction={"id":"abcdefghijkl0001","status":"starting"}
            fake=Fake(prediction,blob)
            with patch("urllib.request.build_opener",return_value=fake):
                created=submit_image({"operation":"generate","prompt":"New product art",
                    "aspect_ratio":"1:1","paid_approval":APPROVAL})
                check(created["status"]=="starting" and
                      fake.calls[0][1].endswith("/models/black-forest-labs/flux-schnell/predictions"),
                      "Approved FLUX image generation endpoint selected")
                sent=json.loads(fake.calls[0][2])
                check(sent["input"]["num_outputs"]==1 and
                      "paid_approval" not in sent["input"],
                      "Exactly one image requested, consent not leaked")
                from ttg_online_image_provider import GENERATION_PROFILES
                check("brand_pro" in GENERATION_PROFILES and
                      "photoreal" in GENERATION_PROFILES,
                      "Professional profiles discoverable from existing provider")
                for profile, model in (
                    ("photoreal","black-forest-labs/flux-2-pro"),
                    ("brand_pro","google/nano-banana-pro"),
                ):
                    fake.calls.clear()
                    outcome=submit_image({
                        "operation":"generate","quality":profile,
                        "prompt":"Professional THETECHGUY wall sign",
                        "aspect_ratio":"4:3","paid_approval":APPROVAL})
                    payload=json.loads(fake.calls[0][2])["input"]
                    check(fake.calls[0][1].endswith("/models/"+model+"/predictions")
                          and outcome["model"]==model,
                          "Model-specific quality route selects "+profile)
                    check(payload["output_format"]=="png"
                          and "num_inference_steps" not in payload
                          and "num_outputs" not in payload
                          and "paid_approval" not in payload,
                          "High-quality request does not reuse fast-only settings or leak consent")
                    if profile=="photoreal":
                        check(payload["resolution"]=="2 MP"
                              and payload["input_images"]==[]
                              and "image_input" not in payload,
                              "FLUX.2 Pro uses correct input_images field")
                    else:
                        check(payload["resolution"]=="2K"
                              and payload["image_input"]==[]
                              and "allow_fallback_model" not in payload,
                              "Nano Banana Pro uses published image_input schema, no invented fallback option")
                fake.calls.clear()
                reference_uri="https://replicate.delivery/ttg/reference.webp"
                for selected, expected_key in (
                    ("photoreal","input_images"),("brand_pro","image_input")
                ):
                    outcome=submit_image({
                        "operation":"generate","quality":selected,
                        "prompt":"Preserve TG signage geometry and wordmark",
                        "reference_image":reference_uri,
                        "aspect_ratio":"match_input_image","paid_approval":APPROVAL
                    })
                    sent=json.loads(fake.calls[-1][2])["input"]
                    check(sent[expected_key]==[reference_uri]
                          and sent["aspect_ratio"]=="match_input_image"
                          and outcome["reference_supplied"],
                          "Professional "+selected+" receives actual approved reference")
                model,pure=build_generation_input({
                    "quality":"brand_pro","prompt":"THETECHGUY sign",
                    "reference_image":reference_uri,
                    "aspect_ratio":"match_input_image"
                })
                check(model=="google/nano-banana-pro" and
                      pure["image_input"]==[reference_uri],
                      "Professional reference payload can be reviewed without network/billing")
                denied(lambda:build_generation_input({
                    "quality":"fast","prompt":"sign",
                    "reference_image":reference_uri,
                }),"does not support reference")
                denied(lambda:build_generation_input({
                    "quality":"brand_pro","prompt":"sign",
                    "aspect_ratio":"match_input_image"
                }),"requires a selected reference")
                denied(lambda:build_generation_input({
                    "quality":"brand_pro","prompt":"sign",
                    "reference_image":"http://localhost/private.jpg"
                }),"HTTPS")
                denied(lambda:submit_image({
                    "operation":"generate","quality":"unsupported",
                    "prompt":"product","paid_approval":APPROVAL,
                }),"quality profile")
                fake.calls.clear()
                prediction["status"]="processing"
                check(image_status("abcdefghijkl0001")["status"]=="processing",
                      "Remote image job progress observed")
                prediction["status"]="succeeded"
                prediction["output"]=["https://replicate.delivery/ttg/example.png"]
                check(image_status("abcdefghijkl0001")["done"],
                      "Real-provider success response is parsed")
                target=Path(temp)/"cloud.png"
                receipt=download_image("abcdefghijkl0001",target)
                check(receipt["width"]==64 and receipt["height"]==48 and
                      target.is_file() and receipt["sha256"]==hashlib.sha256(target.read_bytes()).hexdigest(),
                      "Provider image pixels verified, normalized, and SHA256 recorded")
                denied(lambda:download_image("abcdefghijkl0001",target),"unused")
                prediction["output"]=["https://evil.invalid/x.png"]
                denied(lambda:download_image("abcdefghijkl0001",
                                            Path(temp)/"other.png"),"approved")
                prediction["output"]=["https://replicate.delivery/ttg/example.png"]
                bad=Fake(prediction,b"not image pixels")
                with patch("urllib.request.build_opener",return_value=bad):
                    denied(lambda:download_image("abcdefghijkl0001",
                                                Path(temp)/"invalid.png"),"valid bounded image")
                    check(not (Path(temp)/"invalid.png").exists(),
                          "Invalid remote image leaves no final file")
                prediction["status"]="canceled"
                del prediction["output"]
                check(image_cancel("abcdefghijkl0001")["status"]=="canceled",
                      "Cancel an individual image prediction")
            # A photographic PNG larger than the old 235 KB inline limit
            # must be usable as a downsampled visual guide, without mutation
            # or provider upload.
            import random
            rng=random.Random(491)
            pixels=rng.randbytes(1024*768*3)
            sample=Path(temp)/"user-reference.png"
            Image.frombytes("RGB",(1024,768),pixels).save(sample)
            original_digest=hashlib.sha256(sample.read_bytes()).hexdigest()
            check(sample.stat().st_size>235_000,"Large real-photo reference fixture")
            prepared=compact_reference_image(sample)
            check(prepared["source_sha256"]==original_digest
                  and prepared["transmitted_bytes"]<=235_000
                  and prepared["reference_compressed"]
                  and hashlib.sha256(sample.read_bytes()).hexdigest()==original_digest,
                  "Large reference safely compressed in memory; original retained")
            from ttg_online_image_provider import image_input_uri
            check(image_input_uri(prepared["uri"])==prepared["uri"],
                  "Compressed photo validated as provider-accepted inline reference")
            check(all("fixture-only-no-real-account" not in str(url)
                      for method,url,payload in fake.calls),
                  "API token never placed into URLs or image receipts")

        with patch.dict(os.environ,{"REPLICATE_API_TOKEN":"","TTG_STUDIO_ENABLE_PAID_IMAGE":""}):
            app=QApplication.instance() or QApplication([])
            ui=OnlineImageDialog()
            check(not ui.consent.isChecked(),"Paid image consent unchecked by default")
            check(ui.quality.currentData()=="brand_pro",
                  "Premium branded visual quality selected by default with no billing enabled")
            ui.operation.setCurrentIndex(1)
            check(not ui.quality.isEnabled(),
                  "Generation-only quality selection disabled during editing")
            ui.operation.setCurrentIndex(0)
            check(ui.quality.isEnabled(),
                  "Generation-only quality control re-enabled when appropriate")
            check("No provider token" in ui.ready.text(),
                  "Offline/no-token image UI indicates requirement")
            ui.prepare_wall_sign_recreation()
            check(ui.quality.currentData()=="brand_pro"
                  and "THETECHGUY" in ui.prompt.toPlainText()
                  and "DIGITAL SOLUTIONS" in ui.prompt.toPlainText()
                  and "No provider called" in ui.log.toPlainText(),
                  "Professional recreation preset prepares exact wordmark without billing")
            with tempfile.TemporaryDirectory(prefix="studio-large-reference-ui-") as check_dir:
                sample=Path(check_dir)/"photo.png"
                Image.frombytes("RGB",(800,600),rng.randbytes(800*600*3)).save(sample)
                with patch("PyQt6.QtWidgets.QFileDialog.getOpenFileName",
                           return_value=(str(sample),"")):
                    ui.select_local_source()
            check(ui._source_manifest is not None
                  and ui._local_source.startswith("data:image/webp;base64,"),
                  "Image Lab accepts full-size local visual references without uploading")
            with patch("ttg_online_image_dialog.readiness",
                       return_value={"state":"configured"}), patch(
                       "PyQt6.QtWidgets.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.Yes), patch.object(
                       ui,"_start") as begin:
                ui.consent.setChecked(True)
                ui.prompt.setPlainText("THETECHGUY wall sign with silver TG")
                ui.ratio.setCurrentText("match_input_image")
                ui.generate()
                sent=begin.call_args.kwargs["settings"]
                check(sent["reference_image"]==ui._local_source and
                      sent["quality"]=="brand_pro" and
                      sent["input_image"]=="" and not ui.consent.isChecked(),
                      "Explicit GUI paid confirmation carries chosen reference into generator")
            ui.close()
            desktop=CreativeWorkspace()
            check(hasattr(desktop,"open_online_image"),
                  "Standalone Studio Tools can open image generator")
            desktop.close()
            from ttg_action_engine import ActionEngine
            from ttg_project_schema import TTGProject
            with tempfile.TemporaryDirectory(prefix="studio-cloud-image-project-") as owned:
                owned=Path(owned)
                project=ActionEngine().new_project("Cloud Image Import QA","image")
                project_file=owned/"editable.ttgstudio.json"
                project.save(project_file)
                editor=CreativeWorkspace(owned)
                editor.project=project
                editor.project_path=project_file
                editor._set_asset_root(owned)
                assets=owned/"assets"/"image-lab"
                cloud=OnlineImageDialog(import_callback=editor.import_image_lab_result,
                                        destination_dir=assets)
                cloud.prediction.setText("abcdefghijkl0001")
                cloud._latest={"status":"succeeded","prediction_id":"abcdefghijkl0001"}
                expected=assets/"online-abcdefghijkl0001.png"
                with patch.object(cloud,"_start") as begin:
                    cloud.save_image()
                    check(begin.call_args.kwargs["destination"]==str(expected),
                          "Cloud image saves inside current editable project by default")
                assets.mkdir(parents=True,exist_ok=True)
                Image.new("RGB",(64,48),(30,100,190)).save(expected)
                cloud._completed("submit",{
                    "prediction_id":"abcdefghijkl0001","model":"google/nano-banana-pro",
                    "quality":"brand_pro","status":"starting",
                    "reference_supplied":True,
                })
                cloud._completed("download",{
                    "path":str(expected),"provider":"replicate",
                    "prediction_id":"abcdefghijkl0001",
                    "sha256":hashlib.sha256(expected.read_bytes()).hexdigest(),
                    "width":64,"height":48,
                })
                receipt=editor.selected_layer().properties["online_generation_provenance"]
                check(receipt["model"]=="google/nano-banana-pro"
                      and receipt["model_identity_verified"]
                      and receipt["prediction_id"]=="abcdefghijkl0001"
                      and "prompt" not in receipt,
                      "Exact provider prediction and model preserved on editable result")
                check(editor.selected_layer() is not None and
                      editor.selected_layer().type=="image",
                      "Cloud result imports as an actual editable Studio image layer")
                editor.save_project()
                persisted=TTGProject.load(project_file)
                check(persisted.layers and persisted.layers[0].type=="image"
                      and persisted.layers[0].properties[
                          "online_generation_provenance"]["model_identity_verified"],
                      "Cloud-origin editable image and provider receipt survive save/reopen")
                cloud.close()
                editor.close()
                app.processEvents()
        check("image_generate_online" in
              subprocess.run([sys.executable,"-B",str(ROOT/"src/ttg_creative_studio/cli.py"),
                              "--catalog"],cwd=ROOT,capture_output=True,text=True,timeout=15).stdout,
              "Shared CLI advertises optional online image without requiring Hunter")
    finally:
        if token is None:os.environ.pop("REPLICATE_API_TOKEN",None)
        else:os.environ["REPLICATE_API_TOKEN"]=token
        if paid is None:os.environ.pop("TTG_STUDIO_ENABLE_PAID_IMAGE",None)
        else:os.environ["TTG_STUDIO_ENABLE_PAID_IMAGE"]=paid
    print(json.dumps({"result":"PASS","checks":len(passed),"names":passed},indent=2))

if __name__=="__main__":
    main()
