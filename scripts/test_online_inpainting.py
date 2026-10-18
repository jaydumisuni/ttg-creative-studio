#!/usr/bin/env python3
"""No-charge FLUX Fill provider schema, local masking and UI evidence.

All Replicate HTTP responses are synthetic. This is NOT a real inference run.
"""
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PIL import Image,ImageDraw
from PyQt6.QtWidgets import QApplication,QMessageBox
from ttg_online_image_provider import (
    APPROVAL, VideoProviderError, inline_image_url, image_input_uri,
    submit_image, IMAGE_MODELS,
)
from ttg_online_image_dialog import OnlineImageDialog

checks=[]

def check(expr,name):
    assert expr,name
    checks.append(name)

def denied(fn,part):
    try:fn()
    except VideoProviderError as e:
        check(part.lower() in str(e).lower(),"Refused "+part)
    else:raise AssertionError("Unexpected inpainting permission: "+part)

class Reply:
    def __init__(self,payload):self.data=io.BytesIO(payload)
    def __enter__(self):return self
    def __exit__(self,*args):self.data.close()
    def read(self,n=-1):return self.data.read(n)

class Opener:
    def __init__(self):self.calls=[]
    def open(self,request,timeout=None):
        self.calls.append((request.get_method(),request.full_url,request.data))
        return Reply(json.dumps({"id":"abcdefghijkl9090","status":"starting"}).encode())

def main():
    with tempfile.TemporaryDirectory(prefix="ttg-inpaint-contract-") as temp:
        parent=Path(temp)
        image=parent/"source.png"
        mask=parent/"mask.png"
        mismatch=parent/"mismatch.png"
        Image.new("RGB",(110,85),(80,115,155)).save(image)
        sample=Image.new("L",(110,85),0)
        ImageDraw.Draw(sample).rectangle((10,15,49,55),fill=255)
        sample.save(mask)
        Image.new("L",(85,85),255).save(mismatch)
        image_uri=inline_image_url(image)
        mask_uri=inline_image_url(mask)
        other_uri=inline_image_url(mismatch)
        check(image_uri.startswith("data:image/png;base64,")
              and mask_uri.startswith("data:image/png;base64,"),
              "Selected local pixels represented as bounded data URIs")
        check(image_input_uri(mask_uri)==mask_uri,"Valid local mask bytes accepted")
        denied(lambda:image_input_uri("data:image/png;base64,YWJj"),"bounded")
        denied(lambda:image_input_uri("http://localhost/private"),"HTTPS")
        bad=parent/"bad.png"
        bad.write_text("not an image")
        denied(lambda:inline_image_url(bad),"valid bounded")
        huge=parent/"oversize.png"
        huge.write_bytes(b"x"*235001)
        denied(lambda:inline_image_url(huge),"235")
        link=parent/"link.png"
        link.symlink_to(image)
        denied(lambda:inline_image_url(link),"regular")
        with patch.dict(os.environ,{
            "REPLICATE_API_TOKEN":"fake-contract-only",
            "TTG_STUDIO_ENABLE_PAID_IMAGE":"1",
        }):
            denied(lambda:submit_image({"operation":"inpaint","prompt":"restore details",
                  "input_image":image_uri,"paid_approval":APPROVAL}),"both")
            denied(lambda:submit_image({"operation":"inpaint","prompt":"restore details",
                  "input_image":image_uri,"mask_image":other_uri,
                  "paid_approval":APPROVAL}),"matching")
            denied(lambda:submit_image({"operation":"inpaint","prompt":"restore details",
                  "input_image":image_uri,"mask_image":mask_uri,
                  "paid_approval":"APPROVE_PAID_VIDEO_GENERATION"}),"approval")
            opener=Opener()
            with patch("urllib.request.build_opener",return_value=opener):
                result=submit_image({
                    "operation":"inpaint","prompt":"Replace marked phone case with blue",
                    "input_image":image_uri,"mask_image":mask_uri,
                    "paid_approval":APPROVAL,
                })
                check(result["prediction_id"]=="abcdefghijkl9090",
                      "Inpaint returns provider job identity without invented pixels")
                check(len(opener.calls)==1 and opener.calls[0][1].endswith(
                      "/models/black-forest-labs/flux-fill-pro/predictions"),
                      "Official FLUX Fill provider endpoint is used")
                request=json.loads(opener.calls[0][2])
                check(request["input"]["image"]==image_uri and
                      request["input"]["mask"]==mask_uri,
                      "White/black mask and image transmitted as separate references")
                check(request["input"]["steps"]==30 and
                      request["input"]["output_format"]=="png" and
                      request["input"]["outpaint"]=="None",
                      "Official inpaint input parameters match provider schema")
                check("paid_approval" not in request["input"] and
                      "fake-contract-only" not in str(request),
                      "Approval and API token never included in model input")
                # Larger source/mask assets can use externally provided HTTPS URLs
                response=submit_image({
                    "operation":"inpaint","prompt":"Fix scratched product background",
                    "input_image":"https://example.com/source.png",
                    "mask_image":"https://example.com/mask.png",
                    "paid_approval":APPROVAL,
                })
                check(response["status"]=="starting",
                      "Public HTTPS references accepted without local model weights")
        app=QApplication.instance() or QApplication([])
        ui=OnlineImageDialog()
        idx=ui.operation.findData("inpaint")
        check(idx>=0 and ui.operation.itemText(idx).startswith("Inpaint"),
              "Standalone Image Lab exposes inpainting operation")
        check(not ui.consent.isChecked(),
              "Paid mask inpaint requires a fresh unchecked approval")
        with patch("PyQt6.QtWidgets.QFileDialog.getOpenFileName",
                   side_effect=[(str(image),"png"),(str(mask),"png")]):
            ui.select_local_source()
            ui.select_local_mask()
        check(ui._local_source==image_uri and ui._local_mask==mask_uri,
              "Image Lab supports explicit local source and mask selection")
        ui.image_url.setText("https://example.com/changed.png")
        # Editing a URL field must clear previous local data in the form
        ui.image_url.textEdited.emit(ui.image_url.text())
        check(ui._local_source is None,
              "Switching to a new URL clears previously selected image bytes")
        ui.close()
    print(json.dumps({"result":"PASS","checks":len(checks),"names":checks},indent=2))

if __name__=="__main__":
    main()
