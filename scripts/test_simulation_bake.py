#!/usr/bin/env python3
"""Isolated real physics bake acceptance; no pretend fluid success."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from ttg_blender_simulation import bake_simulation,SimulationBakeError
from ttg_blender_engine import blender_status,isp_box_scene,render_scene
from ttg_native_3d import convert_primitive
from ttg_pro_3d_core import set_extended_physics

checks=[]
def check(x,label):
    if not x: raise AssertionError(label)
    checks.append(label)

def refusal(callback,text):
    try: callback()
    except (ValueError,SimulationBakeError) as e:
        check(text.lower() in str(e).lower(),"Rejected "+text)
    else:raise AssertionError("Invalid simulation request was accepted: "+text)

def main():
    with tempfile.TemporaryDirectory(prefix="studio-physbake-") as area:
        root=Path(area)
        dummy=root/"fake.blend"
        dummy.write_bytes(b"BLENDER"+bytes(150))
        refusal(lambda:bake_simulation(dummy,root/"new",object_id="one",
                                       kind="UNKNOWN"),"Only cloth")
        refusal(lambda:bake_simulation(dummy,root/"new",object_id="../etc"),"identifier")
        refusal(lambda:bake_simulation(dummy,root/"new",object_id="one",
                                       frame_end=99),"2–60")
        refusal(lambda:bake_simulation(dummy,root/"new",object_id="one",
                                       timeout=1),"bounded")
        refusal(lambda:bake_simulation(root/"missing.blend",root/"new",
                                       object_id="one"),"existing normal")
        existing=root/"preexisting";existing.mkdir()
        refusal(lambda:bake_simulation(dummy,existing,
                                       object_id="one"),"must be a new")
        if not blender_status()["available"]:
            refusal(lambda:bake_simulation(dummy,root/"new",
                                           object_id="one"),"Blender executable unavailable")
        else:
            spec=isp_box_scene(width=96,height=96,frames=3,samples=2,engine="CYCLES")
            mesh=spec["objects"][1]
            convert_primitive(mesh)
            mesh.update(set_extended_physics(mesh,kind="CLOTH",quality=2))
            created=render_scene(spec,root/"source",timeout=700)
            check(Path(created["blend"]).is_file(),"Blender physically wrote editable .blend with cloth")
            accepted=bake_simulation(created["blend"],root/"baked",
                                    object_id=mesh["id"],frame_end=3,timeout=170)
            check(accepted["kind"]=="CLOTH" and accepted["point_cache_baked"],
                  "Blender process explicitly confirms real cloth point cache")
            check(Path(accepted["blend"]).is_file() and
                  Path(accepted["receipt"]).is_file(),
                  "Baked simulation accepted with saved .blend and receipt")
            blender=blender_status()["executable"]
            verify=(
                "import bpy; obj=bpy.data.objects['Studio."+mesh["id"]+"']; "
                "mod=next(m for m in obj.modifiers if m.type=='CLOTH'); "
                "assert mod.point_cache.is_baked; "
                "print('STUDIO_CLOTH_CACHE_PHYSICAL_PASS')"
            )
            result=subprocess.run([blender,"--background","--factory-startup",
                                   "--disable-autoexec","--python-exit-code","36",
                                   accepted["blend"],"--python-expr",verify],
                                  text=True,capture_output=True,timeout=70)
            check(result.returncode==0 and "STUDIO_CLOTH_CACHE_PHYSICAL_PASS" in result.stdout,
                  "Fresh Blender subprocess re-opens physically baked point cache: "+
                  result.stderr[-450:])
    print(json.dumps({"status":"PASS","count":len(checks),"checks":checks},indent=2))

if __name__=="__main__":
    main()
