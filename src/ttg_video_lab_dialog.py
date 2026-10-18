"""Standalone Creative Studio video inspector and clip import dialog.

All media decoding runs off the Qt GUI thread. No model is installed or
invoked by default; this is actual FFmpeg frame inspection.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from ttg_video_media import probe_video, video_frame


class VideoInspectionThread(QThread):
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, filename: str):
        super().__init__()
        self.filename = filename

    def run(self) -> None:
        try:
            info = probe_video(self.filename)
            end = info["duration"]
            frames: list[bytes] = []
            for ratio in (.15, .5, .85):
                position = min(end - .001, max(0, end * ratio))
                image = video_frame(self.filename, position)
                image.thumbnail((320, 180), Image.Resampling.LANCZOS)
                buffer = BytesIO()
                image.convert("RGB").save(buffer, format="JPEG", quality=86)
                frames.append(buffer.getvalue())
            self.completed.emit((info, frames))
        except Exception as exc:
            self.failed.emit(str(exc))


class VideoSemanticThread(QThread):
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, filename: str, model_id: str, question: str):
        super().__init__()
        self.filename = filename
        self.model_id = model_id
        self.question = question

    def run(self) -> None:
        import tempfile
        try:
            from ttg_visual_understanding import LocalVisionServer
            model = LocalVisionServer()
            information = probe_video(self.filename)
            result = []
            with tempfile.TemporaryDirectory(prefix="ttg-local-video-vision-") as tmp:
                for i, ratio in enumerate((.15, .5, .85)):
                    second = min(information["duration"]-.001,
                                 information["duration"]*ratio)
                    frame = video_frame(self.filename, second)
                    dest = Path(tmp)/f"frame_{i}.png"
                    frame.save(dest)
                    description = model.describe(dest, self.model_id, self.question)
                    result.append((round(second, 2), description))
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class VideoLabDialog(QDialog):
    """Analyze clips and select non-destructive import/trim settings."""

    def __init__(self, source: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Creative Studio · Video Lab")
        self.resize(870, 610)
        self.metadata: dict | None = None
        self._worker: VideoInspectionThread | None = None
        self._semantic_worker: VideoSemanticThread | None = None
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Inspect real video frames · trim a clip · add to the Studio timeline"))
        file_bar = QHBoxLayout()
        self.filename = QLineEdit(source)
        self.filename.setPlaceholderText("Choose an MP4, MOV, MKV or WebM")
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse)
        analyze = QPushButton("Inspect Video")
        analyze.clicked.connect(self.inspect)
        self.analyze_button = analyze
        file_bar.addWidget(self.filename, 1)
        file_bar.addWidget(browse)
        file_bar.addWidget(analyze)
        root.addLayout(file_bar)

        thumbs = QHBoxLayout()
        self.previews = []
        for text in ("Start · 15%", "Middle · 50%", "End · 85%"):
            container = QWidget()
            layout = QVBoxLayout(container)
            title = QLabel(text)
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img = QLabel("No frame")
            img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img.setMinimumSize(180, 110)
            layout.addWidget(title)
            layout.addWidget(img, 1)
            thumbs.addWidget(container)
            self.previews.append(img)
        root.addLayout(thumbs)

        self.evidence = QPlainTextEdit()
        self.evidence.setReadOnly(True)
        self.evidence.setPlaceholderText("Clip metadata and actual frame evidence will appear here")
        self.evidence.setMaximumHeight(135)
        root.addWidget(self.evidence)

        vision_bar = QHBoxLayout()
        self.vision_model = QLineEdit()
        self.vision_model.setPlaceholderText("Optional installed local vision model ID")
        self.question = QLineEdit("Describe visible actions and scene changes; state uncertainties")
        self.semantic_button = QPushButton("Describe Scenes · Local Model")
        self.semantic_button.clicked.connect(self.describe_scenes)
        vision_bar.addWidget(self.vision_model, 1)
        vision_bar.addWidget(self.question, 2)
        vision_bar.addWidget(self.semantic_button)
        root.addLayout(vision_bar)

        form = QFormLayout()
        self.project_start = QDoubleSpinBox()
        self.project_start.setRange(0, 600)
        self.project_start.setDecimals(2)
        form.addRow("Start on timeline (seconds)", self.project_start)
        self.trim_in = QDoubleSpinBox()
        self.trim_in.setRange(0, 1800)
        self.trim_in.setDecimals(2)
        form.addRow("Trim from source (seconds)", self.trim_in)
        self.trim_out = QDoubleSpinBox()
        self.trim_out.setRange(0, 1800)
        self.trim_out.setDecimals(2)
        form.addRow("Trim source to (seconds)", self.trim_out)
        self.speed = QDoubleSpinBox()
        self.speed.setRange(.25, 4)
        self.speed.setSingleStep(.25)
        self.speed.setValue(1)
        form.addRow("Playback speed", self.speed)
        self.portable = QCheckBox("Copy media into project assets (uses disk space)")
        self.portable.setChecked(False)
        form.addRow("Portability", self.portable)
        self.import_audio = QCheckBox("Use source audio when available (speed 1×)")
        self.import_audio.setChecked(True)
        form.addRow("Sound", self.import_audio)
        root.addLayout(form)

        bottom = QHBoxLayout()
        self.status = QLabel("Ready for a source video")
        self.add_button = QPushButton("Add Editable Clip")
        self.add_button.setEnabled(False)
        self.add_button.clicked.connect(self.confirm)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        bottom.addWidget(self.status, 1)
        bottom.addWidget(cancel)
        bottom.addWidget(self.add_button)
        root.addLayout(bottom)

    def browse(self):
        selected, _ = QFileDialog.getOpenFileName(
            self, "Select Video", "", "Videos (*.mp4 *.mov *.mkv *.webm)")
        if selected:
            self.filename.setText(selected)
            self.inspect()

    def inspect(self):
        if self._worker is not None and self._worker.isRunning():
            return
        self.add_button.setEnabled(False)
        self.metadata = None
        name = self.filename.text().strip()
        if not name:
            self.status.setText("Choose a video first")
            return
        self.status.setText("Inspecting physical media...")
        self.analyze_button.setEnabled(False)
        self._worker = VideoInspectionThread(name)
        self._worker.completed.connect(self._inspected)
        self._worker.failed.connect(self._failed)
        self._worker.finished.connect(lambda: self.analyze_button.setEnabled(True))
        self._worker.start()

    def _failed(self, message: str):
        self.status.setText("Inspection unavailable")
        self.evidence.setPlainText(message)
        self.add_button.setEnabled(False)

    def _inspected(self, payload):
        info, images = payload
        self.metadata = info
        self.trim_in.setValue(0)
        self.trim_out.setRange(.01, info["duration"])
        self.trim_out.setValue(info["duration"])
        for label, raw in zip(self.previews, images):
            pix = QPixmap()
            if not pix.loadFromData(raw, "JPEG"):
                label.setText("Could not display media frame")
                continue
            label.setPixmap(pix.scaled(260, 145,
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.evidence.setPlainText(
            f"Video: {info['width']}×{info['height']}\n"
            f"Duration: {info['duration']:.3f} seconds\n"
            f"Codec: {info['video_codec']} · FPS: {info['fps']}\n"
            f"Audio streams: {info['audio_streams']}\n"
            f"Source bytes: {info['size_bytes']:,}\n"
            "These are actual local frame samples, not AI-generated descriptions."
        )
        self.status.setText("Inspected · non-destructive timeline import is available")
        self.add_button.setEnabled(True)

    def describe_scenes(self):
        if self.metadata is None:
            self.status.setText("Inspect a video first.")
            return
        name = self.vision_model.text().strip()
        if not name:
            self.status.setText("Specify an actually installed local vision model.")
            return
        if self._semantic_worker and self._semantic_worker.isRunning():
            return
        self.semantic_button.setEnabled(False)
        self.status.setText("Analyzing visible frames with installed local vision model...")
        self._semantic_worker = VideoSemanticThread(
            self.filename.text().strip(), name, self.question.text()[:2000]
        )
        self._semantic_worker.completed.connect(self._described)
        self._semantic_worker.failed.connect(self._semantic_failed)
        self._semantic_worker.finished.connect(
            lambda: self.semantic_button.setEnabled(True)
        )
        self._semantic_worker.start()

    def _described(self, observations):
        descriptions = "\n\n".join(
            f"{second:.2f}s — {description}" for second, description in observations
        )
        self.evidence.appendPlainText(
            "\nLOCAL VISION MODEL · review its claims against the frames\n"
            + descriptions
        )
        self.status.setText("Local model observations ready for human review")

    def _semantic_failed(self, message: str):
        self.status.setText("Local model unavailable; frame measurements remain available.")
        self.evidence.appendPlainText(
            "\nSemantic analysis was not performed: " + message
        )

    def confirm(self):
        if (self.metadata is None or
            self.trim_out.value() <= self.trim_in.value() + .01):
            self.status.setText("Trim end must be later than trim start")
            return
        if self.import_audio.isChecked() and self.speed.value() != 1:
            self.status.setText("Change speed to 1× or disable source audio")
            return
        self.accept()

    def closeEvent(self, event):
        if ((self._worker is not None and self._worker.isRunning()) or
            (self._semantic_worker is not None and self._semantic_worker.isRunning())):
            self.status.setText("Video processing is running; complete before closing")
            event.ignore()
            return
        super().closeEvent(event)


class VideoExportThread(QThread):
    """Render a snapshot outside Qt's event loop; UI remains responsive."""
    completed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, project, asset_root: Path, destination: Path, scratch_root: Path):
        super().__init__()
        self.project = project
        self.asset_root = Path(asset_root)
        self.destination = Path(destination)
        self.scratch_root = Path(scratch_root)

    def run(self) -> None:
        try:
            from ttg_motion_exporter import MotionExporter
            from ttg_canvas_engine import RenderContext
            result = MotionExporter(RenderContext(self.asset_root)).export_mp4(
                self.project, self.destination, self.scratch_root
            )
            self.completed.emit(str(result))
        except Exception as exc:
            self.failed.emit(str(exc))


class VideoTrimDialog(QDialog):
    """Change the timing of an already-imported editable Studio video layer."""

    def __init__(self, properties: dict, source_duration: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Creative Studio · Edit Video Timing")
        root=QVBoxLayout(self)
        self.start = QDoubleSpinBox()
        self.start.setRange(0,600)
        self.start.setValue(float(properties.get("start",0)))
        self.trim_in = QDoubleSpinBox()
        self.trim_in.setDecimals(2)
        self.trim_in.setRange(0,source_duration)
        self.trim_in.setValue(float(properties.get("source_in",0)))
        self.trim_out = QDoubleSpinBox()
        self.trim_out.setDecimals(2)
        self.trim_out.setRange(0.01,source_duration)
        self.trim_out.setValue(float(properties.get("source_out",source_duration)))
        self.speed = QDoubleSpinBox()
        self.speed.setRange(.25,4)
        self.speed.setSingleStep(.25)
        self.speed.setValue(float(properties.get("speed",1)))
        form=QFormLayout()
        for title,control in (("Timeline start (s)",self.start),
                              ("Source in (s)",self.trim_in),
                              ("Source out (s)",self.trim_out),
                              ("Playback speed",self.speed)):
            form.addRow(title,control)
        root.addLayout(form)
        self.validation = QLabel("Edits preserve original media")
        root.addWidget(self.validation)
        actions=QHBoxLayout()
        cancel=QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        okay=QPushButton("Apply Trim")
        okay.clicked.connect(self.confirm)
        actions.addWidget(cancel)
        actions.addWidget(okay)
        root.addLayout(actions)

    def confirm(self):
        if self.trim_out.value() <= self.trim_in.value() + .01:
            self.validation.setText("Source out must exceed source in")
            return
        end=self.start.value()+(self.trim_out.value()-self.trim_in.value())/self.speed.value()
        if end > 600:
            self.validation.setText("Clip exceeds Studio's 600-second timeline")
            return
        self.accept()
