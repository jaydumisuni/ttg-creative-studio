#!/usr/bin/env python3
"""Actual Blender 4.2+ smoke/gas or liquid simulation bake acceptance.

Runs in a disposable qualified Blender process, never on KRATOS's main
workspace. No mock frames, cached fixture files or fake success values.
"""
from __future__ import annotations
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ttg_blender_engine import blender_status,render_scene,isp_box_scene
from ttg_blender_simulation import bake_simulation,SimulationBakeError
from ttg_native_3d import convert_primitive
from ttg_pro_3d_core import set_extended_physics


def main() -> None:
    kind=os.environ.get("TTG_FLUID_BAKE_KIND","").strip()
    if kind not in ("GAS","LIQUID"):
        raise RuntimeError("Must explicitly choose GAS or LIQUID verification")
    backend=blender_status()
    if not backend["available"]:
        raise RuntimeError("Real Blender is required: cannot fabricate fluid cache")
    with tempfile.TemporaryDirectory(prefix="ttg-fluid-bake-") as folder:
        work=Path(folder)
        scene=isp_box_scene(width=96,height=96,frames=3,samples=2,engine="CYCLES")
        target=scene["objects"][1]
        convert_primitive(target)
        target["scale"]=[3,3,3]
        target["location"]=[0,0,0]
        target.update(set_extended_physics(
            target,kind=("SMOKE_DOMAIN" if kind=="GAS" else "LIQUID_DOMAIN"),
            quality=2,resolution=16
        ))
        flow=deepcopy(target)
        flow["id"]="v5_fluid_flow"
        flow["scale"]=[.55,.55,.55]
        flow["location"]=[0,0,0]
        flow.update(set_extended_physics(
            flow,kind=("SMOKE_FLOW" if kind=="GAS" else "LIQUID_FLOW"),
            quality=2,resolution=16
        ))
        scene["objects"].append(flow)
        constructed=render_scene(scene,work/"input",timeout=650)
        if not Path(constructed["blend"]).is_file():
            raise AssertionError("No actual pre-bake .blend scene")
        admitted=bake_simulation(
            constructed["blend"],work/"baked",object_id=target["id"],
            kind=kind,frame_end=3,timeout=300
        )
        destination=Path(admitted["blend"])
        if not destination.is_file() or not admitted.get("active_flows"):
            raise AssertionError("No actual fluid model or activated flow")
        cache=destination.parent/"fluid-cache"
        disk_files=[x for x in cache.rglob("*") if x.is_file()]
        if not disk_files or sum(x.stat().st_size for x in disk_files)<1024:
            raise AssertionError("Blender fluid cache missing or empty")
        if admitted["cache_files"]!=len(disk_files):
            raise AssertionError("Reported fluid cache files do not match actual output")
        verify=(
            "import bpy; "
            "obj=bpy.data.objects['Studio."+target["id"]+"']; "
            "m=next(x for x in obj.modifiers if x.type=='FLUID'); "
            "assert m.fluid_type=='DOMAIN'; "
            "assert m.domain_settings.domain_type=='"+kind+"'; "
            "assert m.domain_settings.cache_frame_end==3; "
            "print('STUDIO_REAL_"+kind+"_BAKE_REOPEN_PASS')"
        )
        fresh=subprocess.run([
            backend["executable"],"--background","--factory-startup",
            "--disable-autoexec","--python-exit-code","42",
            str(destination),"--python-expr",verify,
        ],capture_output=True,text=True,timeout=65)
        if fresh.returncode or "STUDIO_REAL_"+kind+"_BAKE_REOPEN_PASS" not in fresh.stdout:
            raise AssertionError("Fresh Blender could not inspect baked scene: "+fresh.stderr[-500:])
        print(json.dumps({
            "status":"PASS", "kind":kind,
            "blender":backend["version"],
            "cache_files":len(disk_files),
            "cache_bytes":sum(x.stat().st_size for x in disk_files),
            "scene_reopened":True,
            "same_scene_mesh":target["id"],
            "ephemeral_runner_cleanup":"automatic",
        },indent=2))


if __name__=="__main__":
    main()
