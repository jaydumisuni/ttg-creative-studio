"""Measured output-layer inspection using Studio's existing CanvasRenderer.

This is not OCR, semantic understanding, or aesthetic approval. Proves whether
each declared text element actually contributes visible pixels. One optional,
bounded correction may raise an obscured editable text layer in stacking order.
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageChops
from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_project_schema import TTGProject

def review_text_contribution(project: TTGProject, project_root: Path, output:Path,
                             *, auto_repair: bool=False, max_retries:int=2) -> dict:
    text_layers=[layer for layer in project.layers if layer.visible and layer.type in ("text","text3d")]
    if len(text_layers)>10:
        return {"state":"manual_review_required","reason":"too_many_text_layers",
                "semantic_review":"not_performed","retries":0,"findings":[]}
    renderer=CanvasRenderer(RenderContext(project_root))
    findings=[]
    corrections=[]
    with Image.open(output) as image:
        observed=image.convert("RGB").copy()
    for attempt in range(max_retries+1):
        findings=[]
        for layer in text_layers:
            layer.visible=False
            try:
                without=renderer.render(project).convert("RGB")
            finally:
                layer.visible=True
            bbox=ImageChops.difference(observed,without).getbbox()
            if bbox is None:
                findings.append({"layer_id":layer.id,"reason":"text_layer_has_no_visible_pixel_contribution",
                                 "check":"actual Studio renderer pixel differential"})
        if not findings:break
        if not auto_repair or attempt>=max_retries:break
        moved=0
        for finding in findings:
            layer=next(x for x in project.layers if x.id==finding["layer_id"])
            if layer.locked or project.layers[-1] is layer:continue
            project.layers.remove(layer)
            project.layers.append(layer)
            corrections.append({"iteration":attempt+1,"layer_id":layer.id,
                                "action":"raise_above_occluding_layers"})
            moved+=1
        if moved==0:break
        observed=renderer.render(project).convert("RGB")
        # The external caller saves final output exactly once after correction.
    return {"state":"pixel_layer_visibility_pass" if not findings else "visual_review_required",
            "findings":findings,"corrections":corrections,"retries":len(corrections),
            "text_layers_examined":len(text_layers),
            "semantic_review":"not_performed_no_OCR_or_vision_model",
            "corrected_image":observed if corrections else None}
