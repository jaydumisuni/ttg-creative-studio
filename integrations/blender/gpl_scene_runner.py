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
    # Ubuntu's distro Blender sometimes lacks OpenImageDenoise entirely.
    # The render must not depend on an optional CPU/GPU denoiser.
    if hasattr(scene.cycles, "use_denoising"):
        scene.cycles.use_denoising=False
    for layer in scene.view_layers:
        if hasattr(layer, "cycles") and hasattr(layer.cycles, "use_denoising"):
            layer.cycles.use_denoising=False
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
    elif kind=="mesh":
        # This GPL file executes separately inside Blender; the Studio
        # application exchanges validated geometry using plain scene JSON.
        geometry=obj["mesh"]
        mesh=bpy.data.meshes.new("TTG editable mesh "+obj["id"])
        mesh.from_pydata(geometry["vertices"], [], geometry["faces"])
        mesh.update()
        target=bpy.data.objects.new("Studio."+obj["id"],mesh)
        scene.collection.objects.link(target)
        bpy.ops.object.select_all(action="DESELECT")
        target.select_set(True)
        bpy.context.view_layer.objects.active=target
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
    for frame_spec in sorted(obj.get("keyframes",[]), key=lambda k:k["frame"]):
        frame=int(frame_spec["frame"])
        target.location=frame_spec["location"]
        target.rotation_euler=[
            math.radians(a) for a in frame_spec["rotation"]
        ]
        target.scale=frame_spec["scale"]
        for property_name in ("location","rotation_euler","scale"):
            target.keyframe_insert(data_path=property_name, frame=frame)
    if obj.get("keyframes"):
        first=sorted(obj["keyframes"],key=lambda k:k["frame"])[0]
        target.location=first["location"]
        target.rotation_euler=[math.radians(a) for a in first["rotation"]]
        target.scale=first["scale"]
    bevel=float(obj.get("bevel",0))
    if bevel and kind in ("cube","cylinder"):
        modifier=target.modifiers.new("Machined edge bevel",type="BEVEL")
        modifier.width=bevel
        modifier.segments=4
        target.modifiers.new("Weighted normals",type="WEIGHTED_NORMAL")


# Advanced features are confined to this GPL Blender subprocess. The source
# Studio scene remains an editable, bounded JSON contract.
def apply_uv(obj_spec, target):
    mappings = obj_spec.get("uv")
    if mappings is None:
        return
    layer = target.data.uv_layers.new(name="TTG Editable UV")
    for polygon, face_uv in zip(target.data.polygons, mappings):
        if len(polygon.loop_indices) != len(face_uv):
            raise ValueError("UV face mapping did not match constructed mesh")
        for index, coords in zip(polygon.loop_indices, face_uv):
            layer.data[index].uv = coords


def apply_geometry_nodes(obj_spec, target):
    settings = obj_spec.get("geometry_nodes")
    if not settings:
        return
    tree = bpy.data.node_groups.new("Studio procedural " + obj_spec["id"], "GeometryNodeTree")
    if hasattr(tree, "interface"):
        tree.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        tree.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    else:
        tree.inputs.new("NodeSocketGeometry", "Geometry")
        tree.outputs.new("NodeSocketGeometry", "Geometry")
    entry = tree.nodes.new("NodeGroupInput")
    result = tree.nodes.new("NodeGroupOutput")
    edit = tree.nodes.new("GeometryNodeSetPosition")
    tree.links.new(entry.outputs["Geometry"],edit.inputs["Geometry"])
    tree.links.new(edit.outputs["Geometry"],result.inputs["Geometry"])
    move = settings.get("offset", [0,0,0])
    if settings["operation"] == "transform":
        edit.inputs["Offset"].default_value = move
    else:
        # Wave is an actual procedural geometry-node network rather than
        # baked vertices. Offset.z = sin(position.x * 6) * amplitude.
        position = tree.nodes.new("GeometryNodeInputPosition")
        split = tree.nodes.new("ShaderNodeSeparateXYZ")
        multiplier = tree.nodes.new("ShaderNodeMath")
        multiplier.operation = "MULTIPLY"
        multiplier.inputs[1].default_value = 6.0
        sine = tree.nodes.new("ShaderNodeMath")
        sine.operation = "SINE"
        amount = tree.nodes.new("ShaderNodeMath")
        amount.operation = "MULTIPLY"
        amount.inputs[1].default_value = settings.get("amplitude", .1)
        xyz = tree.nodes.new("ShaderNodeCombineXYZ")
        xyz.inputs["X"].default_value = move[0]
        xyz.inputs["Y"].default_value = move[1]
        tree.links.new(position.outputs["Position"], split.inputs["Vector"])
        tree.links.new(split.outputs["X"], multiplier.inputs[0])
        tree.links.new(multiplier.outputs[0], sine.inputs[0])
        tree.links.new(sine.outputs[0], amount.inputs[0])
        tree.links.new(amount.outputs[0], xyz.inputs["Z"])
        tree.links.new(xyz.outputs["Vector"], edit.inputs["Offset"])
    modifier=target.modifiers.new("TTG Procedural Geometry",type="NODES")
    modifier.node_group=tree


def apply_rig(obj_spec, target):
    rig = obj_spec.get("armature")
    if not rig:
        return
    arm = bpy.data.armatures.new("Studio skeleton " + obj_spec["id"])
    skeleton = bpy.data.objects.new("Studio Rig " + obj_spec["id"], arm)
    scene.collection.objects.link(skeleton)
    # Bones and skin weights are authored in the mesh object's local coords.
    skeleton.matrix_world = target.matrix_world.copy()
    bpy.ops.object.select_all(action="DESELECT")
    skeleton.select_set(True)
    bpy.context.view_layer.objects.active = skeleton
    bpy.ops.object.mode_set(mode="EDIT")
    constructed = {}
    for bone in rig["bones"]:
        item = arm.edit_bones.new(bone["name"])
        item.head = bone["head"]
        item.tail = bone["tail"]
        if bone.get("parent") is not None:
            item.parent=constructed[bone["parent"]]
        constructed[bone["name"]]=item
    bpy.ops.object.mode_set(mode="OBJECT")
    for bone in rig["bones"]:
        target.vertex_groups.new(name=bone["name"])
    for vi, weight_map in enumerate(rig["weights"]):
        for name, strength in weight_map.items():
            if strength > 0:
                target.vertex_groups[name].add([vi],strength,"REPLACE")
    modifier=target.modifiers.new("TTG Armature Deformation",type="ARMATURE")
    modifier.object=skeleton
    for bone in rig["bones"]:
        pose=skeleton.pose.bones[bone["name"]]
        pose.rotation_mode="XYZ"
        for key in bone.get("keyframes", []):
            pose.rotation_euler = [math.radians(v) for v in key["rotation"]]
            pose.keyframe_insert(data_path="rotation_euler",frame=key["frame"])
    return skeleton


def apply_rigid_body(obj_spec, target):
    setup=obj_spec.get("simulation")
    if not setup:
        return
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active=target
    bpy.ops.rigidbody.object_add()
    target.rigid_body.type=setup["type"]
    target.rigid_body.mass=float(setup.get("mass",1))
    target.rigid_body.friction=float(setup.get("friction",.5))
    target.rigid_body.collision_shape="CONVEX_HULL"


# Construct modifiers in deterministic stages and resolve targets only
# once every scene object exists. Explicit whitelist prevents arbitrary bpy.
for obj_spec in spec["objects"]:
    if obj_spec.get("type")!="mesh":
        continue
    target=bpy.data.objects["Studio."+obj_spec["id"]]
    apply_uv(obj_spec,target)
    apply_geometry_nodes(obj_spec,target)
    apply_rig(obj_spec,target)
    apply_rigid_body(obj_spec,target)

for obj_spec in spec["objects"]:
    source=bpy.data.objects["Studio."+obj_spec["id"]]
    for descriptor in obj_spec.get("constraints", []):
        modifier=source.constraints.new(descriptor["type"])
        modifier.target=bpy.data.objects["Studio."+descriptor["target"]]
        if descriptor["type"]=="TRACK_TO":
            modifier.track_axis="TRACK_NEGATIVE_Z"
            modifier.up_axis="UP_Y"

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
