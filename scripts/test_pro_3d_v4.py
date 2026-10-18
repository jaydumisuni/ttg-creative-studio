#!/usr/bin/env python3
"""Pro 3D V4: physical authored geometry, UV Blender solvers, graph DAG and IK.

On Linux CI with Blender this opens the actual .blend and validates bpy data.
Other hosts qualify bounded native editing without claiming Blender execution.
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
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from ttg_native_3d import cube, convert_primitive
from ttg_blender_engine import isp_box_scene, validate_scene, blender_status, render_scene
from ttg_advanced_3d_core import add_bone, set_skin_weight
from ttg_pro_3d_core import set_bone_ik
from ttg_pro_3d_v4 import (
    set_uv_unwrap,set_geometry_dag,set_ik_pole,
    normalize_skin_weights,sculpt_stroke
)
from ttg_native_3d_viewport import Native3DModeler
from PyQt6.QtWidgets import QApplication

checks=[]
def check(yes,reason):
    if not yes:raise AssertionError(reason)
    checks.append(reason)

def reject(fn,phrase):
    try:fn()
    except (ValueError,TypeError) as exc:
        check(phrase.lower() in str(exc).lower(),"Reject "+phrase)
    else:raise AssertionError("Accepted invalid "+phrase)

def scene_proof():
    data=isp_box_scene(width=96,height=96,frames=2,samples=2,engine="CYCLES")
    obj=data["objects"][1]
    convert_primitive(obj)
    obj.update(set_uv_unwrap(obj))
    obj.update(add_bone(obj,"Root",[0,0,0],[0,0,1]))
    obj.update(add_bone(obj,"Tip",[0,0,1],[0,0,2],parent="Root"))
    obj.update(set_skin_weight(obj,0,"Tip",.5))
    obj.update(set_bone_ik(obj,"Tip",[.5,0,2],chain_count=2))
    obj.update(set_ik_pole(obj,"Tip",[.3,1.,1.]))
    obj.update(set_geometry_dag(obj,[
      {"id":"left","type":"transform","inputs":["input"],"offset":[.25,0,0]},
      {"id":"right","type":"transform","inputs":["input"],"offset":[-.25,0,0]},
      {"id":"middle","type":"join","inputs":["left","right"]},
      {"id":"refine","type":"subdivide","inputs":["middle"],"level":1},
    ],"refine"))
    return data

def main():
    obj={"id":"editing","type":"mesh","mesh":cube()}
    unwrapped=set_uv_unwrap(obj)
    check(unwrapped["uv_unwrap"]["method"]=="SMART_PROJECT",
          "Native scene authors actual Blender UV solver operation")
    check("uv" not in unwrapped, "Solver does not manufacture projected atlas")
    reject(lambda:set_uv_unwrap(obj,method="EXEC_PYTHON"),"UV method")
    reject(lambda:set_uv_unwrap(obj,margin=.99),"margin")

    graph=[
        {"id":"A","type":"transform","inputs":["input"],"offset":[0,0,1]},
        {"id":"B","type":"wave","inputs":["input"],"amplitude":.2},
        {"id":"Join","type":"join","inputs":["A","B"]},
        {"id":"Refine","type":"subdivide","inputs":["Join"],"level":1},
    ]
    accepted=set_geometry_dag(obj,graph,"Refine")
    check(accepted["geometry_nodes"]["output"]=="Refine" and
          len(accepted["geometry_nodes"]["nodes"])==4,
          "Two branches join into downstream geometry node")
    reject(lambda:set_geometry_dag(obj,[{"id":"cycle","type":"join",
                                        "inputs":["cycle","input"]}],"cycle"),"cycle")
    reject(lambda:set_geometry_dag(obj,graph,"missing"),"output")
    reject(lambda:set_geometry_dag(obj,graph+[{"id":"A","type":"wave",
                                               "inputs":["input"],"amplitude":.1}],
                                  "Refine"),"cycle")
    mesh=sculpt_stroke(obj,[0,1],radius=5,strength=.2)
    check(len(mesh["mesh"]["vertices"])>len(obj["mesh"]["vertices"]),
          "Repeated multi-dab sculpt physically changes native topology")
    reject(lambda:sculpt_stroke(unwrapped,[0]),"topology invalidates")
    reject(lambda:sculpt_stroke(obj,[-1]),"vertex index")

    skinned=add_bone(obj,"Root",[0,0,0],[0,0,1])
    skinned=add_bone(skinned,"Tip",[0,0,1],[0,0,2],parent="Root")
    skinned=set_skin_weight(skinned,0,"Tip",.2)
    skinned=set_bone_ik(skinned,"Tip",[0,0,2],chain_count=2)
    with_pole=set_ik_pole(skinned,"Tip",[.2,1,1],angle=45)
    check(with_pole["armature"]["bones"][1]["ik"]["pole_angle"]==45,
          "Two-bone IK pole and offset authored in validated rig")
    reject(lambda:set_ik_pole(skinned,"Root",[0,1,0]),"IK pole")
    normalized=normalize_skin_weights(skinned)
    check(abs(sum(normalized["armature"]["weights"][0].values())-1.)<1e-7,
          "Skin weights normalized on authored rig")

    app=QApplication.instance() or QApplication([])
    editor=Native3DModeler(
        isp_box_scene(width=96,height=96,frames=2,samples=2,engine="CYCLES")
    )
    editor.objects.setCurrentRow(1)
    editor.to_mesh()
    editor.use_blender_unwrap()
    check(editor.scene["objects"][1]["uv_unwrap"]["method"]=="SMART_PROJECT",
          "Qt user control authors physical UV unwrap")
    editor.make_branching_graph()
    check(editor.scene["objects"][1]["geometry_nodes"]["operation"]=="dag",
          "Qt creates real two-branch geometry graph")
    editor.undo()
    check("geometry_nodes" not in editor.scene["objects"][1],
          "Undo safely removes advanced DAG edit")
    editor.redo()
    check(editor.scene["objects"][1]["geometry_nodes"]["operation"]=="dag",
          "Redo restores advanced DAG editing")
    editor.close()
    app.processEvents()

    scene=scene_proof()
    validate_scene(scene)
    with tempfile.TemporaryDirectory(prefix="ttg-pro3d-v4-") as temporary:
        path=Path(temporary)
        source=path/"editable.json"
        source.write_text(json.dumps(scene))
        check(validate_scene(json.loads(source.read_text())) is not None,
              "3D V4 scene roundtrips through existing portable JSON format")
        if blender_status()["available"]:
            output=render_scene(scene,path/"physical",timeout=700)
            check(Path(output["blend"]).is_file(),
                  "Blender physically constructed advanced scene")
            assertion=(
                "import bpy; "
                "obj=bpy.data.objects['Studio.'+'"+scene["objects"][1]["id"]+"']; "
                "assert obj.data.uv_layers.active is not None; "
                "assert len(obj.data.uv_layers.active.data)>0; "
                "modifier=next(m for m in obj.modifiers if m.type=='NODES'); "
                "nodes=modifier.node_group.nodes; "
                "assert any(n.bl_idname=='GeometryNodeJoinGeometry' for n in nodes); "
                "assert len([n for n in nodes if n.bl_idname=='GeometryNodeTransform'])==2; "
                "assert any(n.bl_idname=='GeometryNodeSubdivideMesh' for n in nodes); "
                "arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); "
                "ik=next(c for bone in arm.pose.bones for c in bone.constraints if c.type=='IK'); "
                "assert ik.pole_target and ik.chain_count==2; "
                "assert abs(ik.pole_angle-0.0)<1e-4; "
                "print('TTG_PRO3D_V4_PHYSICAL_PASS')"
            )
            runner=subprocess.run([blender_status()["executable"],"--background",
                                   "--factory-startup","--disable-autoexec",
                                   "--python-exit-code","31",str(output["blend"]),
                                   "--python-expr",assertion],
                                  text=True,capture_output=True,timeout=110)
            check(runner.returncode==0 and "TTG_PRO3D_V4_PHYSICAL_PASS" in runner.stdout,
                  "Actual .blend contains UV map + joined branches + IK pole: "+
                  runner.stderr[-500:])
        else:
            check(not blender_status()["available"],
                  "No Blender installed here: not pretending physical execution")
    print(json.dumps({"result":"PASS","count":len(checks),"checks":checks},indent=2))

if __name__=="__main__":
    main()
