# SPDX-License-Identifier: GPL-3.0-or-later
"""Separate Blender process bridge. Copyright (c) 2026 THETECHGUY.

This module intentionally uses bpy, and therefore is GPL licensed. It is
executed *inside Blender*, never imported or linked into Creative Studio.
All creative/editor state crosses the process boundary as plain scene JSON.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

argv=sys.argv
if "--" not in argv or len(argv[argv.index("--")+1:]) != 2:
    raise SystemExit("Expected scene.json and existing render directory")
spec_path, out_path = (Path(a).resolve() for a in argv[argv.index("--")+1:])
spec=json.loads(spec_path.read_text(encoding="utf-8"))
out_path.mkdir(parents=True,exist_ok=True)
if spec.get("schema")!="ttg.studio.blender.scene.v1":
    raise ValueError("Unexpected scene specification")
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene

try:
    scene.render.engine=spec.get("engine","BLENDER_EEVEE_NEXT")
except TypeError:
    # EEVEE was renamed across Blender releases; hard fail for Cycles
    if spec.get("engine")=="CYCLES":
        raise
    scene.render.engine="BLENDER_EEVEE"
if scene.render.engine=="CYCLES":
    scene.cycles.samples=int(spec.get("samples",32))
else:
    if hasattr(scene,"eevee") and hasattr(scene.eevee,"taa_render_samples"):
        scene.eevee.taa_render_samples=int(spec.get("samples",32))
scene.render.resolution_x=int(spec["width"])
scene.render.resolution_y=int(spec["height"])
scene.render.resolution_percentage=100
scene.render.film_transparent=False
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGBA"
scene.render.film_transparent=False
scene.frame_start=1
scene.frame_end=int(spec["frames"])
scene.render.fps=int(spec["fps"])
scene.render.threads_mode="FIXED"
scene.render.threads=2
try:
    scene.view_settings.view_transform="AgX"
except TypeError:
    scene.view_settings.view_transform="Standard"
world=bpy.data.worlds.new("TTG Physical Studio World")
scene.world=world
world.use_nodes=True
bg=world.node_tree.nodes.get("Background")
if bg:
    props=spec.get("world",{})
    bg.inputs["Color"].default_value=(*props.get("color",[.03,.035,.055]),1)
    bg.inputs["Strength"].default_value=float(props.get("strength",.65))

def material_for(obj):
    data=obj.get("material",{})
    mat=bpy.data.materials.new(name="TTG "+obj["id"])
    mat.diffuse_color=tuple(data.get("color",[.3,.35,.4,1]))
    mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        def param(key,value):
            socket=bsdf.inputs.get(key)
            if socket is not None:
                socket.default_value=value
        param("Base Color",tuple(data.get("color",[.3,.35,.4,1])))
        param("Metallic",float(data.get("metallic",0)))
        param("Roughness",float(data.get("roughness",.4)))
        param("Transmission Weight",float(data.get("transmission",0)))
        param("Emission Color",tuple(data.get("color",[.3,.35,.4,1])))
        param("Emission Strength",float(data.get("emission_strength",0)))
    return mat

for obj in spec["objects"]:
    kind=obj["type"]
    if kind=="cube":
        bpy.ops.mesh.primitive_cube_add()
    elif kind=="cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=48)
    elif kind=="uv_sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16)
    elif kind=="torus":
        bpy.ops.mesh.primitive_torus_add(major_segments=64,minor_segments=12)
    elif kind=="text":
        bpy.ops.object.text_add()
        bpy.context.object.data.body=obj["text"]
        bpy.context.object.data.extrude=.011
        bpy.context.object.data.bevel_depth=.001
    else:
        raise ValueError("Unsupported 3D shape: "+str(kind))
    target=bpy.context.object
    target.name="Studio."+obj["id"]
    target.location=obj.get("location",[0,0,0])
    target.rotation_euler=[math.radians(v) for v in obj.get("rotation",[0,0,0])]
    target.scale=obj.get("scale",[1,1,1])
    target.data.materials.append(material_for(obj))
    bevel=float(obj.get("bevel",0))
    if bevel and kind in ("cube","cylinder"):
        modifier=target.modifiers.new("Machined edge bevel",type="BEVEL")
        modifier.width=bevel
        modifier.segments=4
        target.modifiers.new("Weighted normals",type="WEIGHTED_NORMAL")

for index,light in enumerate(spec.get("lights",[])):
    data=bpy.data.lights.new("Studio softbox "+str(index),type="AREA")
    data.energy=float(light.get("energy",400))
    data.shape="DISK"
    data.size=float(light.get("size",3))
    data.color=light.get("color",[1,1,1])
    obj=bpy.data.objects.new("Studio light "+str(index),data)
    scene.collection.objects.link(obj)
    obj.location=light["location"]
    direction=Vector(spec["camera"]["target"])-obj.location
    obj.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()

camera_settings=spec["camera"]
data=bpy.data.cameras.new("Cinematic product camera")
camera=bpy.data.objects.new("Studio camera",data)
scene.collection.objects.link(camera)
scene.camera=camera
camera.data.lens=float(camera_settings.get("lens",48))
point=Vector(camera_settings["target"])
initial=Vector(camera_settings["location"])
axis=initial-point
orbit=float(camera_settings.get("orbit_degrees",0))
for f,angle in ((1,0),(int(spec["frames"]),orbit)):
    theta=math.radians(angle)
    new=Vector((axis.x*math.cos(theta)-axis.y*math.sin(theta),
                axis.x*math.sin(theta)+axis.y*math.cos(theta),axis.z))
    camera.location=point+new
    camera.rotation_euler=(point-camera.location).to_track_quat("-Z","Y").to_euler()
    camera.keyframe_insert(data_path="location",frame=f)
    camera.keyframe_insert(data_path="rotation_euler",frame=f)
for fc in camera.animation_data.action.fcurves if camera.animation_data and hasattr(camera.animation_data.action,"fcurves") else []:
    for key in fc.keyframe_points:
        key.interpolation="BEZIER"

bpy.context.scene.frame_set(1)
blend_path=out_path/"scene.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
poster=out_path/"poster.png"
scene.render.filepath=str(poster)
bpy.ops.render.render(write_still=True)
if not poster.is_file():
    raise RuntimeError("Blender created no poster")
if int(spec["frames"])>1:
    frame_dir=out_path/"frames"
    frame_dir.mkdir()
    for f in range(1,int(spec["frames"])+1):
        scene.frame_set(f)
        scene.render.filepath=str(frame_dir/f"frame_{f-1:05d}.png")
        bpy.ops.render.render(write_still=True)
print("TTG Blender physical render complete",poster,blend_path,flush=True)
