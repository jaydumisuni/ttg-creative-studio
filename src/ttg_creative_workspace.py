#!/usr/bin/env python3
"""TTG Creative Studio workspace with Advanced Mode."""

from __future__ import annotations

import sys
import tempfile
import uuid
import shutil
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMenu,
    QMessageBox,
    QPushButton,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ttg_action_engine import ActionEngine
from ttg_campaign_composer import CampaignBrief, compose_campaign
from ttg_campaign_dialog import CampaignDesignerDialog
from ttg_image_lab_dialog import ImageLabDialog
from ttg_visual_inspector_dialog import VisualInspectorDialog
from ttg_mask_painter import MaskPainterDialog
from ttg_video_lab_dialog import VideoLabDialog, VideoExportThread, VideoTrimDialog
from ttg_online_video_dialog import OnlineVideoDialog
from ttg_online_image_dialog import OnlineImageDialog
from ttg_recovery import RecoveryStore
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
        self.recovery_store = RecoveryStore()
        self._unsaved_identity = uuid.uuid4().hex
        self._image_lab_dialog = None
        self._video_export_worker = None
        self._autosave_last = None
        self._build_ui()
        self._apply_theme()
        self.show_pack_status()
        self._recovery_timer = QTimer(self)
        self._recovery_timer.setInterval(45_000)
        self._recovery_timer.timeout.connect(self.autosave_snapshot)
        self._recovery_timer.start()

    def _menu_button(self, title: str, actions: list[tuple[str, Callable[[], None]]]) -> QToolButton:
        button = QToolButton()
        button.setText(title)
        button.setMinimumWidth(max(78, 13 * len(title) + 12))
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
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

        toolbar_widget = QWidget(self)
        toolbar = QHBoxLayout(toolbar_widget)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(6)
        self.campaign_button = QPushButton("✦ Design Campaign")
        self.campaign_button.setObjectName("campaignDesignerButton")
        self.campaign_button.setMinimumWidth(170)
        self.campaign_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.campaign_button.setToolTip("Generate an editable layered composition, entirely offline")
        self.campaign_button.clicked.connect(self.design_campaign)
        toolbar.addWidget(self.campaign_button)
        toolbar.addWidget(self._menu_button("File", [
            ("New Project", self.new_project),
            ("Open Project", self.open_project),
            ("Save Project", self.save_project),
            ("Recover Autosave", self.recover_autosave),
            ("Check Updates", self.check_updates),
            ("Import Ad ZIP", self.import_ad_zip),
            ("Import Ad Folder", self.import_ad_folder),
        ]))
        toolbar.addWidget(self._menu_button("Templates", [
            ("New Campaign Designer", self.design_campaign),
            ("Basic Intro", lambda: self.reset_project(make_ttg_intro_project())),
            ("THETECHGUY Reference Intro", self.load_reference_intro),
            ("Cinematic TTG Intro", lambda: self.reset_project(IntroBuilder().build_ttg_intro())),
        ]))
        toolbar.addWidget(self._menu_button("Add", [
            ("Text", self.add_text),
            ("Shape", self.add_shape),
            ("Image", self.add_image),
            ("Video Clip · Inspect / Import", self.open_video_lab),
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
            ("Increase Contrast", lambda: self.adjust_selected_image("contrast", 1.35)),
            ("Increase Saturation", lambda: self.adjust_selected_image("saturation", 1.4)),
            ("Sharpen Image", lambda: self.adjust_selected_image("sharpen", 1.8)),
            ("Grayscale", lambda: self.adjust_selected_image("grayscale", 1.0)),
            ("Premium Text Stack", lambda: self.apply_effect("premium_text")),
        ]))
        toolbar.addWidget(self._menu_button("Animate", [
            ("Fly In", lambda: self.apply_animation("fly")),
            ("Fade In", lambda: self.apply_animation("fade")),
            ("Pulse", lambda: self.apply_animation("pulse")),
            ("Fade Out", lambda: self.apply_animation("fade_out")),
            ("Slide Up", lambda: self.apply_animation("slide_up")),
            ("Clear Animation", lambda: self.apply_animation("clear")),
            ("Playback Preview", self.try_playback_preview),
        ]))
        toolbar.addWidget(self._menu_button("Tools", [
            ("Image Lab · Generate / Enhance", self.open_image_lab),
            ("Visual Inspector · Analyze Image", self.open_visual_inspector),
            ("Brush Mask Selected Image", self.brush_mask_selected_image),
            ("Add Audio Track", self.add_audio_track),
            ("Video Lab · Inspect / Import", self.open_video_lab),
            ("Generate Online Image · Optional Paid", self.open_online_image),
            ("Generate Online Video · Optional Paid", self.open_online_video),
            ("Edit Selected Video Timing", self.edit_selected_video_timing),
            ("Recover Autosave", self.recover_autosave),
            ("Remove Background", self.remove_background_into_project),
            ("Show Packs", self.show_pack_status),
            ("Install Selected Pack", self.install_selected_pack),
            ("FFmpeg Status", self.show_ffmpeg_status),
        ]))
        self.preview_button = QPushButton("Preview Still")
        self.preview_button.setMinimumWidth(117)
        self.preview_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.preview_button.clicked.connect(self.preview_still)
        toolbar.addWidget(self.preview_button)
        toolbar.addWidget(self._menu_button("Export", [
            ("Export PNG", self.export_png),
            ("Export Frames", self.export_frames),
            ("Export MP4", self.export_mp4),
        ]))
        toolbar.addStretch()
        self.toolbar_scroll = QScrollArea()
        self.toolbar_scroll.setWidgetResizable(False)
        self.toolbar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.toolbar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.toolbar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        toolbar_widget.adjustSize()
        self.toolbar_scroll.setWidget(toolbar_widget)
        self.toolbar_scroll.setFixedHeight(toolbar_widget.sizeHint().height() + 10)
        root.addWidget(self.toolbar_scroll)

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
        self.timeline.timeChanged.connect(self.seek_timeline)
        self.advanced.effectRequested.connect(self.apply_effect)
        self.advanced.templateRequested.connect(self.load_template_by_id)
        self.advanced.previewRequested.connect(self.preview_still)
        self.asset_browser.assetSelected.connect(self.add_asset_from_browser)
        self.asset_browser.templateSelected.connect(self.load_template_by_id)
        self._shortcuts = []
        for sequence, callback in [
            ("Ctrl+S", self.save_project),
            ("Ctrl+O", self.open_project),
            ("Ctrl+Z", self.undo),
            ("Ctrl+Shift+Z", self.redo),
            ("Ctrl+E", self.export_png),
        ]:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QWidget{background:#050814;color:#eaf3ff;font-family:Segoe UI;}
            QPushButton,QToolButton{background:#16224d;color:#f1f7ff;border:1px solid #3f72ff;border-radius:7px;padding:6px 10px;}
            QPushButton:hover,QToolButton:hover{background:#25356d;}
            QPushButton#campaignDesignerButton{background:#1c706c;color:#f6fffe;border:1px solid #58e8d9;font-weight:700;padding:7px 13px;}
            QPushButton#campaignDesignerButton:hover{background:#288c82;}
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

    def check_updates(self) -> None:
        import os
        import webbrowser
        from ttg_update_checker import CURRENT_VERSION, fetch_update, is_newer
        manifest_url = os.environ.get("TTG_STUDIO_UPDATE_URL", "").strip()
        if not manifest_url:
            QMessageBox.information(
                self, "Creative Studio Updates",
                "No approved update feed is configured. "
                "The current build is " + CURRENT_VERSION +
                ". Updates must be published through the official signed-release process."
            )
            return
        try:
            notice = fetch_update(manifest_url)
            if not is_newer(notice):
                QMessageBox.information(self,"Creative Studio Updates","No newer official build was advertised.")
                return
            approval = QMessageBox.question(
                self,"Creative Studio Update Available",
                f"Version {notice.version} is available.\n\n"
                +notice.notes+"\n\nOpen the official release page?\n"
                "The app will not download or install executable code automatically."
            )
            if approval == QMessageBox.StandardButton.Yes:
                webbrowser.open(notice.installer_url)
        except Exception as exc:
            QMessageBox.warning(self,"Creative Studio Updates",str(exc))

    def autosave_snapshot(self) -> Path | None:
        if self.project is None:
            return None
        import hashlib
        import json
        current = hashlib.sha256(
            json.dumps(self.project.to_dict(), sort_keys=True).encode()
        ).hexdigest()
        if self._autosave_last == current:
            return None
        saved = self.recovery_store.snapshot(
            self.project, self.project_path, self._unsaved_identity
        )
        self._autosave_last = current
        return saved

    def recover_autosave(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        entries = self.recovery_store.pending()
        if not entries:
            QMessageBox.information(self, "Project Recovery", "No autosaves available.")
            return
        choices = [f"{q.stat().st_mtime:.0f} | {q.name}" for q in entries]
        chosen, ok = QInputDialog.getItem(
            self, "Recover Project", "Select retained recovery:", choices,
            0, False
        )
        if not ok:
            return
        selected = entries[choices.index(chosen)]
        try:
            project, original = self.recovery_store.load(selected)
            # Do not rewrite the original file merely by opening recovery.
            self.reset_project(project)
            if original and original.exists():
                self._set_asset_root(original.parent)
            self.status.setText("Recovered in memory. Use Save to keep your changes.")
        except Exception as exc:
            QMessageBox.warning(self, "Project Recovery", str(exc))

    def adjust_selected_image(self, effect: str, amount: float) -> None:
        layer = self.selected_layer()
        if layer is None or layer.type != "image":
            QMessageBox.information(self,"Image Effects","Select an image layer first.")
            return
        self.remember(f"image effect {effect}")
        layer.effects.append({"type":effect,"amount":amount})
        self.refresh_all()

    def open_visual_inspector(self) -> None:
        """Preview pixel evidence; nothing mutates until the user approves."""
        if self.project is None:
            QMessageBox.information(self, "Visual Inspector", "Open a project first.")
            return
        from ttg_canvas_engine import CanvasRenderer, RenderContext
        from ttg_visual_understanding import measure_image
        base = self.project_path.parent if self.project_path else self.project_root
        layer = self.selected_layer()
        source = None
        editable = False
        temp_snapshot = None
        if layer is not None and layer.type == "image":
            raw = layer.properties.get("path") or layer.properties.get("asset_path")
            if raw:
                source = RenderContext(base).resolve_asset(str(raw))
                editable = source.is_file() and not layer.locked
        if not source or not source.is_file():
            temp_snapshot = tempfile.TemporaryDirectory(prefix="ttg-visual-")
            source = Path(temp_snapshot.name)/"canvas.png"
            CanvasRenderer(RenderContext(base)).render(self.project).save(source)
            editable = False
        inspector = VisualInspectorDialog(source, self, can_apply=editable)
        if temp_snapshot is not None:
            inspector._owned_snapshot = temp_snapshot
            inspector.finished.connect(lambda code, snapshot=temp_snapshot: snapshot.cleanup())
        if editable:
            target_id = layer.id
            source_sha = measure_image(source)["source_sha256"]
            inspector.applySuggestion.connect(
                lambda proposal: self.apply_inspector_edit(
                    proposal, target_id, source, source_sha
                )
            )
        self._visual_inspector_dialog = inspector
        inspector.show()

    def apply_inspector_edit(self, suggestion: dict, target_id: str,
                             image_path: Path, initial_sha: str) -> None:
        """Only explicit user-approved numeric native effects, never model commands."""
        import hashlib
        import math
        from ttg_visual_understanding import ALLOWED_EFFECTS
        layer = self.selected_layer()
        if not (layer is not None and layer.id == target_id and
                layer.type == "image" and not layer.locked):
            raise ValueError("Selected image layer has changed or is locked")
        if hashlib.sha256(image_path.read_bytes()).hexdigest() != initial_sha:
            raise ValueError("Image changed since inspection; analyze it again")
        if suggestion.get("source_sha256") != initial_sha:
            raise ValueError("Review evidence does not match the selected image")
        effect = suggestion.get("effect")
        amount = suggestion.get("amount")
        if not (suggestion.get("action") == "image_effect" and
                suggestion.get("review_required") is True and
                effect in ALLOWED_EFFECTS and
                isinstance(amount, (int, float)) and not isinstance(amount, bool)
                and math.isfinite(amount) and 0 <= amount <= 4):
            raise ValueError("Inspector may only apply approved numeric effects")
        self.remember("visual inspector approved " + effect)
        layer.effects.append({"type": effect, "amount": float(amount)})
        self.refresh_all()
        self.status.setText("Applied reviewed " + effect + " to editable image layer. Undo is available.")

    def brush_mask_selected_image(self) -> None:
        layer = self.selected_layer()
        if layer is None or layer.type != "image":
            QMessageBox.information(self,"Image Mask","Select an image layer first.")
            return
        if self.project_path is None:
            self.save_project()
        if self.project_path is None:
            return
        from ttg_canvas_engine import RenderContext
        raw = layer.properties.get("path") or layer.properties.get("asset_path")
        path = RenderContext(self.project_path.parent).resolve_asset(str(raw))
        if not path.is_file():
            QMessageBox.warning(self,"Image Mask","The selected image is missing.")
            return
        dialog = MaskPainterDialog(path,self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        if not dialog.surface.points:
            QMessageBox.information(self,"Image Mask","No painted selection was made.")
            return
        folder = self.project_path.parent/"assets"/"masks"
        folder.mkdir(parents=True,exist_ok=True)
        target = folder/(uuid.uuid4().hex+".png")
        dialog.mask().save(target)
        self.remember("brush mask")
        layer.properties["mask_path"] = target.relative_to(self.project_path.parent).as_posix()
        layer.properties["mask_feather"] = 1.0
        self.refresh_all()
        self.autosave_snapshot()

    def add_audio_track(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project_path is None:
            self.save_project()
        if self.project_path is None:
            return
        source, _ = QFileDialog.getOpenFileName(
            self,"Import Audio", "", "Audio (*.wav *.mp3 *.flac *.ogg *.m4a)"
        )
        if not source:
            return
        start, ok = QInputDialog.getDouble(
            self,"Track Start","Start time (seconds):",0,0,
            float(self.project.canvas.duration),2
        )
        if not ok:
            return
        origin = Path(source)
        if origin.stat().st_size > 80*1024*1024:
            QMessageBox.warning(self,"Audio","Audio exceeds the 80 MiB track limit")
            return
        asset_dir = self.project_path.parent/"assets"/"audio"
        asset_dir.mkdir(parents=True,exist_ok=True)
        destination = asset_dir/(uuid.uuid4().hex+origin.suffix.lower())
        shutil.copyfile(origin,destination)
        self.remember("add audio track")
        self.project.audio_markers.append({
            "path":destination.relative_to(self.project_path.parent).as_posix(),
            "start":start,"volume":1.0,
        })
        self.refresh_all()
        self.autosave_snapshot()
        self.status.setText("Audio track added to project timeline")

    def open_image_lab(self) -> None:
        if self.project is None:
            self.new_project()
        if self.project_path is None:
            self.save_project()
        if self.project_path is None:
            return  # User cancelled native Save dialog.
        image_source = ""
        layer = self.selected_layer()
        if layer and layer.type == "image":
            from ttg_canvas_engine import RenderContext
            raw = layer.properties.get("path") or layer.properties.get("asset_path")
            if raw:
                candidate = RenderContext(self.project_path.parent).resolve_asset(str(raw))
                if candidate.is_file():
                    image_source = str(candidate)
        target = self.project_path.parent / "assets" / "image-lab"
        dialog = ImageLabDialog(target, self, source=image_source)
        dialog.completed.connect(self.import_image_lab_result)
        dialog.show()
        self._image_lab_dialog = dialog

    def import_image_lab_result(self, filename: str) -> None:
        if self.project is None or self.project_path is None:
            return
        path = Path(filename).resolve()
        if not path.is_file() or not path.is_relative_to(self.project_path.parent.resolve()):
            raise ValueError("Generated image must be inside the saved project")
        self.remember("Import Image Lab result")
        relative = path.relative_to(self.project_path.parent.resolve()).as_posix()
        layer = self.action.add_image(self.project, relative, 80, 80, "Image Lab result")
        self.selected_layer_id = layer.id
        self.refresh_all()
        self.autosave_snapshot()
        self.status.setText(f"Imported editable Image Lab layer: {relative}")

    def remember(self, label: str) -> None:
        if self.project is not None:
            self.history.remember(label, self.project)
            self.still_preview_approved = False

    def _set_asset_root(self, root: Path) -> None:
        """Resolve image assets beside their saved editable project."""
        self.canvas.project_root = root
        self.export_service = ExportService(root)
        self.playback.project_root = root

    def reset_project(self, project: TTGProject) -> None:
        self._autosave_last = None
        self._unsaved_identity = uuid.uuid4().hex
        self._set_asset_root(self.project_root)
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

    def seek_timeline(self, time_seconds: float) -> None:
        self.status.setText(f"Timeline time: {time_seconds:.2f}s")
        if self.project is not None and self.still_preview_approved:
            self.playback.seek(time_seconds)

    def try_playback_preview(self) -> None:
        if not self.still_preview_approved:
            QMessageBox.information(self, "Playback Preview", "Preview the still frame first. Playback is enabled after the still looks right.")
            return
        self.playback.start()

    def validate_project(self, show_dialog: bool = True) -> bool:
        if self.project is None:
            return False
        asset_root = self.project_path.resolve().parent if self.project_path else self.project_root
        messages = self.validator.validate(self.project, asset_root)
        errors = [m for m in messages if m.level == "error"]
        self.info.clear()
        if not messages:
            self.info.addItem("Validation passed")
        for msg in messages:
            self.info.addItem(f"{msg.level.upper()}: {msg.message}")
        if errors and show_dialog:
            QMessageBox.warning(self, "Validation", "Fix project errors before export.")
        return not errors

    def create_campaign(self, brief: CampaignBrief, destination: Path) -> Path:
        """Create actual project assets, open it in Studio, enable layer editing."""
        result = compose_campaign(brief, destination)
        project_path = result["project"]
        project = TTGProject.load(project_path)
        self._set_asset_root(project_path.parent)
        self.project = project
        self.project_path = project_path
        self.selected_layer_id = next(
            (layer.id for layer in project.layers if layer.name == "Hero headline"),
            project.layers[0].id if project.layers else None,
        )
        self.still_preview_approved = False
        self.history.clear()
        self.refresh_all()
        self.status.setText(
            f"Campaign ready: {len(project.layers)} editable layers. Saved to {project_path}"
        )
        return project_path

    def design_campaign(self) -> None:
        dialog = CampaignDesignerDialog(self)
        try:
            if dialog.exec() != dialog.DialogCode.Accepted:
                return
            brief = dialog.brief()
            base = Path.home() / "Documents" / "TTG Creative Studio" / "Projects"
            folder = base / f"{brief.layout}-{uuid.uuid4().hex[:8]}"
            self.create_campaign(brief, folder)
        except Exception as exc:
            QMessageBox.warning(self, "Campaign Designer", str(exc))
        finally:
            dialog.close()

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
            self._set_asset_root(Path(path).resolve().parent)
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
        self._set_asset_root(self.project_path.resolve().parent)
        self.recovery_store.clear(self.project_path)
        self._autosave_last = None
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

    def open_online_image(self) -> None:
        """Cloud output belongs to the current saved project, not a random folder."""
        if self.project is None:
            self.new_project()
        if self.project_path is None:
            self.save_project()
        if self.project_path is None:
            return
        target=self.project_path.resolve().parent/"assets"/"image-lab"
        dialog=OnlineImageDialog(
            import_callback=self.import_image_lab_result,parent=self,
            destination_dir=target
        )
        dialog.exec()

    def open_online_video(self) -> None:
        """Opt-in cloud inference; no local model and no Hunter connection."""
        dialog = OnlineVideoDialog(import_callback=self.import_online_video, parent=self)
        dialog.exec()

    def import_online_video(self, path: Path) -> None:
        """Treat cloud output as untrusted media until actual stream inspection."""
        from ttg_video_media import probe_video
        info = probe_video(path)
        self.import_video_clip(path, info, include_audio=bool(info["audio_streams"]),
                               copy_into_project=False)
        self.status.setText("Cloud-generated video imported as a normal editable clip")

    def open_video_lab(self) -> None:
        """Standalone, model-free video inspection and editable timeline import."""
        dialog = VideoLabDialog(parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        if not dialog.metadata:
            return
        try:
            self.import_video_clip(
                Path(dialog.filename.text().strip()),
                dialog.metadata,
                timeline_start=dialog.project_start.value(),
                trim_in=dialog.trim_in.value(),
                trim_out=dialog.trim_out.value(),
                speed=dialog.speed.value(),
                copy_into_project=dialog.portable.isChecked(),
                include_audio=dialog.import_audio.isChecked(),
            )
        except Exception as exc:
            QMessageBox.warning(self, "Video Lab", str(exc))

    def edit_selected_video_timing(self) -> None:
        layer=self.selected_layer()
        if layer is None or layer.type != "video":
            QMessageBox.information(self, "Video Timing", "Select a video layer first.")
            return
        from ttg_video_media import probe_video
        asset_root=self.project_path.resolve().parent if self.project_path else self.project_root
        path=Path(layer.properties["path"])
        source=path if path.is_absolute() else asset_root/path
        try:
            source_info=probe_video(source)
            dialog=VideoTrimDialog(layer.properties,source_info["duration"],self)
            if dialog.exec() != dialog.DialogCode.Accepted:
                return
            has_audio=any(m.get("clip_layer_id")==layer.id for m in self.project.audio_markers)
            if has_audio and dialog.speed.value()!=1:
                raise ValueError("Remove this clip's audio before changing speed from 1×")
            self.remember("edit video trim")
            layer.properties.update({
                "start":dialog.start.value(), "source_in":dialog.trim_in.value(),
                "source_out":dialog.trim_out.value(), "speed":dialog.speed.value()
            })
            if has_audio:
                for marker in self.project.audio_markers:
                    if marker.get("clip_layer_id")==layer.id:
                        marker["start"]=dialog.start.value()
                        marker["source_in"]=dialog.trim_in.value()
                        marker["duration"]=dialog.trim_out.value()-dialog.trim_in.value()
            self.project.canvas.duration=max(
                self.project.canvas.duration,
                dialog.start.value()+
                (dialog.trim_out.value()-dialog.trim_in.value())/dialog.speed.value()
            )
            self.still_preview_approved=False
            self.refresh_all()
            self.autosave_snapshot()
            self.status.setText("Video clip timing updated non-destructively")
        except Exception as exc:
            QMessageBox.warning(self,"Video Timing",str(exc))

    def import_video_clip(
        self, source: Path, metadata: dict, *, timeline_start: float = 0,
        trim_in: float = 0, trim_out: float | None = None, speed: float = 1,
        copy_into_project: bool = False, include_audio: bool = True
    ) -> None:
        """Add an editable real-media layer. Linking uses no duplicate storage."""
        from ttg_video_media import probe_video
        import hashlib
        import os
        import tempfile
        source = source.expanduser().resolve(strict=True)
        observed = probe_video(source)
        if (observed["width"] != metadata["width"] or
            observed["height"] != metadata["height"] or
            observed["size_bytes"] != metadata["size_bytes"] or
            observed["mtime_ns"] != metadata.get("mtime_ns")):
            raise ValueError("Source video changed since inspection; inspect it again")
        if self.project is None:
            self.new_project()
        if self.project is None:
            return
        source_out = observed["duration"] if trim_out is None else trim_out
        if not (0 <= trim_in < source_out <= observed["duration"]):
            raise ValueError("Video trim is outside the physical source")
        if not (0.25 <= speed <= 4):
            raise ValueError("Video speed must be 0.25–4×")
        timeline_end = timeline_start + (source_out - trim_in) / speed
        if timeline_start < 0 or timeline_end > 600:
            raise ValueError("Trim clip to fit within the 600-second Studio timeline")
        if self.project_path is None:
            self.save_project()
        if self.project_path is None:
            return
        root = self.project_path.resolve().parent
        if copy_into_project:
            folder = root / "assets" / "video"
            folder.mkdir(parents=True, exist_ok=True)
            # Avoid gigabyte-scale duplication when importing the same source.
            digest = hashlib.sha256()
            with source.open("rb") as handle:
                for block in iter(lambda: handle.read(1024*1024), b""):
                    digest.update(block)
            dest = folder / (digest.hexdigest()[:20] + source.suffix.lower())
            if dest.exists():
                existing = hashlib.sha256()
                with dest.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024*1024), b""):
                        existing.update(chunk)
                if existing.hexdigest() != digest.hexdigest():
                    raise ValueError("A different media file already uses this asset identity")
            else:
                fd, staged = tempfile.mkstemp(prefix=".clip-", dir=folder)
                try:
                    with os.fdopen(fd, "wb") as target, source.open("rb") as origin:
                        shutil.copyfileobj(origin, target, length=1024*1024)
                        target.flush()
                        os.fsync(target.fileno())
                    os.replace(staged, dest)
                finally:
                    Path(staged).unlink(missing_ok=True)
            source = dest
        try:
            reference = source.relative_to(root).as_posix()
        except ValueError:
            reference = str(source)
        self.remember("import video clip")
        self.project.canvas.duration = max(self.project.canvas.duration, timeline_end)
        layer = self.action.add_video(
            self.project, reference, duration=observed["duration"],
            width=observed["width"], height=observed["height"],
            source_in=trim_in, source_out=trim_out, start=timeline_start, speed=speed,
        )
        # Explicit source audio selection preserves the video's trim and timeline.
        if include_audio and observed["audio_streams"] and speed == 1:
            self.project.audio_markers.append({
                "path": reference, "start": timeline_start,
                "clip_layer_id": layer.id,
                "source_in": trim_in,
                "duration": (observed["duration"] if trim_out is None else trim_out) - trim_in,
                "volume": 1.0
            })
        self.selected_layer_id = layer.id
        self.still_preview_approved = False
        self.refresh_all()
        self.autosave_snapshot()
        self.status.setText(
            f"Video clip imported: {layer.name} · " +
            ("portable media asset" if copy_into_project else "linked source, no duplicate")
        )

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
            removed_id = self.selected_layer_id
            self.action.remove_layer(self.project, removed_id)
            # Remove only the audio explicitly owned by the removed clip.
            self.project.audio_markers = [
                marker for marker in self.project.audio_markers
                if marker.get("clip_layer_id") != removed_id
            ]
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
        elif preset == "fade_out":
            self.timeline_actions.add_fade_out(self.project, self.selected_layer_id)
        elif preset == "slide_up":
            self.timeline_actions.add_slide_up(self.project, self.selected_layer_id)
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
        """Export native video asynchronously without freezing the editor."""
        if self._video_export_worker is not None and self._video_export_worker.isRunning():
            QMessageBox.information(self, "Export MP4", "An MP4 export is already running.")
            return
        if not self.project or not self.validate_project():
            return
        if not self.still_preview_approved:
            QMessageBox.information(self, "Export MP4", "Preview the still frame first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export MP4", "ttg-export.mp4", "MP4 (*.mp4)"
        )
        if not path:
            return
        if not path.lower().endswith(".mp4"):
            path += ".mp4"
        from copy import deepcopy
        snapshot = deepcopy(self.project)
        asset_root = self.project_path.resolve().parent if self.project_path else self.project_root
        scratch = Path(tempfile.gettempdir()) / "ttg_mp4_export"
        self._video_export_worker = VideoExportThread(snapshot, asset_root, Path(path), scratch)
        self._video_export_worker.completed.connect(self._video_export_complete)
        self._video_export_worker.failed.connect(self._video_export_failed)
        self.status.setText("Rendering MP4 in background. Editor remains responsive.")
        self._video_export_worker.start()

    def _video_export_complete(self, filename: str) -> None:
        self.status.setText(f"Exported verified MP4: {filename}")

    def _video_export_failed(self, message: str) -> None:
        self.status.setText("Video export failed; original output preserved.")
        QMessageBox.warning(self, "Video Export", message)

    def closeEvent(self, event) -> None:
        if self._video_export_worker is not None and self._video_export_worker.isRunning():
            QMessageBox.information(self, "Video Export", "An MP4 export is still running.")
            event.ignore()
            return
        super().closeEvent(event)
