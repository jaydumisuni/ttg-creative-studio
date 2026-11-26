"""CADCraft ARC source preservation and negative cases."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from ttg_cadcraft_dxf_bridge import import_dxf, export_dxf
from ttg_project_schema import TTGProject
from ttg_canvas_engine import CanvasRenderer,RenderContext


def _dxf(*entities: str) -> str:
    return ("0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1015\n"
            "9\n$INSUNITS\n70\n4\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n"
            + "".join(entities) + "0\nENDSEC\n0\nEOF\n")


def _arc(cx=100,cy=100,r=50,start=30,end=150):
    return (f"0\nARC\n8\nPrecise\n420\n65535\n"
            f"10\n{cx}\n20\n{cy}\n30\n0\n40\n{r}\n50\n{start}\n51\n{end}\n")


class CadArcSourceTests(TestCase):
    def test_arc_editable_studio_primitive_and_source_preserved(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            source=root/"arc.dxf";source.write_text(_dxf(_arc()))
            output=root/"editable.ttgstudio.json"
            info=import_dxf(source,output,canvas_width=220,canvas_height=220,units="mm")
            self.assertEqual(info["layers"],1)
            p=TTGProject.load(output)
            layer=p.layers[0]
            self.assertEqual(layer.type,"connector_line")
            self.assertEqual(layer.properties["cad_layer"],"Precise")
            self.assertEqual(layer.properties["cad_arc"]["center"],[100,100])
            self.assertEqual(layer.properties["cad_arc"]["radius"],50)
            self.assertEqual(layer.properties["cad_arc"]["start_degrees"],30)
            self.assertEqual(layer.properties["cad_arc"]["end_degrees"],150)
            self.assertGreater(len(layer.properties["points"]),20)
            canvas=CanvasRenderer(RenderContext(root)).render(p)
            self.assertEqual(canvas.size,(220,220))
            self.assertIsNotNone(canvas.getbbox())
            back=root/"exported.dxf"
            self.assertEqual(export_dxf(p,back,units="mm")["entities"],1)
            content=back.read_text()
            self.assertIn("0\nARC\n",content)
            self.assertIn("50\n30\n51\n150\n",content)
            reopened=root/"reopened.ttgstudio.json"
            import_dxf(back,reopened,canvas_width=220,canvas_height=220,units="mm")
            self.assertEqual(TTGProject.load(reopened).layers[0].properties["cad_arc"]["radius"],50)

    def test_wrapped_arc_and_edit_rejection(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            source=root/"wrapped.dxf";source.write_text(_dxf(_arc(90,80,50,300,60)))
            out=root/"wrapped.ttgstudio.json"
            import_dxf(source,out,canvas_width=190,canvas_height=150,units="mm")
            p=TTGProject.load(out)
            self.assertEqual(p.layers[0].properties["cad_arc"]["start_degrees"],300)
            self.assertEqual(len(p.layers[0].properties["points"]),25)
            p.layers[0].properties["points"][5][0]+=0.25
            with self.assertRaisesRegex(ValueError,"explicitly converted"):
                export_dxf(p,root/"must-not-export.dxf",units="mm")
            self.assertFalse((root/"must-not-export.dxf").exists())

    def test_high_precision_source_arc_and_unmapped_transform_fail_closed(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            source=root/"fractional.dxf"
            source.write_text(_dxf(_arc(
                110.1234567890123,98.1234567890123,44.1234567890123,
                20.123456789,190.987654321)))
            ppath=root/"precise.ttgstudio.json"
            import_dxf(source,ppath,canvas_width=220,canvas_height=220,units="mm")
            original=TTGProject.load(ppath)
            exported=root/"again.dxf"
            export_dxf(original,exported,units="mm")
            reimported=root/"reimport.ttgstudio.json"
            import_dxf(exported,reimported,canvas_width=220,canvas_height=220,units="mm")
            x=TTGProject.load(reimported).layers[0].properties["cad_arc"]
            self.assertAlmostEqual(x["center"][0],110.1234567890123,places=12)
            self.assertAlmostEqual(x["center"][1],98.1234567890123,places=12)
            self.assertAlmostEqual(x["radius"],44.1234567890123,places=12)
            self.assertAlmostEqual(x["start_degrees"],20.123456789,places=9)
            self.assertAlmostEqual(x["end_degrees"],190.987654321,places=9)
            original.layers[0].transform.x=1
            with self.assertRaisesRegex(ValueError,"transform"):
                export_dxf(original,root/"unmapped.dxf",units="mm")
            self.assertFalse((root/"unmapped.dxf").exists())

    def test_zero_sweep_3d_and_outside_rejected_without_artifact(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            cases=[
                (_arc(70,70,40,120,120),"Full-circle"),
                (_arc(70,70,40,5,360),"angle 360"),
                (_arc(4,4,40,180,270),"crosses canvas"),
                (_arc(70,70,40,0,90).replace("30\n0\n","30\n5\n"),"3D adapter"),
            ]
            for i,(entity,error) in enumerate(cases):
                src=root/f"arc{i}.dxf";src.write_text(_dxf(entity))
                out=root/f"arc{i}.ttgstudio.json"
                with self.assertRaisesRegex(ValueError,error):
                    import_dxf(src,out,canvas_width=160,canvas_height=160,units="mm")
                self.assertFalse(out.exists())


if __name__=="__main__":
    main()
