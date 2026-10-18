"""Creative Studio 3D Lab: standalone editor UI for external Blender renderer.

No Blender source is imported; background worker communicates via scene JSON.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import uuid

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
                             QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout)

from ttg_blender_engine import blender_status, isp_box_scene, render_scene, validate_scene


class BlenderRenderWorker(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, scene: dict, directory: Path):
        super().__init__()
        self.scene_spec = scene
        self.directory = directory

    def run(self):
        try:
            self.succeeded.emit(render_scene(self.scene_spec, self.directory))
        except Exception as exc:
            self.failed.emit(str(exc))


class Studio3DLab(QDialog):
    """Parametric scene editing, renderer selection, and Studio media import."""

    def __init__(self, import_image=None, import_video=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Creative Studio · 3D Lab (Blender backend)")
        self.resize(940,700)
        self.import_image=import_image
        self.import_video=import_video
        self._worker=None
        self._result=None
        root=QVBoxLayout(self)
        self.status=QLabel()
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self._refresh_status()
        root.addWidget(QLabel(
            "3D scene: edit objects, locations, material metallic/roughness, "
            "lights and camera as JSON. The resulting .blend stays editable in Blender."
        ))
        self.editor=QPlainTextEdit(json.dumps(isp_box_scene(),indent=2))
        self.editor.setToolTip("Editable 3D scene schema; no scripts or untrusted code")
        root.addWidget(self.editor,2)
        controls=QHBoxLayout()
        self.engine=QComboBox()
        self.engine.addItems(["BLENDER_EEVEE_NEXT","CYCLES"])
        controls.addWidget(QLabel("Render engine"))
        controls.addWidget(self.engine)
        self.samples=QSpinBox()
        self.samples.setRange(1,512)
        self.samples.setValue(32)
        controls.addWidget(QLabel("Samples"))
        controls.addWidget(self.samples)
        self.frames=QSpinBox()
        self.frames.setRange(1,240)
        self.frames.setValue(72)
        controls.addWidget(QLabel("Frames (1=still)"))
        controls.addWidget(self.frames)
        root.addLayout(controls)
        actions=QHBoxLayout()
        preset=QPushButton("Reset ISP Box Scene")
        preset.clicked.connect(self.reset)
        save=QPushButton("Save Editable Scene JSON")
        save.clicked.connect(self.save_scene)
        load=QPushButton("Load Scene JSON")
        load.clicked.connect(self.load_scene)
        preview=QPushButton("Render Still · Blender")
        preview.clicked.connect(lambda:self.start_render(still=True))
        movie=QPushButton("Render Cinematic · Blender")
        movie.clicked.connect(lambda:self.start_render(still=False))
        for b in (preset,save,load,preview,movie):
            actions.addWidget(b)
        root.addLayout(actions)
        self.poster=QLabel("No Blender render yet")
        self.poster.setMinimumHeight(175)
        self.poster.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.poster,1)
        delivered=QHBoxLayout()
        self.image_button=QPushButton("Add Rendered Image to Studio")
        self.image_button.clicked.connect(self.use_image)
        self.video_button=QPushButton("Add Rendered Video to Studio")
        self.video_button.clicked.connect(self.use_video)
        self.blend_button=QPushButton("Open Editable .blend in Blender")
        self.blend_button.clicked.connect(self.open_blend)
        self.image_button.setEnabled(False)
        self.video_button.setEnabled(False)
        self.blend_button.setEnabled(False)
        for b in (self.image_button,self.video_button,self.blend_button):
            delivered.addWidget(b)
        root.addLayout(delivered)

    def _refresh_status(self):
        available=blender_status()
        self.status.setText(
            (f"Blender ready: {available['version']}" if available["available"] else
             "Blender not installed. Install Blender separately and set "
             "TTG_STUDIO_BLENDER_EXECUTABLE. No source checkout or model weights "
             "are needed on KRATOS.")
        )

    def reset(self):
        self.editor.setPlainText(json.dumps(isp_box_scene(),indent=2))

    def _scene(self, *, still=False):
        scene=json.loads(self.editor.toPlainText())
        scene["engine"]=self.engine.currentText()
        scene["samples"]=self.samples.value()
        scene["frames"]=1 if still else self.frames.value()
        return validate_scene(scene)

    def save_scene(self):
        try:
            scene=self._scene()
            target,_=QFileDialog.getSaveFileName(
                self,"Save editable 3D scene","scene.ttg3d.json","Creative Studio 3D (*.json)")
            if not target:return
            Path(target).write_text(json.dumps(scene,indent=2),encoding="utf-8")
            self.status.setText("Saved editable Creative Studio 3D scene specification")
        except Exception as exc:
            QMessageBox.warning(self,"3D Scene",str(exc))

    def load_scene(self):
        path,_=QFileDialog.getOpenFileName(self,"Load 3D scene","","3D scenes (*.json)")
        if not path:return
        try:
            data=validate_scene(json.loads(Path(path).read_text(encoding="utf-8")))
            self.editor.setPlainText(json.dumps(data,indent=2))
            self.frames.setValue(data.get("frames",1))
            self.samples.setValue(data.get("samples",32))
            self.engine.setCurrentText(data.get("engine","BLENDER_EEVEE_NEXT"))
        except Exception as exc:
            QMessageBox.warning(self,"3D Scene",str(exc))

    def start_render(self, *, still=False):
        if self._worker and self._worker.isRunning():
            self.status.setText("A 3D render is already running")
            return
        try:
            scene=self._scene(still=still)
        except Exception as exc:
            QMessageBox.warning(self,"Invalid 3D Scene",str(exc))
            return
        if not blender_status()["available"]:
            self._refresh_status()
            return
        parent=QFileDialog.getExistingDirectory(self,"Choose 3D render parent folder")
        if not parent:return
        destination=Path(parent)/("ttg-blender-scene-"+uuid.uuid4().hex[:10])
        self._result=None
        self._worker=BlenderRenderWorker(scene,destination)
        self._worker.succeeded.connect(self._done)
        self._worker.failed.connect(self._failed)
        self.status.setText("Blender rendering via separate process. UI remains responsive.")
        self._worker.start()

    def _done(self, result):
        self._result=result
        pix=QPixmap(result["poster"])
        if pix.isNull():
            self._failed("Blender output was not a readable image")
            return
        self.poster.setPixmap(pix.scaled(self.poster.size(),Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation))
        self.image_button.setEnabled(True)
        self.video_button.setEnabled(bool(result.get("film")))
        self.blend_button.setEnabled(True)
        self.status.setText("Blender produced editable .blend and verified physical render files.")

    def _failed(self, message):
        self.status.setText("3D render failed (no success claimed): "+message)

    def use_image(self):
        if self._result and self.import_image:
            self.import_image(Path(self._result["poster"]))

    def use_video(self):
        if self._result and self._result.get("film") and self.import_video:
            self.import_video(Path(self._result["film"]))

    def open_blend(self):
        if not self._result:
            return
        status=blender_status()
        if not status["available"]:
            self._refresh_status()
            return
        subprocess.Popen([status["executable"],self._result["blend"]])

    def closeEvent(self,event):
        if self._worker and self._worker.isRunning():
            self.status.setText("3D rendering active; finish the render before closing.")
            event.ignore()
            return
        super().closeEvent(event)
