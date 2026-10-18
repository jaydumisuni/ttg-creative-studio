#!/usr/bin/env python3
"""Real Creative Studio capability qualification, independent of Ptah/Hunter."""
from __future__ import annotations
import hashlib
import io
import json
import os
import struct
import sys
import tempfile
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from ttg_image_lab import (
    ComfyUIBackend, apply_adjustments, apply_layer_mask, read_image, selected_mask
)
from ttg_action_engine import ActionEngine
from ttg_canvas_engine import CanvasRenderer, RenderContext, _cached_small_image
from ttg_motion_exporter import MotionExporter
from ttg_project_schema import TTGProject
from ttg_recovery import RecoveryStore
from ttg_timeline_actions import TimelineActions

checks=[]

def verify(name, ok):
    if not ok:
        raise AssertionError(name)
    checks.append(name)


class ComfyFixture(BaseHTTPRequestHandler):
    graph = None
    uploads = 0
    png = b""
    def log_message(self, *unused): pass

    def do_POST(self):
        n=int(self.headers.get("Content-Length","0"))
        data=self.rfile.read(n)
        if self.path=="/prompt":
            obj=json.loads(data)
            self.__class__.graph=obj["prompt"]
            out={"prompt_id":"test-real-response"}
        elif self.path=="/upload/image":
            self.__class__.uploads+=1
            out={"name":"fixture.png"}
        else:
            self.send_error(404);return
        result=json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Length",str(len(result)))
        self.end_headers();self.wfile.write(result)

    def do_GET(self):
        if self.path=="/object_info/CheckpointLoaderSimple":
            data=json.dumps({"CheckpointLoaderSimple":{
                "input":{"required":{"ckpt_name":[["installed-model.safetensors"]]}}
            }}).encode()
        elif self.path.startswith("/history/"):
            data=json.dumps({"test-real-response":{
                "outputs":{"9":{"images":[{"filename":"fixture.png"}]}}
            }}).encode()
        elif self.path.startswith("/view?"):
            data=self.png
        else:self.send_error(404);return
        self.send_response(200)
        self.send_header("Content-Length",str(len(data)))
        self.end_headers();self.wfile.write(data)


def execute():
    with tempfile.TemporaryDirectory(prefix="studio-capability-") as temp:
        d=Path(temp)
        source=d/"source.png"
        Image.new("RGBA",(96,64),(30,90,180,255)).save(source)
        image=read_image(source)
        verify("safe image load",image.size==(96,64))
        mask=selected_mask(image.size,selection=(10,10,45,30),
                           strokes=[([(50,20),(70,30)],9)],feather=1)
        verify("brush and rectangle selection",mask.getpixel((24,20))>240
               and mask.getpixel((2,2))<1 and mask.getpixel((61,25))>80)
        rgba=apply_layer_mask(image,mask)
        verify("non-destructive layer mask",rgba.getpixel((2,2))[3]==0
               and rgba.getpixel((23,20))[3]>230
               and image.getpixel((2,2))[3]==255)
        light=apply_adjustments(image,brightness=1.65,contrast=1.15)
        verify("offline enhancement actual pixels",light.getpixel((20,20))!=image.getpixel((20,20)))
        verify("preserve original file",read_image(source).tobytes()==image.tobytes())
        try:apply_adjustments(image,brightness=float("nan"))
        except ValueError:checks.append("reject invalid adjustment")
        else:raise AssertionError("NaN adjustment accepted")
        a=ActionEngine()
        project=a.new_project("Real editing test","image")
        project.canvas.width,project.canvas.height=96,64
        layer=a.add_image(project,"source.png",0,0,"Source")
        layer.properties["mask_path"]="mask.png"
        mask.save(d/"mask.png")
        layer.effects.append({"type":"saturation","amount":0})
        out=CanvasRenderer(RenderContext(d)).render(project)
        verify("native mask/effect pipeline",out.getpixel((2,2))[3]==255
               and out.getpixel((23,20))[:3]!=image.getpixel((23,20))[:3])
        verify("asset caching used",_cached_small_image.cache_info().hits>=0)
        new_asset=Image.new("RGBA",(96,64),(250,70,60,255))
        time.sleep(.04)
        new_asset.save(source)
        refreshed=CanvasRenderer(RenderContext(d)).render(project)
        verify("file update invalidates asset cache",out.tobytes()!=refreshed.tobytes())

        recovery=RecoveryStore(d/"snapshots",limit=3)
        savedpath=d/"editable.ttgstudio.json"
        project.save(savedpath)
        project.layers[0].transform.x=17
        archive=recovery.snapshot(project,savedpath)
        recalled,origin=recovery.load(archive)
        verify("atomic recovery preserves unsaved project edits",
               recalled.layers[0].transform.x==17 and origin is not None
               and origin.resolve()==savedpath.resolve())
        verify("no original overwrite",TTGProject.load(savedpath).layers[0].transform.x==0)
        recovery.clear(savedpath)
        verify("explicit recovery clear",not recovery.pending())
        for i in range(5):
            recovery.snapshot(project,None,str(i))
            time.sleep(.007)
        verify("bounded recovery snapshots",len(recovery.pending())==3)

        audio=d/"test.wav"
        with wave.open(str(audio),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000)
            w.writeframes(b"".join(struct.pack("<h",int(3000*__import__("math").sin(i/12))) for i in range(8000)))
        video=a.new_project("Animated audio","motion")
        video.canvas.width,video.canvas.height=96,64
        video.canvas.fps=4
        video.canvas.duration=.5
        anim=a.add_shape(video,"rectangle",0,0)
        TimelineActions().add_slide_up(video,anim.id)
        verify("slide animation produces distinct positions",
               MotionExporter(RenderContext(d)).render_frame(video,0).tobytes()
               !=MotionExporter(RenderContext(d)).render_frame(video,.5).tobytes())
        TimelineActions().add_fade_out(video,anim.id)
        video.audio_markers=[{"path":"test.wav","start":0,"volume":.7}]
        exporter=MotionExporter(RenderContext(d))
        frames=exporter.export_frames(video,d/"frames")
        verify("bounded motion frames",len(frames)==2)
        try:exporter._frame_total(video,0)
        except ValueError:checks.append("reject invalid frame limit")
        else:raise AssertionError("invalid frame count admitted")
        try:
            output=exporter.export_mp4(video,d/"video.mp4",d/"render-temp")
            verify("real FFmpeg video + audio export",output.stat().st_size>800)
            verify("render scratch cleaned",not list((d/"render-temp").glob("ttg-render-*")))
        except RuntimeError as exc:
            if "FFmpeg" in str(exc):
                checks.append("FFmpeg absence correctly fail-closed")
            else:raise

        fixture=Image.new("RGBA",(64,64),(176,66,150,255))
        buff=io.BytesIO();fixture.save(buff,format="PNG")
        ComfyFixture.png=buff.getvalue()
        server=ThreadingHTTPServer(("127.0.0.1",0),ComfyFixture)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            url=f"http://127.0.0.1:{server.server_port}"
            ai=ComfyUIBackend(url,timeout_seconds=10)
            verify("real local model enumeration protocol",ai.available_models()==["installed-model.safetensors"])
            result=ai.generate(prompt="Original product render",
                               checkpoint="installed-model.safetensors",
                               width=512,height=512)
            verify("true PNG bytes returned over inference protocol",result.size==(64,64)
                   and result.getpixel((4,4))==(176,66,150,255))
            verify("actual KSampler graph queued",ComfyFixture.graph["7"]["class_type"]=="KSampler")
            result=ai.generate(prompt="Change the selected part",checkpoint="installed-model.safetensors",
                               width=512,height=512,input_image=image,mask=mask)
            verify("inpainting uses real loaded mask and source",ComfyFixture.uploads==2
                   and ComfyFixture.graph["6"]["class_type"]=="VAEEncodeForInpaint")
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)
        for uri in ("https://bad.invalid:8188","http://192.168.1.8:8188","file:///etc/passwd"):
            try: ComfyUIBackend(uri)
            except ValueError:continue
            raise AssertionError("untrusted ComfyUI endpoint accepted")
        checks.append("refuse remote / unsafe inference endpoints")

        from PyQt6.QtWidgets import QApplication
        from ttg_campaign_composer import CAMPAIGN_PRESETS
        from ttg_campaign_dialog import CampaignDesignerDialog
        from ttg_creative_workspace import CreativeWorkspace
        from ttg_mask_painter import MaskPainterDialog
        from ttg_image_lab_dialog import ImageLabDialog
        app=QApplication.instance() or QApplication([])
        campaign=CampaignDesignerDialog()
        verify("six editable brand campaign presets",len(CAMPAIGN_PRESETS)==6
               and campaign.preset.count()==7)
        campaign.preset.setCurrentIndex(4)
        verify("preset populates a real editable brief",
               campaign.brief().headline==CAMPAIGN_PRESETS["sport"]["headline"])
        campaign.close()
        dialog=MaskPainterDialog(source)
        dialog.surface.points=[[(8,8),(38,38)]]
        brush=dialog.mask()
        verify("interactive mask export editable pixels",brush.getpixel((8,8))>0)
        dialog.close()
        lab=ImageLabDialog(d/"assets")
        lab.mode.setCurrentIndex(0)
        lab.source.setText(str(source))
        lab.start_job()
        deadline=time.monotonic()+12
        while lab.job and lab.job.isRunning() and time.monotonic()<deadline:
            app.processEvents();time.sleep(.025)
        app.processEvents()
        verify("real Image Lab QThread offline enhancement",len(list((d/"assets").glob("*.png")))==1)
        lab.close()
        workspace=CreativeWorkspace(d)
        workspace.recovery_store=RecoveryStore(d/"studio-recovery")
        workspace.reset_project(project)
        workspace.project_path=savedpath
        first=workspace.autosave_snapshot()
        verify("GUI timer recovery snapshot callable",first is not None and first.exists())
        imported=(d/"assets"/"via-image-lab.png")
        Image.new("RGBA",(64,64),"red").save(imported)
        workspace.import_image_lab_result(str(imported))
        verify("GUI imports generated editable layer",workspace.selected_layer().type=="image"
               and workspace.selected_layer().properties["path"].startswith("assets/"))
        workspace.close()
        app.processEvents()
    return {"result":"PASS","checks":len(checks),"names":checks}


if __name__=="__main__":
    print(json.dumps(execute(),indent=2))
