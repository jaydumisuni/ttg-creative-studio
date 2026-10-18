#!/usr/bin/env python3
"""A real 3D mesh / perspective product-concept scene for Creative Studio QA.

The 3D scene is constructed from parametric meshes in x/y/z, depth sorted,
shaded with two directional lights and rendered under a moving 3D camera.
Creative Studio subsequently owns the editable typography, project and MP4
compositing. This is not neural AI, not Blender, and not manufactured hardware.
"""
from __future__ import annotations

from functools import lru_cache
import argparse
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
BG = (4, 10, 20)
LIGHT = np.array([-0.55, 0.92, 0.6], dtype=float)
LIGHT /= np.linalg.norm(LIGHT)
FILL = np.array([0.87, 0.41, -0.22],dtype=float)
FILL /= np.linalg.norm(FILL)
FONT = "/usr/share/fonts/truetype/lato/Lato-Bold.ttf"


def font(size: int):
    return ImageFont.truetype(FONT, size)

@lru_cache(maxsize=1)
def backdrop():
    yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
    radial=np.exp(-(((xx-916)/540)**2+((yy-318)/398)**2)*1.8)
    spot=np.exp(-(((xx-1040)/300)**2+((yy-390)/240)**2)*1.7)
    bottom=np.maximum(0,yy/H)
    vignette=np.clip(1-.52*((xx-W*.53)/(W*.64))**2-.43*((yy-H*.48)/(H*.8))**2,.28,1.0)
    image=np.zeros((H,W,3),np.float32)
    image[:,:,0]=(3.6+radial*8+spot*5+bottom*1.7)*vignette
    image[:,:,1]=(9+radial*16+spot*17)*vignette
    image[:,:,2]=(17+radial*28+spot*29)*vignette
    return Image.fromarray(image.clip(0,255).astype('uint8'),'RGB').convert('RGBA')


def rotate_y(pos, angle):
    x,y,z=pos
    c,s=math.cos(angle),math.sin(angle)
    return np.array([c*x+s*z,y,-s*x+c*z],float)


class Camera:
    def __init__(self, t:float):
        phase=t/5.0
        az=math.radians(29+phase*47+2*math.sin(t*1.4))
        self.eye=np.array([6.6*math.sin(az),4.35+math.sin(t*.55)*.24,7.9*math.cos(az)])
        self.target=np.array([0.,.38,0.])
        fwd=self.target-self.eye
        fwd/=np.linalg.norm(fwd)
        self.fwd=fwd
        self.right=np.cross(fwd,[0.,1.,0.]);self.right/=np.linalg.norm(self.right)
        self.up=np.cross(self.right,fwd)
        self.f=1100.
        self.cx=902.
        self.cy=353.
    def projection(self,pos):
        q=np.array(pos,dtype=float)-self.eye
        dep=np.dot(q,self.fwd)
        dep=max(dep,.01)
        return (self.cx+self.f*np.dot(q,self.right)/dep,
                self.cy-self.f*np.dot(q,self.up)/dep,dep)
    def pt(self,pos):
        x,y,d=self.projection(pos)
        return (round(x),round(y))


def base_curve(w=2.95,d=2.87,r=.22,steps=5):
    points=[]
    a,b=w/2,d/2
    for cx,cz,start in [(a-r,b-r,0),(-a+r,b-r,90),
                        (-a+r,-b+r,180),(a-r,-b+r,270)]:
        for k in range(steps+1):
            angle=math.radians(start+90*k/steps)
            points.append((cx+r*math.cos(angle),cz+r*math.sin(angle)))
    return points


def poly(d,cam,points,color, outline=None,width=1):
    xy=[cam.pt(p) for p in points]
    d.polygon(xy,fill=tuple(int(x) for x in color))
    if outline:
        d.line(xy+[xy[0]],fill=outline,width=width)


def shade(base, normal, boost=1.,metal=.6):
    facing=max(0,float(np.dot(normal,LIGHT)))
    fill=max(0,float(np.dot(normal,FILL)))
    v=.41+.5*facing+.16*fill
    s=max(0,float(np.dot(normal,np.array([.55,.5,.68]))))**18
    col=np.asarray(base,float)*v*boost+(192*metal*s)*np.array([.68,.92,1.])
    return np.clip(col,0,255).astype(int)


def quad_on_front(draw,cam,x1,y1,x2,y2,z,color,outline=None,width=1):
    poly(draw,cam,[(x1,y1,z),(x2,y1,z),(x2,y2,z),(x1,y2,z)],color,outline,width)


def quad_on_top(draw,cam,x1,z1,x2,z2,y,color,outline=None,width=1):
    poly(draw,cam,[(x1,y,z1),(x2,y,z1),(x2,y,z2),(x1,y,z2)],color,outline,width)


def draw_shadow(scene,cam,t):
    floor=Image.new('RGBA',(W,H));d=ImageDraw.Draw(floor)
    z=cam.projection((0,-.16,0))[2]
    mid=cam.pt((0,-.13,0))
    scale=math.sqrt(10/z)
    for radius,alpha in [(240,16),(200,20),(156,23),(120,27),(80,38)]:
        rx=radius*scale;ry=rx*.19
        d.ellipse((mid[0]-rx,mid[1]-ry,mid[0]+rx,mid[1]+ry),
                  fill=(6,45,63,alpha))
    floor=floor.filter(ImageFilter.GaussianBlur(30))
    scene.alpha_composite(floor)


def draw_stage(scene,cam,t):
    layer=Image.new("RGBA",(W,H));d=ImageDraw.Draw(layer)
    # World-space floor grid, progressively fading with distance.
    for value in [i*.45 for i in range(-17,18)]:
        for a,b in [((value,-.19,-9),(value,-.19,9)),
                    ((-9,-.19,value),(9,-.19,value))]:
            p1,p2=cam.pt(a),cam.pt(b)
            d.line([p1,p2],fill=(19,74,92,22),width=1)
    # Concentric world rings are positioned below the mesh, so the 3D
    # enclosure occludes them physically in the foreground.
    for k in range(3):
        radius=1.85+k*.45
        arr=[cam.pt((radius*math.cos(a*math.tau/128),-.135,
                       radius*math.sin(a*math.tau/128))) for a in range(129)]
        d.line(arr,fill=(21,182,185,35-k*8),width=2)
    scene.alpha_composite(layer)
    draw_shadow(scene,cam,t)


def draw_solid(scene,cam,t):
    layer=Image.new('RGBA',(W,H))
    d=ImageDraw.Draw(layer)
    outline=(76,105,121)
    # Real geometric chamfered extrusion, not a flattened bitmap.
    perimeter=base_curve()
    levels=[(.00,.0),(.025,.055),(.09,.075),(.705,.075),(.765,.032),(.800,0.)]
    segments=[]
    for i in range(len(levels)-1):
        y0,in0=levels[i]
        y1,in1=levels[i+1]
        for j in range(len(perimeter)):
            a=np.array(perimeter[j])
            b=np.array(perimeter[(j+1)%len(perimeter)])
            def shrink(v,k):
                return tuple(v*(1-k))
            a0=shrink(a,in0)
            b0=shrink(b,in0)
            a1=shrink(a,in1)
            b1=shrink(b,in1)
            face=[(a0[0],y0,a0[1]),(b0[0],y0,b0[1]),
                  (b1[0],y1,b1[1]),(a1[0],y1,a1[1])]
            normal=np.cross(np.array(face[1])-face[0],np.array(face[3])-face[0])
            norm=np.linalg.norm(normal)
            if norm<1e-7:continue
            normal/=norm
            towards=cam.eye-np.mean(face,axis=0)
            if np.dot(normal,towards)<=0:continue
            dep=np.mean([cam.projection(pt)[2] for pt in face])
            if i==0: base=(80,105,117);boost=.8
            elif i in (1,3):base=(42,62,73);boost=1.3
            elif i==4:base=(115,134,141);boost=1.13
            else:base=(44,62,72);boost=1.1
            segments.append((dep,face,shade(base,normal,boost),i))
    segments.sort(reverse=True,key=lambda p:p[0])
    for _,f,c,i in segments:
        poly(d,cam,f,c,outline if i==4 else None)
    # Top face is a real world polygon at y = .800, viewed in perspective.
    top=[(x*.995,.801,z*.995) for x,z in perimeter]
    poly(d,cam,top,(42,61,74),(104,132,142),2)
    # Machined inset top chamfer.
    inset=[(x*.91,.804,z*.91) for x,z in perimeter]
    poly(d,cam,inset,(34,49,60),(47,77,86),1)
    # Top face stays intentionally uncluttered: OLED, button, branding only.
    # OLED glass window: metallic bevel, recessed black surface, blue lines.
    quad_on_top(d,cam,-.88,-.25,.46,.30,.815,(89,116,131),(130,158,165),2)
    quad_on_top(d,cam,-.82,-.20,.40,.25,.822,(2,15,27),(9,120,142),2)
    for i in range(4):
        yy=-.08+i*.082
        pts=[cam.pt((-0.7,.827,yy)),cam.pt((.15 if i%2 else .3,.827,yy))]
        d.line(pts,fill=(58,207,237,210-i*22),width=2)
    # Side push button beside OLED
    cx,cz=.73,.04
    pts=[(cx+math.cos(k*math.tau/20)*.115,.83,
          cz+math.sin(k*math.tau/20)*.115) for k in range(20)]
    poly(d,cam,pts,(45,68,73),(137,162,162),1)
    pts2=[(cx+math.cos(k*math.tau/20)*.071,.834,
          cz+math.sin(k*math.tau/20)*.071) for k in range(20)]
    poly(d,cam,pts2,(16,29,35),(35,198,215),1)

    # Physically projected top branding rather than screen-flat text.
    label=Image.new("RGBA",(430,85),(0,0,0,0))
    ImageDraw.Draw(label).text((215,38),"THE TECHGUY",font=font(32),
                               anchor="mm",fill=(182,199,201,240))
    quad=[cam.pt((x,.828,z)) for x,z in [
        (-1.02,.56),(1.02,.56),(1.02,1.03),(-1.02,1.03)]]
    source=[(0,0),(label.width,0),(label.width,label.height),(0,label.height)]
    A=[];b=[]
    for (x,y),(u,v) in zip(quad,source):
        A.append([x,y,1,0,0,0,-u*x,-u*y]);b.append(u)
        A.append([0,0,0,x,y,1,-v*x,-v*y]);b.append(v)
    params=np.linalg.solve(np.asarray(A,float),np.asarray(b,float))
    projected=label.transform((W,H),Image.Transform.PERSPECTIVE,tuple(params),
                              resample=Image.Resampling.BICUBIC)
    layer.alpha_composite(projected)
    d=ImageDraw.Draw(layer)
    # Gold-finger slot openings on the actual front vertical face (z +).
    front_z=1.439
    # moving camera sees side and top, but front remains genuinely projected.
    for center in (-.68,+.68):
        # dark CNC cutout
        quad_on_front(d,cam,center-.53,.25,center+.53,.46,front_z+.013,
                      (13,23,30),(99,118,121),2)
        quad_on_front(d,cam,center-.48,.29,center+.48,.42,front_z+.025,
                      (2,8,11),(42,53,55),1)
        # PCB edge inserted in each of two openings; metallic contact fingers.
        quad_on_front(d,cam,center-.36,.29,center+.39,.34,front_z+.037,
                      (56,65,43),(120,107,59))
        for pin in range(8):
            x=center-.31+pin*.088
            quad_on_front(d,cam,x,.299,x+.045,.338,front_z+.045,
                          (181+(pin%3)*12,142+(pin%2)*17,72),(207,177,101))
        # low-light key reflection near front bezel.
        d.line([cam.pt((center-.48,.459,front_z+.015)),
                cam.pt((center+.48,.459,front_z+.015))],
               fill=(165,205,213),width=1)
    # Sculpted seam left/right near the front body rim
    d.line([cam.pt((-1.30,.20,1.430)),cam.pt((-1.30,.62,1.430))],
           fill=(54,85,92),width=2)
    # Two practical screws on front panel
    for x in (-1.31,1.31):
        pos=cam.pt((x,.38,front_z+.019))
        d.ellipse((pos[0]-3,pos[1]-3,pos[0]+3,pos[1]+3),
                  fill=(100,125,133),outline=(12,20,27))
        d.line((pos[0]-2,pos[1]+1,pos[0]+2,pos[1]-1),fill=(17,28,33),width=1)

    # Kicker under lip: a geometric optical edge, not a flat neon rectangle.
    d.line([cam.pt((-1.29,.087,1.40)),cam.pt((1.29,.087,1.40))],
           fill=(39,178,186),width=2)
    scene.alpha_composite(layer)
    # A gentle emissive bloom around the actual OLED and port edges.
    bloom=layer.filter(ImageFilter.GaussianBlur(11))
    bloom.putalpha(bloom.getchannel('A').point(lambda a: int(a*.095)))
    scene.alpha_composite(bloom)
    return scene


def overlay_text(img,t):
    # The actual typography is editable in Creative Studio's project layer
    # stack. This compositor only adds photographic stage annotations.
    draw=ImageDraw.Draw(img)
    draw.line([(82,61),(490,61)],fill=(42,86,96),width=2)
    draw.line([(82,660),(1194,660)],fill=(36,73,86),width=1)
    # restrained technical camera UI.
    draw.text((1095,67),"3D CONCEPT / QA",font=font(13),fill=(92,153,170))
    draw.text((1035,670),"FRAME  /  %03d" % int(t*20),font=font(13),fill=(92,153,170))
    return img


def render_frame(t):
    cam=Camera(t)
    img=backdrop().copy()
    draw_stage(img,cam,t)
    draw_solid(img,cam,t)
    return overlay_text(img,t).convert("RGB")


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--dir",type=Path,required=True)
    a.add_argument("--seconds",type=float,default=4.8)
    a.add_argument("--fps",type=int,default=20)
    a.add_argument("--sample",type=int,default=-1)
    args=a.parse_args()
    assert 1<=args.fps<=24 and .5<=args.seconds<=7
    args.dir.mkdir(parents=True,exist_ok=True)
    count=int(round(args.seconds*args.fps))
    indices=[args.sample] if args.sample>=0 else list(range(count))
    for n in indices:
        img=render_frame(n/args.fps)
        img.save(args.dir/f"shot_{n:04d}.png",optimize=False)
        if n%12==0: print(f"3D mesh frame {n+1}/{count}",flush=True)

if __name__=="__main__":
    main()
