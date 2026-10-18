#!/usr/bin/env python3
"""Creative Studio image/video cloud qualification: synthetic HTTP only, no billing."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ttg_online_image_provider import (
    APPROVAL, state, submit, status, cancel, download,
    IMAGE_TASKS, IMAGE_MODELS, run_image_cloud_job
)
from ttg_creative_studio.engine.video_jobs import tool_catalog
from ttg_creative_studio.engine.image_jobs import CreativeJobError
from PyQt6.QtWidgets import QApplication
from ttg_online_image_dialog import OnlineImageDialog
from ttg_creative_workspace import CreativeWorkspace

checks: list[str] = []


def check(ok, label):
    if not ok:
        raise AssertionError(label)
    checks.append(label)


def deny(call, token):
    try:
        call()
    except Exception as exc:
        check(token.lower() in str(exc).lower(), "fail closed " + token)
    else:
        raise AssertionError("Unexpectedly permitted: " + token)


class Response:
    def __init__(self, data):
        self.file = io.BytesIO(data)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.file.close()
    def read(self, count=-1):
        return self.file.read(count)


class FakeOpener:
    def __init__(self, prediction, image, calls):
        self.prediction = prediction
        self.image = image
        self.calls = calls
    def open(self, request, timeout=None):
        self.calls.append({"method": request.get_method(), "url":request.full_url,
                           "data":request.data, "timeout":timeout})
        if request.full_url.startswith("https://replicate.delivery/"):
            return Response(self.image)
        return Response(json.dumps(self.prediction).encode())


def run_cli(job, directory, label):
    path=directory/(label+".job.json")
    result=directory/(label+".result.json")
    path.write_text(json.dumps(job))
    p=subprocess.run([sys.executable,"-B",str(ROOT/"src/ttg_creative_studio/cli.py"),
       "--job",str(path),"--result",str(result)],cwd=ROOT,capture_output=True,text=True,
       timeout=22)
    return p,json.loads(result.read_text())


def main():
    before={k:os.environ.pop(k,None) for k in
            ("REPLICATE_API_TOKEN","TTG_STUDIO_ENABLE_PAID_IMAGE")}
    try:
        info=state()
        check(info["online"]=="credentials_required","No credentials means NO-GO")
        check(not info["weights_downloaded_by_studio"],"No model downloads")
        check(set(IMAGE_TASKS)=={
            "image_generate_online","image_generation_status",
            "image_generation_download","image_generation_cancel"},"Four shared image tools")
        check(tool_catalog()["operations"]["image_generate_online"]["state"]=="online_opt_in",
              "Shared agent tool contract exposes image provider")
        request={"prompt":"A blue smartphone on a wood table","model":"generate",
                 "aspect_ratio":"16:9", "paid_approval":APPROVAL}
        deny(lambda:submit({"prompt":"test"}),"explicit approval")
        deny(lambda:submit({**request,"mode":"local"}),"local")
        deny(lambda:submit({**request,"model":"arbitrary"}),"unsupported")
        deny(lambda:submit({**request,"aspect_ratio":"match_input_image"}),"Cannot match")
        deny(lambda:submit({**request,"model":"edit"}),"source image URL")
        deny(lambda:submit({**request,"model":"edit",
             "input_image":"http://127.0.0.1/photo.png"}),"public HTTPS")
        deny(lambda:submit(request),"REPLICATE_API_TOKEN")
        os.environ["REPLICATE_API_TOKEN"]="fixture-token-not-a-real-secret"
        deny(lambda:submit(request),"operator")

        with tempfile.TemporaryDirectory(prefix="studio-image-cloud-") as tmp:
            root=Path(tmp)
            blocked,res=run_cli({"task":"image_generate_online","options":request},root,"blocked")
            check(blocked.returncode != 0 and not res["ok"],
                  "CLI refuses paid image generation in unauthorised session")
            check("fixture-token-not-a-real-secret" not in json.dumps(res),
                  "Job receipt never includes private API token")
            os.environ["TTG_STUDIO_ENABLE_PAID_IMAGE"]="1"
            sample=io.BytesIO()
            Image.new("RGB",(96,64),(35,100,150)).save(sample,"PNG")
            real_png=sample.getvalue()
            record={"id":"pictabcd123","status":"starting"}
            calls=[]
            fake=FakeOpener(record, real_png, calls)
            with patch("urllib.request.build_opener",return_value=fake):
                submitted=submit(request)
                check(submitted["status"]=="starting" and submitted["model"]==
                      IMAGE_MODELS["generate"],"Cloud image submitted to correct model")
                check(calls[0]["url"]==
                      "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
                      "Official validated image model endpoint")
                sent=json.loads(calls[0]["data"])["input"]
                check(sent["num_outputs"]==1 and sent["output_format"]=="png" and
                      "paid_approval" not in sent,"Single PNG output and no consent metadata leak")
                record["status"]="processing"
                check(status("pictabcd123")["status"]=="processing",
                      "Real async prediction state returned")
                record["status"]="succeeded"
                record["output"]=["https://replicate.delivery/pbxt/verified/image.png"]
                completed=status("pictabcd123")
                check(completed["status"]=="succeeded" and completed["output_url"],
                      "Single list output normalized and delivery host constrained")
                target=root/"image.png"
                receipt=download("pictabcd123",target)
                check(target.read_bytes()==real_png and receipt["sha256"]==
                      hashlib.sha256(real_png).hexdigest() and receipt["width"]==96,
                      "Generated PNG independently validated and saved with exact SHA256")
                deny(lambda: download("pictabcd123",target),"unused")
                record["output"]=["https://attacker.example/image.png"]
                deny(lambda:download("pictabcd123",root/"evil.png"),
                     "provider delivery domain")
                record["output"]=["https://replicate.delivery/pbxt/verified/image.png"]
                with patch("ttg_online_image_provider.MAX_IMAGE_BYTES",100):
                    deny(lambda:download("pictabcd123",root/"too-large.png"),"24 MiB")
                    check(not (root/"too-large.png").exists(),
                          "Oversize result cleans up temporary files")
                record["status"]="canceled"
                del record["output"]
                check(cancel("pictabcd123")["status"]=="canceled",
                      "Cancellation works for one provider job")

                record["status"]="starting"
                data=submit({**request,"model":"edit",
                   "input_image":"https://public.example/image.png",
                   "aspect_ratio":"match_input_image"})
                edit_body=json.loads(calls[-1]["data"])["input"]
                check(data["model"]==IMAGE_MODELS["edit"] and
                      edit_body["input_image"]=="https://public.example/image.png",
                      "Image editing uses separate official editing model with validated image URL")

            # Exercise real editable Studio image import/save/reopen from
            # the independently verified downloaded PNG.
            from ttg_project_schema import TTGProject
            app=QApplication.instance() or QApplication([])
            source_workspace=CreativeWorkspace(root)
            project_path=root/"cloud-editable.ttgstudio.json"
            project=TTGProject(name="Cloud image editable artifact",project_type="image")
            project.save(project_path)
            source_workspace.project=project
            source_workspace.project_path=project_path
            source_workspace._set_asset_root(root)
            source_workspace.import_image_lab_result(str(target))
            layer=source_workspace.selected_layer()
            check(layer is not None and layer.type=="image",
                  "Verified provider PNG imported as editable native image layer")
            source_workspace.save_project()
            reopened=TTGProject.load(project_path)
            check(reopened.layers and reopened.layers[0].type=="image",
                  "Cloud-origin image survives project save and reopen")
            source_workspace.close()
            app.processEvents()

            gui=OnlineImageDialog(root)
            check(gui.approval.isChecked() is False,"Paid approval unchecked on launch")
            check(gui.mode.count()==2,"Create and edit image modes available")
            gui.close()
            workspace=CreativeWorkspace(root)
            check(hasattr(workspace,"open_online_image_lab") and
                  hasattr(workspace,"import_image_lab_result"),
                  "Studio desktop can import verified online PNG as editable layer")
            workspace.close()

        env=os.environ.copy()
        env.pop("REPLICATE_API_TOKEN",None)
        env.pop("TTG_STUDIO_ENABLE_PAID_IMAGE",None)
        with tempfile.TemporaryDirectory(prefix="studio-image-cli-") as tmp:
            cwd=Path(tmp)
            p,res=run_cli({"task":"image_generation_status",
                "options":{"prediction_id":"not/valid"}},cwd,"invalid-id")
            check(p.returncode != 0 and "Invalid" in res["error"],
                  "CLI rejects invalid prediction path injection")
        check(all("fixture-token-not-a-real-secret" not in a["url"]
                 for a in calls),"Cloud secret never sent in URL")
        check(not any(x["method"]=="POST" for x in calls if x["url"].endswith("/image.png")),
              "Downloading is not a billable prediction request")
        print(json.dumps({"result":"PASS","checks":len(checks),"names":checks},indent=2))
    finally:
        for k,v in before.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v


if __name__=="__main__":
    main()
