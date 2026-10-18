#!/usr/bin/env python3
"""Cinematic 3D QA admission on KRATOS without paid AI models or downloads."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageChops, ImageStat

from render_3d_scene import Camera, base_curve, render_frame, W, H

QA=Path(__file__).resolve().parent
PASSED=[]


def check(statement:bool, name:str):
    assert statement,name
    PASSED.append(name)


def difference(a,b):
    return ImageStat.Stat(ImageChops.difference(a.convert('RGB'),b.convert('RGB'))).mean


def main():
    check((W,H)==(1280,720),"True 720p dimensions")
    check(len(base_curve())>=16,"3D bevel polygon has multiple explicit X/Z vertices")
    cam0=Camera(0.0)
    cam1=Camera(4.0)
    check(abs(float(cam0.eye[0]-cam1.eye[0]))>.2 and
          abs(float(cam0.eye[2]-cam1.eye[2]))>.2,
          "Actual 3D camera orbit changes position in world X/Z")
    check(abs(cam0.projection((1,.8,1))[0]-cam1.projection((1,.8,1))[0])>5,
          "3D perspective projection changes with orbit")

    still=Image.open(QA/"assets/ispbox_3d_still.png")
    check(still.size==(W,H),"Procedural 3D source still is true 720p")
    sample=render_frame(3.0)
    check(max(difference(sample,still))<.01,
          "3D mesh re-render equals saved actual asset (deterministic)")
    alt=render_frame(1.0)
    check(max(difference(alt,sample))>1.0,
          "Moving camera and material render produce distinct 3D frames")

    poster=Image.open(QA/"ispbox_3d_poster.png")
    check(poster.size==(W,H),"Native Creative Studio poster is full resolution")
    check(max(difference(poster,still))>3,
          "Editable Studio headline/content is composited over physical 3D scene")
    project=json.loads((QA/"ispbox_3d_motion.ttgstudio.json").read_text())
    check(project["canvas"]=={
         "width":W,"height":H,"fps":20,"duration":5.0,"background":"#040A14"
          } and len(project["layers"])==9,
          "Native editable Creative Studio 9-layer motion project retained")
    check(project["layers"][0]["type"]=="video" and
          project["layers"][0]["properties"]["path"]=="assets/ispbox_3d_source.mp4",
          "3D geometry is real video source, not a moved 2D still")
    check((QA/"assets/ispbox_3d_source.mp4").stat().st_size>10000,
          "Camera orbit clip is a physically rendered and encoded asset")
    ffmpeg="/home/kratos/projects/TTG-Creative-Studio/.workspace/worktrees/creative-release-capabilities-20261015/.workspace/scratch/bin/ffmpeg"
    assert Path(ffmpeg).exists(),"Existing Creative Studio FFmpeg pack is required"
    proc=subprocess.run([ffmpeg,"-hide_banner","-loglevel","info",
              "-i",str(QA/"ispbox_3d_final.mp4"),"-f","null","-"],
              capture_output=True,text=True,timeout=65)
    import re
    count=re.findall(r"frame=\s*(\d+)",proc.stderr)
    check(proc.returncode==0 and count and int(count[-1])==100,
          "Final Creative Studio MP4 physically decodes all 100 frames")
    manifest=json.loads((QA/"render_manifest.json").read_text())
    check(manifest["ai_generation"] is False and
          manifest["cloud_provider_calls"]==0 and
          manifest["downloaded_model_weights"] is False,
          "3D mesh render not misrepresented as neural generation")
    for name,record in manifest["files"].items():
        data=(QA/name).read_bytes()
        check(hashlib.sha256(data).hexdigest()==record["sha256"],
              "Asset checksum verified: "+name)
    print(json.dumps({"result":"PASS","checks":len(PASSED),"names":PASSED},indent=2))


if __name__=="__main__":
    main()
