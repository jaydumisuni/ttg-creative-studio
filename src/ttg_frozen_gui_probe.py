"""Noninteractive physical GUI QA for a source or PyInstaller frozen Studio app.

This opens the actual QMainWindow and editable workspace. It records a
real window grab, saved Studio document, PNG export and manifest in a
caller-created, empty proof directory. It does not claim visual owner approval.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image
from PyQt6.QtWidgets import QApplication

from ttg_action_engine import ActionEngine
from ttg_creative_app import CreativeStudioWindow
from ttg_project_schema import TTGProject


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify_gui(proof_dir: Path) -> dict:
    proof_dir = proof_dir.expanduser().resolve(strict=True)
    if not proof_dir.is_dir() or list(proof_dir.iterdir()):
        raise ValueError("GUI proof destination must be an existing empty directory")

    app = QApplication.instance() or QApplication([])
    win = CreativeStudioWindow()
    try:
        win.resize(1280, 800)
        win.show()
        app.processEvents()
        assert win.isVisible(), "Main application window failed to open"
        studio = win.centralWidget()
        assert studio.campaign_button.isEnabled(), "Campaign action is unreachable"
        assert studio.toolbar_scroll.widget() is not None
        assert studio.layer_list is not None

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
        screenshot = proof_dir / "gui-window.png"
        app.processEvents()
        assert win.grab().save(str(screenshot), "PNG")
        with Image.open(screenshot) as shot:
            assert shot.width >= 1024 and shot.height >= 640
            assert shot.getbbox() is not None

        report = {
            "schema": "ttg.creative.frozen-gui-qualification.v1",
            "result": "PASS",
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
        (proof_dir / "gui-proof.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        return report
    finally:
        win.close()
        app.processEvents()
