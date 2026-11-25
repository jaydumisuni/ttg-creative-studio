"""Existing Studio CLI and Hunter job contract use the same donor exchange paths."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from ttg_project_schema import CanvasSpec, Layer, TTGProject
from ttg_creative_studio.cli import DONOR_TASKS, run_donor_interchange_job


class DonorJobRouting(unittest.TestCase):
    def test_registered_operations_and_real_lottie_job(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            src=ROOT/"tests/fixtures/effectcraft_bouncing_ball.json"
            output=root/"actual.ttgstudio.json"
            self.assertEqual(len(DONOR_TASKS),9)
            receipt=run_donor_interchange_job({
                "task":"studio_import_lottie", "input":str(src.resolve()),
                "output":str(output.resolve()), "jobId":"donor-prove-1",
            })
            self.assertTrue(receipt["ok"])
            self.assertEqual(receipt["task"],"studio_import_lottie")
            self.assertTrue(output.is_file())
            self.assertEqual(TTGProject.load(output).layers[0].name,"Ball")
            with self.assertRaises(FileExistsError):
                run_donor_interchange_job({
                    "task":"studio_import_lottie", "input":str(src.resolve()),
                    "output":str(output.resolve()),
                })

    def test_manual_cli_export_svg_from_existing_canonical_project(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            project=TTGProject(name="CLI editor")
            project.canvas=CanvasSpec(width=120,height=100)
            project.layers=[Layer(id="shape",name="shape",type="shape",
                                  properties={"shape":"rectangle","width":30,
                                              "height":20,"fill":"#FF00FF"})]
            source=root/"source.ttgstudio.json"
            project.save(source)
            out=root/"out.svg"
            p=subprocess.run(
                [sys.executable,str(ROOT/"scripts/creative_cli.py"),"export-svg",
                 str(source),str(out)],
                capture_output=True,text=True,timeout=12,check=True,
            )
            self.assertEqual(json.loads(p.stdout)["format"],"svg")
            self.assertIn("<",out.read_text())
            reopen=root/"roundtrip.ttgstudio.json"
            q=subprocess.run(
                [sys.executable,str(ROOT/"scripts/creative_cli.py"),"import-svg",
                 str(out),str(reopen)],
                capture_output=True,text=True,timeout=12,check=True,
            )
            self.assertEqual(json.loads(q.stdout)["layers"],2)
            self.assertEqual(TTGProject.load(reopen).layers[1].type,"shape")

    def test_catalog_includes_only_explicit_supported_interchange(self):
        p=subprocess.run([sys.executable,str(ROOT/"src/ttg_creative_studio/cli.py"),
                          "--catalog"],capture_output=True,text=True,timeout=16,check=True)
        catalog=json.loads(p.stdout)
        self.assertEqual(set(DONOR_TASKS),
                         {k for k in catalog["operations"] if k in DONOR_TASKS})
        self.assertNotIn("studio_execute_donor_arbitrary_command",catalog["operations"])


if __name__=="__main__":
    unittest.main()
