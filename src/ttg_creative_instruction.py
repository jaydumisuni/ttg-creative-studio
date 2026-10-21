"""Safe assistant -> Creative Studio instruction bridge.

This module is Studio-owned. It dispatches a bounded, declarative scene or
edit packet through the existing CanvasRenderer/ExportService. No new renderer,
shell execution, AI inference, optional workforce, or hidden payment.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
from typing import Any

from PIL import Image

from ttg_banana_actions import BananaActions
from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_campaign_composer import CampaignBrief, compose_campaign
from ttg_export_service import ExportService
from ttg_production_director import ProductionDirector
from ttg_project_schema import Layer, TTGProject, Transform
from ttg_visual_understanding import measure_image
from ttg_creative_intent import interpret_creation, interpret_edit, correct_layout
from ttg_creative_review import review_text_contribution

SCHEMA = "ttg.studio.creative-instruction.v1"
SCENE_SCHEMA = "ttg.studio.scene-spec.v1"
_ALLOWED_TYPES = frozenset(("shape", "text", "text3d"))
_ALLOWED_MATERIALS = frozenset(("architectural_lobby", "steel_polygon", "steel_text", "neon"))
_COLORS = frozenset(("blue", "purple", "gold"))
_COLOR = re.compile(r"^#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?$")
_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,59}$")


class CreativeInstructionError(ValueError):
    """A request cannot be executed honestly within current Studio capabilities."""


def _text(value: Any, label: str, limit: int = 160) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
        raise CreativeInstructionError(f"{label} requires 1-{limit} characters")
    if any(ord(c) < 32 for c in value):
        raise CreativeInstructionError(f"{label} contains forbidden control characters")
    return value.strip()


def _finite(value: Any, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise CreativeInstructionError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        raise CreativeInstructionError(f"{label} is outside the authorized range")
    return result


def _color(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _COLOR.fullmatch(value):
        raise CreativeInstructionError(f"{label} must be hex RGB/RGBA")
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inside(path: Path, roots: tuple[Path, ...]) -> bool:
    candidate = path.resolve()
    return any(candidate == root or root in candidate.parents for root in roots)


def _assert_keys(item: dict, allowed: set[str], label: str) -> None:
    unknown = set(item) - allowed
    if unknown:
        raise CreativeInstructionError(f"{label} contains unadmitted keys: {sorted(unknown)}")


def compile_scene(spec: dict[str, Any]) -> TTGProject:
    """Compile bounded model-authored instructions to real editable Studio layers.

    A natural-language agent may author *this* schema, but every requested layer
    must be executable in the currently installed Creative Studio engine.
    """
    if not isinstance(spec, dict) or spec.get("schema") != SCENE_SCHEMA:
        raise CreativeInstructionError("Unrecognized Creative Studio scene schema")
    _assert_keys(spec, {"schema", "name", "canvas", "layers"}, "scene")
    settings = spec.get("canvas")
    if not isinstance(settings, dict):
        raise CreativeInstructionError("Scene canvas is required")
    _assert_keys(settings, {"width", "height", "background"}, "canvas")
    w, h = settings.get("width"), settings.get("height")
    if type(w) is not int or type(h) is not int or not 320 <= w <= 1920 or not 240 <= h <= 1440 or w*h > 2_100_000:
        raise CreativeInstructionError("Canvas exceeds admitted local-render limits")
    background = _color(settings.get("background", "#101318"), "background")
    layers = spec.get("layers")
    if not isinstance(layers, list) or not 1 <= len(layers) <= 60:
        raise CreativeInstructionError("A scene requires 1-60 executable layers")
    p = TTGProject(name=_text(spec.get("name", "Studio directed creation"), "scene name", 100),
                   project_type="image")
    p.canvas.width, p.canvas.height = w, h
    p.canvas.background = background
    p.canvas.fps, p.canvas.duration = 12, 1
    p.export = {"format":"png", "renderer":"TTG Creative Studio CanvasRenderer"}
    material_bg = 0
    ids = set()
    for item in layers:
        if not isinstance(item, dict):
            raise CreativeInstructionError("Scene layer must be an object")
        _assert_keys(item, {"id","name","type","x","y","properties"}, "scene layer")
        key = item.get("id")
        if not isinstance(key, str) or not _ID.fullmatch(key) or key in ids:
            raise CreativeInstructionError("Scene layer IDs must be unique and bounded")
        ids.add(key)
        kind = item.get("type")
        if kind not in _ALLOWED_TYPES:
            raise CreativeInstructionError(f"Layer {key}: unsupported type")
        x = _finite(item.get("x", 0), f"{key}.x", -2*w, 2*w)
        y = _finite(item.get("y", 0), f"{key}.y", -2*h, 2*h)
        props = item.get("properties")
        if not isinstance(props, dict):
            raise CreativeInstructionError(f"{key}: properties required")
        props = dict(props)
        material = props.get("cinematic_material")
        if material is not None:
            if material not in _ALLOWED_MATERIALS:
                raise CreativeInstructionError(f"{key}: unqualified material")
            if material == "architectural_lobby":
                material_bg += 1
                if kind != "shape" or material_bg > 1 or len(p.layers) != 0:
                    raise CreativeInstructionError("Architectural environment must be the first and only backdrop")
                _assert_keys(props, {"cinematic_material","seed","warmth"}, key)
                props["seed"] = int(_finite(props.get("seed",49),f"{key}.seed",0,65535))
                props["warmth"] = _finite(props.get("warmth",.55),f"{key}.warmth",0,1)
            elif material == "steel_polygon":
                if kind != "shape":
                    raise CreativeInstructionError("Steel polygon requires shape layer")
                _assert_keys(props, {"cinematic_material","points","depth","seed"},key)
                points = props.get("points")
                if not isinstance(points,list) or not 3 <= len(points) <= 90:
                    raise CreativeInstructionError("Steel polygon needs 3-90 points")
                props["points"] = [[_finite(c,f"{key}.point", -2*w,2*w) for c in point]
                                   for point in points if isinstance(point,list) and len(point)==2]
                if len(props["points"]) != len(points):
                    raise CreativeInstructionError("Steel polygon points must be 2D")
                props["depth"] = int(_finite(props.get("depth",8),f"{key}.depth",0,30))
                props["seed"] = int(_finite(props.get("seed",49),f"{key}.seed",0,65535))
            elif material == "steel_text":
                if kind not in ("text","text3d"):
                    raise CreativeInstructionError("Steel text requires text layer")
                _assert_keys(props, {"cinematic_material","text","size","depth","seed"},key)
                props["text"] = _text(props.get("text"),f"{key}.text",70)
                props["size"] = int(_finite(props.get("size",70),f"{key}.size",10,260))
                props["depth"] = int(_finite(props.get("depth",8),f"{key}.depth",0,30))
                props["seed"] = int(_finite(props.get("seed",49),f"{key}.seed",0,65535))
            else:
                if kind != "shape":
                    raise CreativeInstructionError("Neon line requires shape layer")
                _assert_keys(props, {"cinematic_material","points","width","terminals","led_color"},key)
                points = props.get("points")
                if not isinstance(points,list) or not 2 <= len(points) <= 40:
                    raise CreativeInstructionError("Neon line needs 2-40 points")
                parsed = []
                for point in points:
                    if not isinstance(point,list) or len(point)!=2:
                        raise CreativeInstructionError("Neon points must be 2D")
                    parsed.append([_finite(c,f"{key}.point", -2*w,2*w) for c in point])
                props["points"]=parsed
                props["width"]=int(_finite(props.get("width",4),f"{key}.width",1,16))
                if type(props.get("terminals",False)) is not bool:
                    raise CreativeInstructionError("Neon terminals must be boolean")
                if props.get("led_color","blue") not in _COLORS:
                    raise CreativeInstructionError("Neon color must be blue, purple or gold")
        elif kind == "shape":
            _assert_keys(props, {"shape","fill","outline","width","height","radius","glow","glow_blur"},key)
            if props.get("shape","rectangle") not in ("rectangle","ellipse"):
                raise CreativeInstructionError("Unsupported primitive")
            props["width"]=_finite(props.get("width"),f"{key}.width",1,2*w)
            props["height"]=_finite(props.get("height"),f"{key}.height",1,2*h)
            props["fill"]=_color(props.get("fill","#1E293B"),f"{key}.fill")
            if props.get("outline") is not None:
                props["outline"]=_color(props["outline"],f"{key}.outline")
            props["radius"]=int(_finite(props.get("radius",0),f"{key}.radius",0,min(w,h)))
            if type(props.get("glow",False)) is not bool:
                raise CreativeInstructionError("glow must be boolean")
            props["glow_blur"]=_finite(props.get("glow_blur",10),f"{key}.glow_blur",0,40)
        else:
            _assert_keys(props, {"text","size","color","align","stroke_width","stroke_fill",
                                 "shadow","glow","glow_color","extrude_px","extrude_color"},key)
            props["text"]=_text(props.get("text"),f"{key}.text",110)
            props["size"]=int(_finite(props.get("size",48),f"{key}.size",9,230))
            props["color"]=_color(props.get("color","#EFF6FF"),f"{key}.color")
            if props.get("align","left") not in ("left","center","right"):
                raise CreativeInstructionError("Unknown text alignment")
            for k in ("stroke_fill","glow_color","extrude_color"):
                if k in props: props[k]=_color(props[k],f"{key}.{k}")
            for k in ("shadow","glow"):
                if k in props and type(props[k]) is not bool:
                    raise CreativeInstructionError(f"{k} must be boolean")
            if "extrude_px" in props:
                props["extrude_px"]=int(_finite(props["extrude_px"],"extrude_px",0,20))
            if "stroke_width" in props:
                props["stroke_width"]=int(_finite(props["stroke_width"],"stroke_width",0,6))
        p.layers.append(Layer(id=key, name=_text(item.get("name",key),"layer name",100),
                              type=kind, transform=Transform(x=x,y=y),properties=props))
    return p


def apply_edits(project: TTGProject, operations: list[dict[str,Any]]) -> None:
    if not isinstance(operations,list) or not 1 <= len(operations) <= 20:
        raise CreativeInstructionError("Provide 1-20 explicit editing operations")
    layers={layer.id:layer for layer in project.layers}
    for op in operations:
        if not isinstance(op,dict):
            raise CreativeInstructionError("Edit operation must be an object")
        _assert_keys(op,{"op","layer_id","value","x","y"},"edit")
        kind=op.get("op")
        key=op.get("layer_id")
        if key not in layers:
            raise CreativeInstructionError("Edit target layer not found")
        layer=layers[key]
        if layer.locked:
            raise CreativeInstructionError("Locked layer cannot be edited")
        if kind=="replace_text":
            if layer.type not in ("text","text3d"):
                raise CreativeInstructionError("Text edit requires text layer")
            layer.properties["text"]=_text(op.get("value"),"replacement text",70)
        elif kind=="move_layer":
            if "x" not in op or "y" not in op:
                raise CreativeInstructionError("Move requires x and y")
            layer.transform.x=_finite(op["x"],"move.x",-2*project.canvas.width,2*project.canvas.width)
            layer.transform.y=_finite(op["y"],"move.y",-2*project.canvas.height,2*project.canvas.height)
        elif kind=="set_neon_color":
            if layer.properties.get("cinematic_material")!="neon" or op.get("value") not in _COLORS:
                raise CreativeInstructionError("Neon color change requires a qualified neon layer")
            layer.properties["led_color"]=op["value"]
        elif kind=="set_fill":
            if layer.properties.get("cinematic_material") or layer.type not in ("shape","text","text3d"):
                raise CreativeInstructionError("Fill change is not supported on material layers")
            layer.properties["fill" if layer.type=="shape" else "color"]=_color(op.get("value"),"fill")
        else:
            raise CreativeInstructionError("Unrecognized edit operation")


def _portable_assets(project: TTGProject, source_root: Path, destination_root: Path,
                     name: str) -> Path | None:
    if not project.assets:
        if any(layer.type=="image" and layer.visible for layer in project.layers):
            raise CreativeInstructionError("Image layer cannot be used without a registered asset")
        return None
    assets_root=destination_root/(name+"_assets")
    if assets_root.exists():
        raise CreativeInstructionError("Destination media directory exists")
    assets_root.mkdir()
    mapping={}
    total=0
    try:
        for asset in project.assets:
            path=(source_root/asset.path).resolve()
            if not _inside(path,(source_root.resolve(),)) or not path.is_file():
                raise CreativeInstructionError("Asset escapes approved project or is unavailable")
            total+=path.stat().st_size
            if total > 128*1024*1024:
                raise CreativeInstructionError("Portable media quota exceeded")
            digest=_sha(path)
            if asset.sha256 and asset.sha256.lower()!=digest.lower():
                raise CreativeInstructionError("Asset integrity failure")
            new=assets_root/(digest[:16]+"-"+path.name)
            if not new.exists():
                try:os.link(path,new)
                except OSError:shutil.copy2(path,new)
            mapping[asset.path]=assets_root.name+"/"+new.name
            asset.path=mapping[asset.path]
        for layer in project.layers:
            if layer.type=="image" and "path" in layer.properties:
                old=layer.properties["path"]
                if old not in mapping:
                    raise CreativeInstructionError("Unregistered image layer")
                layer.properties["path"]=mapping[old]
        return assets_root
    except Exception:
        shutil.rmtree(assets_root,ignore_errors=True)
        raise


def run_creative_instruction(job: dict[str,Any]) -> dict[str,Any]:
    """Work for an authorized assistant; does not impersonate Tenfold/Cookpit."""
    if not isinstance(job,dict) or job.get("task")!="creative_execute":
        raise CreativeInstructionError("Expected creative_execute job")
    opts=job.get("options")
    if not isinstance(opts,dict) or opts.get("schema")!=SCHEMA:
        raise CreativeInstructionError("Creative instruction contract is required")
    _assert_keys(opts,{"schema","mode","instruction","scene","edits","campaign",
                       "catalog_roots","dry_run","auto_correct_layout"},"options")
    mode=opts.get("mode")
    if mode not in ("auto","scene","wall_sign","edit_project","campaign"):
        raise CreativeInstructionError("Unsupported creative instruction mode")
    instruction=_text(opts.get("instruction"),"instruction",1000)
    if type(opts.get("auto_correct_layout",False)) is not bool:
        raise CreativeInstructionError("auto_correct_layout must be boolean")
    natural_compile = "none"
    if mode == "auto":
        if opts.get("scene") is not None:
            mode="scene"
        elif opts.get("campaign") is not None:
            mode="campaign"
        elif (job.get("input") or job.get("inputPath")):
            mode="edit_project"
        elif (native_scene := interpret_creation(instruction)) is not None:
            opts=dict(opts)
            opts["scene"]=native_scene
            mode="scene"
            natural_compile="bounded_native_typography"
        else:
            # Use Studio's actual admission logic rather than treating any
            # incidental word "lobby" as permission to produce a TTG logo.
            decision=ProductionDirector.choose_instruction_route(None,instruction)
            if decision["route"] == "studio_native_procedural_scene":
                mode="wall_sign"
            else:
                mode="needs_scene_spec"
    output=job.get("output") or job.get("outputPath")
    if not isinstance(output,str):
        raise CreativeInstructionError("An absolute output PNG is required")
    target=Path(output)
    if not target.is_absolute() or target.suffix.lower()!=".png" or not _ID.fullmatch(target.stem):
        raise CreativeInstructionError("Output must be an absolute, safely named PNG")
    root=target.parent.resolve(strict=True)
    if not root.is_dir() or not _inside(target,(root,)):
        raise CreativeInstructionError("Output must be inside an existing authorized directory")
    project_out=root/(target.stem+".ttgstudio.json")
    receipt_out=root/(target.stem+".receipt.json")
    if any(x.exists() for x in (target,project_out,receipt_out,root/(target.stem+"_assets"))):
        raise CreativeInstructionError("Existing output cannot be overwritten")
    roots=opts.get("catalog_roots") or [str(root)]
    if not isinstance(roots,list) or not roots or not all(isinstance(x,str) for x in roots):
        raise CreativeInstructionError("catalog_roots must list approved directories")
    catalog=tuple(Path(p).resolve(strict=True) for p in roots)
    if any(not p.is_dir() for p in catalog):
        raise CreativeInstructionError("Invalid approved catalog root")
    item={"schema":SCHEMA,"mode":mode,"instruction":instruction,
          "render_owner":"TTG Creative Studio","model_inference_used":False,
          "paid_provider_used":False,"tenfold_executed":False,
          "cookpit_executed":False,"sergeant_visual_approval":False,
          "semantic_visual_review":"required",
          "natural_language_compilation":natural_compile}
    if mode=="needs_scene_spec":
        return {**item,"state":"needs_scene_compilation",
                "required_scene_schema":SCENE_SCHEMA,
                "instruction_parse":"not falsely represented as understood",
                "next":"An authorized assistant must translate this request into a scene spec or select an approved specialist"}
    if mode=="campaign":
        brief=opts.get("campaign")
        if not isinstance(brief,dict):
            raise CreativeInstructionError("Campaign brief object required")
        _assert_keys(brief,{"layout","brand","headline","subhead","product_name","cta",
                            "website","accent"},"campaign")
        args=CampaignBrief(**brief)
        args.validate()
        if opts.get("dry_run") is True:
            return {**item,"state":"planned_not_rendered","campaign":dict(brief)}
        destination=root/(target.stem+"_campaign")
        if destination.exists():
            raise CreativeInstructionError("Campaign destination already exists")
        files=compose_campaign(args,destination)
        return {**item,"state":"rendered_visual_review_required",
                "output":str(files["preview"]),"project":str(files["project"]),
                "bundle":str(files["bundle"]),"render_sha256":_sha(files["preview"])}
    if mode=="scene":
        project=compile_scene(opts.get("scene"))
        if opts.get("edits") is not None:
            apply_edits(project,opts["edits"])
        source_root=root
    elif mode=="wall_sign":
        decision=ProductionDirector.choose_instruction_route(None,instruction)
        if decision["route"]!="studio_native_procedural_scene":
            raise CreativeInstructionError("This prompt is not an admitted native wall-sign scene")
        project=BananaActions().create_professional_wall_sign(instruction,width=640,height=480,
                                                               fps=12,duration=1)
        if opts.get("edits") is not None:
            apply_edits(project,opts["edits"])
        source_root=root
    else:
        source=job.get("input") or job.get("inputPath")
        if not isinstance(source,str) or not Path(source).is_absolute():
            raise CreativeInstructionError("Editing requires absolute existing project input")
        src=Path(source).resolve(strict=True)
        if not _inside(src,catalog) or not src.is_file() or not src.name.endswith(".ttgstudio.json"):
            raise CreativeInstructionError("Input project outside approved catalog")
        project=TTGProject.load(src)
        ProductionDirector(list(catalog),root)._verify_assets(project,src.parent)
        if len(project.layers)>128:
            raise CreativeInstructionError("Source project has too many layers for this edit worker")
        if (type(project.canvas.width) is not int or type(project.canvas.height) is not int or
            not 1 <= project.canvas.width <= 1920 or
            not 1 <= project.canvas.height <= 1440 or
            project.canvas.width * project.canvas.height > 2_100_000):
            raise CreativeInstructionError("Source project exceeds bounded edit-render canvas limits")
        edits=opts.get("edits")
        if edits is None:
            edits=interpret_edit(instruction,project)
            if edits is None:
                return {**item,"state":"needs_edit_compilation",
                        "instruction_parse":"not falsely represented as understood",
                        "next":"Provide one unambiguous natural edit or an approved explicit edit packet"}
            item["natural_language_compilation"]="bounded_native_edit"
        apply_edits(project,edits)
        source_root=src.parent
    if opts.get("dry_run") is True:
        return {**item,"state":"planned_not_rendered","layer_count":len(project.layers)}
    corrections=(correct_layout(project) if opts.get("auto_correct_layout",False)
                 else {"correction_count":0,"edits":[],
                       "structural_layout":"not_requested","semantic_visual_review":"required"})
    portable=None
    try:
        portable=_portable_assets(project,source_root,root,target.stem) if mode=="edit_project" else None
        project.save(project_out)
        ExportService(root).export_png(project,target)
        pixel_review={"state":"not_requested","semantic_review":"required"}
        if opts.get("auto_correct_layout",False):
            pixel_review=review_text_contribution(project,root,target,auto_repair=True)
            image=pixel_review.pop("corrected_image",None)
            if image is not None:
                image.save(target)
                project.save(project_out)
        with Image.open(target) as im:
            size=[im.width,im.height]
            if size!=[project.canvas.width,project.canvas.height]:
                raise CreativeInstructionError("Renderer returned invalid dimensions")
            pixels=im.convert("RGBA").tobytes()
        reopened=TTGProject.load(project_out)
        replay=CanvasRenderer(RenderContext(root)).render(reopened).convert("RGBA")
        if replay.tobytes()!=pixels:
            raise CreativeInstructionError("Reopened Studio project does not reproduce emitted pixels")
        item.update({"state":"rendered_visual_review_required","output":str(target),
                     "project":str(project_out),"layer_count":len(reopened.layers),
                     "dimensions":size,"render_sha256":_sha(target),
                     "reopened_project_exact_pixels":True,
                     "pixel_metrics":measure_image(target),
                     "bounded_layout_corrections":corrections,
                     "pixel_layer_review":pixel_review,
                     "visual_acceptance":"structural_and_replay_only_semantic_review_pending"})
        receipt_out.write_text(json.dumps(item,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        return item
    except Exception:
        target.unlink(missing_ok=True)
        project_out.unlink(missing_ok=True)
        receipt_out.unlink(missing_ok=True)
        if portable:shutil.rmtree(portable,ignore_errors=True)
        raise
