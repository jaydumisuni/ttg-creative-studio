"""LightCraft/CADCraft on incumbent Studio command surfaces: genuine local files."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import subprocess
import sys
import unittest

from PIL import Image
from _synthetic_dng_fixture import write_synthetic_dng

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ttg_creative_studio.cli import DONOR_TASKS,run_donor_interchange_job
from ttg_cadcraft_dxf_bridge import export_dxf
from ttg_project_schema import TTGProject,CanvasSpec,Layer


class LightCadRoutingTests(unittest.TestCase):
    def test_hunter_job_raw_import_and_builder_source_requirement(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            raw=root/"camera.dng";write_synthetic_dng(raw)
            png=root/"developed.png";Image.new("RGB",(12,8),(25,75,125)).save(png)
            dest=root/"imported.ttgstudio.json"
            result=run_donor_interchange_job({
                "task":"studio_import_lightcraft_raw",
                "input":str(raw.resolve()),"output":str(dest.resolve()),
                "options":{"preview_png":str(png.resolve())},
            })
            self.assertTrue(result["ok"])
            self.assertTrue(dest.is_file())
            self.assertEqual(TTGProject.load(dest).canvas.width,12)
            with self.assertRaisesRegex(Exception,"Builder receipt"):
                run_donor_interchange_job({
                    "task":"studio_develop_lightcraft_raw",
                    "input":str(raw.resolve()),
                    "output":str(root/"cannot.ttgstudio.json"),
                    "options":{},
                })
            with self.assertRaisesRegex(Exception,"not arbitrary executables"):
                run_donor_interchange_job({
                    "task":"studio_develop_lightcraft_raw",
                    "input":str(raw.resolve()),
                    "output":str(root/"blocked.ttgstudio.json"),
                    "options":{"lightcraft_cli":str(root/"unreviewed")},
                })

    def test_cad_export_import_same_hunter_job_interface(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            project=TTGProject(name="CAD test",project_type="diagram")
            project.canvas=CanvasSpec(width=120,height=80,background="#00000000")
            project.layers=[
                Layer(id="wire",type="connector_line",name="wire",
                      properties={"points":[[5,12],[50,42]],"color":"#00FF00",
                                  "stroke_width":3}),
            ]
            original=root/"source.ttgstudio.json";project.save(original)
            dxf=root/"drawing.dxf"
            result=run_donor_interchange_job({
                "task":"studio_export_dxf","input":str(original.resolve()),
                "output":str(dxf.resolve()),"options":{"units":"mm"},
            })
            self.assertTrue(result["ok"])
            dest=root/"reopened.ttgstudio.json"
            imported=run_donor_interchange_job({
                "task":"studio_import_dxf","input":str(dxf.resolve()),
                "output":str(dest.resolve()),
                "options":{"width":120,"height":80,"units":"mm"},
            })
            self.assertTrue(imported["ok"])
            self.assertEqual(TTGProject.load(dest).layers[0].properties["points"],
                             [[5,12],[50,42]])

    def test_manual_cli_raw_and_dxf_are_genuine_invocable_commands(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            raw=root/"source.dng";write_synthetic_dng(raw)
            image=root/"raw.png";Image.new("RGB",(10,10),(33,66,99)).save(image)
            project=root/"raw.ttgstudio.json"
            p=subprocess.run([
                sys.executable,str(ROOT/"scripts/creative_cli.py"),
                "import-lightcraft-raw",str(raw),str(image),str(project),
            ],capture_output=True,text=True,timeout=15,check=True)
            self.assertEqual(json.loads(p.stdout)["format"],"lightcraft_developed_raw")
            self.assertTrue(project.is_file())

            # The native 2D CAD CLI operates on exact Studio source files.
            drawing=TTGProject(name="Wire",project_type="diagram")
            drawing.canvas=CanvasSpec(width=100,height=70,background="#00000000")
            drawing.layers=[
                Layer(id="l",type="connector_line",name="wire",
                      properties={"points":[[5,10],[50,40]],"color":"#FF0000",
                                  "stroke_width":3}),
            ]
            source=root/"drawing.ttgstudio.json";drawing.save(source)
            dxf=root/"export.dxf"
            proc=subprocess.run([
                sys.executable,str(ROOT/"scripts/creative_cli.py"),
                "export-dxf",str(source),str(dxf),"--units","mm",
            ],capture_output=True,text=True,timeout=15,check=True)
            self.assertEqual(json.loads(proc.stdout)["entities"],1)
            project2=root/"read.ttgstudio.json"
            proc=subprocess.run([
                sys.executable,str(ROOT/"scripts/creative_cli.py"),
                "import-dxf",str(dxf),str(project2),
                "--width","100","--height","70","--units","mm",
            ],capture_output=True,text=True,timeout=15,check=True)
            self.assertEqual(json.loads(proc.stdout)["layers"],1)
            self.assertEqual(TTGProject.load(project2).layers[0].type,"connector_line")

    def test_catalog_discloses_bounded_native_capabilities(self):
        self.assertTrue({
            "studio_import_lightcraft_raw","studio_develop_lightcraft_raw",
            "studio_import_dxf","studio_export_dxf",
        }.issubset(DONOR_TASKS))
        proc=subprocess.run([
            sys.executable,str(ROOT/"src/ttg_creative_studio/cli.py"),"--catalog",
        ],capture_output=True,text=True,timeout=18,check=True)
        catalog=json.loads(proc.stdout)
        self.assertTrue(set(DONOR_TASKS).issubset(catalog["operations"]))
        self.assertNotIn("studio_run_any_external_executable",catalog["operations"])


if __name__=="__main__":
    unittest.main()
