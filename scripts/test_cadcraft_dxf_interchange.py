"""CADCraft-compatible ASCII DXF presentation exchange checks."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from ttg_cadcraft_dxf_bridge import import_dxf, export_dxf
from ttg_project_schema import TTGProject, Layer, CanvasSpec, Transform
from ttg_canvas_engine import CanvasRenderer, RenderContext


class CadCraftDXFInterop(TestCase):
    def _source(self):
        project=TTGProject(name="CAD drawing",project_type="diagram")
        project.canvas=CanvasSpec(width=160,height=100,background="#00000000")
        project.layers=[
            Layer(id="wire",type="connector_line",name="Wire",
                  properties={"points":[[10,20],[30,30]],"color":"#00FFFF",
                              "stroke_width":3,"cad_layer":"Wires"}),
            Layer(id="route",type="connector_line",name="Route",
                  properties={"points":[[30,20],[65,40],[130,60]],"color":"#FF0000",
                              "stroke_width":3,"cad_layer":"Routes"}),
            Layer(id="circle",type="shape",name="Outline",
                  transform=Transform(x=60,y=10),
                  properties={"shape":"ellipse","width":20,"height":20,
                              "fill":"#00000000","outline":"#0000FF",
                              "cad_layer":"Symbols"}),
        ]
        return project

    def test_real_ascii_dxf_roundtrip_geometry_units_and_pixels(self):
        with TemporaryDirectory() as d:
            root=Path(d);original=self._source()
            out=root/"cadcraft-export.dxf"
            receipt=export_dxf(original,out,units="mm")
            self.assertEqual(receipt["entities"],3)
            body=out.read_text()
            self.assertIn("LWPOLYLINE",body)
            self.assertIn("CIRCLE",body)
            self.assertIn("$INSUNITS",body)
            dest=root/"editable.ttgstudio.json"
            parsed=import_dxf(out,dest,canvas_width=160,canvas_height=100,units="mm")
            self.assertFalse(parsed["geometry_authority"])
            imported=TTGProject.load(dest)
            self.assertEqual(len(imported.layers),3)
            self.assertEqual(imported.layers[0].properties["cad_layer"],"Wires")
            self.assertEqual(imported.layers[0].properties["points"],[[10,20],[30,30]])
            self.assertEqual(imported.layers[1].properties["points"],[[30,20],[65,40],[130,60]])
            self.assertEqual(imported.layers[2].transform.x,60)
            self.assertEqual(imported.layers[2].transform.y,10)
            self.assertEqual(imported.export["cadcraft_dxf"]["units"],"mm")
            a=CanvasRenderer(RenderContext(root)).render(original)
            b=CanvasRenderer(RenderContext(root)).render(imported)
            self.assertEqual(a.tobytes(),b.tobytes())
            with self.assertRaises(FileExistsError):
                import_dxf(out,dest,canvas_width=160,canvas_height=100,units="mm")

    def test_wrong_units_unsupported_arc_and_binary_rejected(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            source=root/"source.dxf"
            export_dxf(self._source(),source,units="mm")
            with self.assertRaisesRegex(ValueError,"units disagree"):
                import_dxf(source,root/"no.ttgstudio.json",
                           canvas_width=160,canvas_height=100,units="inch")
            source.write_text(source.read_text().replace("LINE\n","ARC\n",1))
            with self.assertRaisesRegex(ValueError,"Unsupported DXF entity"):
                import_dxf(source,root/"no.ttgstudio.json",
                           canvas_width=160,canvas_height=100,units="mm")
            source.write_bytes(b"\x00"*24)
            with self.assertRaisesRegex(ValueError,"ASCII DXF"):
                import_dxf(source,root/"no.ttgstudio.json",
                           canvas_width=160,canvas_height=100,units="mm")
            self.assertFalse((root/"no.ttgstudio.json").exists())

    def test_filled_and_animated_studio_shapes_not_silently_flattened(self):
        with TemporaryDirectory() as d:
            root=Path(d);p=self._source()
            p.layers[-1].properties["fill"]="#0000FF"
            with self.assertRaisesRegex(ValueError,"unfilled native circle"):
                export_dxf(p,root/"bad.dxf",units="mm")
            self.assertFalse((root/"bad.dxf").exists())

    def test_closed_polyline_keeps_last_to_first(self):
        with TemporaryDirectory() as d:
            root=Path(d);p=self._source()
            p.layers=[Layer(id="loop",type="connector_line",name="Loop",
                            properties={"points":[[1,1],[20,1],[20,20],[1,20],[1,1]],
                                        "color":"#FFFFFF","stroke_width":3})]
            export_dxf(p,root/"loop.dxf",units="inch")
            q=root/"roundtrip.ttgstudio.json"
            import_dxf(root/"loop.dxf",q,canvas_width=160,canvas_height=100,units="inch")
            self.assertEqual(TTGProject.load(q).layers[0].properties["points"],
                             p.layers[0].properties["points"])


if __name__=="__main__":
    main()
