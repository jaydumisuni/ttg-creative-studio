# SPDX-License-Identifier: GPL-3.0-or-later
"""Separate GPL Blender process for bounded cache baking.

Blender scene is loaded before this script. Blender crashes remain isolated
from the host Studio process. Do not claim success without actual caches.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import bpy

argv=sys.argv
if "--" not in argv or len(argv[argv.index("--")+1:]) != 4:
    raise SystemExit("Expected destination object-id CLOTH|GAS|LIQUID frame-end")
dest_s, obj_id, kind, frames=argv[argv.index("--")+1:]
dest=Path(dest_s).resolve()
if not dest.is_dir() or not 2 <= int(frames) <= 60:
    raise ValueError("Approved working directory and frame range required")
frames=int(frames)
if kind not in ("CLOTH","GAS","LIQUID"):
    raise ValueError("Unapproved simulation bake mode")

object_name="Studio."+obj_id
mesh=bpy.data.objects.get(object_name)
if mesh is None or mesh.type!="MESH":
    raise ValueError("Requested editable Blender simulation mesh not present")
kind_type="CLOTH" if kind=="CLOTH" else "FLUID"
mods=[m for m in mesh.modifiers if m.type==kind_type]
if len(mods)!=1:
    raise ValueError("Target Blender mesh must contain exactly one matching physics modifier")
mod=mods[0]
if kind in ("GAS","LIQUID"):
    # The CI-distributed Blender 3.4 crashed on evaluation of unbaked
    # fluid domains. A newer verified Blender build is a hard prerequisite;
    # never turn on dangerous modifiers in the ordinary scene renderer.
    if bpy.app.version < (4, 2, 0):
        raise RuntimeError("Fluid bake rejected: Blender 4.2+ required for isolated qualification")
    if mod.fluid_type!="DOMAIN" or mod.domain_settings.domain_type!=kind:
        # For GAS, domain_type should be GAS; LIQUID should be LIQUID.
        raise ValueError("Target is not the specified fluid domain")
    # Future-compatible path: independently baked cache, not fake render
    # frames. Blender API availability and resulting cache data are checked.
    domain=mod.domain_settings
    domain.cache_type="MODULAR"
    domain.cache_frame_start=1
    domain.cache_frame_end=frames
    domain.cache_directory=str(dest/"fluid-cache")
    # Fluid flows are deliberately disabled by the ordinary render bridge to
    # prevent evaluation crashes. Activate only matching flow types inside this
    # isolated version-qualified process.
    flows=[]
    for other in bpy.data.objects:
        for candidate in other.modifiers:
            if candidate.type=="FLUID" and candidate.fluid_type=="FLOW":
                if candidate.flow_settings.flow_type == ("SMOKE" if kind=="GAS" else "LIQUID"):
                    candidate.show_viewport=True
                    candidate.show_render=False
                    flows.append(other.name)
    if not flows:
        raise RuntimeError("Fluid simulation requires a real matching flow object")
    mod.show_viewport=True
    mod.show_render=False
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active=mesh
    if not hasattr(bpy.ops.fluid,"bake_data"):
        raise RuntimeError("Installed Blender build cannot bake fluid data")
    result=bpy.ops.fluid.bake_data()
    if "FINISHED" not in result:
        raise RuntimeError("Blender fluid baking did not finish")
    cache_dir=dest/"fluid-cache"
    files=[p for p in cache_dir.rglob("*") if p.is_file()]
    if not files or sum(p.stat().st_size for p in files)<1024:
        raise RuntimeError("Blender produced no valid fluid cache artifacts")
    if len(files)>10000 or sum(p.stat().st_size for p in files)>2*1024**3:
        raise RuntimeError("Fluid cache exceeds admitted disk budget")
    proof={"kind":kind,"status":"baked","frames":frames,
           "active_flows":flows,
           "cache_files":len(files),
           "cache_bytes":sum(p.stat().st_size for p in files)}
else:
    if any(m.type=="FLUID" and m.show_viewport for o in bpy.data.objects
           for m in o.modifiers):
        raise RuntimeError("Active fluid modifier blocks isolated cloth bake")
    cache=mod.point_cache
    cache.frame_start=1
    cache.frame_end=frames
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active=mesh
    bpy.context.scene.frame_set(1)
    # Blender exposes active cloth point cache through a context override.
    with bpy.context.temp_override(point_cache=cache,object=mesh,active_object=mesh):
        answer=bpy.ops.ptcache.bake(bake=True)
    if "FINISHED" not in answer or not cache.is_baked:
        raise RuntimeError("Blender cloth point cache is not physically baked")
    proof={"kind":"CLOTH","status":"baked","frames":frames,
           "point_cache_baked":bool(cache.is_baked)}

blend=dest/"baked.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
if not blend.is_file() or blend.stat().st_size<100:
    raise RuntimeError("No saved Blender scene after bake")
proof["blender_version"]=".".join(map(str,bpy.app.version[:3]))
proof["blend_sha256"]=hashlib.sha256(blend.read_bytes()).hexdigest()
(dest/"simulation-proof.json").write_text(json.dumps(proof,indent=2))
print("TTG_PHYSICAL_SIMULATION_BAKED",json.dumps(proof),flush=True)
