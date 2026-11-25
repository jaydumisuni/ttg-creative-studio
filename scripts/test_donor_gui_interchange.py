"""Actual Qt workspace routing for donor import/export; no real desktop clicks required."""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))

from PIL import Image


def main() -> int:
    from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox, QToolButton
    from ttg_creative_app import CreativeStudioWindow
    from ttg_project_schema import CanvasSpec, Layer, TTGProject

    app = QApplication.instance() or QApplication([])
    with TemporaryDirectory() as d:
        root = Path(d)
        project = TTGProject(name="donor GUI source",project_type="image")
        project.canvas = CanvasSpec(width=100,height=70,background="#0F1234")
        project.layers = [
            Layer(id="shape",type="shape",name="TTG panel",
                  properties={"shape":"rectangle","width":35,"height":20,"fill":"#00E5FF"})
        ]
        source = root/"original.ttgstudio.json"
        project.save(source)
        window = CreativeStudioWindow()
        workspace = window.centralWidget()
        menus = {
            button.text(): [action.text() for action in button.menu().actions()]
            for button in workspace.findChildren(QToolButton)
            if button.menu() is not None
        }
        assert "File" in menus and "Export" in menus
        assert any("PhotoCraft" in line for line in menus["File"])
        assert any("FilmCraft" in line for line in menus["File"])
        assert any("EffectCraft" in line for line in menus["File"])
        assert any("MaterialCraft" in line for line in menus["File"])
        assert any("VectorCraft" in line for line in menus["File"])
        assert any("VectorCraft" in line for line in menus["Export"])
        workspace.project = project
        workspace.project_path = source

        svg = root/"live-vector.svg"
        with patch.object(QFileDialog,"getSaveFileName",return_value=(str(svg),"")):
            workspace.export_vector_svg()
        assert svg.exists()

        imported = root/"vector-editable.ttgstudio.json"
        with (patch.object(QFileDialog,"getOpenFileName",return_value=(str(svg),"")),
              patch.object(QFileDialog,"getSaveFileName",return_value=(str(imported),"")),
              patch.object(QMessageBox,"question",
                           return_value=QMessageBox.StandardButton.Yes)):
            workspace.import_vector_svg()
        assert imported.exists() and workspace.project_path == imported
        assert len(workspace.project.layers) == 2

        lottie = root/"editable-lottie.json"
        with patch.object(QFileDialog,"getSaveFileName",return_value=(str(lottie),"")):
            workspace.export_lottie()
        assert lottie.exists()

        ora = root/"layers.ora"
        with patch.object(QFileDialog,"getSaveFileName",return_value=(str(ora),"")):
            workspace.export_openraster()
        assert ora.exists()

        reopened = root/"layers.ttgstudio.json"
        with (patch.object(QFileDialog,"getOpenFileName",return_value=(str(ora),"")),
              patch.object(QFileDialog,"getSaveFileName",return_value=(str(reopened),"")),
              patch.object(QMessageBox,"question",
                           return_value=QMessageBox.StandardButton.Yes)):
            workspace.import_openraster()
        assert reopened.exists()
        assert workspace.project_path == reopened
        assert workspace.project is not None
        assert workspace.project.layers[0].type == "image"
        assert TTGProject.load(source).layers[0].type == "shape"
        window.close()
    app.processEvents()
    print("STUDIO_DONOR_QT_MENU_AND_REAL_INTERCHANGE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
