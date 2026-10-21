"""Bounded plain-language -> existing Creative Studio construction and editing.

This is an intentionally small, auditable native-language route, not an LLM, OCR,
general text understanding, or a new image renderer. Unsupported requests remain
eligible for an assistant-authored declarative scene under the existing contract.
"""
from __future__ import annotations

import re
from typing import Any

from ttg_project_schema import TTGProject

_POSTER = re.compile(r"\b(poster|flyer|banner|thumbnail|social card|announcement card|typographic(?:al)? design)\b",re.I)
_OBJECTS = re.compile(r"\b(?:showing|depicting|illustrat\w*|draw\w*|photograph|photo|photorealistic|realistic|image of|picture of|with (?:a|an) (?:person|human|woman|man|child|dog|cat|car|phone|computer|mountain|robot|flower|house)|animal|elephant|dog|cat|helicopter|astronaut|video|animation|cinematic film|human face)\b",re.I)
_PHOTO = re.compile(r"\b(photograph|photorealistic|realistic photo|portrait photo|portrait photograph|face portrait|animal|elephant|dog|cat|helicopter|astronaut|video|animation|cinematic film|human face)\b",re.I)
_QUOTES = re.compile(r"""["“]([^"”]{2,85})["”]|'([^']{2,85})'""")
_TITLE = re.compile(r"\b(?:title|headline|text|saying)\s*[:=]\s*(.{2,90}?)(?=\s+(?:with|using|in)\s+(?:a\s+)?(?:blue|purple|gold|dark|light)\b|$)",re.I)
_EDIT_TEXT = re.compile(r"\b(?:change|replace|set|update)\s+(?:the\s+)?(?P<subject>[\w-]+)\s+(?:text\s+)?(?:to|with)\s+['\"“](?P<value>[^'\"”]{1,70})['\"”]",re.I)
_EDIT_MOVE = re.compile(r"\bmove\s+(?:the\s+)?(?P<subject>[\w-]+)\s+to\s*\(?\s*(?P<x>-?\d{1,5})\s*[,;]\s*(?P<y>-?\d{1,5})\s*\)?",re.I)
_EDIT_NEON = re.compile(r"\b(?:change|make|set|switch|turn)\s+(?:the\s+)?(?:neon|led|lighting|lights)\s+(?:(?:color\s+)?to\s+|(?:from\s+(?:blue|purple|gold)\s+to\s+))(?P<color>blue|purple|gold)\b",re.I)

def _headline(prompt: str) -> str | None:
    matches=_QUOTES.findall(prompt)
    quotes=[a or b for a,b in matches]
    if quotes:
        return quotes[0].strip()
    m=_TITLE.search(prompt)
    return m.group(1).strip().rstrip(".") if m else None

def _palette(prompt: str):
    t=prompt.casefold()
    if re.search(r"\b(?:gold|golden|amber)\b",t): return ("#16110C","#D6A75A","#FAF0DA","gold")
    if re.search(r"\b(?:purple|violet)\b",t):return ("#100C1F","#9472E8","#F6EAFF","purple")
    return ("#091521","#4FB7E5","#E8F5FF","blue")

def interpret_creation(prompt: str) -> dict[str,Any] | None:
    """Accept a well-scoped typographic design, not an unrelated photo request."""
    if not isinstance(prompt,str) or len(prompt)>1000 or _OBJECTS.search(prompt):
        return None
    if not _POSTER.search(prompt):
        return None
    title=_headline(prompt)
    if not title or len(title)>65 or "\n" in title:
        return None
    background,accent,foreground,color=_palette(prompt)
    t=prompt.casefold()
    if "thumbnail" in t or "banner" in t or "wide" in t:
        w,h=1280,720
    elif "portrait" in t or "vertical" in t or "flyer" in t:
        w,h=900,1200
    else:
        w,h=960,960
    cx=w//2
    subtitle=None
    q=[a or b for a,b in _QUOTES.findall(prompt)]
    if len(q)>1:subtitle=q[1].strip()[:70]
    # Existing, qualified shape/text renderer; no stock art or reference image.
    layers=[
      {"id":"frame","name":"Editable background panel","type":"shape","x":36,"y":36,
       "properties":{"shape":"rectangle","fill":background,"width":w-72,"height":h-72,"outline":accent,"radius":22}},
      {"id":"highlight","name":"Top accent bar","type":"shape","x":78,"y":int(h*.22),
       "properties":{"shape":"rectangle","fill":accent,"width":w-156,"height":7}},
      {"id":"headline","name":"Exact headline","type":"text","x":cx,"y":int(h*.35),
       "properties":{"text":title,"size":min(72,max(28,int(w/max(10,len(title)*.69)))),"color":foreground,
                     "align":"center","shadow":True}},
      {"id":"footer","name":"Bottom accent rule","type":"shape","x":78,"y":int(h*.76),
       "properties":{"shape":"rectangle","fill":accent,"width":w-156,"height":4}},
    ]
    if subtitle:
        layers.append({"id":"subtitle","name":"Exact subtitle","type":"text","x":cx,"y":int(h*.65),
                       "properties":{"text":subtitle,"size":min(32,max(14,int(w/max(14,len(subtitle)*.72)))),"color":accent,"align":"center"}})
    return {"schema":"ttg.studio.scene-spec.v1","name":"Native typography composition",
            "canvas":{"width":w,"height":h,"background":background},"layers":layers}

def _resolve_layer(project:TTGProject, subject:str, *,allowed:tuple[str,...]) -> str | None:
    token=subject.casefold()
    candidates=[l for l in project.layers if not l.locked and l.type in allowed]
    direct=[l for l in candidates if l.id.casefold()==token or l.name.casefold()==token]
    if len(direct)==1:return direct[0].id
    if token in ("text","lettering") and len(candidates)==1:return candidates[0].id
    matches=[l for l in candidates if token in (l.id.casefold(),l.name.casefold().replace(" ","_"))]
    return matches[0].id if len(matches)==1 else None

def interpret_edit(prompt:str, project:TTGProject) -> list[dict[str,Any]]|None:
    """Exactly one unambiguous operation per natural-language job. No guessing."""
    if not isinstance(prompt,str) or len(prompt)>1000:
        return None
    matches=[]
    if (m:=_EDIT_TEXT.search(prompt)):
        key=_resolve_layer(project,m.group("subject"),allowed=("text","text3d"))
        if key: matches.append({"op":"replace_text","layer_id":key,"value":m.group("value")})
    if (m:=_EDIT_MOVE.search(prompt)):
        key=_resolve_layer(project,m.group("subject"),allowed=("text","text3d","shape","image"))
        if key: matches.append({"op":"move_layer","layer_id":key,"x":int(m.group("x")),"y":int(m.group("y"))})
    if (m:=_EDIT_NEON.search(prompt)):
        neon=[l for l in project.layers if not l.locked and l.properties.get("cinematic_material")=="neon"]
        if len(neon)==1:matches.append({"op":"set_neon_color","layer_id":neon[0].id,"value":m.group("color").lower()})
    return matches if len(matches)==1 else None

def correct_layout(project:TTGProject, *,maximum: int=2) -> dict[str,Any]:
    """Correct provable off-canvas anchor positions, with bounded edit receipts.

    This does not judge or claim photorealism, aesthetic quality or text OCR.
    """
    changes=[]
    margin=24
    for iteration in range(maximum):
        changed=False
        for layer in project.layers:
            if layer.locked or layer.type not in ("text","text3d"):
                continue
            x=float(layer.transform.x);y=float(layer.transform.y)
            # The existing cinematic steel-text renderer interprets geometry
            # in its 1440x1080 authored design space, scaling it to the canvas
            # only when drawing. Clamping to the 640x480 output canvas collapses
            # otherwise valid wordmark/subtitle spacing and corrupts the scene.
            if layer.properties.get("cinematic_material")=="steel_text":
                design_w,design_h=1440,1080
            else:
                design_w,design_h=project.canvas.width,project.canvas.height
            newx=min(max(x,margin),design_w-margin)
            newy=min(max(y,margin),design_h-margin)
            if x==newx and y==newy:continue
            layer.transform.x=newx;layer.transform.y=newy;changed=True
            changes.append({"iteration":iteration+1,"layer_id":layer.id,"op":"move_layer",
                            "from":[x,y],"to":[newx,newy],
                            "reason":"Text anchor was outside the admitted canvas margin"})
        if not changed:break
    return {"correction_count":len(changes),"edits":changes,
            "structural_layout":"bounded_anchor_check_only",
            "semantic_visual_review":"required"}
