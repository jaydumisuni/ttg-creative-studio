"""VectorCraft-compatible SVG basic shape roundtrip to editable TTG layers."""
from __future__ import annotations
import sys, unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from ttg_project_schema import TTGProject, CanvasSpec, Layer, Transform
from ttg_vectorcraft_svg_bridge import export_svg_shapes, import_svg_shapes
from ttg_canvas_engine import CanvasRenderer, RenderContext


class VectorCraftSvgTests(unittest.TestCase):
    def test_native_shapes_to_svg_and_back_keep_editability(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            project=TTGProject(name="diagram",project_type="diagram")
            project.canvas=CanvasSpec(width=120,height=90,background="#050614")
            project.layers=[
                Layer(id="rect",type="shape",name="Panel",
                      transform=Transform(x=2,y=4),
                      properties={"shape":"rectangle","width":30,"height":22,"fill":"#00E5FF"}),
                Layer(id="ellipse",type="shape",name="Badge",
                      transform=Transform(x=60,y=25),
                      properties={"shape":"ellipse","width":20,"height":20,"fill":"#BC13FE"}),
                Layer(id="wire",type="connector_line",name="Wire",
                      properties={"points":[[10,48],[100,48]],"color":"#FFFFFF","stroke_width":3}),
            ]
            source=root/"source.ttgstudio.json";project.save(source)
            expected=CanvasRenderer(RenderContext(project_root=root)).render(project)
            svg=root/"vector.svg"
            receipt=export_svg_shapes(project,svg)
            self.assertEqual(receipt["layers"],3)
            reopened=root/"vector.ttgstudio.json"
            result=import_svg_shapes(svg,reopened)
            self.assertEqual(result["layers"],4)
            p=TTGProject.load(reopened)
            self.assertEqual([x.type for x in p.layers],["shape","shape","shape","connector_line"])
            self.assertEqual(p.layers[2].properties["shape"],"ellipse")
            self.assertEqual(p.layers[-1].properties["stroke_width"],3)
            actual=CanvasRenderer(RenderContext(project_root=root)).render(p)
            self.assertEqual(expected.size,actual.size)
            self.assertEqual(expected.getpixel((10,10)),actual.getpixel((10,10)))
            self.assertEqual(expected.getpixel((68,34)),actual.getpixel((68,34)))
            self.assertEqual(expected.getpixel((10,48)),actual.getpixel((10,48)))
            self.assertEqual(TTGProject.load(source).layers[0].name,"Panel")

    def test_untrusted_svg_external_resources_script_and_path_fail_closed(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            for text in [
                '<svg width="100" height="100"><script>alert(1)</script></svg>',
                '<svg width="100" height="100"><image href="https://example.com/file"/></svg>',
                '<!DOCTYPE svg [<!ENTITY ext SYSTEM "file:///etc/passwd">]><svg width="100" height="100"></svg>',
            ]:
                src=root/"untrusted.svg";src.write_text(text)
                with self.assertRaises(ValueError):
                    import_svg_shapes(src,root/"no.ttgstudio.json")
                self.assertFalse((root/"no.ttgstudio.json").exists())

    def test_source_svg_polyline_real_pixels_and_editable_roundtrip(self):
        from xml.etree import ElementTree as ET
        with TemporaryDirectory() as d:
            root=Path(d)
            svg=root/"zigzag.svg"
            svg.write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="90" height="65"
              viewBox="0 0 90 65">
              <polyline points="6,8 34,8 34,48 70,48"
                  stroke="#00E5FF" stroke-width="3" fill="none"/>
            </svg>''')
            project=root/"zigzag.ttgstudio.json"
            receipt=import_svg_shapes(svg,project)
            self.assertEqual(receipt["layers"],1)
            p=TTGProject.load(project)
            self.assertEqual(p.layers[0].type,"connector_line")
            self.assertEqual(p.layers[0].properties["points"],
                             [[6.,8.],[34.,8.],[34.,48.],[70.,48.]])
            image=CanvasRenderer(RenderContext(root)).render(p).convert("RGBA")
            self.assertEqual(image.getpixel((20,8))[:3],(0,229,255))
            self.assertEqual(image.getpixel((34,28))[:3],(0,229,255))
            self.assertEqual(image.getpixel((50,48))[:3],(0,229,255))
            output=root/"replay.svg"
            export_svg_shapes(p,output)
            document=ET.parse(output)
            self.assertEqual(len(document.getroot()),1)
            self.assertEqual(document.getroot()[0].tag.split("}")[-1],"polyline")
            recreated=root/"returned.ttgstudio.json"
            import_svg_shapes(output,recreated)
            again=CanvasRenderer(RenderContext(root)).render(
                TTGProject.load(recreated)).convert("RGBA")
            self.assertEqual(image.tobytes(),again.tobytes())

    def test_polyline_injection_coordinate_budget_and_effects_refused(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            for points in ("0,0 1,1 2,2;script", "5,5", "0,0 999,5",
                           "0,0 10,10 20,NaN", "0,0 "+("1,1 "*130)):
                svg=root/"bad.svg"
                svg.write_text(
                    '<svg width="60" height="60"><polyline '
                    'points="'+points+'" stroke="#FFFFFF" fill="none"/></svg>'
                )
                with self.assertRaises(ValueError):
                    import_svg_shapes(svg,root/"not-created.ttgstudio.json")
                self.assertFalse((root/"not-created.ttgstudio.json").exists())
            native=TTGProject()
            native.canvas=CanvasSpec(width=60,height=60,background="#00000000")
            native.layers=[Layer(id="bad",type="connector_line",name="out",
                properties={"points":[[0,0],[100,2],[12,12]],
                            "color":"#FFFFFF","stroke_width":3})]
            with self.assertRaises(ValueError):
                export_svg_shapes(native,root/"bad-output.svg")
            self.assertFalse((root/"bad-output.svg").exists())
            native.layers[0].properties["points"]=[[0,0],[30,30],[12,12]]
            native.layers[0].properties["stroke_width"]=-1
            with self.assertRaises(ValueError):
                export_svg_shapes(native,root/"bad-output.svg")

    def test_unsupported_effects_do_not_disappear_during_export(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            p=TTGProject()
            p.layers=[Layer(id="shape",type="shape",name="Glow",
                            properties={"shape":"rectangle","fill":"#FF00AA","width":30,
                                        "height":30,"glow":True})]
            with self.assertRaisesRegex(ValueError,"outline/glow"):
                export_svg_shapes(p,root/"no.svg")
            self.assertFalse((root/"no.svg").exists())


if __name__=="__main__":
    unittest.main()
