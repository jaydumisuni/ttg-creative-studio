#!/usr/bin/env python3
"""Creative Studio 3D backend qualification.

Pure contract checks run with no Blender installed. When the real Blender
binary is installed, execute a physically rendered Cycles 3D scene and MP4.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from ttg_blender_engine import (
    SCHEMA, BlenderUnavailable, blender_status, find_blender,
    isp_box_scene, render_scene, validate_scene,
)
from PyQt6.QtWidgets import QApplication
from ttg_blender_dialog import Studio3DLab

checks = []


def check(cond, message):
    if not cond:
        raise AssertionError(message)
    checks.append(message)


def rejected(data, match):
    try:
        validate_scene(data)
    except ValueError as exc:
        check(match.lower() in str(exc).lower(),f"reject: {match}")
    else:
        raise AssertionError(f"Expected rejected 3D spec: {match}")


def main():
    from ttg_blender_engine import bridge_path
    check(bridge_path().is_file(),"Blender bridge resolves in source checkout")
    spec=(ROOT/"TTG Creative Studio.spec").read_text()
    check("('integrations/blender', 'integrations/blender')" in spec,
          "Windows and Linux frozen installer include GPL bridge and license")
    license=(ROOT/"integrations/blender/GPL-3.0.txt").read_text()
    check("Version 3, 29 June 2007" in license,
          "Full GPLv3 license retained beside Blender API bridge")
    script=(ROOT/"integrations/blender/gpl_scene_runner.py").read_text()
    check("layer.cycles.use_denoising=False" in script and
          "scene.cycles.use_denoising=False" in script,
          "Blender CPU render disables unavailable optional denoisers")
    scene=isp_box_scene(width=192,height=112,frames=3,samples=4,engine="CYCLES")
    check(validate_scene(scene)==scene,"editable parametric product 3D scene accepted")
    check(scene["schema"]==SCHEMA and len(scene["objects"])>=10,"genuine multi-part PBR product scene")
    check(len(scene["lights"])>=3 and scene["camera"]["orbit_degrees"]>0,
          "scene contains multiple physical lights and keyframed orbit")
    check(any(x["material"].get("metallic",0)>.8 for x in scene["objects"]),
          "PBR reflective metals specified")
    changed=json.loads(json.dumps(scene))
    changed["objects"][0]["location"][0]=1.5
    check(validate_scene(changed)["objects"][0]["location"][0]==1.5,
          "geometry editable in persisted scene without rewriting Python")
    changed=json.loads(json.dumps(scene))
    changed["objects"][1]["material"]["roughness"]=.12
    check(validate_scene(changed)["objects"][1]["material"]["roughness"]==.12,
          "material roughness is editable without code")
    changed=json.loads(json.dumps(scene));changed["objects"].append(dict(changed["objects"][0]))
    rejected(changed,"unique")
    changed=json.loads(json.dumps(scene));changed["objects"][0]["type"]="python_script"
    rejected(changed,"unsupported")
    changed=json.loads(json.dumps(scene));changed["objects"][0]["location"][0]=float("nan")
    rejected(changed,"out-of-range")
    changed=json.loads(json.dumps(scene));changed["frames"]=999999
    rejected(changed,"frame")
    changed=json.loads(json.dumps(scene));changed["lights"]=[scene["lights"][0]]*13
    rejected(changed,"lights")
    changed=json.loads(json.dumps(scene));changed["engine"]="UNTRUSTED_PLUGIN"
    rejected(changed,"EEVEE")
    # Qualify the actual native mesh interchange through the same Blender
    # physical render, not only validated JSON or a static primitive scene.
    from ttg_native_3d import convert_primitive, extrude_face
    convert_primitive(scene["objects"][1])
    scene["objects"][1]["mesh"]=extrude_face(
        scene["objects"][1]["mesh"], 0, .16
    )
    from ttg_native_3d import set_keyframe
    mesh_obj=scene["objects"][1]
    set_keyframe(mesh_obj,1,max_frame=scene["frames"])
    mesh_obj["location"][0]+=0.5
    set_keyframe(mesh_obj,3,max_frame=scene["frames"])
    check(len(mesh_obj["keyframes"])==2 and
          mesh_obj["keyframes"][1]["location"][0]!=
          mesh_obj["keyframes"][0]["location"][0],
          "Native object transform keyframes admitted for actual Blender animation")
    check(validate_scene(scene)==scene and
          len(scene["objects"][1]["mesh"]["faces"])>6,
          "Native edited mesh admitted into Blender physical render")
    with tempfile.TemporaryDirectory(prefix="studio-3d-test-") as directory:
        folder=Path(directory)
        (folder/"source.ttg3d.json").write_text(json.dumps(scene))
        reloaded=json.loads((folder/"source.ttg3d.json").read_text())
        check(reloaded==scene,"editable parametric scene survives save/reopen")
        with patch("ttg_blender_engine.find_blender",return_value=None):
            state=blender_status()
            check(not state["available"],"absent Blender never claims 3D runtime ready")
            try:
                render_scene(scene,folder/"absent")
            except BlenderUnavailable:
                check(not (folder/"absent").exists(),
                      "No placeholder renders or fake Blender output")
            else:
                raise AssertionError("Uninstalled Blender unexpectedly rendered")
        app=QApplication.instance() or QApplication([])
        form=Studio3DLab()
        check("TechGuy" in form.editor.toPlainText(),"Studio 3D Lab exposes editable scene data")
        form.frames.setValue(3)
        form.engine.setCurrentText("CYCLES")
        form.samples.setValue(4)
        check(form._scene()["engine"]=="CYCLES",
              "GUI settings are reflected in renderer scene contract")
        form.close()

        real=blender_status()
        if real["available"]:
            result=render_scene(scene,folder/"real")
            check(Path(result["blend"]).stat().st_size>4096,
                  "Actual Blender saved editable .blend file")
            check(Path(result["poster"]).stat().st_size>1000,
                  "Actual Blender Cycles still render saved")
            check(Path(result["film"]).stat().st_size>1000,
                  "Blender frame sequence physically encoded as H264 MP4")
            from PIL import Image,ImageChops
            with Image.open(result["poster"]) as img:
                check(img.size==(192,112),"Physical PBR poster matches requested canvas")
            check(not (folder/"real"/"frames").exists(),
                  "Intermediate frame cache removed after successful encode")
            ffprobe=subprocess.run(["ffprobe","-v","error","-show_entries",
                    "stream=width,height,nb_frames","-of","json",result["film"]],
                    text=True,capture_output=True,timeout=20,check=False)
            if ffprobe.returncode:
                raise AssertionError("Real MP4 failed physical ffprobe")
            meta=json.loads(ffprobe.stdout)
            check(meta["streams"][0]["width"]==192 and meta["streams"][0]["height"]==112,
                  "Produced physical H264 playable resolution")
            with tempfile.TemporaryDirectory(dir=folder) as raw:
                frames=Path(raw)
                out=subprocess.run(["ffmpeg","-hide_banner","-loglevel","error",
                    "-i",result["film"],"-frames:v","3",
                    str(frames/"actual-%02d.png")],
                    text=True,capture_output=True,timeout=45)
                check(out.returncode==0 and len(list(frames.glob("actual-*.png")))==3,
                      "Three genuinely decoded Blender-rendered MP4 frames")
                with Image.open(frames/"actual-01.png") as x, Image.open(frames/"actual-03.png") as y:
                    diff=ImageChops.difference(x.convert("RGB"),y.convert("RGB"))
                    check(diff.getbbox() is not None,
                          "Moving 3D camera produces changing video pixels")
            try:
                render_scene(scene,folder/"real")
            except FileExistsError:
                check(True,"Existing 3D projects are never overwritten")
            else:
                raise AssertionError("Overwrote 3D project")
        else:
            check(True,"Real Blender render skipped honestly on host without executable")
    print(json.dumps({"result":"PASS","checks":len(checks),
                      "blender":real,"checks_detail":checks},indent=2))


if __name__=="__main__":
    main()
