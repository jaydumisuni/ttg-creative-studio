"""Bounded professional 3D authoring atop Studio's existing editable scene.

The GPL Blender process remains the execution backend. These operations
provide REAL geometry edits and validated data, not simulated Blender output.
"""
from __future__ import annotations

from copy import deepcopy
import math

from ttg_native_3d import validate_mesh
from ttg_advanced_3d_core import validate_advanced_object, set_skin_weight


def unwrap_pack_faces(mesh: dict, padding: float = 0.02) -> list[list[list[float]]]:
    """Deterministic separate face islands, normalized and non-overlapping UV atlas.

    This is per-face island packing, not an angle-based global unwrap solver.
    """
    vertices=validate_mesh(mesh)["vertices"]
    faces=mesh["faces"]
    if type(padding) not in (float,int) or not math.isfinite(padding) or not 0 <= padding < .2:
        raise ValueError("UV island padding must be within 0–0.2")
    n=len(faces)
    side=math.ceil(math.sqrt(n))
    cell=1.0/side
    inset=padding*cell
    packed=[]
    for index,face in enumerate(faces):
        points=[vertices[i] for i in face]
        origin=points[0]
        vec_a=[points[1][i]-origin[i] for i in range(3)]
        vec_b=[points[2][i]-origin[i] for i in range(3)]
        cross=[vec_a[1]*vec_b[2]-vec_a[2]*vec_b[1],
               vec_a[2]*vec_b[0]-vec_a[0]*vec_b[2],
               vec_a[0]*vec_b[1]-vec_a[1]*vec_b[0]]
        removed=max(range(3),key=lambda axis:abs(cross[axis]))
        axes=[i for i in range(3) if i!=removed]
        raw=[[p[axes[0]],p[axes[1]]] for p in points]
        min_u=min(v[0] for v in raw);max_u=max(v[0] for v in raw)
        min_v=min(v[1] for v in raw);max_v=max(v[1] for v in raw)
        u_span=max(max_u-min_u,1e-9);v_span=max(max_v-min_v,1e-9)
        col=index%side;row=index//side
        width=cell-2*inset
        packed.append([[round(col*cell+inset+(v[0]-min_u)/u_span*width,7),
                        round(row*cell+inset+(v[1]-min_v)/v_span*width,7)]
                       for v in raw])
    return packed


def assign_uv_seams(obj: dict, edges: list[list[int]]) -> dict:
    result=deepcopy(obj)
    vertices=validate_mesh(result["mesh"])["vertices"]
    actual={tuple(sorted((a, face[(i+1)%len(face)])))
            for face in result["mesh"]["faces"]
            for i,a in enumerate(face)}
    if not isinstance(edges,list) or len(edges)>len(actual):
        raise ValueError("UV seam edges exceed mesh bounds")
    seams=set()
    for edge in edges:
        if not isinstance(edge,list) or len(edge)!=2 or any(type(v) is not int for v in edge):
            raise ValueError("UV seam edge must reference two vertex indices")
        pair=tuple(sorted(edge))
        if pair not in actual or pair in seams:
            raise ValueError("UV seam edge must be unique and belong to mesh")
        seams.add(pair)
    result["uv_seams"]=[list(pair) for pair in sorted(seams)]
    return result


def paint_skin_weights(obj: dict, *, vertex: int, bone: str, radius: float,
                       strength: float, mode: str="add") -> dict:
    result=deepcopy(obj)
    verts=validate_mesh(result["mesh"])["vertices"]
    if type(vertex) is not int or not 0<=vertex<len(verts):
        raise ValueError("Paint center must be an existing mesh vertex")
    if mode not in ("add","subtract","replace") or any(
            type(v) not in (int,float) or not math.isfinite(v) for v in (radius,strength)
        ) or not 0<radius<=100 or not 0<=strength<=1:
        raise ValueError("Invalid skin weight painting brush")
    if not result.get("armature") or bone not in {
        v["name"] for v in result["armature"]["bones"]}:
        raise ValueError("Weight paint requires existing rig bone")
    center=verts[vertex]
    for i,point in enumerate(verts):
        distance=math.dist(center,point)
        if distance>=radius: continue
        influence=max(0,1-distance/radius)*strength
        before=result["armature"]["weights"][i].get(bone,0.)
        weight= (influence if mode=="replace" else
                 min(1,before+influence) if mode=="add" else
                 max(0,before-influence))
        result=set_skin_weight(result,i,bone,weight)
    validate_advanced_object(result,{result["id"]},frames=240)
    return result


def set_multires(obj: dict, *, levels: int=1) -> dict:
    result=deepcopy(obj)
    if result.get("type")!="mesh" or type(levels) is not int or not 1<=levels<=3:
        raise ValueError("Multires levels must be 1–3 on an editable mesh")
    result["sculpt_detail"]={"mode":"multires","levels":levels}
    return result


def set_bone_ik(obj: dict, bone: str, target: list[float],
                chain_count: int=1) -> dict:
    result=deepcopy(obj)
    rig=result.get("armature",{})
    names=[b["name"] for b in rig.get("bones",[])]
    if bone not in names or type(chain_count) is not int or not 1<=chain_count<=len(names):
        raise ValueError("IK bone/chain must exist in the rig")
    if (not isinstance(target,list) or len(target)!=3 or
        any(type(v) not in (float,int) or not math.isfinite(v) or abs(v)>2000 for v in target)):
        raise ValueError("IK target must be bounded XYZ coordinates")
    selected=next(item for item in rig["bones"] if item["name"]==bone)
    # Count actual ancestors, not arbitrary other branches.
    parents={item["name"]:item.get("parent") for item in rig["bones"]}
    count=0;cursor=bone
    while cursor is not None:
        count+=1;cursor=parents[cursor]
    if chain_count>count:
        raise ValueError("IK chain cannot exceed ancestor hierarchy")
    selected["ik"]={"target":[float(x) for x in target],"chain_count":chain_count}
    validate_advanced_object(result,{result["id"]},frames=240)
    return result


def set_geometry_graph(obj: dict, steps: list[dict]) -> dict:
    result=deepcopy(obj)
    if result.get("type")!="mesh" or not isinstance(steps,list) or not 1<=len(steps)<=8:
        raise ValueError("Geometry graph requires 1–8 admitted nodes")
    result["geometry_nodes"]={"operation":"graph","steps":deepcopy(steps)}
    validate_advanced_object(result,{result["id"]},frames=240)
    return result


def set_extended_physics(obj: dict, *, kind: str,
                         quality: int=5, resolution: int=24) -> dict:
    result=deepcopy(obj)
    if result.get("type")!="mesh" or kind not in (
        "CLOTH","COLLISION","SMOKE_DOMAIN","SMOKE_FLOW",
        "LIQUID_DOMAIN","LIQUID_FLOW"):
        raise ValueError("Unsupported Blender physics kind")
    if type(quality) is not int or not 1<=quality<=12 or type(resolution) is not int or not 16<=resolution<=64:
        raise ValueError("Physics quality or fluid resolution outside bounds")
    result["simulation"]={"type":kind,"quality":quality,"resolution":resolution}
    return result


def adaptive_sculpt(mesh: dict, vertex: int, *, radius: float=1.5,
                    strength: float=.1, max_faces: int=64) -> dict:
    """Topology-changing local face-centre refinement, no edge T-junctions.

    Refines only selected nearby polygons into triangle fans while preserving
    the original boundary edges. This is a bounded Dyntopo-style primitive,
    NOT Blender's comprehensive dynamic-topology sculpt brush.
    """
    source=validate_mesh(mesh)
    original=source["vertices"]
    if type(vertex) is not int or not 0<=vertex<len(original):
        raise ValueError("Adaptive sculpt requires an existing selected vertex")
    if (type(radius) not in (float,int) or not math.isfinite(radius) or not 0<radius<=50
        or type(strength) not in (int,float) or not math.isfinite(strength)
        or not -2<=strength<=2 or type(max_faces) is not int or not 1<=max_faces<=256):
        raise ValueError("Invalid adaptive sculpt radius, strength or face budget")
    verts=deepcopy(original)
    faces=[]
    edited=0
    center=original[vertex]
    for face in source["faces"]:
        points=[original[idx] for idx in face]
        centroid=[sum(p[i] for p in points)/len(points) for i in range(3)]
        distance=math.dist(centroid,center)
        if distance >= radius or edited >= max_faces:
            faces.append(list(face))
            continue
        direction_a=[points[1][i]-points[0][i] for i in range(3)]
        direction_b=[points[2][i]-points[0][i] for i in range(3)]
        normal=[direction_a[1]*direction_b[2]-direction_a[2]*direction_b[1],
                direction_a[2]*direction_b[0]-direction_a[0]*direction_b[2],
                direction_a[0]*direction_b[1]-direction_a[1]*direction_b[0]]
        length=math.sqrt(sum(v*v for v in normal))
        if length < 1e-8:
            faces.append(list(face))
            continue
        falloff=max(0.,1.-distance/radius)
        point=[centroid[i]+normal[i]/length*strength*falloff for i in range(3)]
        middle=len(verts)
        verts.append(point)
        for i,val in enumerate(face):
            faces.append([val,face[(i+1)%len(face)],middle])
        edited+=1
    if not edited:
        raise ValueError("Adaptive sculpt radius did not cover any faces")
    if len(verts)>20000 or len(faces)>20000:
        raise ValueError("Adaptive sculpt exceeds Studio's validated mesh budget")
    return validate_mesh({"vertices":verts,"faces":faces})
