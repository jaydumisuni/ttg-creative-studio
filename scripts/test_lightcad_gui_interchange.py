"""Use actual offscreen PyQt6 Studio File/Export actions for LightCraft and CADCraft."""
from __future__ import annotations
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sys

from PIL import Image
from _synthetic_dng_fixture import write_synthetic_dng

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))


def main():
    from PyQt6.QtWidgets import QApplication,QFileDialog,QMessageBox,QInputDialog,QToolButton
    from ttg_creative_app import CreativeStudioWindow
    from ttg_project_schema import TTGProject,CanvasSpec,Layer

    app=QApplication.instance() or QApplication([])
    def no_warning(_parent,title,message,*args,**kw):
        raise AssertionError(f"Unexpected LightCraft/CADCraft warning: {title}: {message}")
    with (
        TemporaryDirectory() as tmp,
        patch.object(QMessageBox,"warning",side_effect=no_warning),
        patch.object(QMessageBox,"information",return_value=QMessageBox.StandardButton.Ok),
    ):
        root=Path(tmp)
        raw=root/"picture.dng";write_synthetic_dng(raw)
        image=root/"developed.png";Image.new("RGB",(24,16),(100,120,140)).save(image)
        win=CreativeStudioWindow()
        workspace=win.centralWidget()
        menu={
            button.text():[action.text() for action in button.menu().actions()]
            for button in workspace.findChildren(QToolButton)
            if button.menu() is not None
        }
        assert any("LightCraft" in text for text in menu["File"])
        assert "Develop RAW with Builder source engine" in menu["File"]
        assert any("CADCraft" in text for text in menu["File"])
        assert any("CADCraft" in text for text in menu["Export"])

        imported=root/"rawimport.ttgstudio.json"
        with (
            patch.object(QFileDialog,"getOpenFileName",
                         side_effect=[(str(raw),""),(str(image),"")]),
            patch.object(QFileDialog,"getSaveFileName",
                         return_value=(str(imported),"")),
            patch.object(QMessageBox,"question",
                         return_value=QMessageBox.StandardButton.Yes),
        ):
            workspace.import_lightcraft_render()
        assert imported.exists() and workspace.project_path==imported
        assert workspace.project.layers[0].type=="image"

        geometry=TTGProject(name="vector CAD",project_type="diagram")
        geometry.canvas=CanvasSpec(width=120,height=80,background="#00000000")
        geometry.layers=[
            Layer(id="line",type="connector_line",name="vector",
                  properties={"points":[[10,15],[90,50]],"color":"#00E5FF",
                              "stroke_width":3}),
        ]
        source=root/"lines.ttgstudio.json";geometry.save(source)
        workspace.project=geometry;workspace.project_path=source
        dxf=root/"lines.dxf"
        with (
            patch.object(QInputDialog,"getItem",return_value=("mm",True)),
            patch.object(QFileDialog,"getSaveFileName",
                         return_value=(str(dxf),"")),
        ):
            workspace.export_cadcraft_dxf()
        assert dxf.is_file()

        reimported=root/"lines-read.ttgstudio.json"
        with (
            patch.object(QFileDialog,"getOpenFileName",
                         return_value=(str(dxf),"")),
            patch.object(QInputDialog,"getInt",
                         side_effect=[(120,True),(80,True)]),
            patch.object(QInputDialog,"getItem",return_value=("mm",True)),
            patch.object(QFileDialog,"getSaveFileName",
                         return_value=(str(reimported),"")),
            patch.object(QMessageBox,"question",
                         return_value=QMessageBox.StandardButton.Yes),
        ):
            workspace.import_cadcraft_dxf()
        assert reimported.exists() and workspace.project_path==reimported
        assert workspace.project.layers[0].type=="connector_line"
        assert TTGProject.load(source).layers[0].type=="connector_line"
        win.close()
    app.processEvents()
    print("STUDIO_LIGHTCRAFT_CADCRAFT_REAL_QT_ACTIONS_PASS")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
