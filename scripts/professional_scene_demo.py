#!/usr/bin/env python3
"""Creative Studio original scene → native still/project → animated MP4 with audio.

No prior image, external model, cloud, Hunter, Ptah implementation change or
Blender. Uses *existing* BananaActions, ExportService and MotionExporter.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import struct
import sys
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ttg_banana_actions import BananaActions
from ttg_project_schema import TTGProject
from ttg_export_service import ExportService
from ttg_motion_exporter import MotionExporter
from ttg_canvas_engine import RenderContext
from PIL import Image, ImageChops, ImageStat

def audio_cue(path: Path, duration: float) -> None:
    rate=22050
    beats=[(0,.28,118),(.52,.23,165),(1.02,.31,130),(1.47,.29,196),(2.02,.35,150)]
    with wave.open(str(path),"wb") as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate)
        block=bytearray()
        for n in range(int(duration*rate)):
            t=n/rate
            val=0.0
            for start,length,hz in beats:
                d=t-start
                if 0<=d<length:
                    amp=math.exp(-d*16)
                    val+=amp*(.7*math.sin(2*math.pi*hz*d*(1-.32*d))
                               +.25*math.sin(2*math.pi*hz*1.51*d))
            # Original warm spatial ping, faded, never random noise.
            if t>.18:
                z=t-.18
                val+=.13*math.exp(-2.1*z)*math.sin(2*math.pi*(500-40*z)*z)
            block.extend(struct.pack("<h",int(max(-.9,min(.9,val)) * 26000)))
        wav.writeframes(bytes(block))

def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as reader:
        for chunk in iter(lambda:reader.read(1048576),b""):h.update(chunk)
    return h.hexdigest()

def make(prompt:str,destination:Path,*,video:bool)->dict:
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError("Creative Studio proof destination must be empty")
    destination.mkdir(parents=True,exist_ok=True)
    studio=BananaActions()
    project=studio.create_professional_wall_sign(prompt)
    project_file=destination/"professional_wall_sign.ttgstudio.json"
    project.save(project_file)
    loaded=TTGProject.load(project_file)
    if loaded.assets or any(layer.type=="image" or "path" in layer.properties for layer in loaded.layers):
        raise AssertionError("A reference image slipped into the from-scratch scene")
    still=destination/"professional_wall_sign.png"
    ExportService(destination).export_png(loaded,still)
    duplicate=ExportService(destination)
    with TemporaryDirectory(prefix="ttg-native-still-",dir=destination) as folder:
        second=Path(folder)/"rerender.png"
        duplicate.export_png(TTGProject.load(project_file),second)
        if digest(still)!=digest(second):
            raise AssertionError("Native re-render differed from saved Studio project")
    with Image.open(still) as rendered:
        colors=rendered.convert("RGB")
        luminance=ImageStat.Stat(colors).stddev
        if colors.size!=(1440,1080) or min(luminance)<18:
            raise AssertionError("Native 1440p image failed resolution or tonal detail check")
    # Reuse Studio's EXISTING Visual Inspector measurements as evidence.
    # These objective numbers cannot certify semantic correctness or realism.
    from ttg_visual_understanding import measure_image, suggest_adjustments
    measurements = measure_image(still)
    suggestions = suggest_adjustments(measurements)
    metrics = {
        key: measurements[key] for key in (
            "dimensions", "luminance_mean_0_255", "luminance_stddev_0_255",
            "edge_energy_0_255", "dominant_colors", "measurement_method"
        )
    }
    quality = {
        "status": "MEASURED_VISUAL_REVIEW_REQUIRED",
        "observed_pixels": metrics,
        "candidate_adjustments": suggestions,
        "semantic_realism_confirmed": False,
        "exact_brand_geometry": "editable_project_text_and_polygons_only",
        "human_review_required": True,
    }
    report={"schema":"ttg.studio.professional-scene-proof.v1",
            "status":"ENGINEERING_PASS_VISUAL_REVIEW_REQUIRED",
            "source_instruction":prompt,
            "native_engine":"Studio CanvasRenderer + existing cinematic materials",
            "from_scratch":True,"external_reference_images":0,"cloud_requests":0,
            "model_inference":False,"native_layers":len(loaded.layers),
            "visual_review":quality,
            "project_file":project_file.name,"still":still.name,
            "still_sha256":digest(still),"rerender_sha256_match":True,
            "visual_quality":"Not certified photorealistic; owner must inspect actual output"}
    if video:
        duration=2.5
        motion=studio.create_professional_wall_sign(prompt,width=768,height=576,
                                                      duration=duration,fps=12)
        cue=destination/"original_sound_cue.wav"
        audio_cue(cue,duration)
        motion.audio_markers=[{"path":cue.name,"start":0,"duration":duration,"volume":.66}]
        motion_path=destination/"professional_wall_sign_motion.ttgstudio.json"
        motion.save(motion_path)
        motion=TTGProject.load(motion_path)
        exporter=MotionExporter(RenderContext(destination))
        image_a=exporter.render_frame(motion,0)
        image_b=exporter.render_frame(motion,1.15)
        diff=ImageChops.difference(image_a,image_b).convert("RGB")
        difference=diff.getbbox()
        if not difference:
            raise AssertionError("Native material video had identical frames")
        final=destination/"professional_wall_sign.mp4"
        with TemporaryDirectory(prefix="ttg-native-motion-",dir=destination) as scratch:
            exporter.export_mp4(motion,final,scratch)
        if not final.is_file() or final.stat().st_size<9000:
            raise AssertionError("Native MP4 output missing or implausibly small")
        report.update({"motion_project":motion_path.name,"video":final.name,
                       "video_sha256":digest(final),"audio_source_sha256":digest(cue),
                       "audio_source":cue.name,"video_duration_seconds":duration,
                       "video_fps":12,"frames_different":True})
    (destination/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
    return report

if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--prompt",required=True)
    cli.add_argument("--output",type=Path,required=True)
    cli.add_argument("--still-only",action="store_true")
    args=cli.parse_args()
    print(json.dumps(make(args.prompt,args.output,video=not args.still_only),indent=2))
