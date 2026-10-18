"""Creative Studio native mesh core.

Pure Python data-model and topology operations. No bpy, Blender runtime,
AI weights, Ptah or GPL code are imported. Blender remains an optional
renderer/interchange application reached through validated scene JSON.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
from typing import Any

MAX_VERTICES = 8192
MAX_FACES = 8192


def _v3(values: Any) -> list[float]:
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        raise ValueError("A vertex needs exactly 3 numeric coordinates")
    if any(type(x) not in (int, float) or not math.isfinite(x)
           or abs(x) > 2000 for x in values):
        raise ValueError("Vertex coordinates must be finite and within bounds")
    return [float(x) for x in values]


def validate_mesh(mesh: dict) -> dict:
    if not isinstance(mesh, dict):
        raise ValueError("Mesh data must be an object")
    vertices = mesh.get("vertices")
    faces = mesh.get("faces")
    if not isinstance(vertices, list) or not (3 <= len(vertices) <= MAX_VERTICES):
        raise ValueError("Mesh vertex count outside 3–8192")
    if not isinstance(faces, list) or not (1 <= len(faces) <= MAX_FACES):
        raise ValueError("Mesh face count outside 1–8192")
    for vert in vertices:
        _v3(vert)
    for face in faces:
        if not isinstance(face, list) or not 3 <= len(face) <= 16:
            raise ValueError("Each face requires 3–16 indices")
        if any(type(i) is not int or not 0 <= i < len(vertices) for i in face):
            raise ValueError("Face contains an invalid vertex index")
        if len(set(face)) != len(face):
            raise ValueError("Degenerate face contains repeated vertices")
        a, b, c = (vertices[i] for i in face[:3])
        ab = [b[i] - a[i] for i in range(3)]
        ac = [c[i] - a[i] for i in range(3)]
        cross = [ab[1]*ac[2]-ab[2]*ac[1],
                 ab[2]*ac[0]-ab[0]*ac[2],
                 ab[0]*ac[1]-ab[1]*ac[0]]
        if sum(t*t for t in cross) < 1e-18:
            raise ValueError("Degenerate face has zero surface area")
    return mesh


def cube() -> dict:
    vertices = [[x, y, z] for z in (-1, 1)
                for y in (-1, 1) for x in (-1, 1)]
    faces = [[0, 2, 3, 1], [4, 5, 7, 6],
             [0, 1, 5, 4], [2, 6, 7, 3],
             [0, 4, 6, 2], [1, 3, 7, 5]]
    return validate_mesh({"vertices": vertices, "faces": faces})


def cylinder(segments: int = 16) -> dict:
    if not 3 <= segments <= 96:
        raise ValueError("Invalid segment count")
    vertices = []
    for z in (-1.0, 1.0):
        for i in range(segments):
            a = 2*math.pi*i/segments
            vertices.append([math.cos(a), math.sin(a), z])
    faces = []
    # Triangulated cap avoids large nonplanar/NGon issues after editing.
    for i in range(1, segments-1):
        faces.append([0, i+1, i])
        faces.append([segments, segments+i, segments+i+1])
    for i in range(segments):
        j = (i+1)%segments
        faces.append([i, j, segments+j, segments+i])
    return validate_mesh({"vertices": vertices, "faces": faces})


def uv_sphere(segments: int = 16, rings: int = 8) -> dict:
    if not 3 <= segments <= 48 or not 2 <= rings <= 32:
        raise ValueError("Invalid spherical resolution")
    verts = [[0, 0, 1]]
    for r in range(1, rings):
        t = math.pi*r/rings
        for i in range(segments):
            a = 2*math.pi*i/segments
            verts.append([math.sin(t)*math.cos(a),
                          math.sin(t)*math.sin(a), math.cos(t)])
    south = len(verts)
    verts.append([0, 0, -1])
    faces = []
    for i in range(segments):
        faces.append([0, 1+i, 1+(i+1)%segments])
    for r in range(rings-2):
        for i in range(segments):
            j=(i+1)%segments
            u=1+r*segments
            v=u+segments
            faces.append([u+i, v+i, v+j, u+j])
    base=1+(rings-2)*segments
    for i in range(segments):
        faces.append([base+i, south, base+(i+1)%segments])
    return validate_mesh({"vertices":verts,"faces":faces})


def torus(major: int = 16, minor: int = 8) -> dict:
    if not 3 <= major <= 48 or not 3 <= minor <= 24:
        raise ValueError("Invalid torus resolution")
    verts=[]
    for i in range(major):
        a=2*math.pi*i/major
        for j in range(minor):
            b=2*math.pi*j/minor
            radius=1+.3*math.cos(b)
            verts.append([radius*math.cos(a),radius*math.sin(a),.3*math.sin(b)])
    faces=[]
    for i in range(major):
        for j in range(minor):
            ni=(i+1)%major
            nj=(j+1)%minor
            faces.append([i*minor+j, ni*minor+j, ni*minor+nj,i*minor+nj])
    return validate_mesh({"vertices":verts,"faces":faces})


PRIMITIVES={"cube":cube,"cylinder":cylinder,"uv_sphere":uv_sphere,"torus":torus}


def convert_primitive(obj: dict) -> dict:
    """Convert only the selected primitive to editable mesh, preserving PBR."""
    if obj.get("type") == "mesh":
        validate_mesh(obj.get("mesh"))
        return obj
    kind=obj.get("type")
    if kind not in PRIMITIVES:
        raise ValueError("Only solid 3D primitives can convert to mesh")
    obj["mesh"]=PRIMITIVES[kind]()
    obj["type"]="mesh"
    return obj


def select_edge(mesh: dict, face_index: int, edge_index: int) -> tuple[int, int]:
    validate_mesh(mesh)
    f=mesh["faces"][face_index]
    if not 0 <= edge_index < len(f):
        raise ValueError("Edge index outside selected face")
    return f[edge_index], f[(edge_index+1)%len(f)]


def transform_selection(mesh: dict, vertices: list[int], delta: list[float]) -> dict:
    validate_mesh(mesh)
    move=_v3(delta)
    if not isinstance(vertices, list) or not vertices:
        raise ValueError("Select one or more mesh vertices")
    if any(type(x) is not int or not 0 <= x < len(mesh["vertices"]) for x in vertices):
        raise ValueError("Invalid selected mesh vertex")
    # Edit a copy so no invalid partial mesh can ever replace live project.
    result=deepcopy(mesh)
    for i in set(vertices):
        result["vertices"][i]=[
            result["vertices"][i][k]+move[k] for k in range(3)
        ]
    return validate_mesh(result)


def subdivide(mesh: dict) -> dict:
    """Manifold-friendly quad subdivision: shared midpoints + per-face centers."""
    validate_mesh(mesh)
    verts=deepcopy(mesh["vertices"])
    mids={}
    faces=[]
    for face in mesh["faces"]:
        new_edges=[]
        for i,a in enumerate(face):
            b=face[(i+1)%len(face)]
            key=tuple(sorted((a,b)))
            if key not in mids:
                va,vb=verts[a],verts[b]
                mids[key]=len(verts)
                verts.append([(va[j]+vb[j])/2 for j in range(3)])
            new_edges.append(mids[key])
        center=[sum(verts[i][k] for i in face)/len(face) for k in range(3)]
        center_id=len(verts)
        verts.append(center)
        for i,a in enumerate(face):
            faces.append([a,new_edges[i],center_id,new_edges[i-1]])
    return validate_mesh({"vertices":verts,"faces":faces})


def extrude_face(mesh: dict, face_index: int, distance: float) -> dict:
    """True mesh face extrusion (cap plus side walls, source face removed)."""
    validate_mesh(mesh)
    if type(face_index) is not int or not 0 <= face_index < len(mesh["faces"]):
        raise ValueError("Select a valid face to extrude")
    if type(distance) not in (int,float) or not math.isfinite(distance) or not .001 <= abs(distance) <= 100:
        raise ValueError("Extrusion distance must be nonzero within bounds")
    vertices=deepcopy(mesh["vertices"])
    faces=deepcopy(mesh["faces"])
    old=faces.pop(face_index)
    a,b,c=(vertices[i] for i in old[:3])
    u=[b[i]-a[i] for i in range(3)]
    v=[c[i]-a[i] for i in range(3)]
    normal=[u[1]*v[2]-u[2]*v[1],
            u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    length=math.sqrt(sum(k*k for k in normal))
    if length < 1e-9:
        raise ValueError("Cannot extrude a degenerate face")
    shift=[distance*n/length for n in normal]
    index={}
    for old_index in old:
        index[old_index]=len(vertices)
        vertices.append([vertices[old_index][k]+shift[k] for k in range(3)])
    for i, current in enumerate(old):
        nxt=old[(i+1)%len(old)]
        faces.append([current,nxt,index[nxt],index[current]])
    faces.append([index[i] for i in old])
    return validate_mesh({"vertices":vertices,"faces":faces})


def delete_faces(mesh: dict, indices: list[int]) -> dict:
    validate_mesh(mesh)
    if not indices or any(type(i) is not int or not 0<=i<len(mesh["faces"]) for i in indices):
        raise ValueError("Invalid face selection")
    faces=[deepcopy(f) for i,f in enumerate(mesh["faces"]) if i not in set(indices)]
    if not faces:
        raise ValueError("At least one face must remain")
    used=sorted(set(v for f in faces for v in f))
    renumber={a:i for i,a in enumerate(used)}
    return validate_mesh({
        "vertices":[deepcopy(mesh["vertices"][i]) for i in used],
        "faces":[[renumber[i] for i in f] for f in faces],
    })


def object_at_frame(obj: dict, frame: float) -> dict:
    """Evaluate native transform keyframes without modifying project data.

    Blender's independently rendered keyframes use the same source values;
    the native viewport performs bounded linear interpolation for preview.
    """
    track=obj.get("keyframes") or []
    if not track:
        return obj
    frames=sorted(track,key=lambda item:item["frame"])
    if frame<=frames[0]["frame"]:
        first=frames[0]
        weight=0.0
        second=first
    elif frame>=frames[-1]["frame"]:
        first=frames[-1]
        weight=0.0
        second=first
    else:
        i=next(i for i,x in enumerate(frames) if x["frame"]>=frame)
        first,second=frames[i-1],frames[i]
        weight=(frame-first["frame"])/(second["frame"]-first["frame"])
    preview=dict(obj)
    for field in ("location","rotation","scale"):
        a=first[field]
        b=second[field]
        preview[field]=[a[k]+weight*(b[k]-a[k]) for k in range(3)]
    return preview


def set_keyframe(obj: dict, frame: int, *, max_frame: int) -> dict:
    """Snapshot actual object transforms to a unique editable keyframe."""
    if type(frame) is not int or not 1<=frame<=max_frame:
        raise ValueError("Keyframe index must lie within project frame bounds")
    track=list(obj.get("keyframes",[]))
    value={"frame":frame}
    for field,default in (("location",[0,0,0]),("rotation",[0,0,0]),
                          ("scale",[1,1,1])):
        value[field]=_v3(obj.get(field,default))
        if field=="scale" and any(x<=0 for x in value[field]):
            raise ValueError("Keyframe scales must remain positive")
    track=[x for x in track if x["frame"]!=frame]
    if len(track)>=64:
        raise ValueError("Maximum 64 keyframes per object")
    track.append(value)
    obj["keyframes"]=sorted(track,key=lambda x:x["frame"])
    return obj


def remove_keyframe(obj: dict, frame: int) -> dict:
    track=obj.get("keyframes",[])
    if not any(k["frame"]==frame for k in track):
        raise ValueError("No keyframe exists at this frame")
    obj["keyframes"]=[k for k in track if k["frame"]!=frame]
    return obj


def export_obj(scene: dict, destination: str | Path) -> Path:
    """Export native editable meshes as independent OBJ using real geometry.

    Primitive transforms apply to vertex coordinates; no Blender required.
    """
    from ttg_blender_engine import validate_scene
    validate_scene(scene)
    dest=Path(destination).expanduser()
    if dest.suffix.lower()!=".obj" or dest.exists() or dest.is_symlink():
        raise ValueError("Choose a new OBJ path (no overwrite)")
    if not dest.parent.is_dir():
        raise FileNotFoundError("OBJ destination directory does not exist")
    lines=["# TTG Creative Studio native 3D mesh v1"]
    offset=0
    for obj in scene["objects"]:
        kind=obj["type"]
        if kind=="mesh":
            mesh=validate_mesh(obj["mesh"])
        elif kind in PRIMITIVES:
            mesh=PRIMITIVES[kind]()
        else:
            continue
        lines.append("o "+obj["id"])
        scale=obj.get("scale",[1,1,1])
        rot=[math.radians(x) for x in obj.get("rotation",[0,0,0])]
        pos=obj.get("location",[0,0,0])
        for v in mesh["vertices"]:
            x,y,z=[v[i]*scale[i] for i in range(3)]
            x,y=y*math.cos(rot[2])-x*math.sin(rot[2]),y*math.sin(rot[2])+x*math.cos(rot[2])
            y,z=y*math.cos(rot[0])-z*math.sin(rot[0]),y*math.sin(rot[0])+z*math.cos(rot[0])
            x,z=x*math.cos(rot[1])+z*math.sin(rot[1]),-x*math.sin(rot[1])+z*math.cos(rot[1])
            lines.append(f"v {x+pos[0]:.9g} {y+pos[1]:.9g} {z+pos[2]:.9g}")
        for face in mesh["faces"]:
            lines.append("f "+" ".join(str(offset+i+1) for i in face))
        offset+=len(mesh["vertices"])
    if offset==0:
        raise ValueError("No mesh geometry to export")
    import os
    import tempfile
    fd,temp=tempfile.mkstemp(prefix=".ttg-obj-",dir=dest.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            f.write("\n".join(lines)+"\n")
            f.flush();os.fsync(f.fileno())
        # Hardlink fails closed rather than clobber an existing file.
        os.link(temp,dest)
    finally:
        Path(temp).unlink(missing_ok=True)
    return dest
