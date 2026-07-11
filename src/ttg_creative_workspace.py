#!/usr/bin/env python3
"""TTG Creative Studio workspace with Advanced Mode."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ttg_action_engine import ActionEngine
from ttg_advanced_panel import AdvancedModePanel
from ttg_asset_browser import AssetTemplateBrowser
from ttg_background_tool import BackgroundRemovalTool
from ttg_diagram_tools import add_basic_board_callout, add_basic_isp_diagram
from ttg_effect_actions import EffectActions
from ttg_export_service import ExportService
from ttg_ffmpeg_manager import FFmpegManager
from ttg_history import ProjectHistory
from ttg_interactive_canvas import InteractiveCanvas
from ttg_intro_builder import IntroBuilder
from ttg_pack_downloader import PackDownloader
from ttg_pack_status import PackStatusReader
from ttg_playback_panel import PlaybackPanel
from ttg_preset_actions import PresetActions
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
        self.effects = EffectActions()
        self.timeline_actions = TimelineActions()
        self.preset_actions = PresetActions()
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
        self.still_preview_approved = False
        self._build_ui()
        self._apply_theme()
        self.show_pack_status()

    def _menu_button(self, title: str, actions: list[tuple[str, Callable[[], None]]]) -> QToolButton:
        button = QToolButton()
        button.setText(title)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(button)
        for label, callback in actions:
            action = QAction(label, self)
            action.triggered.connect(callback)
            menu.addAction(action)
        button.setMenu(menu)
        return button

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        toolbar.addWidget(self._menu_button("File", [
            ("New Project", self.new_project),
            ("Open Project", self.open_project),
            ("Save Project", self.save_project),
            ("Import Ad ZIP", self.import_ad_zip),
            ("Import Ad Folder", self.import_ad_folder),
        ]))
        toolbar.addWidget(self._menu_button("Templates", [
            ("Basic Intro", lambda: self.reset_project(make_ttg_intro_project())),
            ("THETECHGUY Reference Intro", self.load_reference_intro),
            ("Cinematic TTG Intro", lambda: self.reset_project(IntroBuilder().build_ttg_intro())),
        ]))
        toolbar.addWidget(self._menu_button("Add", [
            ("Text", self.add_text),
            ("Shape", self.add_shape),
            ("Image", self.add_image),
            ("ISP Diagram", self.add_isp),
            ("Board Callout", self.add_board),
        ]))
        toolbar.addWidget(self._menu_button("Edit", [
            ("Undo", self.undo),
            ("Redo", self.redo),
            ("Duplicate Layer", self.duplicate_layer),
            ("Delete Layer", self.delete_layer),
        ]))
        toolbar.addWidget(self._menu_button("Effects", [
            ("Glow", lambda: self.apply_effect("glow")),
            ("Stroke + Shadow", lambda: self.apply_effect("stroke_shadow")),
            ("Bevel + Extrude", lambda: self.apply_effect("bevel_extrude")),
            ("Reflection", lambda: self.apply_effect("reflection")),
            ("Gradient Chrome", lambda: self.apply_effect("gradient")),
            ("Premium Text Stack", lambda: self.apply_effect("premium_text")),
        ]))
        toolbar.addWidget(self._menu_button("Animate", [
            ("Fly In", lambda: self.apply_animation("fly")),
            ("Fade In", lambda: self.apply_animation("fade")),
            ("Pulse", lambda: self.apply_animation("pulse")),
            ("Clear Animation", lambda: self.apply_animation("clear")),
            ("Playback Preview", self.try_playback_preview),
        ]))
        toolbar.addWidget(self._menu_button("Tools", [
            ("Remove Background", self.remove_background_into_project),
            ("Show Packs", self.show_pack_status),
            ("Install Selected Pack", self.install_selected_pack),
            ("FFmpeg Status", self.show_ffmpeg_status),
        ]))
        self.preview_button = QPushButton("Preview Still")
        self.preview_button.clicked.connect(self.preview_still)
        toolbar.addWidget(self.preview_button)
        toolbar.addWidget(self._menu_button("Export", [
            ("Export PNG", self.export_png),
            ("Export Frames", self.export_frames),
            ("Export MP4", self.export_mp4),
        ]))
        toolbar.addStretch()
        root.addLayout(toolbar)

        main = QSplitter(Qt.Orientation.Horizontal)
        left_tabs = QTabWidget()
        self.layer_list = QListWidget()
        self.timeline = TimelinePanel()
        self.pack_list = QListWidget()
        self.asset_browser = AssetTemplateBrowser(self.project_root)
        left_tabs.addTab(self.layer_list, "Layers")
        left_tabs.addTab(self.timeline, "Timeline")
        left_tabs.addTab(self.pack_list, "Packs")
        left_tabs.addTab(self.asset_browser, "Assets")
        main.addWidget(left_tabs)

        center_tabs = QTabWidget()
        self.canvas = InteractiveCanvas(self.project_root)
        self.playback = PlaybackPanel(self.project_root)
        center_tabs.addTab(self.canvas, "Canvas")
        center_tabs.addTab(self.playback, "Playback")
        main.addWidget(center_tabs)

        right_tabs = QTabWidget()
        self.properties = PropertiesPanel()
        self.advanced = AdvancedModePanel()
        self.info = QListWidget()
        right_tabs.addTab(self.properties, "Properties")
        right_tabs.addTab(self.advanced, "Advanced")
        right_tabs.addTab(self.info, "Info")
        main.addWidget(right_tabs)
        main.setSizes([270, 760, 330])
        root.addWidget(main, 1)

        self.status = QLabel("TTG Creative Studio ready.")
        root.addWidget(self.status)

        self.layer_list.currentRowChanged.connect(self.select_layer_by_row)
        self.canvas.layerSelected.connect(self.select_layer_by_id)
        self.canvas.layerMoved.connect(self.canvas_moved_layer)
        self.properties.propertyChanged.connect(self.apply_property_change)
        self.timeline.timeChanged.connect(lambda t: self.status.setText(f"Timeline time: {t:.2f}s"))
        self.advanced.effectRequested.connect(self.apply_effect)
        self.advanced.templateRequested.connect(self.load_template_by_id)
        self.advanced.previewRequested.connect(self.preview_still)
        self.asset_browser.assetSelected.connect(self.add_asset_from_browser)
        self.asset_browser.templateSelected.connect(self.load_template_by_id)

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QWidget{background:#050814;color:#eaf3ff;font-family:Segoe UI;}
            QPushButton,QToolButton{background:#16224d;color:#f1f7ff;border:1px solid #3f72ff;border-radius:7px;padding:6px 10px;}
            QPushButton:hover,QToolButton:hover{background:#25356d;}
            QMenu{background:#0b1220;color:#eaf3ff;border:1px solid #2c4f99;padding:4px;}
            QMenu::item{padding:7px 22px;}
            QMenu::item:selected{background:#25356d;}
            QListWidget,QTabWidget::pane{background:#0b1220;border:1px solid #18305f;}
            QTabBar::tab{background:#09111f;color:#dcecff;padding:6px 12px;border:1px solid #18305f;}
            QTabBar::tab:selected{background:#16224d;color:#ffffff;}
            QLabel{color:#9fd8ff;}
            QLineEdit,QSpinBox,QDoubleSpinBox{background:#0b1220;color:#ffffff;border:1px solid #2c4f99;padding:4px;}
            """
        )

    def remember(self, label: str) -> None:
        if self.project is not None:
            self.history.remember(label, self.project)
            self.still_preview_approved = False

    def reset_project(self, project: TTGProject) -> None:
        self.project = project
        self.project_path = None
        self.selected_layer_id = project.layers[0].id if project.layers else None
        self.still_preview_approved = False
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
        self.layer_list.blockSignals(True)
        self.layer_list.clear()
        selected_row = -1
        if self.project is not None:
            for index, layer in enumerate(self.project.layers):
                label = f"{layer.type}: {layer.name}"
                if layer.keyframes:
                    label += " • animated"
                self.layer_list.addItem(label)
                if layer.id == self.selected_layer_id:
                    selected_row = index
        self.layer_list.setCurrentRow(selected_row)
        self.layer_list.blockSignals(False)
        self.timeline.set_project(self.project)
        self.playback.set_project(self.project if self.still_preview_approved else None)
        self.canvas.set_project(self.project, self.selected_layer_id)
        self.properties.set_layer(self.selected_layer())
        self.projectChanged.emit(self.project)

    def refresh_canvas(self) -> None:
        self.validate_project(show_dialog=False)
        self.canvas.set_project(self.project, self.selected_layer_id)

    def preview_still(self) -> None:
        self.refresh_canvas()
        if self.project is not None:
            self.still_preview_approved = True
            self.playback.set_project(self.project)
            self.status.setText("Still preview refreshed. Playback preview is now enabled for this version.")

    def try_playback_preview(self) -> None:
        if not self.still_preview_approved:
            QMessageBox.information(self, "Playback Preview", "Preview the still frame first. Playback is enabled after the still looks right.")
            return
        self.playback.start()

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

    def load_reference_intro(self) -> None:
        self.reset_project(IntroBuilder().build_reference_intro())

    def load_template_by_id(self, template_id: str) -> None:
        if template_id in {"template:ttg_cinematic", "ttg_reference_intro", "template:ttg_reference_intro"}:
            self.load_reference_intro()
        elif template_id == "template:basic_intro":
            self.reset_project(make_ttg_intro_project())

    def open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "TTG Studio (*.json *.ttgstudio)")
        if not path:
            return
        try:
            project = TTGProject.load(path)
            self.project = project
            self.project_path = Path(path)
            self.selected_layer_id = project.layers[0].id if project.layers else None
            self.still_preview_approved = False
            self.history.clear()
            self.refresh_all()
        except Exception as exc:
            QMessageBox.critical(self, "Open Project", str(exc))

    def import_ad_zip(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Ad ZIP", "", "Ad Package (*.zip)")
        if path:
            self.import_ad_source(Path(path))

    def import_ad_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Import Ad Folder")
        if path:
            self.import_ad_source(Path(path))

    def import_ad_source(self, source: Path) -> None:
        try:
            scripts_dir = self.project_root / "scripts"
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            from build_ad_project_from_assets import build_ad_project

            output_dir = Path(tempfile.gettempdir()) / "ttg_creative_studio_imported_ad"
            output_dir.mkdir(parents=True, exist_ok=True)
            project_path = output_dir / "imported_ad.ttgstudio.json"
            workspace = output_dir / "asset_workspace"
            project = build_ad_project(source, project_path, "Imported TTG Ad", workspace=workspace)
            self.project = project
            self.project_path = project_path
            self.selected_layer_id = project.layers[0].id if project.layers else None
            self.still_preview_approved = False
            self.history.clear()
            self.refresh_all()
            self.status.setText(f"Imported ad workflow project: {source}")
        except Exception as exc:
            QMessageBox.warning(self, "Import Ad Workflow", str(exc))

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
            self.still_preview_approved = False
            if self.project.layers and (not self.selected_layer_id or not self.selected_layer()):
                self.selected_layer_id = self.project.layers[0].id
            self.refresh_all()

    def redo(self) -> None:
        if self.project is not None and self.history.can_redo():
            self.project = self.history.redo(self.project)
            self.still_preview_approved = False
            if self.project.layers and (not self.selected_layer_id or not self.selected_layer()):
                self.selected_layer_id = self.project.layers[0].id
            self.refresh_all()

    def add_text(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project is not None:
            self.remember("add text")
            layer = self.action.add_text(self.project, "THETECHGUY", 120, 120)
            layer.properties.update({"shadow": True, "glow": True, "stroke_width": 1, "size": 72})
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

    def add_asset_from_browser(self, path: str) -> None:
        if self.project is None:
            self.new_project()
        if self.project is None:
            return
        self.remember("add browser asset")
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
            self.selected_layer_id = self.project.layers[0].id if self.project.layers else None
            self.refresh_all()

    def add_isp(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project:
            self.remember("add ISP diagram")
            before = len(self.project.layers)
            add_basic_isp_diagram(self.project)
            if len(self.project.layers) > before:
                self.selected_layer_id = self.project.layers[before].id
            self.refresh_all()

    def add_board(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project:
            self.remember("add board callout")
            before = len(self.project.layers)
            add_basic_board_callout(self.project)
            if len(self.project.layers) > before:
                self.selected_layer_id = self.project.layers[before].id
            self.refresh_all()

    def apply_effect(self, effect_id: str) -> None:
        if not self.project or not self.selected_layer_id:
            QMessageBox.information(self, "Advanced Effect", "Select a layer first.")
            return
        self.remember(f"effect {effect_id}")
        if effect_id == "glow":
            self.effects.apply_neon_glow(self.project, self.selected_layer_id)
        elif effect_id == "stroke_shadow":
            self.effects.apply_stroke_shadow(self.project, self.selected_layer_id)
        elif effect_id == "bevel_extrude":
            self.effects.apply_bevel_extrude(self.project, self.selected_layer_id)
        elif effect_id == "reflection":
            self.effects.apply_reflection(self.project, self.selected_layer_id)
        elif effect_id == "gradient":
            self.effects.apply_gradient(self.project, self.selected_layer_id)
        elif effect_id == "premium_text":
            self.effects.apply_premium_text_stack(self.project, self.selected_layer_id)
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
        self.selected_layer_id = self.project.layers[row].id
        self.canvas.set_project(self.project, self.selected_layer_id)
        self.properties.set_layer(self.selected_layer())

    def select_layer_by_id(self, layer_id: str) -> None:
        self.selected_layer_id = layer_id
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
        if not self.still_preview_approved:
            QMessageBox.information(self, "Export Frames", "Preview the still frame first.")
            return
        path = QFileDialog.getExistingDirectory(self, "Export Frames")
        if path:
            frames = self.export_service.export_frames(self.project, path)
            self.status.setText(f"Exported {len(frames)} frames")

    def export_mp4(self) -> None:
        if not self.project or not self.validate_project():
            return
        if not self.still_preview_approved:
            QMessageBox.information(self, "Export MP4", "Preview the still frame first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export MP4", "ttg-export.mp4", "MP4 (*.mp4)")
        if path:
            if not path.lower().endswith(".mp4"):
                path += ".mp4"
            work_dir = Path(tempfile.gettempdir()) / "ttg_mp4_export"
            self.export_service.export_mp4(self.project, path, work_dir)
            self.status.setText(f"Exported {path}")
