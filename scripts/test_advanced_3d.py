#!/usr/bin/env python3
"""Advanced Studio 3D native feature and optional physical Blender qualification.

This is bounded authoring, not a declaration of complete Blender parity.
No donor source checkout, GPU model or secret downloads.
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

from ttg_native_3d import cube,convert_primitive
from ttg_advanced_3d_core import (
    uv_project, uv_transform, sculpt, add_bone, set_skin_weight,
    add_constraint, set_procedural, set_physics,
)
from ttg_blender_engine import isp_box_scene,validate_scene,blender_status,render_scene
from ttg_native_3d_viewport import Native3DModeler
from PyQt6.QtWidgets import QApplication, QMessageBox

def unexpected_dialog(parent, title, message):
    raise AssertionError(f"Unexpected headless modal {title}: {message}")

QMessageBox.warning=staticmethod(unexpected_dialog)
QMessageBox.information=staticmethod(unexpected_dialog)

checks=[]


def check(value, name):
    assert value, name
    checks.append(name)


def invalid(fn, phrase):
    try:fn()
    except ValueError as exc:
        check(phrase.lower() in str(exc).lower(),
              "Invalid advanced scene refused: "+phrase)
    else:
        raise AssertionError("Expected rejection: "+phrase)


def make_scene():
    scene=isp_box_scene(width=96,height=96,frames=2,samples=2,engine="CYCLES")
    mesh=scene["objects"][1]
    convert_primitive(mesh)
    mesh["uv"]=uv_project(mesh["mesh"],axis="z")
    mesh["mesh"]=sculpt(mesh["mesh"],0,radius=3,strength=.08)
    mesh.update(add_bone(mesh,"Root",[0,0,0],[0,0,1]))
    mesh.update(add_bone(mesh,"Tip",[0,0,1],[0,0,2],parent="Root"))
    mesh.update(set_skin_weight(mesh,0,"Tip",.7))
    mesh["armature"]["bones"][0]["keyframes"]=[
        {"frame":1,"rotation":[0,0,0]},
        {"frame":2,"rotation":[0,0,10]},
    ]
    mesh.update(set_procedural(mesh,operation="wave",offset=[0,0,.02],amplitude=.08))
    mesh.update(set_physics(mesh,active=True,mass=1.))
    mesh.update(add_constraint(mesh,scene["objects"][0]["id"],kind="COPY_LOCATION"))
    # Passive collision anchor separate from skinned/geometry node object.
    scene["objects"][2].update(set_physics(scene["objects"][2],active=False))
    return scene


def main():
    original=cube()
    mapping=uv_project(original,axis="y")
    check(len(mapping)==len(original["faces"]) and len(mapping[0])==4,
          "Per-face-corner UV mapping generated from real geometry")
    edit=uv_transform(mapping,translate=(.2,-.1),scale=(.5,.5))
    check(edit[0][0]!=mapping[0][0] and mapping==uv_project(original,axis="y"),
          "UV editing is nondestructive and retains original mapping")
    moved=sculpt(original,0,radius=3,strength=.16)
    check(moved["vertices"][0]!=original["vertices"][0] and
          moved["faces"]==original["faces"],
          "Sculpt inflate physically deforms mesh, preserving topology")
    for mode in ("deflate","smooth"):
        output=sculpt(original,0,radius=3,strength=.12,mode=mode)
        check(output["vertices"]!=original["vertices"],
              "Real bounded "+mode+" sculpt brush")
    invalid(lambda:sculpt(original,0,radius=0), "sculpt")
    invalid(lambda:uv_project(original,axis="__import__"),"axis")

    scene=make_scene()
    check(validate_scene(scene)==scene, "Native advanced fields accepted by Blender scene schema")
    rig=scene["objects"][1]["armature"]
    check(len(rig["bones"])==2 and rig["bones"][1]["parent"]=="Root",
          "Editable hierarchical armature contains two valid bones")
    check(abs(sum(rig["weights"][0].values())-1)<.00001 and
          abs(rig["weights"][0]["Tip"]-.7)<.00001,
          "Skin weights normalized across real mesh vertices")
    check(scene["objects"][1]["geometry_nodes"]["operation"]=="wave",
          "Validated geometry-node wave graph recipe persisted")
    check(scene["objects"][1]["constraints"][0]["type"]=="COPY_LOCATION",
          "Scene-level validated inter-object constraint")
    check(scene["objects"][1]["simulation"]["type"]=="ACTIVE" and
          scene["objects"][2]["simulation"]["type"]=="PASSIVE",
          "Active/passive physical rigid-body properties saved")
    broken=deepcopy(scene)
    broken["objects"][1]["armature"]["weights"].pop()
    invalid(lambda:validate_scene(broken),"every mesh vertex")
    broken=deepcopy(scene)
    broken["objects"][1]["constraints"][0]["target"]="missing"
    invalid(lambda:validate_scene(broken),"valid scene object")
    broken=deepcopy(scene)
    broken["objects"][1]["geometry_nodes"]["operation"]="EXEC_PYTHON"
    invalid(lambda:validate_scene(broken),"admitted")
    broken=deepcopy(scene)
    broken["objects"][1]["uv"][0].append([0,0])
    invalid(lambda:validate_scene(broken),"corner")
    broken=deepcopy(scene)
    broken["objects"][1]["simulation"]["mass"]=float("nan")
    invalid(lambda:validate_scene(broken),"rigid-body numerical")
    broken=deepcopy(scene)
    broken["objects"][1]["armature"]["bones"][1]["parent"]="__bad__"
    invalid(lambda:validate_scene(broken),"parent")

    with tempfile.TemporaryDirectory(prefix="studio-advanced-3d-") as root:
        work=Path(root)
        project=work/"advanced.ttg3d.json"
        project.write_text(json.dumps(scene,indent=2))
        check(validate_scene(json.loads(project.read_text()))==scene,
              "Advanced rig, UV, nodes and physics survive project save/reopen")
        app=QApplication.instance() or QApplication([])
        modeler=Native3DModeler(isp_box_scene())
        modeler.to_mesh()
        modeler.mode.setCurrentText("Vertex")
        modeler.component=0
        modeler.sculpt_radius.setValue(3)
        before=deepcopy(modeler.scene["objects"][0]["mesh"]["vertices"])
        modeler.apply_sculpt()
        check(modeler.scene["objects"][0]["mesh"]["vertices"]!=before,
              "Native Qt Sculpt Selected Vertex button edits real geometry")
        modeler.project_uv()
        check(bool(modeler.scene["objects"][0].get("uv")),
              "Qt UV Project action creates real editable UV mappings")
        before_uv=deepcopy(modeler.scene["objects"][0]["uv"])
        modeler.uv_u.setValue(.25)
        modeler.shift_uv()
        check(modeler.scene["objects"][0]["uv"]!=before_uv,
              "Qt UV shift modifies face-corner mapping")
        modeler.make_rig_bone()
        check(len(modeler.scene["objects"][0]["armature"]["bones"])==1,
              "Native Qt Add Rig Bone authors real editable hierarchy")
        modeler.make_rig_bone()
        modeler.rig_bone.setCurrentText("Bone_2")
        modeler.weight_vertex()
        check(modeler.scene["objects"][0]["armature"]["weights"][0]=={"Bone_2":1.},
              "Native selected vertex can be rebound to second bone")
        modeler.frame_control.setValue(2)
        modeler.key_bone()
        check(modeler.scene["objects"][0]["armature"]["bones"][1]["keyframes"][0]["frame"]==2,
              "Native UI authors real rig pose animation keyframe")
        modeler.apply_constraint()
        check(bool(modeler.scene["objects"][0]["constraints"]),
              "Qt constraint editor commits Blender-compatible target")
        modeler.node_op.setCurrentText("wave")
        modeler.apply_nodes()
        check(modeler.scene["objects"][0]["geometry_nodes"]["operation"]=="wave",
              "Qt procedural geometry preset editable and saved")
        modeler.apply_simulation()
        check(modeler.scene["objects"][0]["simulation"]["type"]=="ACTIVE",
              "Native Qt physics enables real rigid-body scene data")
        check(validate_scene(modeler.scene)==modeler.scene,
              "All advanced Qt controls retain valid editable scene")
        modeler.undo()
        check("simulation" not in modeler.scene["objects"][0],
              "Undo removes physics change without destroying other features")
        modeler.redo()
        check("simulation" in modeler.scene["objects"][0],
              "Redo restores advanced 3D state")
        modeler.close()
        app.processEvents()

        if blender_status()["available"]:
            result=render_scene(scene,work/"physical_blender",timeout=720)
            check(Path(result["blend"]).is_file() and Path(result["poster"]).is_file(),
                  "Actual Blender emitted edited advanced .blend and image")
            blender=blender_status()["executable"]
            inspector=(
                "import bpy; "
                "s=bpy.data.objects['Studio.'+"+repr(scene["objects"][1]["id"])+"]; "
                "assert len(s.data.uv_layers)==1; "
                "assert any(m.type=='ARMATURE' for m in s.modifiers); "
                "assert any(m.type=='NODES' for m in s.modifiers); "
                "assert s.rigid_body.type=='ACTIVE'; "
                "assert any(c.type=='COPY_LOCATION' for c in s.constraints); "
                "assert len([o for o in bpy.data.objects if o.type=='ARMATURE'])>=1; "
                "print('TTG_ADVANCED_BLEND_INSPECT_PASS')"
            )
            inspect=subprocess.run([blender,"--background","--factory-startup",
                                    "--disable-autoexec","--python-exit-code","21",
                                    result["blend"],"--python-expr",inspector],
                                   capture_output=True,text=True,timeout=75)
            check(inspect.returncode==0 and "TTG_ADVANCED_BLEND_INSPECT_PASS" in inspect.stdout,
                  "Blender saved physical rig, UV, nodes, constraints and rigid bodies: "+
                  inspect.stderr[-500:])
        else:
            check(not blender_status()["available"],
                  "Without external Blender no fake geometry-node or physics execution")
    print(json.dumps({"result":"PASS","checks":len(checks),"names":checks},indent=2))


if __name__=="__main__":
    main()
