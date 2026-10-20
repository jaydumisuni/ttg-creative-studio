#!/usr/bin/env python3
"""Independent zero-reference THETECHGUY logo mockup through Studio's native renderer.

No existing logo, reference photo, image generator, Internet or model is used.
The image is built wholly from editable native Studio text/shape layers.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ttg_project_schema import TTGProject, Layer, Transform
from ttg_export_service import ExportService
from ttg_canvas_engine import CanvasRenderer, RenderContext

HERE = Path(__file__).resolve().parent
W,H=1440,1080

project=TTGProject(name="THETECHGUY | Original Blue Steel Identity Mockup",
                   project_type="image")
project.canvas.width=W
project.canvas.height=H
project.canvas.background="#070A10"
project.canvas.duration=1
project.brand.name="THETECHGUY DIGITAL SOLUTIONS"
project.brand.website="thetechguyds.com"
project.layers=[]
n=0

def shape(name,x,y,w,h,fill,*,radius=0,outline=None,glow=False,glow_blur=16):
    global n
    n+=1
    project.layers.append(Layer(id=f"cs_shape_{n:03}",type="shape",name=name,
        transform=Transform(x=x,y=y),
        properties={"shape":"rectangle","width":w,"height":h,"fill":fill,
                    "radius":radius,"outline":outline,
                    "glow":glow,"glow_blur":glow_blur}))

def ellipse(name,x,y,w,h,fill,*,outline=None,glow=False,glow_blur=18):
    global n
    n+=1
    project.layers.append(Layer(id=f"cs_ellipse_{n:03}",type="shape",name=name,
        transform=Transform(x=x,y=y),
        properties={"shape":"ellipse","width":w,"height":h,"fill":fill,
                    "outline":outline,"glow":glow,"glow_blur":glow_blur}))

def typeface(name,text,x,y,size,color="#E4F2FF",**properties):
    global n
    n+=1
    props={"text":text,"size":size,"color":color,**properties}
    project.layers.append(Layer(id=f"cs_text_{n:03}",type="text3d" if properties.pop("three_d",False) else "text",
        name=name,transform=Transform(x=x,y=y),properties=props))

# Architectural mood, not a reused image backdrop. Dim wall bands and horizon.
shape("Wall at left",0,0,155,H,"#0A1119")
shape("Left accent shadow",155,0,4,H,"#1A2631")
shape("Wall at right",1330,0,110,H,"#0B1018")
for idx in range(12):
    x=1344+idx*7
    shape(f"Right wood panel {idx+1}",x,0,2,H,"#18212B")
shape("Upper architectural light",0,76,1440,2,"#24313D")
shape("Floor horizon",0,955,1440,125,"#0C121A")
shape("Floor neon accent",0,956,1440,3,"#132A3F")
for i in range(11):
    shape(f"Floor linear reflection {i+1}",0,972+i*7,1440,1,
          "#132334" if i<5 else "#0D1A29")
# Shadow / recess / panel; large hero sign on wall.
shape("Plaque wide cast shadow",146,121,1164,823,"#030507",radius=29)
shape("Steel outer rim",160,113,1121,815,"#243340",radius=25,
      outline="#5A778B")
shape("Bright upper bevel",163,115,1115,3,"#62798A")
shape("Metal right bevel",1276,126,3,794,"#385672")
shape("Deep charcoal inset",174,128,1094,782,"#101721",radius=22)
shape("Interior shadow frame",183,136,1076,766,"#0C121C",radius=18)
shape("Inset panel face",188,142,1066,756,"#121B27",radius=17)
# A soft blue wash constructed from native 2D shapes; no imported bitmap.
for i in range(28):
    alpha=15+max(0,27-i)*2
    y=148+i*9
    shape(f"Top cobalt lighting band {i+1}",195,y,1052,9,f"#123A{min(95,34+i):02X}{min(100,alpha):02X}")
for i in range(13):
    shape(f"Lower gradient {i+1}",195,725+i*12,1052,12,
          "#131C2A" if i%2 else "#141D2A")
shape("Inset cyan keyline top",205,167,1031,2,"#357CA8")
shape("Inset cool vertical left",204,168,2,704,"#1D597E")
shape("Inset cool vertical right",1235,168,2,704,"#214E74")
shape("Inset bottom keyline",205,873,1031,2,"#24638B")

# Restrained hierarchy and material annotations.
typeface("Identity corner index","THE TECH GUY / IDENTITY SYSTEM",242,198,19,
         "#86ABC5")
typeface("Corner volume","01 / 01",1137,198,19,"#789AB5")

# Centered emblem: TTG mark from ORIGINAL native Studio glyphs and geometry.
ellipse("Outer engineering halo",554,255,332,288,"#111A2700",
        outline="#1F5471AA",glow=True,glow_blur=31)
ellipse("Inner halo",586,283,269,233,"#112A4300",
        outline="#226F96BB",glow=True,glow_blur=19)
shape("Monogram backing slot",606,313,230,152,"#111C28",radius=14,
      outline="#4E90B8")
# Monogram physically printed using Studio's editable text renderer.
typeface("Custom TG dimensional emblem","TG",720,298,168,"#DCECF8",
         align="center",gradient=True,gradient_start="#E8F5FF",
         gradient_end="#59A8E5",shadow=True,shadow_fill="#020810CC",
         shadow_blur=9,stroke_width=1,stroke_fill="#8FB5CB",
         extrude_px=7,extrude_color="#0D3856",three_d=True)
# Micro circuit traces trace the sign, not a stock logo asset.
shape("Circuit left connector",544,414,64,4,"#42AEF1")
ellipse("Circuit left terminal",532,408,15,15,"#85DAFF",
        outline="#2C6F96",glow=True,glow_blur=8)
shape("Circuit right connector",836,414,62,4,"#42AEF1")
ellipse("Circuit right terminal",894,408,15,15,"#85DAFF",
        outline="#2C6F96",glow=True,glow_blur=8)
shape("Emblem top streak",657,292,127,2,"#54BDFD")
shape("Center decorative rule left",346,547,258,2,"#3777A4")
ellipse("Rule center dot",714,539,12,12,"#B4EFFF",
        glow=True,outline="#56B3E7")
shape("Center decorative rule right",836,547,259,2,"#3777A4")
# Exact wordmark and subline, designed for this centered single hero.
typeface("THETECHGUY official name","THETECHGUY",720,584,96,"#E9F2F9",
         align="center",shadow=True,shadow_fill="#000000E0",
         shadow_blur=6,stroke_width=1,stroke_fill="#D4E8F6",
         gradient=True,gradient_start="#FBFEFF",gradient_end="#97BAD2")
shape("Brand underline",341,724,763,3,"#39759D")
typeface("Digital solutions legal subtitle","D I G I T A L    S O L U T I O N S",
         720,755,29,"#9CC4DC",align="center")
typeface("One Brand All Solutions","ONE BRAND  •  ALL SOLUTIONS",720,826,20,
         "#7897B2",align="center")
shape("Baseline signature",604,870,232,3,"#4A9AC5")
# No imported background/reference files; validate native-only artwork.
assert not project.assets
assert all(layer.type in ("text","text3d","shape") for layer in project.layers)
assert all(layer.properties.get("path") is None for layer in project.layers)
HERE.mkdir(parents=True,exist_ok=True)
path=HERE/"studio_original_logo.ttgstudio.json"
project.save(path)
restored=TTGProject.load(path)
assert len(restored.layers)==len(project.layers)
output=HERE/"studio_original_logo.png"
ExportService(HERE).export_png(restored,output)
# Cross-check renderer itself using a fresh reload, independent of export helper.
fresh=CanvasRenderer(RenderContext(HERE)).render(TTGProject.load(path)).convert("RGB")
with Image.open(output) as preview:
    assert preview.size==(W,H)
    assert ImageChops.difference(preview.convert("RGB"),fresh).getbbox() is None
    palette=preview.convert("RGB").getcolors(W*H) or []
    assert len(palette)>450, f"Logo mockup lacks depth: {len(palette)} colors"
report={
  "creative_engine":"TTG Creative Studio native CanvasRenderer through ExportService",
  "from_scratch":True,
  "reference_images_used":0,
  "model_inference_used":False,
  "asset_images_imported":0,
  "native_editable_layers":len(restored.layers),
  "canvas":[W,H],
  "image_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
  "project_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
  "validation":"save/reload plus independent identical native rerender PASS",
  "transparent_claims":"Not a diffusion model or photorealistic 3D renderer. Mockup uses native 2D shapes, text and Studio gradient/shadow/extrusion effects."
}
(HERE/"render_proof.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))
