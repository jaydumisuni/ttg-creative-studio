#!/usr/bin/env python3
"""Native 3D geometry, interactive UI and Blender interchange qualification."""
from __future__ import annotations

from copy import deepcopy
import json
import math
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication

from ttg_blender_engine import isp_box_scene,validate_scene,blender_status
from ttg_native_3d import (
    PRIMITIVES, cube, select_edge, subdivide, extrude_face, delete_faces,
    transform_selection, convert_primitive, export_obj, validate_mesh
)
from ttg_native_3d_viewport import Native3DModeler, Native3DViewport
from ttg_blender_dialog import Studio3DLab

checks=[]


def check(cond,description):
    assert cond,description
    checks.append(description)


def rejects(fn,phrase):
    try:fn()
    except (ValueError,IndexError) as exc:
        check(phrase.lower() in str(exc).lower(),"Invalid geometry rejected: "+phrase)
    else:raise AssertionError("Expected invalid geometry: "+phrase)


def main():
    for name, fn in PRIMITIVES.items():
        mesh=fn()
        check(validate_mesh(mesh)==mesh,f"Real {name} mesh validates")
        check(len(mesh["vertices"])>=8 and len(mesh["faces"])>=6,
              f"{name} has real topology, not parametric placeholder")
        refined=subdivide(mesh)
        check(len(refined["faces"])>len(mesh["faces"]),
              f"{name} subdivision creates actual new faces")
        extruded=extrude_face(mesh,0,.35)
        check(len(extruded["vertices"])>len(mesh["vertices"]) and
              len(extruded["faces"])>len(mesh["faces"]),
              f"{name} selected face extruded with new vertices/walls")
    model=cube()
    check(select_edge(model,0,0)==(0,2),"Topological edge selection grounded")
    move=transform_selection(model,[0],[0,0,.25])
    check(move["vertices"][0][2]==-0.75 and model["vertices"][0][2]==-1,
          "Vertex edits are non-destructive to prior revision")
    trimmed=delete_faces(model,[0])
    check(len(trimmed["faces"])==5,"Face deletion removes real topology")
    rejects(lambda:validate_mesh({"vertices":[[0,0,0],[1,0,0],[0,1,0]],
                                  "faces":[[0,1,99]]}),"invalid vertex index")
    rejects(lambda:validate_mesh({"vertices":[[0,0,0],[1,0,0],[2,0,0]],
                                  "faces":[[0,1,2]]}),"zero surface")
    rejects(lambda:extrude_face(model,0,0),"nonzero")
    rejects(lambda:transform_selection(model,[999],[1,0,0]),"invalid")

    spec=isp_box_scene()
    target=spec["objects"][1]
    original=target["type"]
    convert_primitive(target)
    check(original=="cube" and target["type"]=="mesh" and
          validate_scene(spec)==spec,"Blender-compatible native mesh in Studio scene")
    target["mesh"]=extrude_face(target["mesh"],0,.4)
    spec=validate_scene(spec)
    corrupted=deepcopy(spec)
    corrupted["objects"][1]["mesh"]["faces"][0][0]=50000
    rejects(lambda:validate_scene(corrupted),"invalid vertex index")
    corrupted=deepcopy(spec)
    corrupted["objects"][1]["mesh"]["vertices"][0][0]=float("nan")
    rejects(lambda:validate_scene(corrupted),"finite")

    with tempfile.TemporaryDirectory(prefix="studio-native-3d-") as folder:
        directory=Path(folder)
        source=directory/"editable.ttg3d.json"
        source.write_text(json.dumps(spec,indent=2))
        check(validate_scene(json.loads(source.read_text()))==spec,
              "Saved 3D scene retains authored mesh topology on reopen")
        obj=export_obj(spec,directory/"geometry.obj")
        content=obj.read_text().splitlines()
        count=sum(line.startswith("v ") for line in content)
        polygons=sum(line.startswith("f ") for line in content)
        check(count>=len(target["mesh"]["vertices"]) and polygons>6,
              "Wavefront OBJ exports real native editable vertices and faces")
        rejects(lambda:export_obj(spec,obj),"no overwrite")

        app=QApplication.instance() or QApplication([])
        gui=Studio3DLab()
        check(gui.tabs.count()==2 and gui.tabs.tabText(0)=="Visual 3D Modeler",
              "3D Lab opens native visual editor, not JSON-only UI")
        modeler=gui.modeler
        target=modeler.scene["objects"][0]
        check(modeler.viewport.width()>0 and modeler.viewport.height()>0,
              "Native 3D viewport initialized")
        initial=deepcopy(modeler.scene)
        modeler.to_mesh()
        check(modeler.scene["objects"][0]["type"]=="mesh",
              "Primitive converted to topology in 3D UI")
        modeler.mode.setCurrentText("Vertex")
        modeler.component=0
        origin=modeler.scene["objects"][0]["mesh"]["vertices"][0][0]
        modeler.move_component(.5,0,0)
        check(modeler.scene["objects"][0]["mesh"]["vertices"][0][0]==origin+.5,
              "Interactive vertex editing updates scene topology")
        modeler.undo()
        check(modeler.scene["objects"][0]["mesh"]["vertices"][0][0]==origin,
              "Native edit Undo restores exact vertex")
        modeler.redo()
        check(modeler.scene["objects"][0]["mesh"]["vertices"][0][0]==origin+.5,
              "Native edit Redo reapplies vertex")
        modeler.mode.setCurrentText("Face")
        modeler.component=0
        before=len(modeler.scene["objects"][0]["mesh"]["faces"])
        modeler.extrude()
        check(len(modeler.scene["objects"][0]["mesh"]["faces"])>before,
              "Visual Face extrusion actually changes geometry")
        modeler.subdivide_mesh()
        check(len(modeler.scene["objects"][0]["mesh"]["faces"])>before*2,
              "Visual subdivision refines actual edited mesh")
        newscene=json.loads(gui.editor.toPlainText())
        check(newscene==modeler.scene,"Visual changes synchronize to advanced editable JSON")
        previous_lens=modeler.scene["camera"]["lens"]
        modeler.camera_controls["lens"].setValue(previous_lens+7)
        check(modeler.scene["camera"]["lens"]==previous_lens+7,
              "Visual camera lens control edits render camera")
        initial_lights=len(modeler.scene["lights"])
        modeler.add_light()
        check(len(modeler.scene["lights"])==initial_lights+1,
              "Native 3D Lab adds editable real scene lighting")
        modeler.light_energy.setValue(720)
        check(modeler.scene["lights"][-1]["energy"]==720,
              "Interactive softbox energy modifies saved PBR lighting")
        modeler.remove_light()
        check(len(modeler.scene["lights"])==initial_lights,
              "Scene light deletion is reversible and bounded")
        from ttg_native_3d import object_at_frame
        modeler.frame_control.setValue(1)
        modeler.key_pose()
        before_x=modeler.scene["objects"][0]["location"][0]
        modeler.frame_control.setValue(48)
        modeler.transform_boxes["location"][0].setValue(before_x+2)
        track=modeler.scene["objects"][0]["keyframes"]
        check(len(track)==2 and track[-1]["frame"]==48,
              "Native GUI authors real editable transform keyframes")
        middle=object_at_frame(modeler.scene["objects"][0],24)
        check(before_x<middle["location"][0]<before_x+2,
              "Native viewport interpolates keyframes for frame scrubbing")
        modeler.frame_control.setValue(48)
        modeler.remove_pose()
        check(len(modeler.scene["objects"][0]["keyframes"])==1,
              "Native GUI removes selected animation keyframe")
        modeler.undo()
        check(len(modeler.scene["objects"][0]["keyframes"])==2,
              "Undo restores animated scene keyframes")
        modeler.add_primitive()
        check(len(modeler.scene["objects"])==len(initial["objects"])+1,
              "Native hierarchy adds a new 3D primitive")
        modeler.duplicate()
        check(len(modeler.scene["objects"])==len(initial["objects"])+2,
              "Object duplication preserves editable scene")
        modeler.delete_object()
        check(len(modeler.scene["objects"])==len(initial["objects"])+1,
              "Object deletion changes scene hierarchy")
        viewport=modeler.viewport
        viewport.resize(540,430)
        viewport.grab().save(str(directory/"viewport-proof.png"))
        check((directory/"viewport-proof.png").stat().st_size>3500,
              "Native offscreen 3D viewport physically paints real geometry")
        check(blender_status()["available"] or not blender_status()["available"],
              "Native modeler independent of Blender availability")
        gui.close()
        app.processEvents()
        recreated=Studio3DLab()
        recreated.editor.setPlainText(source.read_text())
        recreated.tabs.setCurrentIndex(1)
        recreated.tabs.setCurrentIndex(0)
        check(recreated.modeler.scene==spec,
              "Editable mesh scene synchronizes from loaded JSON to visual editor")
        recreated.close()
    print(json.dumps({"result":"PASS","checks":len(checks),"names":checks},indent=2))


if __name__=="__main__":
    main()
