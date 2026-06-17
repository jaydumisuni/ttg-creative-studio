#!/usr/bin/env python3
"""TTG Creative Studio V2 workspace.

This is the release-track workspace: interactive canvas, editable properties,
timeline panel, pack status/download path, FFmpeg status and background tool.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QListWidget, QMessageBox, QPushButton, QSplitter, QTabWidget, QVBoxLayout, QWidget

from ttg_action_engine import ActionEngine
from ttg_background_tool import BackgroundRemovalTool
from ttg_diagram_tools import add_basic_board_callout, add_basic_isp_diagram
from ttg_export_service import ExportService
from ttg_ffmpeg_manager import FFmpegManager
from ttg_history import ProjectHistory
from ttg_interactive_canvas import InteractiveCanvas
from ttg_intro_builder import IntroBuilder
from ttg_pack_downloader import PackDownloader
from ttg_pack_status import PackStatusReader
from ttg_project_schema import TTGProject, make_ttg_intro_project
from ttg_properties_panel import PropertiesPanel
from ttg_property_actions import PropertyActions
from ttg_render_plan import RenderPlanner
from ttg_timeline_actions import TimelineActions
from ttg_timeline_panel import TimelinePanel
from ttg_validation import ProjectValidator


class CreativeWorkspace(QWidget):
    projectChanged = pyqtSignal(object)

    def __init__(self, project_root: str | Path | None = None) -> None:
        super().__init__()
        self.project_root = Path(project_root or Path.cwd())
        self.action = ActionEngine()
        self.props = PropertyActions()
        self.timeline_actions = TimelineActions()
        self.history = ProjectHistory()
        self.validator = ProjectValidator()
        self.planner = RenderPlanner()
        self.export_service = ExportService(self.project_root)
        self.pack_reader = PackStatusReader(self.project_root)
        self.pack_downloader = PackDownloader(self.project_root)
        self.ffmpeg = FFmpegManager()
        self.bg_tool = BackgroundRemovalTool(self.project_root)
        self.project: TTGProject | None = None
        self.project_path: Path | None = None
        self.selected_layer_id: str | None = None
        self._build_ui()
        self._apply_theme()
        self.show_pack_status()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        buttons = [
            ("new_button", "New"), ("open_button", "Open"), ("save_button", "Save"),
            ("intro_button", "Intro"), ("cinematic_button", "Cinematic"),
            ("undo_button", "Undo"), ("redo_button", "Redo"),
            ("text_button", "Text"), ("shape_button", "Shape"), ("image_button", "Image"),
            ("duplicate_button", "Duplicate"), ("delete_button", "Delete"),
            ("fly_button", "Fly"), ("fade_button", "Fade"), ("pulse_button", "Pulse"), ("clear_anim_button", "Clear Anim"),
            ("isp_button", "ISP"), ("board_button", "Board"), ("bg_button", "BG Remove"),
            ("pack_button", "Packs"), ("install_pack_button", "Install Pack"), ("ffmpeg_button", "FFmpeg"),
            ("preview_button", "Preview"), ("png_button", "PNG"), ("frames_button", "Frames"), ("mp4_button", "MP4"),
        ]
        for attr, label in buttons:
            button = QPushButton(label)
            setattr(self, attr, button)
            toolbar.addWidget(button)
        toolbar.addStretch()
        root.addLayout(toolbar)

        main = QSplitter(Qt.Orientation.Horizontal)
        left_tabs = QTabWidget()
        self.layer_list = QListWidget()
        self.timeline = TimelinePanel()
        self.pack_list = QListWidget()
        left_tabs.addTab(self.layer_list, "Layers")
        left_tabs.addTab(self.timeline, "Timeline")
        left_tabs.addTab(self.pack_list, "Packs")
        main.addWidget(left_tabs)

        self.canvas = InteractiveCanvas(self.project_root)
        main.addWidget(self.canvas)

        right_tabs = QTabWidget()
        self.properties = PropertiesPanel()
        self.info = QListWidget()
        right_tabs.addTab(self.properties, "Properties")
        right_tabs.addTab(self.info, "Info")
        main.addWidget(right_tabs)
        main.setSizes([290, 820, 340])
        root.addWidget(main, 1)

        self.status = QLabel("TTG Creative Studio ready.")
        root.addWidget(self.status)

        self.new_button.clicked.connect(self.new_project)
        self.open_button.clicked.connect(self.open_project)
        self.save_button.clicked.connect(self.save_project)
        self.intro_button.clicked.connect(lambda: self.reset_project(make_ttg_intro_project()))
        self.cinematic_button.clicked.connect(lambda: self.reset_project(IntroBuilder().build_ttg_intro()))
        self.undo_button.clicked.connect(self.undo)
        self.redo_button.clicked.connect(self.redo)
        self.text_button.clicked.connect(self.add_text)
        self.shape_button.clicked.connect(self.add_shape)
        self.image_button.clicked.connect(self.add_image)
        self.duplicate_button.clicked.connect(self.duplicate_layer)
        self.delete_button.clicked.connect(self.delete_layer)
        self.fly_button.clicked.connect(lambda: self.apply_animation("fly"))
        self.fade_button.clicked.connect(lambda: self.apply_animation("fade"))
        self.pulse_button.clicked.connect(lambda: self.apply_animation("pulse"))
        self.clear_anim_button.clicked.connect(lambda: self.apply_animation("clear"))
        self.isp_button.clicked.connect(self.add_isp)
        self.board_button.clicked.connect(self.add_board)
        self.bg_button.clicked.connect(self.remove_background_into_project)
        self.pack_button.clicked.connect(self.show_pack_status)
        self.install_pack_button.clicked.connect(self.install_selected_pack)
        self.ffmpeg_button.clicked.connect(self.show_ffmpeg_status)
        self.preview_button.clicked.connect(self.refresh_canvas)
        self.png_button.clicked.connect(self.export_png)
        self.frames_button.clicked.connect(self.export_frames)
        self.mp4_button.clicked.connect(self.export_mp4)
        self.layer_list.currentRowChanged.connect(self.select_layer_by_row)
        self.canvas.layerSelected.connect(self.select_layer_by_id)
        self.canvas.layerMoved.connect(self.canvas_moved_layer)
        self.properties.propertyChanged.connect(self.apply_property_change)
        self.timeline.timeChanged.connect(lambda t: self.status.setText(f"Timeline time: {t:.2f}s"))

    def _apply_theme(self) -> None:
        self.setStyleSheet("QWidget{background:#050814;color:#eaf3ff;} QPushButton{background:#16224d;color:#f1f7ff;border:1px solid #3f72ff;border-radius:7px;padding:6px;} QPushButton:hover{background:#25356d;} QListWidget,QTabWidget::pane{background:#0b1220;border:1px solid #18305f;} QLabel{color:#9fd8ff;} QLineEdit,QSpinBox,QDoubleSpinBox{background:#0b1220;color:#ffffff;border:1px solid #2c4f99;padding:4px;}")

    def remember(self, label: str) -> None:
        if self.project is not None:
            self.history.remember(label, self.project)

    def reset_project(self, project: TTGProject) -> None:
        self.project = project
        self.project_path = None
        self.selected_layer_id = None
        self.history.clear()
        self.refresh_all()

    def selected_layer(self):
        if self.project is None or not self.selected_layer_id:
            return None
        for layer in self.project.layers:
            if layer.id == self.selected_layer_id:
                return layer
        return None

    def refresh_all(self) -> None:
        self.layer_list.clear()
        if self.project is not None:
            for layer in self.project.layers:
                label = f"{layer.type}: {layer.name}"
                if layer.keyframes:
                    label += " • animated"
                self.layer_list.addItem(label)
        self.timeline.set_project(self.project)
        self.canvas.set_project(self.project, self.selected_layer_id)
        self.properties.set_layer(self.selected_layer())
        self.projectChanged.emit(self.project)

    def refresh_canvas(self) -> None:
        self.validate_project(show_dialog=False)
        self.canvas.set_project(self.project, self.selected_layer_id)

    def validate_project(self, show_dialog: bool = True) -> bool:
        if self.project is None:
            return False
        messages = self.validator.validate(self.project, self.project_root)
        errors = [m for m in messages if m.level == "error"]
        self.info.clear()
        if not messages:
            self.info.addItem("Validation passed")
        for msg in messages:
            self.info.addItem(f"{msg.level.upper()}: {msg.message}")
        if errors and show_dialog:
            QMessageBox.warning(self, "Validation", "Fix project errors before export.")
        return not errors

    def new_project(self) -> None:
        self.reset_project(self.action.new_project("Untitled TTG Project", "image"))

    def open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "TTG Studio (*.json *.ttgstudio)")
        if not path:
            return
        try:
            self.project = TTGProject.load(path)
            self.project_path = Path(path)
            self.history.clear()
            self.refresh_all()
        except Exception as exc:
            QMessageBox.critical(self, "Open Project", str(exc))

    def save_project(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project is None:
            return
        if self.project_path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save Project", "project.ttgstudio.json", "TTG Studio (*.json)")
            if not path:
                return
            self.project_path = Path(path)
        self.project.save(self.project_path)
        self.status.setText(f"Saved {self.project_path}")

    def undo(self) -> None:
        if self.project is not None and self.history.can_undo():
            self.project = self.history.undo(self.project)
            self.refresh_all()

    def redo(self) -> None:
        if self.project is not None and self.history.can_redo():
            self.project = self.history.redo(self.project)
            self.refresh_all()

    def add_text(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project is not None:
            self.remember("add text")
            layer = self.action.add_text(self.project, "THETECHGUY", 120, 120)
            layer.properties.update({"shadow": True, "glow": True, "stroke_width": 1})
            self.select_layer_by_id(layer.id)

    def add_shape(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project is not None:
            self.remember("add shape")
            layer = self.action.add_shape(self.project, "rectangle", 160, 220)
            self.select_layer_by_id(layer.id)

    def add_image(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Add Image", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            self.remember("add image")
            layer = self.action.add_image(self.project, path, 80, 80)
            self.select_layer_by_id(layer.id)

    def duplicate_layer(self) -> None:
        if self.project and self.selected_layer_id:
            self.remember("duplicate layer")
            layer = self.action.duplicate_layer(self.project, self.selected_layer_id)
            self.select_layer_by_id(layer.id)

    def delete_layer(self) -> None:
        if self.project and self.selected_layer_id:
            self.remember("delete layer")
            self.action.remove_layer(self.project, self.selected_layer_id)
            self.selected_layer_id = None
            self.refresh_all()

    def add_isp(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project:
            self.remember("add ISP diagram")
            add_basic_isp_diagram(self.project)
            self.refresh_all()

    def add_board(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project:
            self.remember("add board callout")
            add_basic_board_callout(self.project)
            self.refresh_all()

    def apply_animation(self, preset: str) -> None:
        if not self.project or not self.selected_layer_id:
            return
        self.remember(f"animation {preset}")
        if preset == "fly":
            self.timeline_actions.add_fly_in_left(self.project, self.selected_layer_id)
        elif preset == "fade":
            self.timeline_actions.add_fade_in(self.project, self.selected_layer_id)
        elif preset == "pulse":
            self.timeline_actions.add_pulse(self.project, self.selected_layer_id)
        elif preset == "clear":
            self.timeline_actions.clear_animation(self.project, self.selected_layer_id)
        self.refresh_all()

    def select_layer_by_row(self, row: int) -> None:
        if self.project is None or row < 0 or row >= len(self.project.layers):
            return
        self.select_layer_by_id(self.project.layers[row].id)

    def select_layer_by_id(self, layer_id: str) -> None:
        self.selected_layer_id = layer_id
        if self.project:
            for index, layer in enumerate(self.project.layers):
                if layer.id == layer_id:
                    self.layer_list.setCurrentRow(index)
                    break
        self.refresh_all()

    def canvas_moved_layer(self, layer_id: str, x: float, y: float) -> None:
        if self.project is None:
            return
        self.props.set_position(self.project, layer_id, x, y)
        self.selected_layer_id = layer_id
        self.refresh_all()

    def apply_property_change(self, key: str, value) -> None:  # noqa: ANN001
        if self.project is None or not self.selected_layer_id:
            return
        self.remember(f"property {key}")
        if key == "name":
            self.props.rename_layer(self.project, self.selected_layer_id, str(value))
        elif key == "text":
            self.props.set_text(self.project, self.selected_layer_id, str(value))
        elif key == "position":
            self.props.set_position(self.project, self.selected_layer_id, value[0], value[1])
        elif key == "scale":
            self.props.set_scale(self.project, self.selected_layer_id, float(value))
        elif key == "rotation":
            self.props.set_rotation(self.project, self.selected_layer_id, float(value))
        elif key == "opacity":
            self.props.set_opacity(self.project, self.selected_layer_id, float(value))
        elif key == "size":
            self.props.set_size(self.project, self.selected_layer_id, int(value))
        elif key == "color":
            self.props.set_color(self.project, self.selected_layer_id, str(value))
        elif key == "fill":
            self.props.set_fill(self.project, self.selected_layer_id, str(value))
        self.refresh_all()

    def show_pack_status(self) -> None:
        self.pack_list.clear()
        self.info.clear()
        statuses = self.pack_reader.list_statuses()
        for pack in statuses:
            state = "installed" if pack.installed else "not installed"
            self.pack_list.addItem(f"{pack.id} | {pack.name} | {state}")
            self.info.addItem(f"{pack.name}: {state} / {pack.kind}")
        self.status.setText(f"Pack status loaded: {len(statuses)} packs")

    def install_selected_pack(self) -> None:
        item = self.pack_list.currentItem()
        if not item:
            QMessageBox.information(self, "Install Pack", "Select a pack first.")
            return
        pack_id = item.text().split("|", 1)[0].strip()
        try:
            result = self.pack_downloader.install_pack(pack_id, lambda msg: self.status.setText(msg))
            QMessageBox.information(self, "Install Pack", f"Installed {result.pack_id}: {result.installed_files} files, {result.skipped_files} skipped.")
            self.show_pack_status()
        except Exception as exc:
            QMessageBox.warning(self, "Install Pack", str(exc))

    def show_ffmpeg_status(self) -> None:
        status = self.ffmpeg.status()
        QMessageBox.information(self, "FFmpeg", status.message + (f"\n{status.version}" if status.version else ""))

    def remove_background_into_project(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Remove Background", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if not path:
            return
        try:
            self.remember("background removal")
            output_dir = Path(tempfile.gettempdir()) / "ttg_bg_outputs"
            cutout = self.bg_tool.remove_background(path, output_dir, lambda msg: self.status.setText(msg))
            layer = self.action.add_image(self.project, str(cutout), 80, 80, "Background Removed")
            self.select_layer_by_id(layer.id)
        except Exception as exc:
            QMessageBox.warning(self, "Background Removal", str(exc))

    def export_png(self) -> None:
        if not self.project or not self.validate_project():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export PNG", "ttg-export.png", "PNG (*.png)")
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            self.export_service.export_png(self.project, path)
            self.status.setText(f"Exported {path}")

    def export_frames(self) -> None:
        if not self.project or not self.validate_project():
            return
        path = QFileDialog.getExistingDirectory(self, "Export Frames")
        if path:
            frames = self.export_service.export_frames(self.project, path)
            self.status.setText(f"Exported {len(frames)} frames")

    def export_mp4(self) -> None:
        if not self.project or not self.validate_project():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export MP4", "ttg-export.mp4", "MP4 (*.mp4)")
        if path:
            if not path.lower().endswith(".mp4"):
                path += ".mp4"
            work_dir = Path(tempfile.gettempdir()) / "ttg_mp4_export"
            self.export_service.export_mp4(self.project, path, work_dir)
            self.status.setText(f"Exported {path}")
