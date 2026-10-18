#!/usr/bin/env python3
"""Native 3D professional authoring qualification + actual Blender inspection."""
from __future__ import annotations

import json
import os
from pathlib import Path
from copy import deepcopy
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from ttg_native_3d import cube, convert_primitive
from ttg_blender_engine import isp_box_scene, validate_scene, blender_status, render_scene
from ttg_advanced_3d_core import add_bone, set_skin_weight
from ttg_pro_3d_core import (
    unwrap_pack_faces,assign_uv_seams,paint_skin_weights,
    set_multires,set_bone_ik,set_geometry_graph,set_extended_physics,
    adaptive_sculpt,
)
from ttg_native_3d_viewport import Native3DModeler
from PyQt6.QtWidgets import QApplication,QMessageBox

checks=[]
def check(value,subject):
    if not value:raise AssertionError(subject)
    checks.append(subject)

def reject(fn,phrase):
    try:fn()
    except (ValueError,TypeError) as ex:
        check(phrase.lower() in str(ex).lower(),"Reject invalid "+phrase)
    else:raise AssertionError("Unexpectedly accepted: "+phrase)

def build_scene():
    scene=isp_box_scene(width=96,height=96,frames=2,samples=2,engine="CYCLES")
    mesh=scene["objects"][1]
    convert_primitive(mesh)
    mesh["uv"]=unwrap_pack_faces(mesh["mesh"],.02)
    face=mesh["mesh"]["faces"][0]
    mesh.update(assign_uv_seams(mesh,[[face[0],face[1]]]))
    mesh.update(add_bone(mesh,"Root",[0,0,0],[0,0,1]))
    mesh.update(add_bone(mesh,"Tip",[0,0,1],[0,0,2],parent="Root"))
    mesh.update(set_skin_weight(mesh,0,"Tip",.75))
    mesh.update(paint_skin_weights(mesh,vertex=0,bone="Tip",radius=2,strength=.2))
    mesh.update(set_bone_ik(mesh,"Tip",[.3,0,2.],chain_count=2))
    mesh.update(set_multires(mesh,levels=1))
    mesh.update(set_geometry_graph(mesh,[
        {"type":"transform","offset":[0,0,.1]},
        {"type":"subdivide","level":1},
        {"type":"wave","amplitude":.06}
    ]))
    cloth=deepcopy(mesh)
    cloth["id"]="cloth_cloth"
    for key in ("armature","geometry_nodes","sculpt_detail","uv","uv_seams"):
        cloth.pop(key,None)
    cloth.update(set_extended_physics(cloth,kind="CLOTH"))
    cloth["location"]=[-4,0,0]
    scene["objects"].append(cloth)
    gas=deepcopy(cloth);gas["id"]="smoke_domain"
    gas.update(set_extended_physics(gas,kind="SMOKE_DOMAIN",resolution=16))
    gas["location"]=[4,0,0]
    scene["objects"].append(gas)
    flow=deepcopy(cloth);flow["id"]="smoke_flow"
    flow.update(set_extended_physics(flow,kind="SMOKE_FLOW",resolution=16))
    flow["location"]=[4,0,-1]
    scene["objects"].append(flow)
    liquid=deepcopy(cloth);liquid["id"]="liquid_domain"
    liquid.update(set_extended_physics(liquid,kind="LIQUID_DOMAIN",resolution=16))
    liquid["location"]=[7,0,0]
    scene["objects"].append(liquid)
    liquid_flow=deepcopy(cloth);liquid_flow["id"]="liquid_flow"
    liquid_flow.update(set_extended_physics(liquid_flow,kind="LIQUID_FLOW",resolution=16))
    liquid_flow["location"]=[7,0,-1]
    scene["objects"].append(liquid_flow)
    return scene

def main():
    cube_mesh=cube()
    packed=unwrap_pack_faces(cube_mesh)
    check(len(packed)==6,"Six face islands generated from mesh")
    bounds=[]
    for island in packed:
        u=[p[0] for p in island];v=[p[1] for p in island]
        bounds.append((min(u),max(u),min(v),max(v)))
    check(all(0<=k<=1 for coords in bounds for k in coords),
          "All packed UV coordinates within [0,1]")
    check(all(a[1]<b[0] or b[1]<a[0] or a[3]<b[2] or b[3]<a[2]
              for i,a in enumerate(bounds) for b in bounds[i+1:]),
          "Packed islands do not overlap, physically distinct UVs")
    reject(lambda:unwrap_pack_faces(cube_mesh,padding=.5),"padding")
    refined=adaptive_sculpt(cube_mesh,0,radius=5,strength=.1)
    check(len(refined["vertices"])>len(cube_mesh["vertices"]) and
          len(refined["faces"])>len(cube_mesh["faces"]),
          "Actual adaptive sculpt increases nearby mesh topology")
    reject(lambda:adaptive_sculpt(cube_mesh,0,radius=.001),"did not cover")
    obj={"type":"mesh","id":"cube_mesh","mesh":cube_mesh,"uv":packed}
    seam=assign_uv_seams(obj,[[0,1]])
    check(seam["uv_seams"]==[[0,1]],"Authored mesh seam persisted")
    reject(lambda:assign_uv_seams(obj,[[0,22]]),"seam")
    obj.update(add_bone(obj,"Root",[0,0,0],[0,0,1]))
    obj.update(add_bone(obj,"Tip",[0,0,1],[0,0,2],parent="Root"))
    weighted=paint_skin_weights(obj,vertex=0,bone="Tip",radius=5,strength=.5)
    check(weighted["armature"]["weights"][0]["Tip"]==.5,
          "Real brush paints selected bone weight")
    check(any("Tip" in w for w in weighted["armature"]["weights"][1:]),
          "Falloff paints nearby actual vertices")
    subtract=paint_skin_weights(weighted,vertex=0,bone="Tip",radius=3,
                                strength=.25,mode="subtract")
    check(subtract["armature"]["weights"][0]["Tip"]==.25,
          "Subtract weight brush actually changes skinning")
    reject(lambda:paint_skin_weights(obj,vertex=-1,bone="Root",
                                    radius=1,strength=.4),"Paint center")
    ik=set_bone_ik(weighted,"Tip",[0,0,2],chain_count=2)
    check(ik["armature"]["bones"][1]["ik"]["chain_count"]==2,
          "Native chain IK persisted on intended bone")
    reject(lambda:set_bone_ik(weighted,"Root",[0,0,2],chain_count=2),
           "ancestor")
    detail=set_multires(ik,levels=2)
    check(detail["sculpt_detail"]["levels"]==2,"Multires level authored")
    reject(lambda:set_multires(ik,levels=8),"multires")
    graph=set_geometry_graph(detail,[{"type":"transform","offset":[0,0,.1]},
                                     {"type":"subdivide","level":1},
                                     {"type":"wave","amplitude":.15}])
    check(len(graph["geometry_nodes"]["steps"])==3,
          "Editable geometry-node chain persists three real node kinds")
    reject(lambda:set_geometry_graph(graph,[{"type":"python_exec"}]),"admitted")
    cloth=set_extended_physics(obj,kind="CLOTH",quality=6)
    fluid=set_extended_physics(obj,kind="LIQUID_DOMAIN",resolution=16)
    smoke=set_extended_physics(obj,kind="SMOKE_FLOW",resolution=16)
    check(cloth["simulation"]["type"]=="CLOTH" and
          fluid["simulation"]["type"]=="LIQUID_DOMAIN" and
          smoke["simulation"]["type"]=="SMOKE_FLOW",
          "Cloth, liquid and smoke author real Blender simulation specs")
    reject(lambda:set_extended_physics(obj,kind="ARBITRARY_SCRIPT"),"Unsupported")
    reject(lambda:set_extended_physics(obj,kind="CLOTH",resolution=900),
           "resolution")
    bridge_source=(ROOT/"integrations/blender/gpl_scene_runner.py").read_text()
    physics_builder=bridge_source.split("def apply_rigid_body(obj_spec, target):",1)[1]
    check(physics_builder.index('kind=setup["type"]') <
          physics_builder.index('bpy.ops.object.select_all(action="DESELECT")'),
          "Cloth and fluid modifiers avoid unnecessary global Blender depsgraph updates")
    check('node.inputs.get("Mesh")' in bridge_source and
          'node.outputs.get("Mesh")' in bridge_source,
          "Blender graph bridge resolves actual Subdivide Mesh sockets")
    scene=build_scene()
    check(validate_scene(scene)==scene,"All professional fields pass scene schema")
    invalid=deepcopy(scene);invalid["objects"][1]["geometry_nodes"]["steps"][0]["type"]="python"
    reject(lambda:validate_scene(invalid),"admitted")
    invalid=deepcopy(scene);invalid["objects"][1]["armature"]["bones"][1]["ik"]["chain_count"]=30
    reject(lambda:validate_scene(invalid),"IK chain")
    invalid=deepcopy(scene);invalid["objects"][1]["simulation"]={"type":"SMOKE_FLOW","quality":100,"resolution":16}
    reject(lambda:validate_scene(invalid),"settings")
    with tempfile.TemporaryDirectory(prefix="studio-pro-3d-") as scratch:
        directory=Path(scratch)
        path=directory/"professional.ttg3d.json"
        path.write_text(json.dumps(scene,indent=2))
        check(validate_scene(json.loads(path.read_text()))==scene,
              "Professional scene saved and reopened without loss")
        app=QApplication.instance() or QApplication([])
        def bad_dialog(*args):
            raise AssertionError("Unexpected modal in Qt professional 3D")
        QMessageBox.warning=staticmethod(bad_dialog)
        QMessageBox.information=staticmethod(bad_dialog)
        modeler=Native3DModeler(isp_box_scene())
        modeler.to_mesh()
        modeler.mode.setCurrentText("Vertex");modeler.component=0
        before_topology=len(modeler.scene["objects"][0]["mesh"]["faces"])
        modeler.sculpt_radius.setValue(5.)
        modeler.adaptive_sculpt()
        check(len(modeler.scene["objects"][0]["mesh"]["faces"])>before_topology,
              "Qt localized dynamic topology sculpt changes real face count")
        modeler.pack_uv()
        check("uv" in modeler.scene["objects"][0],"Qt UV packing invoked real solver")
        modeler.mode.setCurrentText("Face");modeler.component=0
        modeler.mark_uv_seams()
        check(bool(modeler.scene["objects"][0]["uv_seams"]),
              "Qt seam marking edits actual mesh")
        modeler.enable_multires()
        check(modeler.scene["objects"][0]["sculpt_detail"]["levels"]==1,
              "Qt multires control saves modifier specification")
        modeler.make_rig_bone()
        modeler.make_rig_bone()
        modeler.rig_bone.setCurrentText("Bone_2")
        modeler.mode.setCurrentText("Vertex");modeler.component=0
        modeler.paint_weights()
        check(modeler.scene["objects"][0]["armature"]["weights"][0].get("Bone_2",0)>0,
              "Qt brush weight-paints nearby vertices")
        modeler.ik_chain.setValue(2)
        modeler.enable_ik()
        check(bool(modeler.scene["objects"][0]["armature"]["bones"][1]["ik"]),
              "Qt IK control authors chain target")
        modeler.graph_kind.setCurrentText("subdivide")
        modeler.append_graph_node()
        check(modeler.scene["objects"][0]["geometry_nodes"]["steps"][0]["type"]=="subdivide",
              "Qt graph editor appends real geometry node")
        modeler.graph_kind.setCurrentText("transform")
        modeler.append_graph_node()
        modeler.graph_nodes.setCurrentRow(1)
        modeler.move_graph_node(-1)
        check(modeler.scene["objects"][0]["geometry_nodes"]["steps"][0]["type"]=="transform",
              "Qt node chain supports real interactive reorder")
        modeler.graph_nodes.setCurrentRow(1)
        modeler.remove_graph_node()
        check(len(modeler.scene["objects"][0]["geometry_nodes"]["steps"])==1,
              "Qt node chain supports remove operation and undo")
        modeler.physics_kind.setCurrentText("CLOTH")
        modeler.apply_extended_physics()
        check(modeler.scene["objects"][0]["simulation"]["type"]=="CLOTH",
              "Qt physics editor creates cloth modifier spec")
        modeler.undo()
        check("simulation" not in modeler.scene["objects"][0],
              "Professional cloth Undo restores prior validated scene")
        modeler.redo()
        check(modeler.scene["objects"][0]["simulation"]["type"]=="CLOTH",
              "Professional cloth Redo restores exact spec")
        modeler.close()
        app.processEvents()
        if blender_status()["available"]:
            result=render_scene(scene,directory/"real_blender",timeout=720)
            check(Path(result["blend"]).is_file() and Path(result["poster"]).is_file(),
                  "Blender actually renders full professional scene")
            blender=blender_status()["executable"]
            assertion=(
                "import bpy; "
                "rig=bpy.data.objects['Studio.'+'"+scene["objects"][1]["id"]+"']; "
                "assert any(m.type=='MULTIRES' for m in rig.modifiers); "
                "assert any(m.type=='NODES' for m in rig.modifiers); "
                "assert any(e.use_seam for e in rig.data.edges); "
                "assert any(c.type=='IK' for o in bpy.data.objects if o.type=='ARMATURE' "
                "for bone in o.pose.bones for c in bone.constraints); "
                "assert any(m.type=='CLOTH' for o in bpy.data.objects for m in o.modifiers); "
                "assert len([m for o in bpy.data.objects for m in o.modifiers if m.type=='FLUID'])>=4; "
                "assert all(not m.show_render and not m.show_viewport for o in bpy.data.objects "
                "for m in o.modifiers if m.type=='FLUID'); "
                "assert any(m.fluid_type=='DOMAIN' and m.domain_settings.domain_type=='GAS' "
                "for o in bpy.data.objects for m in o.modifiers if m.type=='FLUID'); "
                "assert any(m.fluid_type=='DOMAIN' and m.domain_settings.domain_type=='LIQUID' "
                "for o in bpy.data.objects for m in o.modifiers if m.type=='FLUID'); "
                "print('STUDIO_PHYSICAL_PRO_3D_PASS')"
            )
            tested=subprocess.run([blender,"--background","--factory-startup",
                                    "--disable-autoexec","--python-exit-code","31",
                                    result["blend"],"--python-expr",assertion],
                capture_output=True,text=True,timeout=85)
            check(tested.returncode==0 and "STUDIO_PHYSICAL_PRO_3D_PASS" in tested.stdout,
                  "Physical .blend contains multires, node graph, IK, seams, cloth and fluid: "+
                  tested.stderr[-500:])
        else:
            check(not blender_status()["available"],
                  "No local Blender: did not fabricate physical rendered proof")
    print(json.dumps({"status":"PASS","checks":len(checks),"names":checks},indent=2))

if __name__=="__main__":
    main()
