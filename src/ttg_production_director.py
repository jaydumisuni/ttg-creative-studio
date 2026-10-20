"""Studio-owned, evidence-backed production selection and render.

No Hunter or Ptah dependency: an approved workspace may invoke this module.
No invented inference: native-scene creation or exact reference re-composition
are distinct, reported routes.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any

from PIL import Image, ImageChops

from ttg_banana_actions import BananaActions
from ttg_export_service import ExportService
from ttg_project_schema import TTGProject


class ProductionError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as reader:
        for block in iter(lambda: reader.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


class ProductionDirector:
    """Choose and execute one Studio rendering path using observed assets.

    Discovery never crawls outside explicitly authorized catalog roots.
    Exactly matched source compositions are highest priority *only when*
    exact recreation was requested. Native procedural generation remains
    a separate no-reference route with an honestly restricted scene family.
    """

    def __init__(self, asset_roots: list[Path], output_root: Path):
        if not asset_roots:
            raise ProductionError("At least one approved asset catalog is required")
        self.roots = tuple(Path(p).expanduser().resolve(strict=True) for p in asset_roots)
        if any(not p.is_dir() for p in self.roots):
            raise ProductionError("Catalog roots must be directories")
        self.output_root = Path(output_root).expanduser().resolve(strict=True)
        if not self.output_root.is_dir():
            raise ProductionError("Output directory does not exist")
    def discover(self, reference: Path | None = None) -> dict[str, Any]:
        observed: dict[str, Any] = {
            "native_studio_compositor": True,
            "native_professional_wall_sign": True,
            "online_neural_generation": "not_used",
            "catalog_roots": [str(x) for x in self.roots],
            "catalog_projects_checked": 0,
            "eligible_reference_projects": [],
            "rejected_candidates": [],
        }
        refhash = None
        if reference is not None:
            reference = Path(reference).expanduser().resolve(strict=True)
            if not any(_within(reference, root) for root in self.roots):
                raise ProductionError("Reference is outside authorized catalog roots")
            if reference.suffix.lower() not in {".png",".jpg",".jpeg",".webp"} or not reference.is_file():
                raise ProductionError("Reference must be a real local image")
            refhash = _sha256(reference)
            observed["reference_sha256"] = refhash
        checked = 0
        for root in self.roots:
            # Bounded discovery: inspect at most 256 candidate files and depth 2.
            paths = sorted(set(root.glob("*.ttgstudio.json")) |
                           set(root.glob("*/*.ttgstudio.json")) |
                           set(root.glob("*/*/*.ttgstudio.json")))
            for path in paths:
                if checked >= 256:
                    raise ProductionError("Catalog has more than 256 projects; narrow the approved root")
                checked += 1
                try:
                    project = TTGProject.load(path)
                    asset_lookup = self._verify_assets(project,path.parent)
                    if refhash:
                        matches=[a for a in project.assets if
                                 a.sha256 == refhash and
                                 (path.parent/a.path).is_file()]
                        if not matches:
                            observed["rejected_candidates"].append(
                                {"path":str(path),"reason":"no matching original reference digest"})
                            continue
                        hidden = any(
                            layer.type=="image" and not layer.visible and
                            any(layer.properties.get("path")==a.path for a in matches)
                            for layer in project.layers
                        )
                        if not hidden:
                            observed["rejected_candidates"].append(
                                {"path":str(path),"reason":"original reference must be hidden in composite"})
                            continue
                        if sum(layer.visible for layer in project.layers) < 2:
                            observed["rejected_candidates"].append(
                                {"path":str(path),"reason":"no independently composited editable layers"})
                            continue
                        observed["eligible_reference_projects"].append({
                            "path":str(path),
                            "native_layers":len(project.layers),
                            "verified_assets":len(asset_lookup),
                            "reference_sha256":refhash,
                        })
                except (ValueError,KeyError,OSError,ProductionError,TypeError) as ex:
                    observed["rejected_candidates"].append(
                        {"path":str(path),"reason":str(ex)[:220]})
        observed["catalog_projects_checked"]=checked
        return observed

    def _verify_assets(self, project: TTGProject, base: Path) -> list[dict[str,str]]:
        verified=[]
        for asset in project.assets:
            if not asset.path:
                if asset.required:
                    raise ProductionError(f"Required asset {asset.name} has no path")
                continue
            p = (base/asset.path).resolve()
            if not _within(p,base.resolve()):
                raise ProductionError("Project asset escapes approved project directory")
            if not p.is_file():
                if asset.required:
                    raise ProductionError(f"Required asset missing: {asset.name}")
                continue
            digest=_sha256(p)
            if asset.sha256 and digest.lower()!=asset.sha256.lower():
                raise ProductionError(f"Asset checksum mismatch: {asset.name}")
            verified.append({"name":asset.name,"sha256":digest})
        for layer in project.layers:
            if not layer.visible or layer.type!="image":
                continue
            source = layer.properties.get("path")
            if not isinstance(source,str):
                raise ProductionError(f"Image layer {layer.name} lacks source path")
            path=(base/source).resolve()
            if not _within(path,base.resolve()) or not path.is_file():
                raise ProductionError(f"Visible image layer unavailable: {layer.name}")
        return verified

    def produce(self, *, instruction:str, exact:bool=False,
                reference:Path|None=None, output_name:str="studio_production",
                dry_run:bool=False) -> dict[str,Any]:
        if not isinstance(instruction,str) or not instruction.strip() or len(instruction)>1000:
            raise ProductionError("A bounded creative instruction is required")
        if not output_name.replace("_","").replace("-","").isalnum() or len(output_name)>60:
            raise ProductionError("Unsafe output name")
        if exact and reference is None:
            raise ProductionError("Exact recreation requires a supplied reference")
        inventory=self.discover(reference)
        candidates=inventory["eligible_reference_projects"]
        if exact:
            if not candidates:
                raise ProductionError(
                    "No reference-grounded editable Studio project was found. "
                    "Native generation cannot honestly claim an exact reproduction."
                )
            # deterministic: sorted catalog path; no paid provider fallback
            route="reference_layer_composite"
            selected=Path(candidates[0]["path"])
            project=TTGProject.load(selected)
            assets=self._verify_assets(project,selected.parent)
        else:
            if reference is not None:
                raise ProductionError("Reference supplied without exact mode: choose an explicit mode")
            route="studio_native_procedural_scene"
            try:
                project=BananaActions().create_professional_wall_sign(instruction)
            except ValueError as exc:
                raise ProductionError(str(exc)) from exc
            selected=None
            assets=[]
        plan = {
            "schema":"ttg.studio.production.v1",
            "request":instruction,
            "render_owner":"TTG Creative Studio",
            "workspace_role":"executor_only",
            "ai_operator_used_as_renderer":False,
            "hunter_connected":False,
            "chargeable_provider_used":False,
            "model_checkpoint_downloaded":False,
            "mode":route,
            "quality_claim":"pixel-exact to supplied reference" if exact
                           else "procedural office wall scene, not certified photorealism",
            "selected_project":str(selected) if selected else None,
            "verified_assets":assets,
            "inventory":inventory,
        }
        if dry_run:
            plan["state"]="planned_not_rendered"
            return plan
        output=self.output_root/(output_name+".png")
        receipt=self.output_root/(output_name+".receipt.json")
        project_output=self.output_root/(output_name+".ttgstudio.json")
        if any(p.exists() for p in (output,receipt,project_output)):
            raise ProductionError("Production artifacts already exist; refusing overwrite")
        # Preserve a genuinely editable project at the output destination.
        # Prefer links when moving between directories on the same filesystem:
        # no redundant multi-megabyte media copies are consumed.
        studio_asset_root=selected.parent if selected else self.output_root
        portable_dir=self.output_root/(output_name+"_assets")
        try:
            if selected and selected.parent != self.output_root:
                if portable_dir.exists():
                    raise ProductionError("Destination media directory already exists")
                portable_dir.mkdir()
                remap={}
                total=0
                for asset in project.assets:
                    source=(selected.parent/asset.path).resolve()
                    if not source.is_file():
                        if asset.required:
                            raise ProductionError("Required project asset disappeared during production")
                        continue
                    total += source.stat().st_size
                    if total > 128*1024*1024:
                        raise ProductionError("Asset quota exceeds 128 MiB portable snapshot allowance")
                    key=_sha256(source)[:16]+"-"+source.name
                    target=portable_dir/key
                    try:
                        os.link(source,target)
                    except OSError:
                        shutil.copy2(source,target)
                    remap[asset.path]=(portable_dir.name+"/"+key)
                    asset.path=remap[asset.path]
                for layer in project.layers:
                    path=layer.properties.get("path")
                    if layer.type=="image" and path is not None:
                        if path not in remap:
                            raise ProductionError("Unregistered source image prevented portable export")
                        layer.properties["path"]=remap[path]
                studio_asset_root=self.output_root
            project.save(project_output)

            ExportService(studio_asset_root).export_png(project,output)
            with Image.open(output) as img:
                observed_size=list(img.size)
                if observed_size!=[project.canvas.width,project.canvas.height]:
                    raise ProductionError("Renderer output differs from project canvas")
            plan["render_sha256"]=_sha256(output)
            plan["dimensions"]=observed_size
            plan["state"]="native_render_verified"
            plan["output"]=str(output)
            if exact:
                with Image.open(output) as img, Image.open(reference) as ref:
                    left,right=img.convert("RGB"),ref.convert("RGB")
                    bbox=ImageChops.difference(left,right).getbbox() if left.size==right.size else [0,0,*right.size]
                plan["pixel_mismatch_bbox"]=bbox
                plan["pixel_exact"]=bbox is None
                plan["state"]="accepted_exact" if bbox is None else "rendered_reference_mismatch"
            else:
                plan["pixel_exact"]=None
                plan["state"]="rendered_visual_review_required"
            # For a reference-linked project, do not claim a portable project
            # copy: the full assets remain in the original approved catalog.
            plan["project"]=str(project_output)
            plan["project_assets_root"]=str(studio_asset_root)
            plan["portable_media_hardlinked_when_possible"]=bool(
                selected and selected.parent != self.output_root)
            receipt.write_text(json.dumps(plan,indent=2,ensure_ascii=False)+"\n")
            if exact and not plan["pixel_exact"]:
                raise ProductionError("Studio output does not match the reference; see receipt")
            return plan
        except Exception:
            # A receipt is retained only when a rendered result is auditable.
            if not receipt.exists():
                output.unlink(missing_ok=True)
                project_output.unlink(missing_ok=True)
                if portable_dir.is_dir():
                    shutil.rmtree(portable_dir)
            raise
