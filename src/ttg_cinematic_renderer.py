#!/usr/bin/env python3
"""Cinematic 2.5D renderer for TTG Creative Studio.

This is the bridge between flat 2D preview and a future true 3D backend.
It creates depth, extrusion, glow, particles and camera-feel using Pillow.
"""

from __future__ import annotations

from pathlib import Path
import math
import random
from PIL import Image, ImageDraw, ImageFilter

from ttg_project_schema import TTGProject
from ttg_timeline_engine import TimelineEngine
from ttg_text_renderer import render_text_layer


class CinematicRenderer:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.timeline = TimelineEngine()

    def render_frame(self, project: TTGProject, time: float = 0.0) -> Image.Image:
        canvas = Image.new("RGBA", (project.canvas.width, project.canvas.height), project.canvas.background)
        self._draw_background_energy(canvas, time)
        for raw in project.layers:
            if not raw.visible:
                continue
            layer = self.timeline.apply_to_layer(raw, time)
            if layer.type in {"text", "text3d"}:
                self._draw_cinematic_text(canvas, layer, time)
            elif layer.type == "particle":
                self._draw_particles(canvas, layer, time)
            elif layer.type == "shape":
                self._draw_shape(canvas, layer)
        self._draw_vignette(canvas)
        return canvas

    def _draw_cinematic_text(self, canvas: Image.Image, layer, time: float) -> None:
        text = str(layer.properties.get("text", layer.name))
        props = dict(layer.properties)
        props.setdefault("shadow", True)
        props.setdefault("glow", True)
        props.setdefault("stroke_width", 1 if layer.type == "text3d" else 0)
        props.setdefault("stroke_fill", "#00111F")
        depth = int(props.get("extrude_px", 14 if layer.type == "text3d" else 0))
        for offset in range(depth, 0, -2):
            extrude_props = dict(props)
            extrude_props["color"] = props.get("extrude_color", "#24004A")
            extrude_props["glow"] = False
            extrude_props["shadow"] = False
            img = render_text_layer(canvas.size, text, layer.transform.x + offset, layer.transform.y + offset, extrude_props)
            canvas.alpha_composite(img)
        img = render_text_layer(canvas.size, text, layer.transform.x, layer.transform.y, props)
        if layer.transform.opacity < 1:
            img.putalpha(img.getchannel("A").point(lambda p: int(p * layer.transform.opacity)))
        canvas.alpha_composite(img)

    def _draw_background_energy(self, canvas: Image.Image, time: float) -> None:
        draw = ImageDraw.Draw(canvas)
        w, h = canvas.size
        for i in range(26):
            angle = (i / 26) * math.tau + time * 0.18
            x1 = w / 2 + math.cos(angle) * 70
            y1 = h / 2 + math.sin(angle) * 40
            x2 = w / 2 + math.cos(angle) * w
            y2 = h / 2 + math.sin(angle) * h
            color = "#00E5FF44" if i % 2 == 0 else "#BC13FE44"
            draw.line((x1, y1, x2, y2), fill=color, width=2)

    def _draw_particles(self, canvas: Image.Image, layer, time: float) -> None:
        draw = ImageDraw.Draw(canvas)
        colors = layer.properties.get("colors", ["#00E5FF", "#BC13FE"])
        density = int(layer.properties.get("density", 140))
        w, h = canvas.size
        rng = random.Random(49)
        for i in range(min(density, 400)):
            base_x = rng.random() * w
            base_y = rng.random() * h
            drift = time * (20 + (i % 11))
            x = (base_x + drift) % w
            y = (base_y + math.sin(time + i) * 8) % h
            r = 1 + (i % 4)
            draw.ellipse((x, y, x + r, y + r), fill=colors[i % len(colors)])

    def _draw_shape(self, canvas: Image.Image, layer) -> None:
        draw = ImageDraw.Draw(canvas)
        x, y = layer.transform.x, layer.transform.y
        width = float(layer.properties.get("width", 200)) * layer.transform.scale_x
        height = float(layer.properties.get("height", 100)) * layer.transform.scale_y
        fill = layer.properties.get("fill", "#00E5FF")
        draw.rounded_rectangle((x, y, x + width, y + height), radius=18, fill=fill)

    def _draw_vignette(self, canvas: Image.Image) -> None:
        w, h = canvas.size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((-w * 0.15, -h * 0.25, w * 1.15, h * 1.25), fill=220)
        mask = Image.eval(mask.filter(ImageFilter.GaussianBlur(80)), lambda p: 255 - p)
        vignette = Image.new("RGBA", (w, h), (0, 0, 0, 150))
        vignette.putalpha(mask)
        canvas.alpha_composite(vignette)


"""Creative Studio's existing cinematic renderer: physically inspired material layers.

These are native, parameterised Studio shape/text layers, not image-model output,
downloaded stock artwork, or a second renderer. The material compositor is
called by CanvasRenderer and its existing MotionExporter.
"""

from functools import lru_cache
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops
from ttg_text_renderer import load_font

def _c(a):
    return tuple(int(a[i:i+2], 16) for i in (1,3,5))

@lru_cache(maxsize=4)
def _room(w:int,h:int,seed:int=49,warmth:float=.55)->Image.Image:
    if w*h>3_300_000 or w<320 or h<240: raise ValueError("Studio scene size out of native material budget")
    rng=np.random.default_rng(seed)
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    xf=xx/w;yf=yy/h
    left=np.clip((xf-.17)*w/12,0,1)
    grain=rng.normal(0,1.65,(h,w)).astype(np.float32)
    shade=np.clip(.5+.46*(1-yf)+.12*(xf-.65),0,1)
    highlight=np.exp(-((xf-.48)/.28)**2-((yf-.02)/.4)**2)*warmth
    vignette=np.clip(((xf-.52)/.84)**2+((yf-.50)/.93)**2,0,1)
    lum=grain + shade*7 + highlight*28-vignette*9
    wall=np.stack((27+lum,30+lum*.96,35+lum*.9),axis=2)
    wall=np.clip(wall,0,255).astype('uint8')
    im=Image.fromarray(wall,"RGB").convert("RGBA")
    d=ImageDraw.Draw(im,'RGBA')
    X=lambda u:round(w*u)
    Y=lambda u:round(h*u)
    # Architectural glass lobby and steel mullions left of the sign wall.
    # City-facing glazing has independent atmospheric depth; not a stock photo.
    sky=Image.new("RGBA",(w,h))
    sky_draw=ImageDraw.Draw(sky)
    for row in range(Y(.09),Y(.85)):
        t=(row-Y(.09))/max(1,Y(.76))
        c=(round(78-33*t),round(112-54*t),round(140-66*t),255)
        sky_draw.line((0,row,X(.176),row),fill=c)
    sky_draw.rectangle((0,0,X(.176),Y(.09)),fill=(13,20,28,255))
    for k in range(26):
        bx=round(k*X(.0083)) ; by=Y(.33+(k*17%14)/43)
        bw=max(3,round(X(.0065)))
        sky_draw.rectangle((bx,by,bx+bw,Y(.87)),fill=(22+(k%4)*8,39+(k%3)*10,53+(k%2)*8,255))
        for light_y in range(by+6,Y(.8),max(12,Y(.021))):
            if ((k*17+light_y//12)%9)<3:
                sky_draw.rectangle((bx+1,light_y,bx+max(2,bw//2),light_y+2),
                                   fill=(243,182,104,210))
    sky=sky.filter(ImageFilter.GaussianBlur(max(1,w//900)))
    im.alpha_composite(sky)
    d=ImageDraw.Draw(im,'RGBA')
    d.rectangle((0,0,X(.178),h),fill=(9,16,26,73))
    for j in range(7):
        bx=X(.009+j*.026)
        bh=Y(.56+(.1*((j*19)%6)/6))
        d.rectangle((bx,bh,bx+X(.012),Y(.82)),fill=(22+j*3,37+j*3,53+j*4,210))
    d.polygon([(0,0),(X(.174),0),(X(.16),Y(.79)),(0,Y(.9))],fill=(17,27,37,74))
    d.line((X(.084),0,X(.084),h),fill=(4,7,11,255),width=max(3,X(.006)))
    d.line((X(.159),0,X(.159),Y(.94)),fill=(5,8,12,255),width=max(3,X(.008)))
    d.polygon([(0,Y(.195)),(X(.155),Y(.118)),(X(.155),Y(.128)),(0,Y(.206))],fill=(247,180,105,210))
    d.line((0,Y(.81),X(.16),Y(.8)),fill=(12,17,24,255),width=max(2,X(.004)))
    d.rectangle((0,Y(.83),X(.162),h), fill=(21,30,39,215))
    for k in range(7):
        x=X(k*.028)
        d.line((x,Y(.82),x-X(.018),h), fill=(54,65,72,50),width=2)
    # Dark window reveal, sharp architectural join and ceiling light.
    d.rectangle((X(.172),0,X(.18),Y(.915)),fill=(5,7,11,255))
    d.line((X(.181),0,X(.181),Y(.915)),fill=(84,81,72,100),width=max(2,X(.0018)))
    d.line((X(.18),Y(.04),X(.89),Y(.04)),fill=(215,169,125,26),width=3)
    # Right walnut slats as depth/context.
    d.rectangle((X(.943),0,w,Y(.86)),fill=(23,21,18,255))
    for i in range(7):
        x=X(.947+i*.008)
        d.line((x,0,x,Y(.86)),fill=(102,70,47,100),width=max(1,X(.002)))
        d.line((x+X(.002),0,x+X(.002),Y(.86)),fill=(12,10,11,235),width=max(1,X(.001)))
    # Floor: marble slab with perspective seams.
    d.polygon([(0,Y(.87)),(X(.89),Y(.86)),(w,Y(.90)),(w,h),(0,h)],fill=(21,22,26,255))
    d.line((0,Y(.867),X(.92),Y(.86)),fill=(252,185,117,160),width=max(2,Y(.004)))
    # Warm floor bounce, polished enough to read as architectural stone.
    d.line((X(.17),Y(.885),X(.7),Y(.883)),fill=(184,141,107,32),width=max(3,Y(.008)))
    d.line((X(.32),Y(.89),X(.28),h),fill=(82,82,78,65),width=2)
    d.line((X(.68),Y(.88),X(.82),h),fill=(71,79,84,65),width=2)
    # Right glossy marble reception desk; intentionally behind lower edge of sign.
    d.polygon([(X(.62),Y(.9)),(X(.92),Y(.8)),(w,Y(.86)),(w,h),(X(.64),h)],fill=(8,12,15,255))
    d.polygon([(X(.62),Y(.9)),(X(.91),Y(.80)),(w,Y(.855)),(X(.80),Y(.93))],fill=(27,31,35,255))
    d.line((X(.62),Y(.90),X(.91),Y(.80),w,Y(.855)),fill=(139,139,133,105),width=2)
    for k in range(12):
        x=X(.64+k*.025)
        y=Y(.9-k*.008)
        d.line((x,y,x+X(.008),y-Y(.013)),fill=(129,134,132,38),width=1)
    # Soft, blurred plant at far right for foreground depth.
    plant=Image.new("RGBA",(w,h))
    q=ImageDraw.Draw(plant)
    q.rectangle((X(.962),Y(.77),X(.987),Y(.94)),fill=(27,26,22,200))
    for i in range(19):
        a=i*2.4+.2
        x=X(.966)+math.cos(a)*X(.077)*(0.55+.4*(i%5)/5)
        y=Y(.80)-abs(math.sin(a))*Y(.23)
        q.line((X(.966),Y(.84),x,y),fill=(46,67,40,175),width=max(2,X(.004)))
        q.ellipse((x-X(.021),y-Y(.012),x+X(.018),y+Y(.01)),
                  fill=(50+(i%4)*9,72+(i%5)*10,39,175))
    im=Image.alpha_composite(im,plant.filter(ImageFilter.GaussianBlur(max(2,w//420))))
    # Architectural spotlights, soft photographic falloff.
    lighting=Image.new("RGBA",(w,h))
    ld=ImageDraw.Draw(lighting)
    for cx,cy,rx,ry,rgba in [
        (.27,.045,.14,.28,(236,189,130,32)),
        (.74,.02,.19,.24,(243,205,153,26)),
        (.10,.58,.11,.36,(91,141,187,13))]:
        for k in range(14,0,-1):
            f=k/14
            box=(X(cx-rx*f),Y(cy-ry*f),X(cx+rx*f),Y(cy+ry*f))
            ld.ellipse(box,fill=(rgba[0],rgba[1],rgba[2],int(rgba[3]*(1-f)**1.8)))
    im=Image.alpha_composite(im,lighting.filter(ImageFilter.GaussianBlur(max(9,w//90))))
    # Soft physically plausible downlight pools on the actual plaster wall.
    array=np.asarray(im.convert("RGB")).astype(np.float32).copy()
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    for cx,cy,rx,ry,power in [(.35,.06,.10,.20,25),(.79,.03,.10,.18,22)]:
        field=np.exp(-(((xx/w-cx)/rx)**2+((yy/h-cy)/ry)**2))
        wall=(xx/w>.183)&(xx/w<.94)
        array[:,:,0]+=field*power*wall
        array[:,:,1]+=field*power*.74*wall
        array[:,:,2]+=field*power*.54*wall
    im=Image.fromarray(np.uint8(np.clip(array,0,255)),"RGB").convert("RGBA")
    return _architectural_finish(im,seed,warmth)


def _architectural_finish(im: Image.Image, seed: int, warmth: float) -> Image.Image:
    """Native Studio optical finish for an authored architectural scene.

    Adds deterministic multi-scale wall plaster, plausible window-occlusion
    gradients, diffuse floor/desk stone microstructure, and soft-bounced light.
    This improves the existing Studio scene; it is not a ray tracer or photo.
    """
    w, h = im.size
    rng = np.random.default_rng(seed ^ 0x753AD)
    sy, sx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = sx / w
    v = sy / h

    # Coarse and high-frequency texture operate at independent spatial scales.
    coarse = np.asarray(Image.fromarray(
        rng.integers(0, 256, (max(2, h // 55), max(2, w // 55)), dtype=np.uint8)
    ).resize((w, h), Image.Resampling.BICUBIC), dtype=np.float32)
    medium = np.asarray(Image.fromarray(
        rng.integers(0, 256, (max(2, h // 10), max(2, w // 10)), dtype=np.uint8)
    ).resize((w, h), Image.Resampling.BICUBIC), dtype=np.float32)
    micro = rng.normal(0, 1, (h, w)).astype(np.float32)
    grain = (coarse - 127) * .075 + (medium - 127) * .027 + micro * 2.1
    wall = (u > .181) & (u < .939) & (v < .861)
    # The wall is not uniformly lit; the glazed doorway darkens its edge.
    occlusion = 14 * np.exp(-((u-.19)/.028)**2)
    occlusion += 10 * np.exp(-((u-.93)/.03)**2)
    indirect = 8 * np.exp(-((v-.86)/.045)**2)
    upper = 5 * np.exp(-((v-.02)/.085)**2)
    falloff = np.clip((v-.56)*19, 0, 8)
    img = np.asarray(im.convert("RGB"), dtype=np.float32).copy()
    wall_light = grain - occlusion + indirect + upper - falloff
    for c, tint in enumerate((1.0, .95, .88)):
        img[:,:,c] += wall * wall_light * tint

    # Polished stone, bounded to the floor and the existing reception desk:
    # slightly distorted veins, fine fissures and shifted reflection pools.
    vein_a = np.sin((u*14 + np.sin(v*45 + u*22)*.19 +
                     np.sin(u*63-v*25)*.041 + v*1.7)*math.pi)
    vein_b = np.sin((u*30 - v*6 + np.sin(v*28-u*11)*.37)*math.pi)
    seam = np.clip((vein_a-.915)/.075, 0, 1)
    hairline = np.clip((vein_b-.976)/.02, 0, 1)
    stone = seam*16 + hairline*9 + micro*.86
    floor = (v > .87) & (u < .615)  # keep original wall and glass untouched
    desk = (u > .64) & (v > (.9-(u-.64)*.31)) & (v < .985)
    slab = floor | desk
    warm_bounce = 9*np.exp(-((v-.89)/.013)**2)
    for c, strength in enumerate((1.0, 1.01, 1.02)):
        img[:,:,c] += slab * (stone*strength + warm_bounce*warmth)
    im = Image.fromarray(np.uint8(np.clip(img,0,255)), "RGB").convert("RGBA")

    # Procedural leaf silhouettes with specular veins (no image assets).
    # Restrained, because foliage is deliberately foreground/out of focus.
    leaves = Image.new("RGBA", (w,h))
    draw = ImageDraw.Draw(leaves, "RGBA")
    anchor=(int(w*.977), int(h*.81))
    for i in range(24):
        theta=(i*2.39996323 + .2)
        scale=.023+.033*((i*11)%13)/13
        ex=int(w*(.967 + math.cos(theta)*(.018 + .052*((i*7)%11)/11)))
        ey=int(h*(.81 - abs(math.sin(theta))*(.05+.16*((i*5)%9)/9)))
        mid=((anchor[0]+ex)//2,(anchor[1]+ey)//2)
        dx,dy=ex-anchor[0],ey-anchor[1]
        norm=max(1,math.hypot(dx,dy))
        perp=(-dy/norm,dx/norm)
        breadth=scale*min(w,h)*(.50+.4*((i*13)%7)/7)
        tip=(ex,ey)
        a=(int(mid[0]+perp[0]*breadth),int(mid[1]+perp[1]*breadth))
        b=(int(mid[0]-perp[0]*breadth),int(mid[1]-perp[1]*breadth))
        green=(31+i%5*5,54+i%7*6,26+i%4*3,195)
        draw.polygon([anchor,a,tip,b],fill=green)
        draw.line([anchor,mid,tip],fill=(96,107,48,95),width=max(1,w//1100))
    # Multi-plane focus: foreground leaves soften without losing contours.
    leaf_soft=leaves.filter(ImageFilter.GaussianBlur(max(1,w//950)))
    return Image.alpha_composite(im,leaf_soft)


def _metallic_shading(shape: tuple[int,int], seed: int, light_shift: float):
    """Generate fine horizontal brushed metal with studio-window reflections."""
    w,h = shape
    rng=np.random.default_rng(seed)
    xs=np.arange(w,dtype=np.float32)[None,:]/max(1,w)
    ys=np.arange(h,dtype=np.float32)[:,None]/max(1,h)
    # Long anisotropic horizontal scratches (same intensity across each row).
    scratches=rng.normal(0,2.1,(h,1)).astype(np.float32)
    scratches+=1.3*np.sin(ys*math.pi*260)
    fine=rng.normal(0,1.15,(h,w)).astype(np.float32)
    # Several broad softbox reflections with specular attenuation.
    window=36*np.exp(-((xs-(.35+light_shift*.1))/.11)**2)
    window+=21*np.exp(-((xs-(.81-light_shift*.12))/.055)**2)
    window-=26*np.exp(-((xs-.58)/.08)**2)
    lateral=9*np.cos((ys*4.0+xs*.25)*math.pi)
    burnish=7*np.sin(xs*math.pi*19)
    metal=np.clip(159+window+scratches+fine+lateral+burnish,45,246)
    return np.stack((metal,metal+4.0,metal+9.0),axis=2).clip(0,255).astype("uint8")

def _steel_texture(size,seed=1,light_shift=0.):
    """Brushed metal finished by Studio's own anisotropic material routine."""
    return Image.fromarray(_metallic_shading(size,seed,light_shift),"RGB").convert("RGBA")

def _mask(size,layer,kind):
    w,h=size
    m=Image.new("L",size,0)
    d=ImageDraw.Draw(m)
    scx=w/1440;scy=h/1080
    x=layer.transform.x*scx;y=layer.transform.y*scy
    transform_scale_x=float(layer.transform.scale_x)
    transform_scale_y=float(layer.transform.scale_y)
    if not (0.05<=transform_scale_x<=10 and 0.05<=transform_scale_y<=10):
        raise ValueError("Invalid material layer transform scale")
    p=layer.properties
    if kind=="steel_polygon":
        pts=p.get("points")
        if not isinstance(pts,list) or len(pts)<3 or len(pts)>90:raise ValueError("Studio metal polygon requires 3..90 points")
        points=[(int(x+float(a)*scx*transform_scale_x),
                  int(y+float(b)*scy*transform_scale_y)) for a,b in pts]
        d.polygon(points,fill=255)
    elif kind=="steel_text":
        font=load_font(p.get("font_path"),max(5,round(float(p.get("size",80))*scy*transform_scale_y)))
        msg=str(p.get("text","")).strip()
        if not 1<=len(msg)<=70:raise ValueError("Studio material text must be 1..70 characters")
        d.text((int(x),int(y)),msg,font=font,fill=255,stroke_width=max(0,int(p.get("stroke_width",0))))
    else:raise ValueError("Unknown native material mask type")
    return m

def _material_object(canvas,mask,seed=49,light_shift=0.,led=(26,128,255),depth=8):
    w,h=canvas.size
    outline=mask.filter(ImageFilter.MaxFilter(7))
    glow=outline.filter(ImageFilter.GaussianBlur(max(4,w//160)))
    light=Image.new("RGBA",canvas.size,(*led,0))
    light.putalpha(glow.point(lambda p:int(p*.48)))
    canvas.alpha_composite(light)
    blur=mask.filter(ImageFilter.GaussianBlur(max(5,w//140)))
    shadow=Image.new("RGBA",canvas.size,(0,0,0,0))
    shadow.putalpha(blur.point(lambda v:int(v*.82)))
    from PIL import ImageChops
    offset=ImageChops.offset(shadow,round(w*.008),round(h*.011))
    canvas.alpha_composite(offset)
    for i in range(depth,0,-2):
        side=Image.new("RGBA",canvas.size,(4+max(0,i),12+2*i,23+3*i,0))
        side.putalpha(ImageChops.offset(mask,i,i))
        canvas.alpha_composite(side)
    base=_steel_texture(canvas.size,seed,light_shift)
    base.putalpha(mask)
    canvas.alpha_composite(base)
    # Emboss rim and top bevel, with strong floating shadow.
    high=ImageChops.subtract(mask,ImageChops.offset(mask,0,2))
    low=ImageChops.subtract(mask,ImageChops.offset(mask,0,-2))
    hi=Image.new("RGBA",canvas.size,(245,250,255,0));hi.putalpha(high.point(lambda v:int(v*.8)))
    lo=Image.new("RGBA",canvas.size,(28,39,52,0));lo.putalpha(low.point(lambda v:int(v*.92)))
    canvas.alpha_composite(hi);canvas.alpha_composite(lo)

def _neon(canvas,layer,clock=0):
    p=layer.properties
    pts=p.get("points",[])
    if not 2<=len(pts)<=40:raise ValueError("Invalid neon polyline")
    w,h=canvas.size;scx=w/1440;scy=h/1080
    points=[(round((layer.transform.x+x*layer.transform.scale_x)*scx),
             round((layer.transform.y+y*layer.transform.scale_y)*scy)) for x,y in pts]
    palette={"blue":(45,138,255),"gold":(245,165,47),
             "purple":(155,97,250)}
    led=palette.get(str(p.get("led_color","blue")),palette["blue"])
    beam=Image.new("RGBA",canvas.size);d=ImageDraw.Draw(beam)
    intensity=.77+.2*math.sin(clock*2.8+.7)
    width=max(2,round(float(p.get("width",4))*scx))
    d.line(points,fill=(*led,255),width=width+2,joint="curve")
    halo=beam.filter(ImageFilter.GaussianBlur(max(5,w//165)))
    halo.putalpha(halo.getchannel("A").point(lambda a:int(a*.82*intensity)))
    canvas.alpha_composite(halo)
    d=ImageDraw.Draw(beam)
    d.line(points,fill=(200,240,255,255),width=max(1,width//2),joint="curve")
    canvas.alpha_composite(beam)
    if p.get("terminals",False):
        d=ImageDraw.Draw(canvas)
        for x,y in (points[0],points[-1]):
            rr=max(2,round(w*.005))
            d.ellipse((x-rr,y-rr,x+rr,y+rr),outline=(*led,255),width=max(2,rr//2))

def draw_native_material(canvas,layer,time=0):
    """Dispatch high-fidelity material rendering inside the existing Studio engine."""
    kind=layer.properties.get("cinematic_material")
    if kind=="architectural_lobby":
        seed=int(layer.properties.get("seed",49))
        scene=_room(canvas.width,canvas.height,seed,float(layer.properties.get("warmth",.55)))
        canvas.alpha_composite(scene)
    elif kind in {"steel_polygon","steel_text"}:
        mask=_mask(canvas.size,layer,kind)
        _material_object(canvas,mask,int(layer.properties.get("seed",49)),
                         math.sin(time*1.5)*.15,depth=max(0,min(30,int(layer.properties.get("depth",9)))))
    elif kind=="neon":
        _neon(canvas,layer,time)
    else:
        raise ValueError("Unsupported Studio cinematic material: "+str(kind))
