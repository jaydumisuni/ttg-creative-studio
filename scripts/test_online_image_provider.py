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
from PyQt6.QtWidgets import QApplication
from ttg_online_image_provider import (
    readiness,submit_image,image_status,image_cancel,download_image,
    VideoProviderError,APPROVAL,validate_public_https,
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
            check(all("fixture-only-no-real-account" not in str(url)
                      for method,url,payload in fake.calls),
                  "API token never placed into URLs or image receipts")

        with patch.dict(os.environ,{"REPLICATE_API_TOKEN":"","TTG_STUDIO_ENABLE_PAID_IMAGE":""}):
            app=QApplication.instance() or QApplication([])
            ui=OnlineImageDialog()
            check(not ui.consent.isChecked(),"Paid image consent unchecked by default")
            check("No provider token" in ui.ready.text(),
                  "Offline/no-token image UI indicates requirement")
            ui.close()
            desktop=CreativeWorkspace()
            check(hasattr(desktop,"open_online_image"),
                  "Standalone Studio Tools can open image generator")
            desktop.close()
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
