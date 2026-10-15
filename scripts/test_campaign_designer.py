#!/usr/bin/env python3
"""Physical, offline end-to-end campaign quality/portability/GUI qualification."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from ttg_campaign_composer import CampaignBrief, FORMATS, compose_campaign
from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_project_schema import TTGProject
from ttg_validation import ProjectValidator

def check(name: str, condition: bool, checks: list[str]) -> None:
    if not condition:
        raise AssertionError(f"Campaign qualification failed: {name}")
    checks.append(name)

def run() -> dict:
    checks: list[str] = []
    (ROOT/".workspace/scratch").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ttg-campaign-e2e-",
                                     dir=ROOT/".workspace/scratch") as temp:
        root = Path(temp)
        previews = {}
        for style in FORMATS:
            brief = CampaignBrief(
                layout=style,
                brand="THETECHGUY",
                headline="TECHNOLOGY FOR\nTHE EXTRAORDINARY.",
                subhead="A better way to imagine, design and deliver.",
                product_name="FLAGSHIP EXPERIENCE",
                cta="EXPLORE THE FUTURE",
                website="thetechguyds.com",
                accent={"flagship": "aqua", "social": "violet", "wide": "amber"}[style],
            )
            created = compose_campaign(brief, root/style)
            project = TTGProject.load(created["project"])
            w,h = FORMATS[style][1:]
            with Image.open(created["preview"]) as im:
                preview = im.convert("RGBA")
            check(style+"_correct_canvas", preview.size == (w,h), checks)
            check(style+"_rich_layered_document",
                  len(project.layers) >= 14 and
                  sum(l.type == "text" for l in project.layers) >= 8 and
                  sum(l.type == "image" for l in project.layers) == 3, checks)
            check(style+"_editable_headline",
                  any(l.name == "Hero headline" and l.type == "text" and
                      "\n" in l.properties["text"] for l in project.layers), checks)
            check(style+"_passes_validator",
                  ProjectValidator().is_valid(project, created["project"].parent), checks)
            check(style+"_true_studio_renderer",
                  CanvasRenderer(RenderContext(created["project"].parent))
                  .render(project).tobytes() == preview.tobytes(), checks)
            manifest = json.loads(created["manifest"].read_text())
            check(style+"_manifest_hashes",
                  all(hashlib.sha256((created["project"].parent/relative).read_bytes()).hexdigest()==digest
                      for relative,digest in manifest["sha256"].items()), checks)
            check(style+"_no_absolute_image_refs",
                  all(not Path(l.properties["path"]).is_absolute()
                      for l in project.layers if l.type=="image"), checks)
            check(style+"_portable_zip_members", zipfile.ZipFile(created["bundle"]).namelist()
                  == list(manifest["sha256"])+["manifest.json"], checks)
            relocated = root/("relocated_"+style)
            relocated.mkdir()
            with zipfile.ZipFile(created["bundle"]) as archive:
                archive.extractall(relocated)
            copy = TTGProject.load(relocated/"campaign.ttgstudio.json")
            check(style+"_relocation_pixel_replay",
                  CanvasRenderer(RenderContext(relocated)).render(copy).tobytes()
                  == preview.tobytes(), checks)
            with Image.open(created["preview"]) as im:
                previews[style] = hashlib.sha256(im.tobytes()).hexdigest()
            try:
                compose_campaign(brief, root/style)
            except ValueError as error:
                check(style+"_existing_directory_protected",
                      "nonempty" in str(error), checks)
            else:
                raise AssertionError("overwriting prior campaign was allowed")
        check("three_designs_distinct", len(set(previews.values()))==3, checks)
        product = root/"provided_product.png"
        Image.new("RGBA", (360, 640), (234, 67, 83, 255)).save(product)
        provided = compose_campaign(CampaignBrief(layout="social", image_path=str(product)), root/"provided")
        project=TTGProject.load(provided["project"])
        check("provided_product_is_editable_layer",
              any(l.name=="Replaceable hero product" and
                  l.type=="image" for l in project.layers), checks)
        with Image.open(provided["project"].parent/"assets/product.png") as im:
            check("provided_product_pixels_preserved",
                  im.getpixel((350, 510))[:3] == (234, 67, 83), checks)
        check("source_filename_not_embedded",
              str(product) not in provided["project"].read_text(), checks)
        for invalid in [
            CampaignBrief(layout="broken"),
            CampaignBrief(headline=""),
            CampaignBrief(headline="H"*86),
            CampaignBrief(image_path=str(root/"missing.png")),
            CampaignBrief(subhead="invalid\ncontrol"),
        ]:
            try:
                invalid.validate()
            except ValueError:
                continue
            raise AssertionError("invalid brief accepted")
        checks.append("invalid_briefs_rejected")

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        from ttg_creative_workspace import CreativeWorkspace
        from ttg_campaign_dialog import CampaignDesignerDialog
        app = QApplication.instance() or QApplication([])
        dialog = CampaignDesignerDialog()
        check("gui_campaign_designer_presets",
              dialog.layout_choice.count() == len(FORMATS), checks)
        check("gui_campaign_designer_editable_fields",
              dialog.brief().brand == "THETECHGUY" and
              dialog.headline.text() != "", checks)
        dialog.render_preview()
        check("gui_preview_real_png",
              dialog.preview.pixmap() is not None and
              not dialog.preview.pixmap().isNull(), checks)
        dialog.close()
        workspace = CreativeWorkspace(ROOT)
        destination = root/"ui_campaign"
        path = workspace.create_campaign(
            CampaignBrief(layout="flagship", headline="A CREATIVE STUDIO,\nNOT A STATIC PICTURE."),
            destination
        )
        check("gui_uses_saved_project",workspace.project_path==path and path.is_file(),checks)
        check("gui_relative_asset_root",
              workspace.export_service.project_root==destination and
              workspace.canvas.project_root==destination, checks)
        check("gui_layers_and_hero_selection",
              len(workspace.project.layers)>=14 and
              workspace.selected_layer().name=="Hero headline",checks)
        check("gui_toolbar_accessible",
              workspace.toolbar_scroll is not None and
              workspace.campaign_button.toolTip().startswith("Generate"), checks)
        workspace.resize(1024, 640)
        workspace.show()
        app.processEvents()
        check("compact_toolbar_scrolls_instead_of_crushing_menus",
              workspace.toolbar_scroll.horizontalScrollBar().maximum() > 0 and
              all(menu.width() >= menu.minimumWidth()
                  for menu in workspace.toolbar_scroll.widget().findChildren(
                      __import__("PyQt6.QtWidgets", fromlist=["QToolButton"]).QToolButton)), checks)
        gui_png=root/"from_gui.png"
        workspace.export_service.export_png(workspace.project, gui_png)
        with Image.open(gui_png) as img:
            with Image.open(destination/"campaign.png") as orig:
                check("gui_export_exact_same_pixels", img.tobytes()==orig.tobytes(),checks)
        workspace.reset_project(workspace.action.new_project())
        check("new_project_resets_asset_root",
              workspace.export_service.project_root==ROOT, checks)
        workspace.close()
        app.processEvents()
        cli_dest = root/"cli_generated"
        cli = subprocess.run([
            sys.executable, "-B", str(ROOT/"scripts/creative_cli.py"),
            "design-campaign", str(cli_dest), "--layout", "social",
            "--headline", "A BRAND YOU CAN BELIEVE IN.", "--accent", "amber",
        ], cwd=ROOT, capture_output=True, text=True, timeout=40)
        check("cli_creates_editable_project",
              cli.returncode == 0 and
              (cli_dest/"campaign.ttgstudio.json").is_file() and
              (cli_dest/"portable-campaign.zip").is_file(), checks)
    return {"status":"PASS", "checks_count":len(checks),"checks":checks,
            "qualification":"manual/procedural offline only; no generative AI"}


def main() -> int:
    print(json.dumps(run(), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
