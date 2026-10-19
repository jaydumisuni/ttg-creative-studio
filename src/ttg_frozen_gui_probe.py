"""Noninteractive physical GUI QA for a source or PyInstaller frozen Studio app.

This opens the actual QMainWindow and editable workspace. It records a
real window grab, saved Studio document, PNG export and manifest in a
caller-created, empty proof directory. It does not claim visual owner approval.
"""
from __future__ import annotations

import hashlib
import os
import json
from pathlib import Path

from PIL import Image
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QApplication

from ttg_action_engine import ActionEngine
from ttg_creative_app import CreativeStudioWindow
from ttg_project_schema import TTGProject


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify_gui(proof_dir: Path) -> dict:
    def phase(label: str) -> None:
        # Written only for installed frozen-app QA, not direct unit tests.
        stage = os.environ.get("TTG_STUDIO_GUI_STAGE_FILE")
        if stage:
            Path(stage).write_text(label + "\n", encoding="utf-8")

    phase("qualifier-entered")
    proof_dir = proof_dir.expanduser().resolve(strict=True)
    expected_trace = os.environ.get("TTG_STUDIO_GUI_STAGE_FILE")
    diagnostic_files = set()
    if expected_trace and Path(expected_trace).parent.resolve() == proof_dir:
        diagnostic_files = {Path(expected_trace).name, "gui-hang-stack.txt"}
    if not proof_dir.is_dir() or any(
        item.name not in diagnostic_files for item in proof_dir.iterdir()
    ):
        raise ValueError("GUI proof destination must be an existing empty directory")

    phase("qt-application")
    app = QApplication.instance() or QApplication([])
    phase("constructing-main-window")
    win = CreativeStudioWindow()
    phase("constructed-main-window")
    try:
        win.resize(1280, 800)
        phase("show-window")
        win.show()
        app.processEvents()
        assert win.isVisible(), "Main application window failed to open"
        studio = win.centralWidget()
        assert studio.campaign_button.isEnabled(), "Campaign action is unreachable"
        assert studio.toolbar_scroll.widget() is not None
        assert studio.layer_list is not None

        # QT_QPA_PLATFORM=offscreen on Windows can render missing font
        # glyphs as identical squares, despite passing a GUI screenshot
        # existence test. Qualify real proportional Latin glyph metrics
        # in the *actual* themed widget font, not a fresh unrelated QFont.
        phase("measure-themed-font")
        ui_font = studio.campaign_button.font()
        ui_metrics = QFontMetrics(ui_font)
        narrow = ui_metrics.horizontalAdvance("iiiiii")
        wide = ui_metrics.horizontalAdvance("WWWWWW")
        assert narrow > 0 and wide > narrow * 1.3, (
            f"Unreadable/missing Windows UI font: {ui_font.family()!r}, "
            f"narrow={narrow}, wide={wide}"
        )

        phase("create-test-project")
        project = ActionEngine().new_project("Standalone Installed GUI QA", "image")
        project.canvas.width, project.canvas.height = 480, 320
        shape = ActionEngine().add_shape(project, "rectangle", 76, 61)
        shape.properties["fill"] = "#0B98CC"
        layer = ActionEngine().add_text(project, "STUDIO READY", 95, 145)
        layer.properties["size"] = 42
        studio.reset_project(project)
        studio.project_path = proof_dir / "gui-editable.ttgstudio.json"
        studio._set_asset_root(proof_dir)
        studio.selected_layer_id = layer.id
        phase("refresh-project-widgets")
        studio.refresh_all()
        app.processEvents()
        assert studio.selected_layer().id == layer.id
        assert studio.layer_list.count() == 2

        studio.apply_property_change("text", "EDITED IN STUDIO")
        assert studio.selected_layer().properties["text"] == "EDITED IN STUDIO"
        studio.undo()
        assert studio.selected_layer().properties["text"] == "STUDIO READY"
        studio.redo()
        assert studio.selected_layer().properties["text"] == "EDITED IN STUDIO"
        phase("save-edited-project")
        studio.save_project()
        saved = TTGProject.load(studio.project_path)
        assert len(saved.layers) == 2
        assert next(x for x in saved.layers if x.id == layer.id).properties["text"] == "EDITED IN STUDIO"

        png = proof_dir / "gui-export.png"
        studio.export_service.export_png(studio.project, png)
        with Image.open(png) as rendered:
            assert rendered.size == (480, 320)
            assert len(rendered.convert("RGB").getcolors(480 * 320) or []) > 4, (
                "Rendered canvas appears blank/monochrome"
            )
        phase("capture-native-window")
        screenshot = proof_dir / "gui-window.png"
        app.processEvents()
        assert win.grab().save(str(screenshot), "PNG")
        with Image.open(screenshot) as shot:
            assert shot.width >= 1024 and shot.height >= 640
            assert shot.getbbox() is not None

        report = {
            "schema": "ttg.creative.frozen-gui-qualification.v1",
            "result": "PASS",
            "ui_font_evidence": {"family": ui_font.family(),
                                 "narrow_advance": narrow,
                                 "wide_advance": wide},
            "checks": [
                "real QWidget window shown",
                "Campaign Designer reachable",
                "native two-layer canvas loaded",
                "editable layer selection",
                "Properties editing",
                "Undo and Redo",
                "native project save and reload",
                "real exported nonblank PNG",
                "actual full application window screenshot",
            ],
            "artifacts": {
                file.name: {
                    "sha256": _sha(file),
                    "bytes": file.stat().st_size,
                }
                for file in (studio.project_path, png, screenshot)
            },
        }
        phase("write-proof-manifest")
        (proof_dir / "gui-proof.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        phase("proof-complete")
        return report
    finally:
        phase("close-window")
        win.close()
        app.processEvents()
