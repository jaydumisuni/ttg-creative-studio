"""PhotoCraft/OpenRaster actual editable-layer roundtrips and rejection checks."""
from __future__ import annotations

import sys
from pathlib import Path
from io import BytesIO
from tempfile import TemporaryDirectory
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZIP_STORED, ZipFile

from PIL import Image

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_openraster_bridge import export_openraster, import_openraster
from ttg_project_schema import CanvasSpec, Layer, TTGProject, Transform


class OpenRasterBridgeTests(unittest.TestCase):
    def test_two_real_alpha_layers_and_multiply_replay_merged_pixels(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            color = Image.new("RGBA", (12, 10), (50, 150, 180, 255))
            color.save(root / "base.png")
            tint = Image.new("RGBA", (7, 6), (220, 95, 200, 180))
            tint.save(root / "overlay.png")
            p = TTGProject(name="PhotoCraft layered interchange", project_type="image")
            p.canvas = CanvasSpec(width=20, height=18, background="#181F36")
            p.layers = [
                Layer(id="bottom", name="Photo background", type="image",
                      transform=Transform(x=1, y=2),
                      properties={"path": "base.png"}),
                Layer(id="top", name="Photo overlay", type="image",
                      transform=Transform(x=6, y=5),
                      properties={"path": "overlay.png", "blend_mode": "multiply"}),
            ]
            original = root / "source.ttgstudio.json"
            p.save(original)
            expected = CanvasRenderer(RenderContext(project_root=root)).render(p)
            ora = root / "photo-interop.ora"
            receipt = export_openraster(p, ora, project_root=root)
            self.assertEqual(receipt.layers, 3)
            with ZipFile(ora) as z:
                self.assertEqual(z.namelist()[0], "mimetype")
                self.assertEqual(z.getinfo("mimetype").compress_type, ZIP_STORED)
                stack = ET.fromstring(z.read("stack.xml")).find("stack")
                self.assertEqual([x.get("name") for x in stack],
                                 ["Photo overlay", "Photo background", "TTG Canvas Background"])
                self.assertEqual(stack[0].get("composite-op"), "svg:multiply")
                with Image.open(BytesIO(z.read("mergedimage.png"))) as saved:
                    self.assertEqual(expected.tobytes(), saved.convert("RGBA").tobytes())
            imported_path = root / "photo-reimport.ttgstudio.json"
            importer = import_openraster(ora, imported_path)
            imported = TTGProject.load(imported_path)
            actual = CanvasRenderer(RenderContext(project_root=root)).render(imported)
            self.assertEqual(importer.layers, 3)
            self.assertEqual(expected.tobytes(), actual.tobytes())
            self.assertEqual(imported.layers[-1].properties["blend_mode"], "multiply")
            self.assertEqual(TTGProject.load(original).layers[-1].type, "image")

    def test_unsupported_layers_are_explicitly_rejected_without_writes(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            p = TTGProject()
            p.canvas = CanvasSpec(width=16, height=16)
            p.layers = [Layer(id="unsupported", name="Audio track", type="audio")]
            out = root / "cannot.ora"
            with self.assertRaisesRegex(ValueError, "cannot faithfully"):
                export_openraster(p, out, project_root=root)
            self.assertFalse(out.exists())

    def test_refuse_duplicate_overwrite_and_malicious_or_nested_archive(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            p = TTGProject()
            p.canvas = CanvasSpec(width=8, height=8)
            p.layers = [Layer(id="p", name="pixel", type="shape",
                              properties={"shape": "rectangle", "width": 5, "height": 5})]
            ora = root / "source.ora"
            export_openraster(p, ora, project_root=root)
            with self.assertRaisesRegex(ValueError, "must be a new"):
                export_openraster(p, ora, project_root=root)
            project_path = root / "out.ttgstudio.json"
            import_openraster(ora, project_path)
            with self.assertRaises(FileExistsError):
                import_openraster(ora, project_path)

            zip_path = root / "malicious.ora"
            with ZipFile(zip_path, "w") as archive:
                archive.writestr("mimetype", "image/openraster")
                archive.writestr("stack.xml",
                    '<image w="8" h="8"><stack><layer src="data/../../evil.png" /></stack></image>')
                archive.writestr("data/../../evil.png", b"not-png")
            with self.assertRaisesRegex(ValueError, "unsafe"):
                import_openraster(zip_path, root / "malicious.ttgstudio.json")
            self.assertFalse((root / "evil.png").exists())

            groups = root / "groups.ora"
            with ZipFile(groups, "w") as archive:
                archive.writestr("mimetype", "image/openraster")
                archive.writestr("stack.xml",
                    '<image w="8" h="8"><stack><stack name="group"></stack></stack></image>')
            with self.assertRaisesRegex(ValueError, "group|layers|No"):
                import_openraster(groups, root / "groups.ttgstudio.json")

    def test_neutral_nested_group_tree_import_render_export_roundtrip(self):
        from io import BytesIO
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            Image.new("RGBA",(12,10),(220,75,40,255)).save(root/"red.png")
            Image.new("RGBA",(8,7),(35,175,230,175)).save(root/"blue.png")
            native=TTGProject(name="Layer family",project_type="image")
            native.canvas=CanvasSpec(width=24,height=20,background="#00000000")
            native.layers=[
                Layer(id="red",type="image",name="Red",
                      transform=Transform(x=1,y=1),properties={"path":"red.png"}),
                Layer(id="blue",type="image",name="Blue",
                      transform=Transform(x=4,y=5),properties={"path":"blue.png"})]
            base=root/"base.ora"
            export_openraster(native,base,project_root=root)
            grouped=root/"grouped.ora"
            with ZipFile(base) as original, ZipFile(grouped,"w") as modified:
                for item in original.infolist():
                    if item.filename!="stack.xml":
                        modified.writestr(item,original.read(item.filename))
                doc=ET.fromstring(original.read("stack.xml"))
                stack=doc.find("stack")
                top,bottom=list(stack)
                stack.clear()
                parent=ET.SubElement(stack,"stack",{"name":"Family"})
                parent.append(top)
                detail=ET.SubElement(parent,"stack",{"name":"Detail"})
                detail.append(bottom)
                modified.writestr("stack.xml",ET.tostring(doc))
            output=root/"layers.ttgstudio.json"
            import_openraster(grouped,output)
            imported=TTGProject.load(output)
            self.assertEqual([x.name for x in imported.layers],["Red","Blue"])
            self.assertEqual([[g["name"] for g in x.properties["ora_groups"]]
                              for x in imported.layers],
                             [["Family","Detail"],["Family"]])
            original_frame=CanvasRenderer(RenderContext(root)).render(native)
            imported_frame=CanvasRenderer(RenderContext(root)).render(imported)
            self.assertEqual(original_frame.tobytes(),imported_frame.tobytes())
            saved=root/"roundtrip.ora"
            export_openraster(imported,saved,project_root=root)
            with ZipFile(saved) as z:
                xml=ET.fromstring(z.read("stack.xml")).find("stack")
                self.assertEqual(len(xml),1)
                family=xml[0]
                self.assertEqual((family.tag,family.get("name")),("stack","Family"))
                self.assertEqual(family[0].get("name"),"Blue")
                self.assertEqual(family[1].tag,"stack")
                self.assertEqual(family[1].get("name"),"Detail")
                self.assertEqual(family[1][0].get("name"),"Red")
            reopened=root/"returned.ttgstudio.json"
            import_openraster(saved,reopened)
            again=CanvasRenderer(RenderContext(root)).render(
                TTGProject.load(reopened))
            self.assertEqual(original_frame.tobytes(),again.tobytes())

    def test_grouped_child_multiply_is_rejected_without_pixel_semantics_guess(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            Image.new("RGBA",(5,5),(205,130,75,180)).save(root/"color.png")
            p=TTGProject(project_type="image")
            p.canvas=CanvasSpec(width=12,height=12,background="#00000000")
            p.layers=[Layer(id="blend",type="image",name="Blend",
                            properties={"path":"color.png","blend_mode":"multiply",
                                        "ora_groups":[{"id":"ora_g0001","name":"Group"}]})]
            with self.assertRaisesRegex(ValueError,"grouped blend"):
                export_openraster(p,root/"bad.ora",project_root=root)
            self.assertFalse((root/"bad.ora").exists())

    def test_group_opacity_and_blend_rejected_without_creating_project(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            Image.new("RGBA",(5,5),(200,150,100,200)).save(root/"px.png")
            native=TTGProject(project_type="image")
            native.canvas=CanvasSpec(width=8,height=8,background="#00000000")
            native.layers=[Layer(id="one",type="image",name="One",
                                  properties={"path":"px.png"})]
            source=root/"flat.ora"
            export_openraster(native,source,project_root=root)
            for attr,value in (
                ("opacity","0.7"),
                ("composite-op","svg:multiply"),
                ("visibility","hidden"),
                ("x","4"),
                ("isolation","isolate"),
            ):
                target=root/(attr+".ora")
                with ZipFile(source) as read,ZipFile(target,"w") as write:
                    for info in read.infolist():
                        if info.filename!="stack.xml":
                            write.writestr(info,read.read(info.filename))
                    xml=ET.fromstring(read.read("stack.xml"))
                    parent=xml.find("stack")
                    child=list(parent)[0]
                    parent.clear()
                    group=ET.SubElement(parent,"stack",{"name":"Unqualified",attr:value})
                    group.append(child)
                    write.writestr("stack.xml",ET.tostring(xml))
                out=root/(attr+".ttgstudio.json")
                with self.assertRaisesRegex(ValueError,"group"):
                    import_openraster(target,out)
                self.assertFalse(out.exists())

    def test_missing_source_and_unsupported_blending_fail_closed(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            p = TTGProject()
            p.canvas = CanvasSpec(width=8, height=8)
            p.layers = [Layer(id="bad", name="bad", type="image",
                              properties={"path": "absent.png"})]
            with self.assertRaises(FileNotFoundError):
                export_openraster(p, root / "bad.ora", project_root=root)
            p.layers[0].properties["path"] = None
            p.layers[0].properties["blend_mode"] = "overlay"
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                export_openraster(p, root / "bad.ora", project_root=root)


if __name__ == "__main__":
    unittest.main()
