"""Standalone Creative Studio -> separately installed Blender renderer.

This module imports no Blender code. It creates/validates scene-data contracts and
invokes a separate process. Blender and its GPL bridge are not vendored into
Creative Studio. No source checkout, GPU model, Hunter or Ptah is required.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

SCHEMA = "ttg.studio.blender.scene.v1"
MAX_OBJECTS = 96
MAX_LIGHTS = 12
ALLOWED = {"cube", "cylinder", "uv_sphere", "torus", "text"}
def bridge_path() -> Path:
    """Find standalone GPL bridge in source or PyInstaller onedir/onefile."""
    roots = [
        Path(__file__).resolve().parent.parent,
        Path(__file__).resolve().parent,
        Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "frozen", False) else None,
    ]
    for root in roots:
        if root is None:
            continue
        candidate = root / "integrations" / "blender" / "gpl_scene_runner.py"
        if candidate.is_file():
            return candidate
    raise RuntimeError("Blender GPL bridge not packaged; release is incomplete")


class BlenderUnavailable(RuntimeError):
    pass


def _vec(value, size, name, limit=2000):
    if not isinstance(value, list) or len(value) != size:
        raise ValueError(f"{name} must have {size} numeric coordinates")
    vals = [float(v) for v in value]
    if not all(math.isfinite(v) and abs(v) <= limit for v in vals):
        raise ValueError(f"{name} contains out-of-range coordinates")
    return vals


def validate_scene(data: dict) -> dict:
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("Unsupported 3D scene schema")
    name = data.get("name")
    if not isinstance(name, str) or not 1 <= len(name) <= 100:
        raise ValueError("Scene name must have 1–100 characters")
    frames = data.get("frames", 1)
    fps = data.get("fps", 24)
    width = data.get("width", 960)
    height = data.get("height", 540)
    samples = data.get("samples", 32)
    if any(type(x) is not int for x in (frames, fps, width, height, samples)):
        raise ValueError("Frame settings must be integers")
    if not (1 <= frames <= 240 and 1 <= fps <= 60
            and 96 <= width <= 3840 and 96 <= height <= 2160
            and width*height <= 8_300_000 and 1 <= samples <= 512):
        raise ValueError("3D render exceeds scene frame, time or pixel limits")
    if data.get("engine", "BLENDER_EEVEE_NEXT") not in ("BLENDER_EEVEE_NEXT", "CYCLES"):
        raise ValueError("Only EEVEE or Cycles supported")
    camera = data.get("camera")
    if not isinstance(camera, dict):
        raise ValueError("3D camera required")
    _vec(camera.get("location"), 3, "camera.location")
    _vec(camera.get("target"), 3, "camera.target")
    orbit = camera.get("orbit_degrees", 0)
    if type(orbit) not in (int, float) or not math.isfinite(orbit) or abs(orbit)>720:
        raise ValueError("Camera orbit outside bounds")
    lens = camera.get("lens", 48)
    if type(lens) not in (float, int) or not 12 <= lens <= 160:
        raise ValueError("Camera lens must be 12–160mm")
    objects = data.get("objects")
    if not isinstance(objects, list) or not 1 <= len(objects) <= MAX_OBJECTS:
        raise ValueError("Scene must have 1–96 objects")
    identifiers = set()
    for obj in objects:
        if not isinstance(obj, dict):
            raise ValueError("Object must be a dictionary")
        key = obj.get("id")
        if not isinstance(key, str) or not 1 <= len(key) <= 48 or not key.replace("_","").replace("-","").isalnum() or key in identifiers:
            raise ValueError("Object IDs must be unique and alphanumeric")
        identifiers.add(key)
        if obj.get("type") not in ALLOWED:
            raise ValueError("Unsupported primitive object type")
        for field, default in (("location", [0,0,0]),("rotation", [0,0,0]),("scale", [1,1,1])):
            values = _vec(obj.get(field, default), 3, f"{key}.{field}")
            if field == "scale" and any(v <= 0 for v in values):
                raise ValueError("All object scales must be positive")
        mat = obj.get("material", {})
        if not isinstance(mat, dict):
            raise ValueError("Material must be a dictionary")
        color = _vec(mat.get("color", [.3,.4,.5,1]), 4, f"{key}.color", limit=1)
        if min(color)<0:
            raise ValueError("Color components must be 0–1")
        for field in ("metallic","roughness","transmission","emission_strength"):
            value = mat.get(field, 0 if field != "roughness" else .4)
            if type(value) not in (int,float) or not math.isfinite(value) or not (0 <= value <= (5 if field=="emission_strength" else 1)):
                raise ValueError(f"Invalid {key}.{field}")
        bevel=obj.get("bevel",0)
        if type(bevel) not in (int,float) or not math.isfinite(bevel) or not 0<=bevel<=2:
            raise ValueError("Invalid bevel amount")
        if obj["type"] == "text" and not (isinstance(obj.get("text"),str) and 1<=len(obj["text"])<=160):
            raise ValueError("Text primitive requires bounded text")
    lights = data.get("lights", [])
    if not isinstance(lights, list) or len(lights)>MAX_LIGHTS:
        raise ValueError("Maximum 12 lights")
    for light in lights:
        if not isinstance(light,dict):
            raise ValueError("Light must be a dictionary")
        _vec(light.get("location"),3,"light.location")
        _vec(light.get("color",[1,1,1]),3,"light.color",limit=1)
        power=light.get("energy",400)
        if type(power) not in (int,float) or not math.isfinite(power) or not 0<=power<=10000:
            raise ValueError("Invalid light energy")
    return data


def isp_box_scene(*, width=960, height=540, frames=72, samples=32, engine="BLENDER_EEVEE_NEXT"):
    """Fully editable parametric ISP Box studio lighting / materials concept."""
    black={"color":[.024,.027,.036,1],"metallic":.88,"roughness":.27}
    glass={"color":[.016,.058,.085,1],"metallic":.15,"roughness":.09,"transmission":.68}
    gold={"color":[.62,.35,.064,1],"metallic":.96,"roughness":.22}
    silver={"color":[.12,.16,.19,1],"metallic":.8,"roughness":.26}
    oled={"color":[.006,.28,.43,1],"emission_strength":3,"metallic":.05,"roughness":.14}
    def item(key, shape, loc, scale, material, bevel=0, rotation=None, text=None):
        x={"id":key,"type":shape,"location":loc,"scale":scale,"rotation":rotation or [0,0,0],
           "material":material,"bevel":bevel}
        if text is not None:x["text"]=text
        return x
    objects=[
        item("ground","cube",[0,0,-.5],[10,10,.14],{"color":[.01,.012,.025,1],"roughness":.34},.02),
        item("case","cube",[0,0,.37],[.82,.82,.28],black,.095),
        item("lid","cube",[0,0,.69],[.79,.79,.044],silver,.044),
        item("glass","cube",[-.14,.06,.747],[.36,.18,.018],glass,.035),
        item("oled","cube",[-.14,.06,.766],[.31,.12,.005],oled,.018),
        item("button","cylinder",[.44,.06,.777],[.085,.085,.022],silver,.009),
        item("s1","cube",[-.29,-.839,.43],[.19,.018,.095],{"color":[.003,.004,.007,1],"roughness":.3},.008),
        item("s2","cube",[.22,-.839,.43],[.19,.018,.095],{"color":[.003,.004,.007,1],"roughness":.3},.008),
        item("gold1","cube",[-.29,-.864,.39],[.16,.006,.013],gold,.003),
        item("gold2","cube",[.22,-.864,.39],[.16,.006,.013],gold,.003),
        item("logo","text",[-.4,.39,.779],[.17,.17,.17],{"color":[.75,.78,.82,1],"metallic":.74,"roughness":.24},text="THE TECHGUY"),
        item("ring","torus",[0,0,.08],[1.28,1.28,1],{"color":[.04,.46,.72,1],"emission_strength":2.1},rotation=[0,0,0]),
    ]
    return validate_scene({
        "schema":SCHEMA,"name":"TechGuy ISP Box · PBR Studio Concept",
        "width":width,"height":height,"fps":24,"frames":frames,
        "engine":engine,"samples":samples,
        "camera":{"location":[3.1,-4.0,2.65],"target":[0,0,.39],"lens":48,"orbit_degrees":32},
        "world":{"color":[.026,.035,.054],"strength":.48},
        "objects":objects,
        "lights":[
            {"location":[-3,-2,6],"color":[.75,.89,1],"energy":850,"size":4},
            {"location":[4,1,4],"color":[.4,.75,1],"energy":1150,"size":3},
            {"location":[-1,4,3],"color":[1,.54,.29],"energy":650,"size":2},
        ],
    })


def find_blender():
    configured = os.environ.get("TTG_STUDIO_BLENDER_EXECUTABLE", "").strip()
    return configured or shutil.which("blender")


def blender_status():
    binary = find_blender()
    if not binary or not Path(binary).is_file():
        return {"available":False,"detail":"Install Blender separately and set TTG_STUDIO_BLENDER_EXECUTABLE; no source/weight download required"}
    try:
        reply = subprocess.run([binary,"--version"],capture_output=True,text=True,timeout=12)
        version=reply.stdout.splitlines()[0] if reply.returncode==0 and reply.stdout else None
    except (OSError,subprocess.TimeoutExpired):
        version=None
    return {"available":bool(version),"executable":binary,"version":version}


def render_scene(spec: dict, destination: str|Path, *, timeout=1200):
    """Run separate GPL Blender process and reuse native Studio image/video import.

    OUTPUT: new directory containing the editable scene JSON, real scene.blend,
    first-frame PNG and optionally MP4. Scratch frames are deleted.
    """
    validate_scene(spec)
    found=blender_status()
    if not found["available"]:
        raise BlenderUnavailable(found["detail"])
    target=Path(destination).expanduser().resolve()
    if target.exists():
        raise FileExistsError("3D render never overwrites existing project folders")
    if not target.parent.is_dir() or target.is_symlink():
        raise ValueError("Choose a new folder inside an existing authorized workspace")
    bridge = bridge_path()
    if type(timeout) is not int or not 30<=timeout<=3600:
        raise ValueError("Invalid time budget")
    staging=target.parent/(".ttg3d-"+uuid.uuid4().hex)
    staging.mkdir()
    try:
        (staging/"scene.ttg3d.json").write_text(json.dumps(spec,indent=2),encoding="utf-8")
        command=[found["executable"],"--background","--factory-startup",
                 "--disable-autoexec","--python-exit-code","21",
                 "--threads","2","--python",str(bridge),
                 "--",str(staging/"scene.ttg3d.json"),str(staging)]
        try:
            job=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("Blender rendering timed out") from e
        if job.returncode:
            raise RuntimeError("Blender render failed (last diagnostic): "+job.stderr[-650:])
        poster=staging/"poster.png"
        blend=staging/"scene.blend"
        if not poster.is_file() or not blend.is_file():
            raise RuntimeError("Blender did not produce required physical scene outputs")
        receipt={"renderer":"external-Blender","blender_version":found["version"],
                 "schema":SCHEMA,"scene_sha256":hashlib.sha256((staging/"scene.ttg3d.json").read_bytes()).hexdigest(),
                 "poster_sha256":hashlib.sha256(poster.read_bytes()).hexdigest()}
        if spec["frames"]>1:
            ffmpeg=shutil.which("ffmpeg")
            if not ffmpeg:
                raise RuntimeError("MP4 output requires separately installed FFmpeg")
            movie=staging/"film.mp4"
            proc=subprocess.run([ffmpeg,"-hide_banner","-loglevel","error","-y",
                "-framerate",str(spec["fps"]),"-i",str(staging/"frames"/"frame_%05d.png"),
                "-c:v","libx264","-pix_fmt","yuv420p",str(movie)],
                capture_output=True,text=True,timeout=max(60,timeout//2))
            if proc.returncode or not movie.is_file() or movie.stat().st_size<512:
                raise RuntimeError("FFmpeg could not encode Blender frame sequence: "+proc.stderr[-450:])
            receipt["film_sha256"]=hashlib.sha256(movie.read_bytes()).hexdigest()
            receipt["film_bytes"]=movie.stat().st_size
        shutil.rmtree(staging/"frames",ignore_errors=True)
        (staging/"render.evidence.json").write_text(json.dumps(receipt,indent=2))
        staging.rename(target)
        return {"directory":str(target),"poster":str(target/"poster.png"),"blend":str(target/"scene.blend"),
                "film":str(target/"film.mp4") if spec["frames"]>1 else None,"evidence":receipt}
    finally:
        if staging.is_dir():shutil.rmtree(staging,ignore_errors=True)
