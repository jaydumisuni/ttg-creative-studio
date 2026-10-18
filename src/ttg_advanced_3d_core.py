"""Native advanced 3D authoring primitives, Blender-agnostic and bounded.

The scene is Studio-owned JSON. Blender remains a separately installed renderer.
Each operation returns a validated new value; no arbitrary Python/nodes/scripts.
"""
from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from ttg_native_3d import validate_mesh, _v3

MAX_BONES = 32
MAX_CONSTRAINTS = 8


def _local_reference_ids(obj: dict) -> set[str]:
    # Individual mesh/rig mutation cannot know the entire scene; the parent
    # scene validator separately checks those references against actual IDs.
    return {obj.get("id", "object")} | {
        item.get("target") for item in obj.get("constraints", [])
        if isinstance(item,dict) and isinstance(item.get("target"),str)
    }


def validate_advanced_object(obj: dict, identifiers: set[str], *, frames: int) -> None:
    """Reject malformed UV, rigs, constraints, nodes and simulation before bpy."""
    if obj.get("type") != "mesh" and any(k in obj for k in ("uv", "uv_seams", "armature", "geometry_nodes", "sculpt_detail")):
        raise ValueError("Advanced mesh data requires converted mesh geometry")
    mesh = obj.get("mesh") if obj.get("type") == "mesh" else None
    if "uv" in obj:
        faces = validate_mesh(mesh)["faces"]
        uv = obj["uv"]
        if not isinstance(uv, list) or len(uv) != len(faces):
            raise ValueError("UV face corner mapping must match mesh faces")
        for mapping, face in zip(uv, faces):
            if not isinstance(mapping, list) or len(mapping) != len(face):
                raise ValueError("UV face corner count mismatch")
            for coords in mapping:
                if (not isinstance(coords, list) or len(coords) != 2 or
                    any(type(v) not in (int, float) or not math.isfinite(v) or abs(v)>100 for v in coords)):
                    raise ValueError("UV coordinates out of bounds")
    if "uv_seams" in obj:
        if "uv" not in obj:
            raise ValueError("UV seams require authored UV coordinates")
        seams=obj["uv_seams"]
        if not isinstance(seams,list):
            raise ValueError("UV seam edges must be a list")
        from ttg_pro_3d_core import assign_uv_seams
        assign_uv_seams({**obj, "uv_seams":[]}, seams)
    if "sculpt_detail" in obj:
        detail=obj["sculpt_detail"]
        if (not isinstance(detail,dict) or detail.get("mode")!="multires" or
            type(detail.get("levels")) is not int or not 1<=detail["levels"]<=3):
            raise ValueError("Sculpt multires levels outside 1–3")
    if "armature" in obj:
        data = obj["armature"]
        bones = data.get("bones") if isinstance(data, dict) else None
        weights = data.get("weights") if isinstance(data, dict) else None
        if not isinstance(bones, list) or not 1 <= len(bones) <= MAX_BONES:
            raise ValueError("Armature must contain 1–32 bones")
        names = set()
        for bone in bones:
            if not isinstance(bone, dict):
                raise ValueError("Bone must be an object")
            name = bone.get("name")
            if (not isinstance(name, str) or not 1 <= len(name) <= 48 or
                not name.replace("_","").isalnum() or name in names):
                raise ValueError("Bone names must be unique safe identifiers")
            parent = bone.get("parent")
            if parent is not None and parent not in names:
                raise ValueError("Parent bone must be earlier in hierarchy")
            names.add(name)
            head, tail = _v3(bone.get("head")), _v3(bone.get("tail"))
            if sum((a-b)**2 for a,b in zip(head,tail)) < 1e-8:
                raise ValueError("Bone head and tail must differ")
            if "ik" in bone:
                ik=bone["ik"]
                if not isinstance(ik,dict):
                    raise ValueError("IK constraint must be an object")
                from ttg_native_3d import _v3 as coordinates
                try:
                    coordinates(ik.get("target"))
                except (ValueError,TypeError):
                    raise ValueError("IK target requires finite XYZ") from None
                count=0
                cursor=name
                parents={item["name"]:item.get("parent") for item in bones
                         if isinstance(item,dict) and "name" in item}
                while cursor is not None:
                    count+=1;cursor=parents.get(cursor)
                if (type(ik.get("chain_count")) is not int or
                    not 1<=ik["chain_count"]<=count):
                    raise ValueError("IK chain count exceeds actual ancestors")
            for frame in bone.get("keyframes", []):
                if (not isinstance(frame,dict) or type(frame.get("frame")) is not int or
                    not 1 <= frame["frame"] <= frames):
                    raise ValueError("Bone keyframe outside scene")
                _v3(frame.get("rotation"))
        vertex_count = len(validate_mesh(mesh)["vertices"])
        if not isinstance(weights, list) or len(weights) != vertex_count:
            raise ValueError("Skin weights must match every mesh vertex")
        for entry in weights:
            if not isinstance(entry, dict) or len(entry)>4:
                raise ValueError("At most four bone weights per vertex")
            for name, weight in entry.items():
                if (name not in names or type(weight) not in (int,float) or
                    not math.isfinite(weight) or not 0 <= weight <= 1):
                    raise ValueError("Skin weights must refer to valid bones")
            if sum(entry.values()) > 1.001:
                raise ValueError("Skin weights cannot exceed one per vertex")
    constraints=obj.get("constraints", [])
    if not isinstance(constraints,list) or len(constraints)>MAX_CONSTRAINTS:
        raise ValueError("At most eight constraints per object")
    for constraint in constraints:
        if (not isinstance(constraint,dict) or constraint.get("type") not in
            ("COPY_LOCATION","TRACK_TO") or constraint.get("target") not in identifiers or
            constraint["target"] == obj.get("id")):
            raise ValueError("Constraint must target another valid scene object")
    geo=obj.get("geometry_nodes")
    if geo is not None:
        if not isinstance(geo,dict) or geo.get("operation") not in ("transform", "wave", "graph"):
            raise ValueError("Only admitted geometry node operations may execute")
        if geo["operation"]=="graph":
            steps=geo.get("steps")
            if not isinstance(steps,list) or not 1<=len(steps)<=8:
                raise ValueError("Geometry graph requires 1–8 nodes")
            for step in steps:
                if not isinstance(step,dict) or step.get("type") not in (
                    "transform","subdivide","wave"):
                    raise ValueError("Geometry graph node must be an admitted kind")
                if step["type"]=="transform":
                    _v3(step.get("offset"))
                if step["type"]=="subdivide":
                    level=step.get("level")
                    if type(level) is not int or not 1<=level<=2:
                        raise ValueError("Geometry subdivide level out of bounds")
                if step["type"]=="wave":
                    strength=step.get("amplitude")
                    if type(strength) not in (int,float) or not math.isfinite(strength) or not 0<=strength<=2:
                        raise ValueError("Geometry wave amplitude out of bounds")
        else:
            _v3(geo.get("offset",[0,0,0]))
            amplitude=geo.get("amplitude",0.1)
            if type(amplitude) not in (int,float) or not math.isfinite(amplitude) or not 0 <= amplitude <= 2:
                raise ValueError("Geometry node amplitude outside range")
    simulation=obj.get("simulation")
    if simulation is not None:
        if not isinstance(simulation,dict):
            raise ValueError("Simulation must be a validated object")
        mode=simulation.get("type")
        if mode in ("PASSIVE","ACTIVE"):
            mass=simulation.get("mass",1)
            friction=simulation.get("friction",.5)
            if any(type(v) not in (int,float) or not math.isfinite(v) for v in (mass, friction)):
                raise ValueError("Invalid rigid-body numerical property")
            if not .01<=mass<=1000 or not 0<=friction<=1:
                raise ValueError("Rigid-body mass or friction out of range")
        elif mode in ("CLOTH","COLLISION","SMOKE_DOMAIN","SMOKE_FLOW","LIQUID_DOMAIN","LIQUID_FLOW"):
            if obj.get("type")!="mesh":
                raise ValueError("Extended physics requires a mesh")
            quality=simulation.get("quality")
            resolution=simulation.get("resolution")
            if type(quality) is not int or not 1<=quality<=12 or type(resolution) is not int or not 16<=resolution<=64:
                raise ValueError("Fluid/cloth simulation settings out of bounds")
        else:
            raise ValueError("Simulation type not admitted")



def uv_project(mesh: dict, *, axis: str = "z") -> list[list[list[float]]]:
    """Deterministic editable per-face-corner UV projection; no external assets."""
    validate_mesh(mesh)
    if axis not in ("x","y","z"):
        raise ValueError("UV projection axis must be x/y/z")
    axes = {"x":(1,2),"y":(0,2),"z":(0,1)}[axis]
    coords = [[v[k] for k in axes] for v in mesh["vertices"]]
    low=[min(v[i] for v in coords) for i in range(2)]
    high=[max(v[i] for v in coords) for i in range(2)]
    span=[max(high[i]-low[i],1e-9) for i in range(2)]
    return [
        [[round((coords[index][k]-low[k])/span[k],7) for k in range(2)]
         for index in face] for face in mesh["faces"]
    ]


def uv_transform(mapping: list, *, translate: tuple[float,float]=(0,0),
                 scale: tuple[float,float]=(1,1)) -> list:
    """Edit UV placement without mutating original mapping."""
    for x in (*translate,*scale):
        if type(x) not in (int,float) or not math.isfinite(x) or abs(x)>20:
            raise ValueError("Invalid UV transform")
    if any(v == 0 for v in scale):
        raise ValueError("UV scale cannot be zero")
    return [
        [[round(coord[axis]*scale[axis]+translate[axis],7) for axis in range(2)]
         for coord in face] for face in deepcopy(mapping)
    ]


def sculpt(mesh: dict, vertex: int, *, radius: float=.8,
           strength: float=.15, mode: str="inflate") -> dict:
    """Real gaussian falloff sculpt or Laplacian smooth; one atomic mesh edit."""
    validate_mesh(mesh)
    if type(vertex) is not int or not 0 <= vertex < len(mesh["vertices"]):
        raise ValueError("Choose a sculpt center vertex")
    if (type(radius) not in (int,float) or not math.isfinite(radius) or not .001<=radius<=50 or
        type(strength) not in (int,float) or not math.isfinite(strength) or not .001<=strength<=2 or
        mode not in ("inflate","deflate","smooth")):
        raise ValueError("Sculpt brush settings invalid")
    verts=mesh["vertices"]
    center=verts[vertex]
    linked = [set() for _ in verts]
    for face in mesh["faces"]:
        for a,b in zip(face,face[1:]+face[:1]):
            linked[a].add(b)
            linked[b].add(a)
    normal = [0.,0.,0.]
    for face in mesh["faces"]:
        if vertex not in face: continue
        a,b,c = [verts[i] for i in face[:3]]
        ab=[b[k]-a[k] for k in range(3)]
        ac=[c[k]-a[k] for k in range(3)]
        n=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
        normal=[normal[k]+n[k] for k in range(3)]
    length=math.sqrt(sum(x*x for x in normal))
    if length < 1e-9:
        raise ValueError("Cannot sculpt with a degenerate vertex normal")
    normal=[x/length for x in normal]
    output=deepcopy(mesh)
    for i,pos in enumerate(verts):
        dist=math.sqrt(sum((pos[k]-center[k])**2 for k in range(3)))
        if dist >= radius: continue
        influence=(1-(dist/radius)**2)**2
        if mode=="smooth":
            if not linked[i]:continue
            avg=[sum(verts[j][k] for j in linked[i])/len(linked[i]) for k in range(3)]
            result=[pos[k]+min(1,strength)*influence*(avg[k]-pos[k]) for k in range(3)]
        else:
            sign=1 if mode=="inflate" else -1
            result=[pos[k]+sign*strength*influence*normal[k] for k in range(3)]
        output["vertices"][i]=result
    return validate_mesh(output)


def add_bone(obj: dict, name: str, head: list[float], tail: list[float],
             *, parent: str | None = None) -> dict:
    """Bounded editable rig authoring with initial uniform skin weights."""
    if obj.get("type")!="mesh":
        raise ValueError("Armatures require editable mesh objects")
    outcome=deepcopy(obj)
    rig=outcome.setdefault("armature",{"bones":[],"weights":[]})
    if len(rig["bones"]) >= MAX_BONES:
        raise ValueError("Bone count exceeded")
    if not rig["bones"]:
        rig["weights"]=[{} for _ in outcome["mesh"]["vertices"]]
    bone={"name":name,"head":_v3(head),"tail":_v3(tail),"parent":parent}
    rig["bones"].append(bone)
    if len(rig["bones"])==1:
        rig["weights"]=[{name:1.} for _ in outcome["mesh"]["vertices"]]
    validate_advanced_object(outcome,_local_reference_ids(outcome),frames=240)
    return outcome


def set_skin_weight(obj: dict, vertex: int, bone: str, weight: float) -> dict:
    result=deepcopy(obj)
    rig=result.get("armature")
    if not isinstance(rig,dict) or type(vertex) is not int or not 0 <= vertex < len(result["mesh"]["vertices"]):
        raise ValueError("Select a valid rigged mesh vertex")
    names={x["name"] for x in rig["bones"]}
    if bone not in names or type(weight) not in (int,float) or not math.isfinite(weight) or not 0<=weight<=1:
        raise ValueError("Invalid weight assignment")
    entry=dict(rig["weights"][vertex])
    if weight == 0:entry.pop(bone,None)
    else:entry[bone]=float(weight)
    # Adjust other influences proportionally to leave exactly the
    # requested weight available. Prevent full reassignment failing because
    # the first bone initially owns 100% of every vertex.
    remaining = 1-float(weight)
    others = {key:value for key,value in entry.items() if key!=bone}
    total = sum(others.values())
    entry = ({key:value*remaining/total for key,value in others.items()}
             if total>0 else {})
    if weight>0:
        entry[bone]=float(weight)
    rig["weights"][vertex]={key:val for key,val in entry.items() if val>1e-9}
    validate_advanced_object(result,_local_reference_ids(result),frames=240)
    return result


def add_constraint(obj: dict, target: str, *, kind: str="TRACK_TO") -> dict:
    result=deepcopy(obj)
    result.setdefault("constraints",[]).append({"type":kind,"target":target})
    return result


def set_procedural(obj: dict, *, operation: str="transform",
                   offset: list[float] | None=None, amplitude: float=.1) -> dict:
    if obj.get("type")!="mesh":
        raise ValueError("Geometry nodes require an editable mesh")
    result=deepcopy(obj)
    result["geometry_nodes"]={"operation":operation,
                              "offset":_v3(offset if offset is not None else [0,0,.1]),
                              "amplitude":amplitude}
    validate_advanced_object(result,_local_reference_ids(result),frames=240)
    return result


def set_physics(obj: dict, *, active: bool=True, mass: float=1.,
                friction: float=.5) -> dict:
    result=deepcopy(obj)
    result["simulation"]={"type":"ACTIVE" if active else "PASSIVE",
                          "mass":mass,"friction":friction}
    validate_advanced_object(result,_local_reference_ids(result),frames=240)
    return result
