#!/usr/bin/env python3
"""Engineering proof for offline, native Studio authored scene family."""
from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
from PIL import ImageChops,ImageStat
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ttg_banana_actions import BananaActions
from ttg_banana_level import find_workflow
from ttg_canvas_engine import CanvasRenderer,RenderContext
from ttg_project_schema import TTGProject

def main():
    checks=[]
    def test(value,description):
        if not value:raise AssertionError(description)
        checks.append(description)
    action=BananaActions()
    p=action.create_professional_wall_sign("Premium THETECHGUY brushed-metal office-wall signage in a luminous lobby",
                                          width=640,height=480,fps=6,duration=.6)
    test(len(p.layers)>=10 and not p.assets,"Original project has editable layers and no imported images")
    test(all(layer.type!="image" and not layer.properties.get("path") for layer in p.layers),"No source photograph")
    test(sum("steel_polygon"==l.properties.get("cinematic_material") for l in p.layers)>=2,
         "Native editable steel emblem geometry")
    test(any(l.properties.get("text")=="THETECHGUY" for l in p.layers),
         "Exact THETECHGUY wordmark is editable")
    test(any("DIGITAL SOLUTIONS" in l.properties.get("text","") or
             "D I G I T A L" in l.properties.get("text","") for l in p.layers),
         "Exact DIGITAL SOLUTIONS tagline retained in font layer")
    test(find_workflow("professional_wall_sign").id=="professional_wall_sign",
         "Workflow registered in Banana Level")
    with tempfile.TemporaryDirectory(prefix="ttg-studio-pro-scene-") as tmp:
        root=Path(tmp);src=root/"original.ttgstudio.json"
        p.save(src);loaded=TTGProject.load(src)
        test(len(loaded.layers)==len(p.layers),"Save/reload keeps all native scene layers")
        renderer=CanvasRenderer(RenderContext(root))
        a=renderer.render(loaded,time=0).convert("RGB")
        b=renderer.render(TTGProject.load(src),time=0).convert("RGB")
        test(ImageChops.difference(a,b).getbbox() is None,"Deterministic identical re-render")
        variance=ImageStat.Stat(a).stddev
        test(min(variance)>17 and a.size==(640,480),"Native output contains genuine tonal detail")
        later=renderer.render(loaded,time=.36).convert("RGB")
        test(ImageChops.difference(a,later).getbbox() is not None,
             "Motion frames change from dynamic actual Studio neon material")
        metal=next(l for l in loaded.layers if l.properties.get("cinematic_material")=="steel_polygon")
        metal.transform.x+=23
        edited=renderer.render(loaded,time=0).convert("RGB")
        test(ImageChops.difference(a,edited).getbbox() is not None,
             "Editing native emblem transform changes final rendered pixels")
        word=next(l for l in loaded.layers if l.properties.get("text")=="THETECHGUY")
        word.properties["text"]="TG SYSTEMS"
        modified=renderer.render(loaded,time=0).convert("RGB")
        test(ImageChops.difference(edited,modified).getbbox() is not None,
             "Editable metal lettering changes physical output")
    # Material qualification uses observable pixels and unchanged source data.
    from ttg_cinematic_renderer import _room, _metallic_shading
    import numpy as np
    brushed = _metallic_shading((256,256), seed=19, light_shift=0)
    brushed_again = _metallic_shading((256,256), seed=19, light_shift=0)
    test(np.array_equal(brushed, brushed_again),
         "Brushed-metal anisotropy is deterministic for a frozen scene")
    vertical = np.abs(np.diff(brushed.astype(np.int16), axis=0)).mean()
    horizontal = np.abs(np.diff(brushed.astype(np.int16), axis=1)).mean()
    test(vertical > horizontal * 1.10,
         "Real brushed steel fine structure is directional, not a flat gradient")
    lobby = np.asarray(_room(640, 480, 67, .55).convert("RGB"))
    center_wall=lobby[160:255,280:440,:]
    test(center_wall.std() > 5,
         "Native plaster wall shows measured nonuniform material microtexture")
    test(np.unique(lobby[410:470,320:430,:].reshape(-1,3),axis=0).shape[0] > 15,
         "Native floor shows actual procedural stone detail")
    try:action.create_professional_wall_sign("Generate a random portrait of a person")
    except ValueError: checks.append("Unsupported arbitrary generative prompt rejected explicitly")
    else:raise AssertionError("Must not fake general text-to-image generation")
    gold=action.create_professional_wall_sign(
        "Make a premium gold-lit THETECHGUY office wall sign",
        width=640,height=480,duration=.6,fps=6)
    violet=action.create_professional_wall_sign(
        "Make a premium violet-lit THETECHGUY office wall sign",
        width=640,height=480,duration=.6,fps=6)
    test(gold.export["professional_creation"]["accent_palette"]=="gold" and
         violet.export["professional_creation"]["accent_palette"]=="purple",
         "Scene material colors respond to authored instructions")
    test(gold.layers[0].properties["seed"] != violet.layers[0].properties["seed"],
         "Different instructions produce independent deterministic architecture")
    for bad in ((10000,9000),(320,240)):
        try:action.create_professional_wall_sign("A lobby sign",width=bad[0],height=bad[1])
        except ValueError:checks.append("Unsafe native output dimensions rejected")
        else:raise AssertionError("Unbounded resolution")
    try:
        from PyQt6.QtWidgets import QApplication,QToolButton
        from ttg_creative_workspace import CreativeWorkspace
        app=QApplication.instance() or QApplication([])
        ui=CreativeWorkspace(ROOT)
        labels=[action.text() for b in ui.findChildren(QToolButton)
                if b.menu() for action in b.menu().actions()]
        test(any("Professional Office Wall Sign" in name for name in labels),
             "Standalone Studio GUI exposes professional creation workflow")
        ui.reset_project(p)
        test(ui.project is p and ui.validate_project(show_dialog=False),
             "Standalone Studio opens native editable scene")
        ui.close()
    except ImportError as exc:
        print("Qt GUI dependency not installed:",exc)
    print(json.dumps({"result":"PASS","checks":len(checks),"evidence":checks},indent=2))

if __name__=="__main__":main()
