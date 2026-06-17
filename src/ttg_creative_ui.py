#!/usr/bin/env python3
"""PyQt Creative Studio mode widgets."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QMessageBox, QPushButton, QSplitter, QVBoxLayout, QWidget

from ttg_action_engine import ActionEngine
from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_diagram_tools import add_basic_board_callout, add_basic_isp_diagram
from ttg_intro_builder import IntroBuilder
from ttg_motion_exporter import MotionExporter
from ttg_pack_status import PackStatusReader
from ttg_project_schema import TTGProject, make_ttg_intro_project
from ttg_render_plan import RenderPlanner
from ttg_validation import ProjectValidator


class CreativeCanvasPreview(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("creativeCanvasPreview")
        self.setMinimumSize(640, 420)
        layout = QVBoxLayout(self)
        self.preview = QLabel("Create or open a .ttgstudio project")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview)

    def set_image(self, path: str) -> None:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.preview.setText("Preview failed")
            return
        self.preview.setPixmap(pixmap.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.preview.setText("")


class CreativeStudioWidget(QWidget):
    projectChanged = pyqtSignal(object)

    def __init__(self, project_root: str | Path | None = None) -> None:
        super().__init__()
        self.project_root = Path(project_root or Path.cwd())
        self.action = ActionEngine()
        self.validator = ProjectValidator()
        self.planner = RenderPlanner()
        self.pack_reader = PackStatusReader(self.project_root)
        self.project: TTGProject | None = None
        self.project_path: Path | None = None
        self._build_ui()
        self._apply_theme()
        self.show_pack_status()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.new_button = QPushButton("New")
        self.intro_button = QPushButton("Intro Template")
        self.cinematic_intro_button = QPushButton("Cinematic TTG")
        self.isp_button = QPushButton("ISP Diagram")
        self.board_button = QPushButton("Board Callout")
        self.open_button = QPushButton("Open")
        self.save_button = QPushButton("Save")
        self.add_text_button = QPushButton("Add Text")
        self.add_shape_button = QPushButton("Add Shape")
        self.validate_button = QPushButton("Validate")
        self.plan_button = QPushButton("Render Plan")
        self.pack_button = QPushButton("Packs")
        self.render_button = QPushButton("Render Preview")
        self.export_png_button = QPushButton("Export PNG")
        self.export_frames_button = QPushButton("Export Frames")
        for button in [self.new_button, self.intro_button, self.cinematic_intro_button, self.isp_button, self.board_button, self.open_button, self.save_button, self.add_text_button, self.add_shape_button, self.validate_button, self.plan_button, self.pack_button, self.render_button, self.export_png_button, self.export_frames_button]:
            toolbar.addWidget(button)
        toolbar.addStretch()
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.layer_list = QListWidget()
        self.canvas = CreativeCanvasPreview()
        self.properties = QListWidget()
        splitter.addWidget(self.layer_list)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.properties)
        splitter.setSizes([260, 760, 300])
        root.addWidget(splitter, 1)
        self.status_label = QLabel("Creative Studio ready.")
        root.addWidget(self.status_label)

        self.new_button.clicked.connect(self.new_project)
        self.intro_button.clicked.connect(self.load_intro_template)
        self.cinematic_intro_button.clicked.connect(self.load_cinematic_intro)
        self.isp_button.clicked.connect(self.add_isp_diagram)
        self.board_button.clicked.connect(self.add_board_callout)
        self.open_button.clicked.connect(self.open_project)
        self.save_button.clicked.connect(self.save_project)
        self.add_text_button.clicked.connect(self.add_text)
        self.add_shape_button.clicked.connect(self.add_shape)
        self.validate_button.clicked.connect(self.validate_project)
        self.plan_button.clicked.connect(self.show_render_plan)
        self.pack_button.clicked.connect(self.show_pack_status)
        self.render_button.clicked.connect(self.render_preview)
        self.export_png_button.clicked.connect(self.export_png)
        self.export_frames_button.clicked.connect(self.export_frames)
        self.layer_list.currentRowChanged.connect(self._selected_layer_changed)

    def _apply_theme(self) -> None:
        self.setStyleSheet("QWidget{background:#050814;color:#eaf3ff;} QPushButton{background:#182552;color:#f1f7ff;border:1px solid #3f72ff;border-radius:8px;padding:7px;} QListWidget,QFrame{background:#0b1220;border:1px solid #18305f;} QLabel{color:#9fd8ff;}")

    def new_project(self) -> None:
        self.project = self.action.new_project("Untitled TTG Project", "image")
        self.project_path = None
        self.refresh_panels()
        self.render_preview()

    def load_intro_template(self) -> None:
        self.project = make_ttg_intro_project()
        self.project_path = None
        self.refresh_panels()
        self.render_preview()

    def load_cinematic_intro(self) -> None:
        self.project = IntroBuilder().build_ttg_intro()
        self.project_path = None
        self.refresh_panels()
        self.render_preview()

    def add_isp_diagram(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project is None:
            return
        add_basic_isp_diagram(self.project)
        self.refresh_panels()
        self.render_preview()

    def add_board_callout(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project is None:
            return
        add_basic_board_callout(self.project)
        self.refresh_panels()
        self.render_preview()

    def open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open TTG Studio Project", "", "TTG Studio (*.json *.ttgstudio)")
        if not path:
            return
        try:
            self.project = TTGProject.load(path)
            self.project_path = Path(path)
            self.refresh_panels()
            self.render_preview()
        except Exception as exc:
            QMessageBox.critical(self, "Open Project", str(exc))

    def save_project(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project is None:
            return
        if self.project_path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save TTG Studio Project", "project.ttgstudio.json", "TTG Studio (*.json)")
            if not path:
                return
            self.project_path = Path(path)
        self.project.save(self.project_path)
        self.status_label.setText(f"Saved {self.project_path}")

    def add_text(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project is None:
            return
        self.action.add_text(self.project, "THETECHGUY", 120, 120)
        self.refresh_panels()
        self.render_preview()

    def add_shape(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project is None:
            return
        self.action.add_shape(self.project, "rectangle", 160, 220)
        self.refresh_panels()
        self.render_preview()

    def validate_project(self) -> bool:
        if self.project is None:
            self.status_label.setText("No project loaded.")
            return False
        messages = self.validator.validate(self.project, self.project_root)
        warnings = [item for item in messages if item.level == "warning"]
        errors = [item for item in messages if item.level == "error"]
        self.properties.clear()
        if not messages:
            self.properties.addItem("Validation passed")
            self.status_label.setText("Validation passed.")
            return True
        for item in messages:
            self.properties.addItem(f"{item.level.upper()}: {item.message}")
        self.status_label.setText(f"Validation: {len(errors)} errors, {len(warnings)} warnings.")
        if errors:
            QMessageBox.warning(self, "Project Validation", "Fix validation errors before export.")
            return False
        return True

    def show_render_plan(self) -> None:
        if self.project is None:
            return
        plan = self.planner.create_plan(self.project)
        self.properties.clear()
        self.properties.addItem(f"Project: {plan.project_name}")
        self.properties.addItem(f"Canvas: {plan.canvas}")
        for task in plan.tasks:
            self.properties.addItem(f"{task.id}: {task.backend} / {len(task.layer_ids)} layers")
        self.status_label.setText(f"Render plan has {len(plan.tasks)} tasks.")

    def show_pack_status(self) -> None:
        self.properties.clear()
        statuses = self.pack_reader.list_statuses()
        if not statuses:
            self.properties.addItem("No pack manifests found.")
            self.status_label.setText("No optional packs listed.")
            return
        for pack in statuses:
            state = "installed" if pack.installed else "not installed"
            optional = "required" if pack.required else "optional"
            self.properties.addItem(f"{pack.name}: {state} / {optional} / {pack.kind}")
        self.status_label.setText(f"Pack status loaded: {len(statuses)} packs.")

    def render_preview(self) -> None:
        if self.project is None:
            return
        if not self.validate_project():
            return
        try:
            temp_dir = Path(tempfile.gettempdir()) / "ttg_creative_preview"
            temp_dir.mkdir(parents=True, exist_ok=True)
            preview_path = temp_dir / "preview.png"
            CanvasRenderer(RenderContext(project_root=self.project_root)).render(self.project).save(preview_path)
            self.canvas.set_image(str(preview_path))
            self.status_label.setText("Preview rendered.")
        except Exception as exc:
            QMessageBox.critical(self, "Render Preview", str(exc))

    def export_png(self) -> None:
        if self.project is None:
            return
        if not self.validate_project():
            return
        target, _ = QFileDialog.getSaveFileName(self, "Export PNG", "ttg-export.png", "PNG Image (*.png)")
        if not target:
            return
        if not target.lower().endswith(".png"):
            target = f"{target}.png"
        try:
            CanvasRenderer(RenderContext(project_root=self.project_root)).render(self.project).save(target)
            self.status_label.setText(f"Exported {target}")
        except Exception as exc:
            QMessageBox.critical(self, "Export PNG", str(exc))

    def export_frames(self) -> None:
        if self.project is None:
            return
        if not self.validate_project():
            return
        target = QFileDialog.getExistingDirectory(self, "Export Frames")
        if not target:
            return
        try:
            frames = MotionExporter(RenderContext(project_root=self.project_root)).export_frames(self.project, target)
            self.status_label.setText(f"Exported {len(frames)} frames.")
        except Exception as exc:
            QMessageBox.critical(self, "Export Frames", str(exc))

    def refresh_panels(self) -> None:
        self.layer_list.clear()
        self.properties.clear()
        if self.project is None:
            return
        for layer in self.project.layers:
            self.layer_list.addItem(f"{layer.type}: {layer.name}")
        self.projectChanged.emit(self.project)

    def _selected_layer_changed(self, row: int) -> None:
        self.properties.clear()
        if self.project is None or row < 0 or row >= len(self.project.layers):
            return
        layer = self.project.layers[row]
        self.properties.addItem(f"id: {layer.id}")
        self.properties.addItem(f"type: {layer.type}")
        self.properties.addItem(f"name: {layer.name}")
        self.properties.addItem(f"x: {layer.transform.x}")
        self.properties.addItem(f"y: {layer.transform.y}")
        for key, value in layer.properties.items():
            self.properties.addItem(f"{key}: {value}")
