"""Advanced Studio-owned 3D authoring with validated Blender execution.

These operations serialize reviewable scene changes, not unbounded bpy scripts.
"""
from __future__ import annotations
from copy import deepcopy
import math
from ttg_native_3d import validate_mesh
from ttg_advanced_3d_core import validate_advanced_object
from ttg_pro_3d_core import adaptive_sculpt

def set_uv_unwrap(obj: dict, *, method: str="SMART_PROJECT",
                  margin: float=.025, angle_limit: float=66.) -> dict:
    result=deepcopy(obj)
    if result.get("type")!="mesh": raise ValueError("UV unwrap requires an editable mesh")
    validate_mesh(result["mesh"])
    if method not in ("SMART_PROJECT","ANGLE_BASED","CONFORMAL"):
        raise ValueError("UV method must be approved")
    if (type(margin) not in (int,float) or not math.isfinite(margin) or not 0 <= margin <= .12 or
        type(angle_limit) not in (int,float) or not math.isfinite(angle_limit)
        or not 1 <= angle_limit <= 89):
        raise ValueError("UV margin/angle invalid")
    result.pop("uv",None)
    result.pop("uv_seams",None)
    result["uv_unwrap"]={"method":method,"margin":float(margin),
                         "angle_limit":float(angle_limit)}
    return result

def set_geometry_dag(obj: dict, nodes: list[dict], output: str) -> dict:
    result=deepcopy(obj)
    if result.get("type")!="mesh":
        raise ValueError("Geometry graph requires an editable mesh")
    result["geometry_nodes"]={"operation":"dag","nodes":deepcopy(nodes),"output":output}
    validate_advanced_object(result,{result["id"]},frames=240)
    return result

def set_ik_pole(obj: dict, bone: str, pole: list[float], *, angle: float=0.) -> dict:
    result=deepcopy(obj)
    rig=result.get("armature",{})
    chosen=next((b for b in rig.get("bones",[]) if b["name"]==bone),None)
    if chosen is None or "ik" not in chosen or chosen["ik"]["chain_count"]<2:
        raise ValueError("IK pole requires a bone with 2+ chain")
    if (not isinstance(pole,list) or len(pole)!=3 or
        any(type(q) not in (int,float) or not math.isfinite(q) or abs(q)>2000 for q in pole) or
        type(angle) not in (int,float) or not math.isfinite(angle) or abs(angle)>180):
        raise ValueError("IK pole requires finite XYZ and angle")
    chosen["ik"]["pole"]=[float(q) for q in pole]
    chosen["ik"]["pole_angle"]=float(angle)
    validate_advanced_object(result,{result["id"]},frames=240)
    return result

def normalize_skin_weights(obj: dict) -> dict:
    result=deepcopy(obj)
    rig=result.get("armature")
    if result.get("type")!="mesh" or not rig:
        raise ValueError("Weight normalization requires a skinned mesh")
    for weights in rig["weights"]:
        summation=sum(weights.values())
        if summation>0:
            for bone in weights:
                weights[bone]=round(weights[bone]/summation,8)
    validate_advanced_object(result,{result["id"]},frames=240)
    return result

def sculpt_stroke(obj: dict, vertices: list[int], *, radius: float=1.5,
                  strength: float=.12) -> dict:
    """Bounded sequential adaptive-topology stroke. Does not claim full Dyntopo."""
    result=deepcopy(obj)
    if result.get("type")!="mesh" or not isinstance(vertices,list) or not 1<=len(vertices)<=8:
        raise ValueError("Sculpt stroke requires 1–8 mesh vertex picks")
    if any(key in result for key in ("uv","uv_unwrap","uv_seams","armature","sculpt_detail")):
        raise ValueError("Changing topology invalidates UV/skin/multires metadata")
    original=validate_mesh(result["mesh"])
    if any(type(i) is not int or not 0<=i<len(original["vertices"]) for i in vertices):
        raise ValueError("Sculpt stroke vertex index invalid")
    for index in vertices:
        result["mesh"]=adaptive_sculpt(result["mesh"],index,radius=radius,
                                       strength=strength,max_faces=32)
    return result
