#!/usr/bin/env python3
"""Initial Banana Level actions.

These actions must be deterministic and useful without AI. AI can later choose or
combine them, but the tool should already do damage on its own.
"""

from __future__ import annotations

from ttg_project_schema import TTGProject
from ttg_preset_actions import PresetActions


class BananaActions:
    def __init__(self) -> None:
        self.presets = PresetActions()

    def make_it_pop(self, project: TTGProject) -> None:
        project.export.setdefault("banana", {})["last_workflow"] = "make_it_pop"
        project.export["banana"]["promise"] = "Polished glow, contrast and premium text depth."
        for layer in project.layers:
            if layer.type in {"text", "text3d"}:
                layer.properties.update({
                    "glow": True,
                    "glow_color": "#00E5FF",
                    "glow_blur": max(int(layer.properties.get("glow_blur", 8)), 12),
                    "stroke_width": max(int(layer.properties.get("stroke_width", 1)), 3),
                    "stroke_fill": layer.properties.get("stroke_fill", "#120026"),
                    "shadow": True,
                    "shadow_blur": max(int(layer.properties.get("shadow_blur", 6)), 10),
                    "gradient": True,
                    "gradient_start": layer.properties.get("gradient_start", "#BC13FE"),
                    "gradient_end": layer.properties.get("gradient_end", "#00E5FF"),
                })
                if layer.type == "text":
                    layer.type = "text3d"
            elif layer.type in {"shape", "image"}:
                layer.properties.setdefault("shadow", True)
                layer.properties.setdefault("glow", True)
                layer.properties.setdefault("opacity", 0.96)

    def brand_everything(self, project: TTGProject, primary: str = "#00E5FF", accent: str = "#BC13FE") -> None:
        project.export.setdefault("banana", {})["last_workflow"] = "brand_everything"
        project.export["banana"]["primary"] = primary
        project.export["banana"]["accent"] = accent
        for layer in project.layers:
            if layer.type in {"text", "text3d"}:
                layer.properties.setdefault("gradient", True)
                layer.properties["gradient_start"] = accent
                layer.properties["gradient_end"] = primary
                layer.properties.setdefault("glow", True)
                layer.properties["glow_color"] = primary
            elif layer.type == "shape":
                layer.properties["fill"] = layer.properties.get("fill", "#07132F80")
                layer.properties["stroke_fill"] = primary


    def create_professional_wall_sign(self, prompt: str, *, width: int = 1440,
                                      height: int = 1080, fps: int = 12,
                                      duration: float = 2.5) -> TTGProject:
        """Build a genuine editable cinematic office-sign scene from a new instruction.

        It is a supported local *scene family*, not unrestricted generative AI.
        Native materials, brand geometry and lighting render through Studio's
        existing CanvasRenderer/MotionExporter; no reference image or model.
        """
        import re
        from ttg_project_schema import Layer, Transform
        if not isinstance(prompt,str) or len(prompt)>1000:
            raise ValueError("Instruction must be a short scene description")
        words=prompt.lower()
        if not any(w in words for w in ("wall", "sign", "lobby", "office", "logo")):
            raise ValueError("This workflow supports professional office-wall logo scenes only")
        if width*height>3_300_000 or width<640 or height<480:
            raise ValueError("Native architectural render supports 640x480 to 3.3MP")
        if abs(width/height - 4/3)>.06:
            raise ValueError("Architectural scene needs an approximately 4:3 canvas")
        if not 0.3<=duration<=12 or not 1<=fps<=30:
            raise ValueError("Duration or frame rate is outside bounded Studio settings")
        import hashlib
        palette=("gold" if any(x in words for x in ("gold","amber","warm light")) else
                 "purple" if any(x in words for x in ("purple","violet")) else "blue")
        seed=int.from_bytes(hashlib.sha256(prompt.encode("utf-8")).digest()[:2],"big")
        p=TTGProject(name="Professional office-wall identity | instruction-created",
                     project_type="motion")
        p.canvas.width,p.canvas.height=width,height
        p.canvas.duration=duration
        p.canvas.fps=fps
        p.canvas.background="#101318"
        p.brand.name="THETECHGUY DIGITAL SOLUTIONS"
        p.layers=[]
        def add(type_,name,props,x=0,y=0):
            i=len(p.layers)+1
            layer=Layer(id=f"pro_scene_{i:03d}",type=type_,name=name,
                        transform=Transform(x=x,y=y),properties=props)
            p.layers.append(layer)
            return layer
        add("shape","Original architectural lobby · procedural surface",
            {"cinematic_material":"architectural_lobby","seed":seed,
             "warmth":.83 if palette=="gold" else .55})
        # Original authored geometry: no SVG/bitmap, photographic reference, or stock logo.
        add("shape","Raised stainless-steel T · editable polygon",
            {"cinematic_material":"steel_polygon","depth":12,"seed":11,
             "points":[[0,5],[415,0],[390,64],[257,70],[249,361],
                       [185,361],[183,77],[45,77]]},430,192)
        add("shape","Raised stainless-steel G · editable polygon",
            {"cinematic_material":"steel_polygon","depth":13,"seed":18,
             "points":[[263,5],[494,5],[540,82],[319,87],
                       [267,129],[267,230],[398,230],[398,184],
                       [505,184],[505,335],[455,372],[246,372],
                       [206,323],[205,103]]},480,194)
        add("shape","T/G circuit connector, illuminated",
            {"cinematic_material":"neon","width":6,"terminals":True,"led_color":palette,
             "points":[[0,0],[49,-51],[145,-52],[189,-118]]},745,281)
        add("shape","Central microcircuit track",
            {"cinematic_material":"neon","width":5,"terminals":True,"led_color":palette,
             "points":[[0,0],[0,123],[46,170],[101,173]]},684,352)
        add("shape","G terminal illumination",
            {"cinematic_material":"neon","width":5,"terminals":True,"led_color":palette,
             "points":[[0,0],[52,-59],[156,-60]]},742,488)
        # Material based type, spacing and lower hierarchy remain precise.
        add("text3d","THETECHGUY · brushed stainless exact wordmark",
            {"cinematic_material":"steel_text","text":"THETECHGUY",
             "size":130,"depth":10,"seed":32,
             "font_path":"/usr/share/fonts/truetype/lato/Lato-Heavy.ttf"},292,594)
        add("text3d","DIGITAL SOLUTIONS · raised letterform",
            {"cinematic_material":"steel_text","text":"D I G I T A L    S O L U T I O N S",
             "size":30,"depth":5,"seed":13,
             "font_path":"/usr/share/fonts/truetype/lato/Lato-Medium.ttf"},463,729)
        add("shape","Left steel footer line",
            {"cinematic_material":"steel_polygon","points":[[0,0],[110,0],[109,3],[0,3]],"depth":1},295,748)
        add("shape","Right steel footer line",
            {"cinematic_material":"steel_polygon","points":[[0,0],[132,0],[131,3],[0,3]],"depth":1},1040,748)
        p.export["professional_creation"]={
            "input_instruction":prompt,"renderer":"native-canvas-cinematic-materials",
            "model_inference":False,"reference_image_count":0,
            "scope":"authored office-wall signage scene family",
            "seed":seed,"accent_palette":palette,
            "intent":"premium photorealistic architectural office sign, branded video"
        }
        return p
