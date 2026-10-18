"""Interactive Qt software 3D viewport, object and topology editing.

Native, model-free and Blender-free. The project remains owned by Creative
Studio: plain editable scene JSON and validated mesh vertices/faces. No GPL
runtime linkage and no optional GPU/large data download.
"""
from __future__ import annotations

from copy import deepcopy
import math

from PyQt6.QtCore import Qt, QPointF, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPolygonF, QBrush
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QListWidget,
    QPushButton, QComboBox, QDoubleSpinBox, QMessageBox, QGroupBox, QScrollArea,
    QColorDialog, QSpinBox
)

from ttg_blender_engine import validate_scene
from ttg_native_3d import (
    PRIMITIVES, convert_primitive, transform_selection, subdivide,
    extrude_face, delete_faces, select_edge, validate_mesh, object_at_frame,
    set_keyframe, remove_keyframe,
)
from ttg_advanced_3d_core import (
    uv_project, uv_transform, sculpt, add_bone, set_skin_weight,
    add_constraint, set_procedural, set_physics,
)
from ttg_pro_3d_core import (
    unwrap_pack_faces, assign_uv_seams, paint_skin_weights,
    set_multires, set_bone_ik, set_geometry_graph, set_extended_physics,
    adaptive_sculpt,
)
from ttg_pro_3d_v4 import (
    set_uv_unwrap, set_geometry_dag, set_ik_pole, normalize_skin_weights,
    sculpt_stroke,
)

def _rotate(v: list[float], angles: list[float]) -> list[float]:
    x,y,z=v
    ax,ay,az=[math.radians(a) for a in angles]
    x,y=x*math.cos(az)-y*math.sin(az),x*math.sin(az)+y*math.cos(az)
    y,z=y*math.cos(ax)-z*math.sin(ax),y*math.sin(ax)+z*math.cos(ax)
    x,z=x*math.cos(ay)+z*math.sin(ay),-x*math.sin(ay)+z*math.cos(ay)
    return [x,y,z]


def _distance_to_segment(p: QPointF, a: QPointF, b: QPointF) -> float:
    vx,vy=b.x()-a.x(),b.y()-a.y()
    den=vx*vx+vy*vy
    f=min(1,max(0,((p.x()-a.x())*vx+(p.y()-a.y())*vy)/den)) if den else 0
    return math.hypot(p.x()-(a.x()+f*vx),p.y()-(a.y()+f*vy))


def _inside(p: QPointF, points: list[QPointF]) -> bool:
    on=False
    j=len(points)-1
    for i in range(len(points)):
        a,b=points[i],points[j]
        if ((a.y()>p.y())!=(b.y()>p.y()) and
                p.x()<(b.x()-a.x())*(p.y()-a.y())/(b.y()-a.y())+a.x()):
            on=not on
        j=i
    return on


class Native3DViewport(QWidget):
    picked=pyqtSignal(int, object)
    dragged=pyqtSignal(float,float)
    camera_moved=pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(430,350)
        self.setMouseTracking(True)
        self.scene={}
        self.object_index=-1
        self.mode="Object"
        self.selection=None
        self.yaw=-42.
        self.pitch=27.
        self.distance=75.
        self.frame=1
        self.pan=[0.,0.]
        self._mouse=None
        self._button=None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_scene(self, scene:dict, object_index=-1, mode="Object", selection=None):
        self.scene=scene
        self.object_index=object_index
        self.mode=mode
        self.selection=selection
        self.update()

    def _project(self,v):
        yaw=math.radians(self.yaw)
        pitch=math.radians(self.pitch)
        x,y,z=v
        horiz=x*math.cos(yaw)-y*math.sin(yaw)
        depth=x*math.sin(yaw)+y*math.cos(yaw)
        vert=z*math.cos(pitch)-depth*math.sin(pitch)
        depth=z*math.sin(pitch)+depth*math.cos(pitch)
        scale=min(self.width(),self.height())/self.distance
        return QPointF(self.width()/2+(horiz-self.pan[0])*scale,
                       self.height()/2-(vert-self.pan[1])*scale),depth

    def _world(self,obj,mesh):
        loc=obj.get("location",[0,0,0])
        scale=obj.get("scale",[1,1,1])
        angles=obj.get("rotation",[0,0,0])
        return [[loc[k]+_rotate([v[i]*scale[i] for i in range(3)],angles)[k]
                 for k in range(3)] for v in mesh["vertices"]]

    def _project_object(self,obj):
        obj=object_at_frame(obj,self.frame)
        if obj["type"]=="mesh":
            mesh=validate_mesh(obj["mesh"])
        elif obj["type"] in PRIMITIVES:
            mesh=PRIMITIVES[obj["type"]]()
        else:
            return None,None,None
        world=self._world(obj,mesh)
        pts=[self._project(v) for v in world]
        return mesh,[p[0] for p in pts],[p[1] for p in pts]

    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(),QColor("#111a29"))
        # Light ground-plane orientation marks: no fake render.
        for k in range(-10,11):
            a=self._project([k,-10,0])[0];b=self._project([k,10,0])[0]
            c=self._project([-10,k,0])[0];d=self._project([10,k,0])[0]
            p.setPen(QPen(QColor("#283347"),1))
            p.drawLine(a,b);p.drawLine(c,d)
        for axis,paint in (([4,0,0],"#d96b78"),([0,4,0],"#7ace9b"),
                           ([0,0,4],"#68a5f0")):
            p.setPen(QPen(QColor(paint),2))
            p.drawLine(self._project([0,0,0])[0],self._project(axis)[0])
        faces=[]
        objects=self.scene.get("objects",[])
        for oid,obj in enumerate(objects):
            mesh,points,depths=self._project_object(obj)
            if mesh is None:
                continue
            material=obj.get("material",{})
            color=material.get("color",[.36,.54,.7,1])
            r,g,b=[max(0,min(255,round(float(t)*255))) for t in color[:3]]
            for fid,face in enumerate(mesh["faces"]):
                poly=[points[i] for i in face]
                if all(not math.isfinite(z) for z in [v.x() for v in poly]):
                    continue
                z=sum(depths[i] for i in face)/len(face)
                faces.append((z,oid,fid,poly,mesh,points,(r,g,b)))
        # Painter's order: farther polygons first.
        faces.sort(key=lambda x:x[0],reverse=True)
        for _,oid,fid,polygon,mesh,points,rgb in faces:
            selected=oid==self.object_index
            active=selected and self.mode=="Face" and self.selection==fid
            fill=QColor(*rgb)
            fill.setAlpha(145 if selected else 115)
            if active:fill=QColor(255,181,69,205)
            p.setBrush(QBrush(fill))
            p.setPen(QPen(QColor("#fff1b0" if active else
                                 "#729cc6" if selected else "#41556c"),
                          2 if active else 1))
            p.drawPolygon(QPolygonF(polygon))
        if 0<=self.object_index<len(objects):
            mesh,points,depths=self._project_object(objects[self.object_index])
            if mesh:
                if self.mode=="Vertex":
                    for n,pos in enumerate(points):
                        selected=n==self.selection
                        p.setPen(QPen(QColor("#161616"),1))
                        p.setBrush(QColor("#ffe195" if selected else "#62c8ef"))
                        radius=6 if selected else 3
                        p.drawEllipse(pos,radius,radius)
                if self.mode=="Edge":
                    for face_index,face in enumerate(mesh["faces"]):
                        for edge_index,a in enumerate(face):
                            b=face[(edge_index+1)%len(face)]
                            active=self.selection==(face_index,edge_index)
                            if active:
                                p.setPen(QPen(QColor("#ffce65"),4))
                                p.drawLine(points[a],points[b])
        p.setPen(QColor("#c2d6f0"))
        p.drawText(12,23,f"TTG Native 3D · {self.mode} mode · drag selected part · wheel zoom")
        p.drawText(12,self.height()-12,"Left: select/move  |  Right: orbit  |  Middle: pan  |  X/Y/Z axes")
        p.end()

    def _hit(self,pos):
        arr=self.scene.get("objects",[])
        if self.mode in ("Vertex","Edge","Face") and 0<=self.object_index<len(arr):
            mesh,pts,depth=self._project_object(arr[self.object_index])
            if mesh:
                if self.mode=="Vertex":
                    matches=[(math.hypot(pos.x()-x.x(),pos.y()-x.y()),i)
                             for i,x in enumerate(pts)]
                    d,i=min(matches,default=(float("inf"),None))
                    return self.object_index,i if d<=13 else None
                if self.mode=="Edge":
                    matches=[]
                    for fi,f in enumerate(mesh["faces"]):
                        for ei,a in enumerate(f):
                            b=f[(ei+1)%len(f)]
                            matches.append((_distance_to_segment(pos,pts[a],pts[b]),(fi,ei)))
                    d,index=min(matches,default=(float("inf"),None))
                    return self.object_index,index if d<=12 else None
                if self.mode=="Face":
                    matches=[(sum(depth[i] for i in f)/len(f), fi)
                             for fi,f in enumerate(mesh["faces"])
                             if _inside(pos,[pts[i] for i in f])]
                    if matches:
                        return self.object_index,min(matches,key=lambda q:q[0])[1]
                    return self.object_index,None
        matches=[]
        for oid,obj in enumerate(arr):
            mesh,pts,depth=self._project_object(obj)
            if mesh:
                for face in mesh["faces"]:
                    if _inside(pos,[pts[i] for i in face]):
                        matches.append((sum(depth[i] for i in face)/len(face),oid))
        return (min(matches,key=lambda x:x[0])[1],None) if matches else (-1,None)

    def mousePressEvent(self,event):
        self._mouse=event.position()
        self._button=event.button()
        if self._button==Qt.MouseButton.LeftButton:
            oid,component=self._hit(event.position())
            self.picked.emit(oid,component)

    def mouseMoveEvent(self,event):
        if self._mouse is None:return
        dx=event.position().x()-self._mouse.x()
        dy=event.position().y()-self._mouse.y()
        if self._button==Qt.MouseButton.RightButton:
            self.yaw=(self.yaw+dx*.55)%360
            self.pitch=max(-89,min(89,self.pitch+dy*.45))
            self.camera_moved.emit()
        elif self._button==Qt.MouseButton.MiddleButton:
            scale=min(self.width(),self.height())/self.distance
            self.pan[0]-=dx/scale
            self.pan[1]+=dy/scale
            self.camera_moved.emit()
        elif self._button==Qt.MouseButton.LeftButton and self.object_index>=0:
            scale=min(self.width(),self.height())/self.distance
            self.dragged.emit(dx/scale,-dy/scale)
        self._mouse=event.position()
        self.update()

    def mouseReleaseEvent(self,event):
        self._mouse=None
        self._button=None

    def wheelEvent(self,event):
        self.distance=max(8,min(300,self.distance *
                     (0.85 if event.angleDelta().y()>0 else 1.17)))
        self.update()


class Native3DModeler(QWidget):
    """Visual modeling surface editing the SAME JSON scene as Blender backend."""
    scene_changed=pyqtSignal(object)

    def __init__(self,scene:dict,parent=None):
        super().__init__(parent)
        self.scene=deepcopy(validate_scene(scene))
        self.selected=0
        self.component=None
        self._undo=[]
        self._redo=[]
        self._syncing=False
        body=QHBoxLayout(self)
        left=QVBoxLayout()
        self.objects=QListWidget()
        self.objects.setMinimumWidth(150)
        self.objects.currentRowChanged.connect(self.select_object)
        left.addWidget(QLabel("Scene hierarchy"))
        left.addWidget(self.objects,1)
        self.add_kind=QComboBox()
        for kind in PRIMITIVES:
            self.add_kind.addItem(kind)
        left.addWidget(self.add_kind)
        add=QPushButton("Add Primitive")
        add.clicked.connect(self.add_primitive)
        left.addWidget(add)
        duplicate=QPushButton("Duplicate Object")
        duplicate.clicked.connect(self.duplicate)
        left.addWidget(duplicate)
        remove=QPushButton("Delete Object")
        remove.clicked.connect(self.delete_object)
        left.addWidget(remove)
        self.mode=QComboBox()
        self.mode.addItems(["Object","Vertex","Edge","Face"])
        self.mode.currentTextChanged.connect(self.change_mode)
        left.addWidget(QLabel("Selection mode"))
        left.addWidget(self.mode)
        button_row=QHBoxLayout()
        undo=QPushButton("Undo")
        redo=QPushButton("Redo")
        undo.clicked.connect(self.undo)
        redo.clicked.connect(self.redo)
        button_row.addWidget(undo);button_row.addWidget(redo)
        left.addLayout(button_row)
        body.addLayout(left,1)

        self.viewport=Native3DViewport()
        self.viewport.picked.connect(self.pick)
        self.viewport.dragged.connect(self.drag)
        body.addWidget(self.viewport,4)

        sidebar=QWidget()
        sidebar.setMinimumWidth(200)
        properties=QVBoxLayout(sidebar)
        properties.addWidget(QLabel("Selected geometry"))
        self.detail=QLabel("No selection")
        self.detail.setWordWrap(True)
        properties.addWidget(self.detail)
        self.transform_boxes={}
        for field,title,default in (("location","Position",0),
                                    ("rotation","Rotation °",0),
                                    ("scale","Scale",1)):
            properties.addWidget(QLabel(title))
            triple=QHBoxLayout()
            spins=[]
            for axis in "XYZ":
                spin=QDoubleSpinBox()
                spin.setRange(.001 if field=="scale" else -2000,
                              100 if field=="scale" else 2000)
                spin.setDecimals(3)
                spin.setSingleStep(.1 if field!="rotation" else 5)
                spin.setValue(default)
                spin.setPrefix(axis+":")
                spin.valueChanged.connect(self._transform_change)
                triple.addWidget(spin)
                spins.append(spin)
            properties.addLayout(triple)
            self.transform_boxes[field]=spins
        properties.addWidget(QLabel("Object animation"))
        self.frame_control=QSpinBox()
        self.frame_control.setRange(1,int(self.scene.get("frames",1)))
        self.frame_control.setValue(1)
        self.frame_control.setToolTip("Scrub actual object pose/keyframes in viewport")
        self.frame_control.valueChanged.connect(self.seek_animation)
        properties.addWidget(self.frame_control)
        keybuttons=QHBoxLayout()
        keyadd=QPushButton("Key Pose")
        keyremove=QPushButton("Delete Key")
        keyadd.clicked.connect(self.key_pose)
        keyremove.clicked.connect(self.remove_pose)
        keybuttons.addWidget(keyadd)
        keybuttons.addWidget(keyremove)
        properties.addLayout(keybuttons)
        properties.addWidget(QLabel("PBR material"))
        self.material_boxes={}
        for field,limit,default in (("metallic",1.,0.),("roughness",1.,.4),
                                    ("transmission",1.,0.),("emission_strength",5.,0.)):
            spin=QDoubleSpinBox()
            spin.setRange(0,limit)
            spin.setSingleStep(.05)
            spin.setValue(default)
            spin.valueChanged.connect(self._material_change)
            properties.addWidget(QLabel(field.title()))
            properties.addWidget(spin)
            self.material_boxes[field]=spin
        color_button=QPushButton("Set PBR Base Color")
        color_button.clicked.connect(self.choose_material_color)
        properties.addWidget(color_button)

        properties.addWidget(QLabel("Render camera"))
        self.camera_controls={}
        for field,minimum,maximum in (("lens",12,160),("orbit_degrees",-720,720)):
            spin=QDoubleSpinBox()
            spin.setRange(minimum,maximum)
            spin.setValue(float(self.scene["camera"].get(field,48 if field=="lens" else 0)))
            spin.valueChanged.connect(self.change_camera)
            properties.addWidget(QLabel(field.replace("_"," ").title()))
            properties.addWidget(spin)
            self.camera_controls[field]=spin
        self.camera_position=[]
        for axis in range(3):
            spin=QDoubleSpinBox()
            spin.setRange(-2000,2000)
            spin.setValue(self.scene["camera"]["location"][axis])
            spin.valueChanged.connect(self.change_camera)
            self.camera_position.append(spin)
        properties.addWidget(QLabel("Camera position XYZ"))
        camera_row=QHBoxLayout()
        for spin in self.camera_position: camera_row.addWidget(spin)
        properties.addLayout(camera_row)

        properties.addWidget(QLabel("Studio lighting"))
        self.light_picker=QComboBox()
        self.light_picker.currentIndexChanged.connect(self._light_selected)
        properties.addWidget(self.light_picker)
        self.light_energy=QDoubleSpinBox()
        self.light_energy.setRange(0,10000)
        self.light_energy.setSingleStep(50)
        self.light_energy.valueChanged.connect(self.change_light)
        properties.addWidget(QLabel("Light energy"))
        properties.addWidget(self.light_energy)
        light_row=QHBoxLayout()
        create_light=QPushButton("Add Light")
        create_light.clicked.connect(self.add_light)
        delete_light=QPushButton("Delete Light")
        delete_light.clicked.connect(self.remove_light)
        light_row.addWidget(create_light)
        light_row.addWidget(delete_light)
        properties.addLayout(light_row)

        convert=QPushButton("Convert to Editable Mesh")
        convert.clicked.connect(self.to_mesh)
        properties.addWidget(convert)
        delta=QHBoxLayout()
        self.delta=QDoubleSpinBox()
        self.delta.setRange(-100,100)
        self.delta.setValue(.25)
        self.delta.setSingleStep(.1)
        delta.addWidget(QLabel("Delta"))
        delta.addWidget(self.delta)
        properties.addLayout(delta)
        for name,action in (
            ("Move Selection +X",lambda:self.move_component(self.delta.value(),0,0)),
            ("Move Selection +Y",lambda:self.move_component(0,self.delta.value(),0)),
            ("Move Selection +Z",lambda:self.move_component(0,0,self.delta.value())),
            ("Extrude Selected Face",self.extrude),
            ("Subdivide Mesh",self.subdivide_mesh),
            ("Delete Selected Face",self.delete_face),
        ):
            btn=QPushButton(name);btn.clicked.connect(action)
            properties.addWidget(btn)
        properties.addWidget(QLabel("Advanced mesh sculpting"))
        self.sculpt_mode=QComboBox()
        self.sculpt_mode.addItems(["inflate","deflate","smooth"])
        properties.addWidget(self.sculpt_mode)
        self.sculpt_radius=QDoubleSpinBox()
        self.sculpt_radius.setRange(.01,50)
        self.sculpt_radius.setValue(2.5)
        self.sculpt_strength=QDoubleSpinBox()
        self.sculpt_strength.setRange(.01,2)
        self.sculpt_strength.setValue(.1)
        properties.addWidget(QLabel("Brush radius"))
        properties.addWidget(self.sculpt_radius)
        properties.addWidget(QLabel("Brush strength"))
        properties.addWidget(self.sculpt_strength)
        sculpt_button=QPushButton("Sculpt Selected Vertex")
        sculpt_button.clicked.connect(self.apply_sculpt)
        properties.addWidget(sculpt_button)

        properties.addWidget(QLabel("UV face-corner editing"))
        self.uv_axis=QComboBox()
        self.uv_axis.addItems(["z","x","y"])
        properties.addWidget(self.uv_axis)
        self.uv_u=QDoubleSpinBox()
        self.uv_v=QDoubleSpinBox()
        for spin in (self.uv_u,self.uv_v):
            spin.setRange(-20,20)
            spin.setSingleStep(.05)
        uvs=QHBoxLayout()
        uvs.addWidget(self.uv_u)
        uvs.addWidget(self.uv_v)
        properties.addLayout(uvs)
        for label,fn in (
            ("Project UV Coordinates",self.project_uv),
            ("Shift UV by U / V",self.shift_uv),
            ("Set Selected Face Corner UV",self.edit_uv_corner),
        ):
            button=QPushButton(label)
            button.clicked.connect(fn)
            properties.addWidget(button)

        properties.addWidget(QLabel("Blender UV solver (executed during Blender render)"))
        self.advanced_uv_method=QComboBox()
        self.advanced_uv_method.addItems(["SMART_PROJECT","ANGLE_BASED","CONFORMAL"])
        properties.addWidget(self.advanced_uv_method)
        uv_solve=QPushButton("Use Genuine Blender UV Unwrap")
        uv_solve.clicked.connect(self.use_blender_unwrap)
        properties.addWidget(uv_solve)

        properties.addWidget(QLabel("Rig and skin weights"))
        self.rig_bone=QComboBox()
        properties.addWidget(self.rig_bone)
        for label,fn in (
            ("Add Rig Bone",self.make_rig_bone),
            ("Weight Selected Vertex",self.weight_vertex),
            ("Key Selected Bone Rotation",self.key_bone),
        ):
            button=QPushButton(label);button.clicked.connect(fn)
            properties.addWidget(button)

        properties.addWidget(QLabel("Object constraints"))
        self.constraint_target=QComboBox()
        self.constraint_type=QComboBox()
        self.constraint_type.addItems(["TRACK_TO","COPY_LOCATION"])
        properties.addWidget(self.constraint_target)
        properties.addWidget(self.constraint_type)
        constrained=QPushButton("Constrain Selected Object")
        constrained.clicked.connect(self.apply_constraint)
        properties.addWidget(constrained)

        properties.addWidget(QLabel("Procedural geometry nodes"))
        self.node_op=QComboBox()
        self.node_op.addItems(["transform","wave"])
        properties.addWidget(self.node_op)
        node_button=QPushButton("Add/Update Node Graph")
        node_button.clicked.connect(self.apply_nodes)
        properties.addWidget(node_button)

        properties.addWidget(QLabel("Professional UV and seam tools"))
        for label,fn in (
            ("Pack UV Face Islands",self.pack_uv),
            ("Mark Selected Face Seams",self.mark_uv_seams),
        ):
            button=QPushButton(label);button.clicked.connect(fn)
            properties.addWidget(button)

        branch_button=QPushButton("Create Two-Branch Geometry Graph")
        branch_button.clicked.connect(self.make_branching_graph)
        properties.addWidget(branch_button)
        properties.addWidget(QLabel("Multiresolution sculpt detail"))
        self.multires_levels=QSpinBox()
        self.multires_levels.setRange(1,3)
        properties.addWidget(self.multires_levels)
        detail_button=QPushButton("Enable Multires Sculpt Levels")
        detail_button.clicked.connect(self.enable_multires)
        properties.addWidget(detail_button)
        adapt=QPushButton("Adaptive Local Topology Sculpt")
        adapt.clicked.connect(self.adaptive_sculpt)
        properties.addWidget(adapt)

        topology_stroke=QPushButton("Multi-Dab Adaptive Sculpt Stroke")
        topology_stroke.clicked.connect(self.apply_sculpt_stroke)
        properties.addWidget(topology_stroke)

        properties.addWidget(QLabel("Rig weight painting and IK"))
        self.paint_mode=QComboBox()
        self.paint_mode.addItems(["add","subtract","replace"])
        properties.addWidget(self.paint_mode)
        weight_paint=QPushButton("Paint Nearby Vertex Weights")
        weight_paint.clicked.connect(self.paint_weights)
        properties.addWidget(weight_paint)
        self.ik_chain=QSpinBox()
        self.ik_chain.setRange(1,32)
        self.ik_x=QDoubleSpinBox()
        self.ik_y=QDoubleSpinBox()
        self.ik_z=QDoubleSpinBox()
        for spin in (self.ik_x,self.ik_y,self.ik_z):
            spin.setRange(-2000,2000)
        properties.addWidget(QLabel("IK target XYZ / chain"))
        row=QHBoxLayout()
        for spin in (self.ik_x,self.ik_y,self.ik_z,self.ik_chain):
            row.addWidget(spin)
        properties.addLayout(row)
        ik_button=QPushButton("Set IK on Selected Bone")
        ik_button.clicked.connect(self.enable_ik)
        properties.addWidget(ik_button)

        pole=QPushButton("Set IK Pole from XYZ Controls")
        pole.clicked.connect(self.enable_ik_pole)
        properties.addWidget(pole)
        normalize=QPushButton("Normalize Painted Skin Weights")
        normalize.clicked.connect(self.normalize_weights)
        properties.addWidget(normalize)

        properties.addWidget(QLabel("Editable Geometry Node Chain"))
        self.graph_kind=QComboBox()
        self.graph_kind.addItems(["transform","subdivide","wave"])
        properties.addWidget(self.graph_kind)
        graph_button=QPushButton("Append Geometry Graph Node")
        graph_button.clicked.connect(self.append_graph_node)
        properties.addWidget(graph_button)
        self.graph_nodes=QListWidget()
        self.graph_nodes.setMaximumHeight(105)
        properties.addWidget(self.graph_nodes)
        graph_buttons=QHBoxLayout()
        up=QPushButton("Node ↑");down=QPushButton("Node ↓")
        remove=QPushButton("Remove Node")
        up.clicked.connect(lambda:self.move_graph_node(-1))
        down.clicked.connect(lambda:self.move_graph_node(1))
        remove.clicked.connect(self.remove_graph_node)
        for btn in (up,down,remove):graph_buttons.addWidget(btn)
        properties.addLayout(graph_buttons)

        properties.addWidget(QLabel("Extended Blender physics"))
        self.physics_kind=QComboBox()
        self.physics_kind.addItems([
            "CLOTH","COLLISION","SMOKE_DOMAIN","SMOKE_FLOW",
            "LIQUID_DOMAIN","LIQUID_FLOW"])
        properties.addWidget(self.physics_kind)
        physics_button=QPushButton("Set Cloth / Fluid / Smoke Modifier")
        physics_button.clicked.connect(self.apply_extended_physics)
        properties.addWidget(physics_button)

        properties.addWidget(QLabel("Physics simulation"))
        self.rigid_body=QComboBox()
        self.rigid_body.addItems(["ACTIVE","PASSIVE"])
        properties.addWidget(self.rigid_body)
        simulation_button=QPushButton("Enable Rigid-Body Simulation")
        simulation_button.clicked.connect(self.apply_simulation)
        properties.addWidget(simulation_button)

        properties.addStretch(1)
        scroll=QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(265)
        scroll.setWidget(sidebar)
        body.addWidget(scroll,2)
        self.refresh()

    def snapshot(self):
        self._undo.append(deepcopy(self.scene))
        if len(self._undo)>50:self._undo.pop(0)
        self._redo.clear()

    def commit(self):
        validate_scene(self.scene)
        self.refresh()
        self.scene_changed.emit(deepcopy(self.scene))

    def refresh(self):
        self._syncing=True
        try:
            self.objects.clear()
            for obj in self.scene["objects"]:
                self.objects.addItem(obj["id"]+" · "+obj["type"])
            if self.scene["objects"]:
                self.selected=max(0,min(self.selected,len(self.scene["objects"])-1))
                self.objects.setCurrentRow(self.selected)
                obj=self.scene["objects"][self.selected]
                preview=object_at_frame(obj,self.frame_control.value())
                self.detail.setText(f"{obj['id']} · {obj['type']}\\n"
                                   +("Double-click a primitive via Convert to Mesh for topology" if
                                     obj["type"]!="mesh" else
                                     f"{len(obj['mesh']['vertices'])} vertices · "
                                     f"{len(obj['mesh']['faces'])} faces"))
                for field,boxes in self.transform_boxes.items():
                    vals=preview.get(field,[1,1,1] if field=="scale" else [0,0,0])
                    for box,value in zip(boxes,vals):
                        box.setValue(float(value))
                mat=obj.get("material",{})
                for key,box in self.material_boxes.items():
                    box.setValue(float(mat.get(key,.4 if key=="roughness" else 0)))
            for name,spin in self.camera_controls.items():
                spin.setValue(float(self.scene["camera"].get(name,48 if name=="lens" else 0)))
            for box,value in zip(self.camera_position,self.scene["camera"]["location"]):
                box.setValue(float(value))
            selected_light=self.light_picker.currentIndex()
            self.light_picker.clear()
            for i,light in enumerate(self.scene.get("lights",[])):
                self.light_picker.addItem(f"Light {i+1}")
            lights=self.scene.get("lights",[])
            if lights:
                selected_light=max(0,min(selected_light,len(lights)-1))
                self.light_picker.setCurrentIndex(selected_light)
                self.light_energy.setValue(float(lights[selected_light].get("energy",400)))
            targets = [item["id"] for item in self.scene["objects"]
                       if self.scene["objects"] and
                       item["id"] != self.scene["objects"][self.selected]["id"]]
            target_selected = self.constraint_target.currentText()
            self.constraint_target.clear()
            self.constraint_target.addItems(targets)
            if target_selected in targets:
                self.constraint_target.setCurrentText(target_selected)
            bones = self.scene["objects"][self.selected].get("armature",{}).get("bones",[]) if self.scene["objects"] else []
            prior_bone = self.rig_bone.currentText()
            self.rig_bone.clear()
            self.rig_bone.addItems([b["name"] for b in bones])
            if prior_bone in [b["name"] for b in bones]:
                self.rig_bone.setCurrentText(prior_bone)
            selected_graph_row=self.graph_nodes.currentRow()
            self.graph_nodes.clear()
            if self.scene["objects"]:
                geo=self.scene["objects"][self.selected].get("geometry_nodes",{})
                steps=geo.get("steps",[]) if geo.get("operation")=="graph" else []
                self.graph_nodes.addItems([
                    f"{i+1}. {item['type']}" for i,item in enumerate(steps)
                ])
                if steps:self.graph_nodes.setCurrentRow(
                    max(0,min(selected_graph_row,len(steps)-1)))
            self.frame_control.setMaximum(max(1,int(self.scene.get("frames",1))))
            self.viewport.frame=self.frame_control.value()
            self.viewport.set_scene(self.scene,self.selected,self.mode.currentText(),
                                    self.component)
        finally:
            self._syncing=False

    def select_object(self,index):
        if self._syncing or index<0:return
        self.selected=index
        self.component=None
        self.refresh()

    def change_mode(self,mode):
        self.component=None
        if mode in ("Vertex","Face","Edge"):
            self.ensure_mesh()
        self.refresh()

    def ensure_mesh(self):
        if not (0<=self.selected<len(self.scene["objects"])):return False
        obj=self.scene["objects"][self.selected]
        if obj["type"]!="mesh":
            if obj["type"] not in PRIMITIVES:
                return False
            self.snapshot()
            convert_primitive(obj)
            self.commit()
        return True

    def pick(self,index,component):
        if index<0:return
        if index!=self.selected:
            self.selected=index
            self.component=None
            self.refresh()
            return
        self.component=component
        self.viewport.selection=component
        self.viewport.update()

    def drag(self,dx,dy):
        if self.mode.currentText()=="Object":
            self.move_component(dx,dy,0)
        else:
            # View-plane oriented dragging constrained to XY geometry axes.
            self.move_component(dx,dy,0)

    def _selected_vertices(self):
        obj=self.scene["objects"][self.selected]
        if obj["type"]!="mesh" or self.component is None:
            return []
        mesh=obj["mesh"]
        mode=self.mode.currentText()
        if mode=="Vertex":return [self.component]
        if mode=="Edge":return list(select_edge(mesh,*self.component))
        if mode=="Face":return mesh["faces"][self.component].copy()
        return []

    def move_component(self,dx,dy,dz):
        if not 0<=self.selected<len(self.scene["objects"]):return
        obj=self.scene["objects"][self.selected]
        try:
            self.snapshot()
            if self.mode.currentText()=="Object":
                obj["location"]=[obj.get("location",[0,0,0])[i]+v
                                  for i,v in enumerate([dx,dy,dz])]
            else:
                indices=self._selected_vertices()
                if not indices:
                    self._undo.pop()
                    return
                obj["mesh"]=transform_selection(obj["mesh"],indices,[dx,dy,dz])
            self.commit()
        except Exception as exc:
            self.scene=self._undo.pop()
            self.refresh()
            QMessageBox.warning(self,"3D move",str(exc))

    def seek_animation(self,frame):
        if self._syncing:return
        self.viewport.frame=frame
        self.refresh()

    def key_pose(self):
        if not 0<=self.selected<len(self.scene["objects"]):return
        self.snapshot()
        try:
            set_keyframe(self.scene["objects"][self.selected],
                         self.frame_control.value(),
                         max_frame=int(self.scene.get("frames",1)))
            self.commit()
        except Exception as exc:
            self.scene=self._undo.pop()
            self.refresh()
            QMessageBox.warning(self,"3D animation",str(exc))

    def remove_pose(self):
        if not 0<=self.selected<len(self.scene["objects"]):return
        self.snapshot()
        try:
            remove_keyframe(self.scene["objects"][self.selected],
                            self.frame_control.value())
            self.commit()
        except Exception as exc:
            self.scene=self._undo.pop()
            self.refresh()
            QMessageBox.warning(self,"3D animation",str(exc))

    def _transform_change(self):
        if self._syncing:return
        if not 0<=self.selected<len(self.scene["objects"]):return
        self.snapshot()
        obj=self.scene["objects"][self.selected]
        for field,spins in self.transform_boxes.items():
            obj[field]=[box.value() for box in spins]
        if self.frame_control.value()>1 or obj.get("keyframes"):
            try:
                set_keyframe(obj,self.frame_control.value(),
                             max_frame=int(self.scene.get("frames",1)))
            except ValueError as exc:
                self.scene=self._undo.pop()
                self.refresh()
                QMessageBox.warning(self,"3D animation",str(exc))
                return
        self.commit()

    def _material_change(self):
        if self._syncing:return
        if not 0<=self.selected<len(self.scene["objects"]):return
        self.snapshot()
        mat=self.scene["objects"][self.selected].setdefault("material",{})
        for name,spin in self.material_boxes.items():
            mat[name]=spin.value()
        self.commit()

    def choose_material_color(self):
        if not 0<=self.selected<len(self.scene["objects"]):return
        material=self.scene["objects"][self.selected].get("material",{})
        original=material.get("color",[.3,.4,.5,1])
        chosen=QColorDialog.getColor(QColor(
            *[int(max(0,min(255,channel*255))) for channel in original[:3]]
        ),self,"Choose 3D Material Color")
        if not chosen.isValid():return
        self.snapshot()
        self.scene["objects"][self.selected].setdefault("material",{})["color"]=[
            chosen.redF(),chosen.greenF(),chosen.blueF(),original[3]
        ]
        self.commit()

    def change_camera(self):
        if self._syncing:return
        self.snapshot()
        for name,spin in self.camera_controls.items():
            self.scene["camera"][name]=spin.value()
        self.scene["camera"]["location"]=[box.value() for box in self.camera_position]
        self.commit()

    def _light_selected(self,index):
        if self._syncing:return
        self.refresh()

    def change_light(self):
        if self._syncing:return
        index=self.light_picker.currentIndex()
        if not 0<=index<len(self.scene.get("lights",[])):return
        self.snapshot()
        self.scene["lights"][index]["energy"]=self.light_energy.value()
        self.commit()

    def add_light(self):
        if len(self.scene.get("lights",[]))>=12:
            QMessageBox.information(self,"Lights","Maximum 12 lights")
            return
        self.snapshot()
        self.scene.setdefault("lights",[]).append({
            "location":[2.,-2.,4.],
            "color":[1.,1.,1.],"energy":450.,"size":2.
        })
        self.commit()
        self.light_picker.setCurrentIndex(len(self.scene["lights"])-1)

    def remove_light(self):
        index=self.light_picker.currentIndex()
        if not 0<=index<len(self.scene.get("lights",[])):return
        self.snapshot()
        self.scene["lights"].pop(index)
        self.commit()

    def add_primitive(self):
        if len(self.scene["objects"])>=96:
            QMessageBox.warning(self,"3D", "Scene object limit reached")
            return
        kind=self.add_kind.currentText()
        used={x["id"] for x in self.scene["objects"]}
        name="new_"+kind
        i=1
        while name in used:
            i+=1
            name=f"new_{kind}_{i}"
        self.snapshot()
        self.scene["objects"].append({
            "id":name,"type":kind,"location":[0,0,0],
            "rotation":[0,0,0],"scale":[1,1,1],
            "material":{"color":[.2,.57,.78,1],"metallic":.15,"roughness":.35}
        })
        self.selected=len(self.scene["objects"])-1
        self.component=None
        self.commit()

    def duplicate(self):
        if len(self.scene["objects"])>=96:return
        self.snapshot()
        item=deepcopy(self.scene["objects"][self.selected])
        original=item["id"]
        used={o["id"] for o in self.scene["objects"]}
        n=1
        while f"{original}_{n}" in used:n+=1
        item["id"]=f"{original}_{n}"
        item["location"][0]+=0.5
        self.scene["objects"].append(item)
        self.selected=len(self.scene["objects"])-1
        self.commit()

    def delete_object(self):
        if len(self.scene["objects"])<=1:
            QMessageBox.information(self,"3D","At least one scene object must remain")
            return
        self.snapshot()
        deleted=self.scene["objects"].pop(self.selected)["id"]
        for obj in self.scene["objects"]:
            obj["constraints"]=[entry for entry in obj.get("constraints",[])
                                if entry["target"]!=deleted]
        self.selected=max(0,self.selected-1)
        self.component=None
        self.commit()

    def to_mesh(self):
        if self.ensure_mesh():
            self.mode.setCurrentText("Vertex")
            self.refresh()

    def subdivide_mesh(self):
        if not self.ensure_mesh():return
        self.snapshot()
        try:
            obj=self.scene["objects"][self.selected]
            if "armature" in obj:
                raise ValueError("Remove or rebind rig before changing vertex topology")
            obj["mesh"]=subdivide(obj["mesh"])
            if "uv" in obj:
                obj["uv"]=uv_project(obj["mesh"])
            self.component=None
            self.commit()
        except Exception as exc:
            self.scene=self._undo.pop();self.refresh()
            QMessageBox.warning(self,"3D subdivision",str(exc))

    def extrude(self):
        if self.mode.currentText()!="Face" or self.component is None:
            QMessageBox.information(self,"Extrude","Choose Face mode and select a face first")
            return
        self.snapshot()
        try:
            obj=self.scene["objects"][self.selected]
            oldcount=len(obj["mesh"]["faces"])
            if "armature" in obj:
                raise ValueError("Remove or rebind rig before changing vertex topology")
            obj["mesh"]=extrude_face(obj["mesh"],self.component,self.delta.value())
            if "uv" in obj:
                obj["uv"]=uv_project(obj["mesh"])
            self.component=len(obj["mesh"]["faces"])-1
            self.commit()
        except Exception as exc:
            self.scene=self._undo.pop();self.refresh()
            QMessageBox.warning(self,"3D extrusion",str(exc))

    def delete_face(self):
        if self.mode.currentText()!="Face" or self.component is None:
            return
        self.snapshot()
        try:
            obj=self.scene["objects"][self.selected]
            if "armature" in obj:
                raise ValueError("Remove or rebind rig before changing vertex topology")
            obj["mesh"]=delete_faces(obj["mesh"],[self.component])
            if "uv" in obj:
                obj["uv"]=uv_project(obj["mesh"])
            self.component=None
            self.commit()
        except Exception as exc:
            self.scene=self._undo.pop();self.refresh()
            QMessageBox.warning(self,"3D topology",str(exc))

    def _advanced_edit(self, title, make_edit):
        """Atomic scene edits, retaining Undo and Blender-schema validation."""
        self.snapshot()
        try:
            make_edit(self.scene["objects"][self.selected])
            self.commit()
        except Exception as exc:
            self.scene=self._undo.pop()
            self.refresh()
            QMessageBox.warning(self,title,str(exc))

    def apply_sculpt(self):
        if not self.ensure_mesh():return
        selected=self._selected_vertices()
        if not selected:
            QMessageBox.information(self,"Sculpt","Select a vertex/edge/face first")
            return
        def edit(obj):
            obj["mesh"]=sculpt(
                obj["mesh"],selected[0],radius=self.sculpt_radius.value(),
                strength=self.sculpt_strength.value(),mode=self.sculpt_mode.currentText()
            )
        self._advanced_edit("Sculpt",edit)

    def project_uv(self):
        if not self.ensure_mesh():return
        self._advanced_edit("UV Projection",lambda obj: obj.update(
            uv=uv_project(obj["mesh"],axis=self.uv_axis.currentText())
        ))

    def shift_uv(self):
        if not self.ensure_mesh():return
        def edit(obj):
            if "uv" not in obj:raise ValueError("Project UVs first")
            obj["uv"]=uv_transform(obj["uv"],translate=(self.uv_u.value(),self.uv_v.value()))
        self._advanced_edit("UV Editing",edit)

    def edit_uv_corner(self):
        if not self.ensure_mesh():return
        if self.mode.currentText()!="Face" or self.component is None:
            QMessageBox.information(self,"UV","Select a face first")
            return
        def edit(obj):
            if "uv" not in obj:raise ValueError("Project UVs first")
            obj["uv"][self.component][0]=[self.uv_u.value(),self.uv_v.value()]
        self._advanced_edit("UV Corner",edit)

    def make_rig_bone(self):
        if not self.ensure_mesh():return
        def edit(obj):
            existing=obj.get("armature",{}).get("bones",[])
            name=f"Bone_{len(existing)+1}"
            while name in {item["name"] for item in existing}:
                name += "_"
            obj.update(add_bone(obj,name,[0,0,0],[0,0,1+len(existing)*.25],
                                parent=existing[-1]["name"] if existing else None))
        self._advanced_edit("Armature",edit)

    def weight_vertex(self):
        if not self.ensure_mesh():return
        indices=self._selected_vertices()
        bone=self.rig_bone.currentText()
        if not indices or not bone:
            QMessageBox.information(self,"Skinning","Select a vertex and rig bone")
            return
        def edit(obj):
            for vertex in indices:
                obj.update(set_skin_weight(obj,vertex,bone,1.))
        self._advanced_edit("Skin Weight",edit)

    def key_bone(self):
        name=self.rig_bone.currentText()
        if not name:return
        def edit(obj):
            for bone in obj["armature"]["bones"]:
                if bone["name"]==name:
                    frames=bone.setdefault("keyframes",[])
                    pose={"frame":self.frame_control.value(),
                          "rotation":[0.,0.,round(self.delta.value()*20,3)]}
                    frames[:]=[frame for frame in frames if frame["frame"]!=pose["frame"]]
                    frames.append(pose)
                    frames.sort(key=lambda frame:frame["frame"])
                    return
            raise ValueError("Bone no longer exists")
        self._advanced_edit("Rig Animation",edit)

    def apply_constraint(self):
        target=self.constraint_target.currentText()
        if not target:return
        self._advanced_edit("Constraint",lambda obj: obj.update(add_constraint(
            obj,target,kind=self.constraint_type.currentText()
        )))

    def apply_nodes(self):
        if not self.ensure_mesh():return
        self._advanced_edit("Geometry Nodes",lambda obj: obj.update(set_procedural(
            obj,operation=self.node_op.currentText(),offset=[0,0,self.delta.value()]
        )))

    def apply_simulation(self):
        def edit(obj):
            obj.update(set_physics(obj,active=self.rigid_body.currentText()=="ACTIVE"))
        self._advanced_edit("Rigid Body",edit)

    def use_blender_unwrap(self):
        if not self.ensure_mesh():return
        self._advanced_edit("Blender UV Unwrap",lambda obj:obj.update(
            set_uv_unwrap(obj,method=self.advanced_uv_method.currentText())
        ))

    def enable_ik_pole(self):
        if not self.ensure_mesh():return
        name=self.rig_bone.currentText()
        position=[self.ik_x.value(),self.ik_y.value(),self.ik_z.value()]
        self._advanced_edit("IK Pole",lambda obj:obj.update(
            set_ik_pole(obj,name,position)
        ))

    def normalize_weights(self):
        if not self.ensure_mesh():return
        self._advanced_edit("Normalize Weights",lambda obj:obj.update(
            normalize_skin_weights(obj)
        ))

    def make_branching_graph(self):
        if not self.ensure_mesh():return
        # Edits real Blender DAG branches, with an actual Join Geometry node.
        offset=self.delta.value()
        nodes=[
          {"id":"left","type":"transform","inputs":["input"],"offset":[offset,0,0]},
          {"id":"right","type":"transform","inputs":["input"],"offset":[-offset,0,0]},
          {"id":"merged","type":"join","inputs":["left","right"]},
        ]
        self._advanced_edit("Branch Geometry Graph",lambda obj:obj.update(
            set_geometry_dag(obj,nodes,"merged")
        ))

    def apply_sculpt_stroke(self):
        if not self.ensure_mesh():return
        chosen=self._selected_vertices()
        if not chosen:
            QMessageBox.information(self,"Sculpt Stroke","Select a mesh vertex first")
            return
        self._advanced_edit("Adaptive Sculpt Stroke",lambda obj:obj.update(
            mesh=sculpt_stroke(obj,chosen,radius=self.sculpt_radius.value(),
                               strength=self.sculpt_strength.value())
        ))

    def adaptive_sculpt(self):
        if not self.ensure_mesh():return
        selected=self._selected_vertices()
        if not selected:
            QMessageBox.information(self,"Topology Sculpt",
                                    "Select a vertex, edge or face first")
            return
        def edit(obj):
            if any(key in obj for key in ("uv","uv_seams","armature","sculpt_detail")):
                raise ValueError(
                    "Adaptive topology would invalidate UVs/skin; use it before "
                    "UV mapping, weights or multires editing")
            obj["mesh"]=adaptive_sculpt(
                obj["mesh"],selected[0],radius=self.sculpt_radius.value(),
                strength=self.sculpt_strength.value())
        self._advanced_edit("Adaptive Sculpt",edit)

    def move_graph_node(self,step):
        index=self.graph_nodes.currentRow()
        if index<0 or not self.ensure_mesh():return
        def edit(obj):
            graph=obj.get("geometry_nodes",{})
            if graph.get("operation")!="graph":return
            items=list(graph["steps"])
            target=index+step
            if not 0<=target<len(items):return
            items[index],items[target]=items[target],items[index]
            obj.update(set_geometry_graph(obj,items))
        self._advanced_edit("Reorder Nodes",edit)
        self.graph_nodes.setCurrentRow(index+step)

    def remove_graph_node(self):
        index=self.graph_nodes.currentRow()
        if index<0 or not self.ensure_mesh():return
        def edit(obj):
            graph=obj.get("geometry_nodes",{})
            if graph.get("operation")!="graph":return
            steps=[x for i,x in enumerate(graph["steps"]) if i!=index]
            if steps:obj.update(set_geometry_graph(obj,steps))
            else:obj.pop("geometry_nodes",None)
        self._advanced_edit("Remove Node",edit)

    def pack_uv(self):
        if not self.ensure_mesh():return
        self._advanced_edit("Pack UV",lambda obj:obj.update(
            uv=unwrap_pack_faces(obj["mesh"])
        ))

    def mark_uv_seams(self):
        if not self.ensure_mesh():return
        if self.mode.currentText()!="Face" or self.component is None:
            QMessageBox.information(self,"UV Seams","Select a face first")
            return
        def edit(obj):
            face=obj["mesh"]["faces"][self.component]
            existing=obj.get("uv_seams",[])
            seams={tuple(sorted(x)) for x in existing}
            for index,value in enumerate(face):
                seams.add(tuple(sorted((value,face[(index+1)%len(face)]))))
            if "uv" not in obj:
                obj["uv"]=unwrap_pack_faces(obj["mesh"])
            obj.update(assign_uv_seams(obj,[list(x) for x in sorted(seams)]))
        self._advanced_edit("UV Seams",edit)

    def enable_multires(self):
        if not self.ensure_mesh():return
        self._advanced_edit("Multires",lambda obj:obj.update(
            set_multires(obj,levels=self.multires_levels.value())
        ))

    def paint_weights(self):
        if not self.ensure_mesh():return
        selected=self._selected_vertices()
        bone=self.rig_bone.currentText()
        if not selected or not bone:
            QMessageBox.information(self,"Paint Weights","Select vertex and rig bone")
            return
        self._advanced_edit("Paint Weights",lambda obj:obj.update(
            paint_skin_weights(obj,vertex=selected[0],bone=bone,
                               radius=self.sculpt_radius.value(),
                               strength=self.sculpt_strength.value(),
                               mode=self.paint_mode.currentText())
        ))

    def enable_ik(self):
        bone=self.rig_bone.currentText()
        if not bone:return
        coords=[s.value() for s in (self.ik_x,self.ik_y,self.ik_z)]
        self._advanced_edit("IK",lambda obj:obj.update(
            set_bone_ik(obj,bone,coords,self.ik_chain.value())
        ))

    def append_graph_node(self):
        if not self.ensure_mesh():return
        kind=self.graph_kind.currentText()
        def edit(obj):
            geo=obj.get("geometry_nodes",{})
            current=geo.get("steps",[]) if geo.get("operation")=="graph" else []
            step=({"type":"transform","offset":[0,0,self.delta.value()]}
                  if kind=="transform" else
                  {"type":"subdivide","level":1} if kind=="subdivide" else
                  {"type":"wave","amplitude":abs(self.delta.value())})
            obj.update(set_geometry_graph(obj,[*current,step]))
        self._advanced_edit("Geometry Graph",edit)

    def apply_extended_physics(self):
        if not self.ensure_mesh():return
        kind=self.physics_kind.currentText()
        self._advanced_edit("Physics",lambda obj:obj.update(
            set_extended_physics(obj,kind=kind)
        ))

    def undo(self):
        if not self._undo:return
        self._redo.append(deepcopy(self.scene))
        self.scene=self._undo.pop()
        self.component=None
        self.commit_nohistory()

    def redo(self):
        if not self._redo:return
        self._undo.append(deepcopy(self.scene))
        self.scene=self._redo.pop()
        self.component=None
        self.commit_nohistory()

    def commit_nohistory(self):
        validate_scene(self.scene)
        self.refresh()
        self.scene_changed.emit(deepcopy(self.scene))

    def set_scene(self,scene):
        self.scene=deepcopy(validate_scene(scene))
        self.selected=0
        self.component=None
        self._undo.clear()
        self._redo.clear()
        self.refresh()
