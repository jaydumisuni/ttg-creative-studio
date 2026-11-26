"""Bounded CADCraft DXF 2D presentation interchange for existing TTG Studio.

This is not a STEP/BREP, electrical netlist or qualified mechanical CAD
interface. It preserves exact source coordinates for simple DXF line,
circle and straight polyline primitives with explicit units and true color.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path

from ttg_filmcraft_otio_bridge import _safe_write
from ttg_project_schema import CanvasSpec, Layer, Transform, TTGProject

MAX_BYTES = 4 * 1024 * 1024
MAX_ENTITIES = 256
UNITS = {"unitless": 0, "inch": 1, "mm": 4}
ACI = {
    1:"#FF0000", 2:"#FFFF00", 3:"#00FF00", 4:"#00FFFF",
    5:"#0000FF", 6:"#FF00FF", 7:"#FFFFFF",
}


def _num(value, name, bound=4096.0):
    if isinstance(value, bool):
        raise ValueError(f"DXF {name} must be numeric")
    try:
        v = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"DXF {name} must be numeric") from exc
    if not math.isfinite(v) or v < -0.000001 or v > bound:
        raise ValueError(f"DXF {name} coordinate outside canvas")
    return max(v, 0.0)


def _raw_pairs(raw: bytes) -> list[tuple[int, str]]:
    if not raw or len(raw) > MAX_BYTES or b"\x00" in raw:
        raise ValueError("Only bounded ASCII DXF is supported")
    try:
        lines = raw.decode("utf-8-sig").replace("\r\n","\n").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("Only text-encoded DXF is supported") from exc
    if len(lines) % 2:
        raise ValueError("DXF group-code/value pairs are incomplete")
    if len(lines) > 30000:
        raise ValueError("DXF group budget exceeded")
    result = []
    for index in range(0,len(lines),2):
        try:
            code = int(lines[index].strip())
        except ValueError as exc:
            raise ValueError("DXF group code is not an integer") from exc
        val = lines[index+1].strip()
        if not 0 <= code <= 1071 or len(val) > 1024:
            raise ValueError("Unsupported DXF group code/value size")
        result.append((code,val))
    return result


def _sections(pairs):
    sections = {}
    idx = 0
    while idx < len(pairs):
        if pairs[idx] == (0,"EOF"):
            if idx != len(pairs)-1:
                raise ValueError("Data after DXF EOF")
            return sections
        if pairs[idx] != (0,"SECTION") or idx+1 >= len(pairs) or pairs[idx+1][0] != 2:
            raise ValueError("DXF requires explicit SECTION headers")
        kind = pairs[idx+1][1]
        if kind not in {"HEADER","ENTITIES"} or kind in sections:
            raise ValueError(f"Unsupported DXF section or duplicate: {kind}")
        idx += 2
        start = idx
        while idx < len(pairs) and pairs[idx] != (0,"ENDSEC"):
            idx += 1
        if idx >= len(pairs):
            raise ValueError("DXF section missing ENDSEC")
        sections[kind] = pairs[start:idx]
        idx += 1
    raise ValueError("DXF missing EOF")


def _fields(records, allowed):
    fields = {}
    for code,value in records:
        if code not in allowed:
            raise ValueError(f"Unsupported DXF geometry group code {code}")
        fields.setdefault(code,[]).append(value)
    return fields


def _one(fields, key, default=None):
    values=fields.get(key, [])
    if len(values)>1:
        raise ValueError(f"Duplicate DXF geometry value {key}")
    if not values:
        if default is None:
            raise ValueError(f"Missing DXF geometry value {key}")
        return default
    return values[0]


def _hex_color(fields):
    value=fields.get(420,[])
    if len(value)>1:
        raise ValueError("Duplicate DXF truecolor")
    if value:
        number = int(value[0])
        if not 0 <= number <= 0xFFFFFF:
            raise ValueError("Invalid DXF truecolor")
        return f"#{number:06X}"
    aci=int(_one(fields,62,"7"))
    if aci not in ACI:
        raise ValueError("Unsupported DXF indexed color")
    return ACI[aci]


def _check_layer(fields):
    name = _one(fields,8,"0")
    if not 1 <= len(name) <= 80 or "\n" in name:
        raise ValueError("Invalid DXF layer name")
    return name


def _cad_arc_screen_points(cx: float, cy: float, radius: float,
                           start_degrees: float, end_degrees: float,
                           width: float, height: float) -> list[list[float]]:
    """Sample the explicitly 2D CAD ARC for Studio presentation, CCW and y-up.

    Curve source values are retained separately; sampled points have no
    engineering tolerance or BREP authority. End<=start wraps past 360°.
    """
    if any(not math.isfinite(v) for v in (cx, cy, radius, start_degrees, end_degrees)):
        raise ValueError("DXF ARC requires finite geometry")
    if radius <= 0 or radius > max(width, height):
        raise ValueError("DXF ARC radius is outside canvas")
    if not 0 <= start_degrees < 360 or not 0 <= end_degrees < 360:
        raise ValueError("DXF ARC angles must be in [0,360)")
    delta = (end_degrees-start_degrees) % 360
    if delta <= 1e-8:
        raise ValueError("Full-circle or zero-sweep ARC must use CIRCLE")
    samples = max(2, min(128, math.ceil(delta/5)+1))
    points = []
    for index in range(samples):
        rad = math.radians(start_degrees + delta * index/(samples-1))
        x = cx + radius*math.cos(rad)
        y = height - (cy + radius*math.sin(rad))
        if not -1e-7 <= x <= width+1e-7 or not -1e-7 <= y <= height+1e-7:
            raise ValueError("CAD ARC crosses canvas boundary")
        points.append([min(width,max(0,x)),min(height,max(0,y))])
    return points


def _points_digest(points: list[list[float]]) -> str:
    return sha256(json.dumps(points,sort_keys=True,separators=(",",":"),
                            allow_nan=False).encode("utf8")).hexdigest()


def _geometry_entities(pairs, width, height):
    pos = 0
    layers = []
    while pos < len(pairs):
        kindcode,kind=pairs[pos]
        if kindcode!=0 or kind not in {"LINE","LWPOLYLINE","CIRCLE","ARC"}:
            raise ValueError(f"Unsupported DXF entity: {kind}")
        pos += 1
        records=[]
        while pos < len(pairs) and pairs[pos][0] != 0:
            records.append(pairs[pos]);pos+=1
        if len(layers)>=MAX_ENTITIES:
            raise ValueError("DXF entity budget exceeded")
        if kind=="LINE":
            f=_fields(records,{5,8,62,420,10,20,11,21,30,31})
            if float(_one(f,30,"0")) or float(_one(f,31,"0")):
                raise ValueError("3D CAD lines require a 3D adapter")
            pts=[[_num(_one(f,10),"x",width),height-_num(_one(f,20),"y",height)],
                 [_num(_one(f,11),"x",width),height-_num(_one(f,21),"y",height)]]
            if pts[0]==pts[1]:
                raise ValueError("Zero-length CAD line")
            layer=Layer(id=f"cad_{len(layers):04d}",type="connector_line",
                        name=f"CAD line {len(layers)}",
                        properties={"points":pts,"color":_hex_color(f),
                                    "stroke_width":3,"cad_layer":_check_layer(f)})
        elif kind=="LWPOLYLINE":
            f=_fields(records,{5,8,62,420,90,70,10,20,38,43})
            if float(_one(f,38,"0")) or float(_one(f,43,"0")):
                raise ValueError("Elevated or wide CAD polyline unsupported")
            number=int(_one(f,90))
            xs=f.get(10,[]);ys=f.get(20,[])
            if not 2 <= number <= 128 or len(xs)!=number or len(ys)!=number:
                raise ValueError("DXF polyline count does not match vertices")
            flags=int(_one(f,70,"0"))
            if flags not in {0,1}:
                raise ValueError("Curved/mesh/3D CAD polyline unsupported")
            pts=[[_num(x,"x",width),height-_num(y,"y",height)]
                 for x,y in zip(xs,ys)]
            if flags:
                if len(pts)<3:raise ValueError("Closed CAD polyline requires three vertices")
                pts.append(pts[0][:])
            layer=Layer(id=f"cad_{len(layers):04d}",type="connector_line",
                        name=f"CAD polyline {len(layers)}",
                        properties={"points":pts,"color":_hex_color(f),
                                    "stroke_width":3,"cad_layer":_check_layer(f)})
        elif kind=="ARC":
            f=_fields(records,{5,8,62,420,10,20,30,40,50,51})
            if float(_one(f,30,"0")):
                raise ValueError("Elevated CAD ARC needs qualified 3D adapter")
            cx,cy=_num(_one(f,10),"ARC center x",width),_num(_one(f,20),"ARC center y",height)
            radius=_num(_one(f,40),"ARC radius",max(width,height))
            start=_num(_one(f,50),"ARC start",360)
            end=_num(_one(f,51),"ARC end",360)
            if start==360 or end==360:
                raise ValueError("DXF ARC angle 360 must be normalized to 0")
            points=_cad_arc_screen_points(cx,cy,radius,start,end,width,height)
            layer=Layer(id=f"cad_{len(layers):04d}",type="connector_line",
                        name=f"CAD arc {len(layers)}",
                        properties={
                            "points":points,"stroke_width":3,
                            "color":_hex_color(f),"cad_layer":_check_layer(f),
                            "cad_arc":{
                                "center":[cx,cy],"radius":radius,
                                "start_degrees":start,"end_degrees":end,
                                "samples_digest":_points_digest(points),
                                "representation":"presentation_polyline",
                            },
                        })
        else:
            f=_fields(records,{5,8,62,420,10,20,30,40})
            if float(_one(f,30,"0")):
                raise ValueError("Elevated CAD circle requires 3D adapter")
            cx,cy=_num(_one(f,10),"center x",width),_num(_one(f,20),"center y",height)
            r=_num(_one(f,40),"radius",max(width,height))
            if not r or cx-r < 0 or cy-r < 0 or cx+r > width or cy+r > height:
                raise ValueError("CAD circle outside canvas")
            layer=Layer(id=f"cad_{len(layers):04d}",type="shape",
                        name=f"CAD circle {len(layers)}",
                        transform=Transform(x=cx-r,y=height-cy-r),
                        properties={"shape":"ellipse","width":2*r,"height":2*r,
                                    "fill":"#00000000","outline":_hex_color(f),
                                    "cad_layer":_check_layer(f)})
        layers.append(layer)
    if not layers:
        raise ValueError("DXF contains no supported presentation geometry")
    return layers


def import_dxf(source: str | Path, output_project: str | Path,
               *, canvas_width: int, canvas_height: int,
               units: str) -> dict:
    src,dest=Path(source),Path(output_project)
    if src.suffix.lower()!=".dxf" or not src.is_file() or src.is_symlink():
        raise ValueError("Expected a real ASCII DXF file")
    if not dest.name.endswith(".ttgstudio.json") or dest.exists() or dest.is_symlink():
        raise FileExistsError("DXF requires new .ttgstudio.json project")
    if units not in UNITS:
        raise ValueError("Explicit DXF units must be unitless, inch or mm")
    if (not isinstance(canvas_width,int) or not isinstance(canvas_height,int) or
            not 1 <= canvas_width <= 4096 or not 1 <= canvas_height <= 4096
            or canvas_width*canvas_height > 4_000_000):
        raise ValueError("DXF viewport outside bounded dimensions")
    parts=_sections(_raw_pairs(src.read_bytes()))
    if "ENTITIES" not in parts:
        raise ValueError("DXF ENTITIES section missing")
    header=parts.get("HEADER",[])
    header_values={}
    i=0
    while i<len(header):
        if header[i][0]!=9:
            raise ValueError("Malformed DXF HEADER variable")
        name=header[i][1];i+=1
        values=[]
        while i<len(header) and header[i][0]!=9:
            values.append(header[i]);i+=1
        if name in header_values:
            raise ValueError("Duplicate DXF header variable")
        if name not in {"$ACADVER","$INSUNITS"}:
            raise ValueError("Unsupported DXF header metadata")
        header_values[name]=values
    if "$ACADVER" in header_values:
        if header_values["$ACADVER"]!=[(1,"AC1009")] and header_values["$ACADVER"]!=[(1,"AC1015")]:
            raise ValueError("Only R12/R2000 ASCII DXF supported")
    if "$INSUNITS" in header_values:
        if header_values["$INSUNITS"] != [(70,str(UNITS[units]))]:
            raise ValueError("DXF declared units disagree with selected units")
    layers=_geometry_entities(parts["ENTITIES"],canvas_width,canvas_height)
    project=TTGProject(name=src.stem,project_type="diagram")
    project.canvas=CanvasSpec(width=canvas_width,height=canvas_height,
                              background="#00000000")
    project.layers=layers
    project.export["cadcraft_dxf"]={
        "format":"ttg.studio.cadcraft-2d-presentation.v1",
        "units":units,
        "original_source_sha256":sha256(src.read_bytes()).hexdigest(),
        "coord_frame":"CAD y-up, TTG canvas y-down",
        "electrical_or_mechanical_authority":False,
    }
    payload=(json.dumps(project.to_dict(),indent=2)+"\n").encode()
    _safe_write(dest,payload)
    return {"format":"dxf_ascii","output":str(dest),"layers":len(layers),
            "project_sha256":sha256(payload).hexdigest(),"geometry_authority":False}


def _p(group,value) -> str:
    return f"{group}\n{value}\n"


def _fmt(value) -> str:
    if not math.isfinite(float(value)):
        raise ValueError("Nonfinite CAD geometry")
    return f"{float(value):.6f}".rstrip("0").rstrip(".") or "0"


def _native_pt(point,width,height):
    if not isinstance(point,(list,tuple)) or len(point)!=2:
        raise ValueError("Invalid native CAD point")
    return _num(point[0],"x",width),height-_num(point[1],"y",height)


def export_dxf(project: TTGProject, output: str | Path, *, units: str) -> dict:
    dest=Path(output)
    if dest.suffix.lower()!=".dxf" or units not in UNITS:
        raise ValueError("DXF export requires .dxf and explicit units")
    width,height=int(project.canvas.width),int(project.canvas.height)
    if not 1 <= width <= 4096 or not 1 <= height <= 4096 or width*height>4_000_000:
        raise ValueError("DXF canvas outside limits")
    if not 1<=len(project.layers)<=MAX_ENTITIES:
        raise ValueError("DXF entity count invalid")
    items=[]
    for layer in project.layers:
        if (not layer.visible or layer.effects or layer.keyframes
                or layer.transform.opacity!=1 or layer.transform.rotation_z):
            raise ValueError("Hidden/effected/animated CAD geometry not representable")
        name=layer.properties.get("cad_layer","0")
        if not isinstance(name,str) or not 1<=len(name)<=80 or any(x in name for x in "\r\n") or not name.isascii():
            raise ValueError("Invalid CAD drawing layer")
        if layer.type=="connector_line":
            pts=layer.properties.get("points")
            if not isinstance(pts,list) or not 2<=len(pts)<=129:
                raise ValueError("Unsupported CAD polyline point count")
            raw_arc=layer.properties.get("cad_arc")
            if raw_arc is not None:
                if not isinstance(raw_arc,dict) or raw_arc.get("representation") != "presentation_polyline":
                    raise ValueError("Unqualified CAD ARC metadata")
                if raw_arc.get("samples_digest") != _points_digest(pts):
                    raise ValueError("Edited CAD ARC must be explicitly converted to polyline")
                center=raw_arc.get("center")
                if not isinstance(center,list) or len(center)!=2:
                    raise ValueError("Invalid CAD ARC provenance")
                cx,cy=center
                radius=raw_arc.get("radius")
                start=raw_arc.get("start_degrees")
                end=raw_arc.get("end_degrees")
                expected=_cad_arc_screen_points(float(cx),float(cy),float(radius),
                    float(start),float(end),width,height)
                if _points_digest(expected)!=_points_digest(pts):
                    raise ValueError("CAD ARC source metadata no longer matches geometry")
                color=layer.properties.get("color","#FFFFFF")
                if not isinstance(color,str) or len(color)!=7 or color[0]!="#":
                    raise ValueError("Invalid CAD ARC color")
                int_color=int(color[1:],16)
                common=_p(8,name)+_p(62,"7")+_p(420,str(int_color))
                items.append(_p(0,"ARC")+common+_p(10,_fmt(cx))+_p(20,_fmt(cy))
                             +_p(40,_fmt(radius))+_p(50,_fmt(start))+_p(51,_fmt(end)))
                continue
            real=[_native_pt(pt,width,height) for pt in pts]
            closed=len(real)>=4 and real[0]==real[-1]
            vertices=real[:-1] if closed else real
            if not 2<=len(vertices)<=128:
                raise ValueError("Too many CAD vertices")
            color=layer.properties.get("color","#FFFFFF")
            if not isinstance(color,str) or len(color)!=7 or color[0]!="#":
                raise ValueError("Native CAD stroke must be #RRGGBB")
            truecolor=int(color[1:],16)
            common=_p(8,name)+_p(62,"7")+_p(420,str(truecolor))
            if len(vertices)==2 and not closed:
                (x1,y1),(x2,y2)=vertices
                body=_p(0,"LINE")+common+_p(10,_fmt(x1))+_p(20,_fmt(y1))+_p(11,_fmt(x2))+_p(21,_fmt(y2))
            else:
                body=_p(0,"LWPOLYLINE")+common+_p(90,str(len(vertices)))+_p(70,"1" if closed else "0")
                for x,y in vertices:body+=_p(10,_fmt(x))+_p(20,_fmt(y))
            items.append(body)
        elif layer.type=="shape" and layer.properties.get("shape")=="ellipse":
            raw_w=float(layer.properties.get("width",0))
            raw_h=float(layer.properties.get("height",0))
            if abs(raw_w-raw_h)>1e-7 or raw_w<=0 or layer.properties.get("fill")!="#00000000":
                raise ValueError("Only unfilled native circle can be exported to CAD")
            if layer.transform.scale_x!=1 or layer.transform.scale_y!=1:
                raise ValueError("Scaled CAD circles must be flattened explicitly")
            r=raw_w/2
            cx=layer.transform.x+r
            cy=height-layer.transform.y-r
            _num(cx-r,"circle x",width);_num(cx+r,"circle x",width)
            _num(cy-r,"circle y",height);_num(cy+r,"circle y",height)
            stroke=layer.properties.get("outline")
            if not isinstance(stroke,str) or len(stroke)!=7 or stroke[0]!="#":
                raise ValueError("Native CAD circle needs explicit outline color")
            color=int(stroke[1:],16)
            items.append(_p(0,"CIRCLE")+_p(8,name)+_p(62,"7")+_p(420,str(color))
                         +_p(10,_fmt(cx))+_p(20,_fmt(cy))+_p(40,_fmt(r)))
        else:
            raise ValueError("Unmapped native 2D CAD layer, refusing silent conversion")
    text=(_p(0,"SECTION")+_p(2,"HEADER")+_p(9,"$ACADVER")+_p(1,"AC1015")
          +_p(9,"$INSUNITS")+_p(70,str(UNITS[units]))+_p(0,"ENDSEC")
          +_p(0,"SECTION")+_p(2,"ENTITIES")+"".join(items)
          +_p(0,"ENDSEC")+_p(0,"EOF"))
    data=text.encode("ascii")
    if len(data)>MAX_BYTES:
        raise ValueError("DXF output exceeds bounded size")
    _safe_write(dest,data)
    return {"format":"dxf_ascii","output":str(dest),"entities":len(items),
            "units":units,"sha256":sha256(data).hexdigest(),
            "electrical_or_mechanical_authority":False}
