from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
import json
import sys
from pathlib import Path
from typing import Any, Dict

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ttg_creative_studio.engine import run_image_job
from ttg_creative_studio.engine.video_jobs import VIDEO_TASKS, run_video_job, tool_catalog
from ttg_creative_studio.engine.online_image_jobs import ONLINE_IMAGE_TASKS, run_online_image_job
from ttg_creative_studio.engine.image_jobs import CreativeJobError
from ttg_production_director import ProductionDirector, ProductionError
from ttg_creative_instruction import run_creative_instruction, creative_scene_contract
from ttg_professional_image_production import ProfessionalImagePipeline, choose_quality


DONOR_TASKS = frozenset({
    "studio_export_openraster", "studio_import_openraster",
    "studio_export_otio", "studio_import_otio",
    "studio_export_lottie", "studio_import_lottie",
    "studio_import_pbr_maps",
    "studio_export_svg", "studio_import_svg",
    "studio_import_lightcraft_raw", "studio_develop_lightcraft_raw",
    "studio_import_dxf", "studio_export_dxf",
})


def run_donor_interchange_job(job: dict[str, Any]) -> dict[str, Any]:
    """Use exact existing Studio project and actual native interchange engines.

    No subprocess donor runtime or unapproved provider side effect is
    introduced. Every output is new, source assets remain unchanged.
    """
    from ttg_project_schema import TTGProject

    task = job.get("task")
    output = Path(job.get("output") or job.get("outputPath") or "")
    if task not in DONOR_TASKS or not output.is_absolute():
        raise CreativeJobError("Donor interchange needs known task and absolute output")
    options = job.get("options") or {}
    if not isinstance(options, dict):
        raise CreativeJobError("Donor interchange options must be an object")
    input_value = job.get("input") or job.get("inputPath")
    if not isinstance(input_value, str) or not Path(input_value).is_absolute():
        raise CreativeJobError("Donor interchange requires an absolute input path")
    source = Path(input_value)
    if task == "studio_export_openraster":
        from ttg_openraster_bridge import export_openraster
        result = export_openraster(
            TTGProject.load(source), output,
            project_root=Path(options.get("project_root") or source.parent),
        )
    elif task == "studio_import_openraster":
        from ttg_openraster_bridge import import_openraster
        result = import_openraster(source, output)
    elif task == "studio_export_otio":
        from ttg_filmcraft_otio_bridge import export_otio
        result = export_otio(
            TTGProject.load(source), output,
            project_root=Path(options.get("project_root") or source.parent),
        )
    elif task == "studio_import_otio":
        from ttg_filmcraft_otio_bridge import import_otio
        result = import_otio(source, output)
    elif task == "studio_export_svg":
        from ttg_vectorcraft_svg_bridge import export_svg_shapes
        result = export_svg_shapes(TTGProject.load(source), output)
    elif task == "studio_import_svg":
        from ttg_vectorcraft_svg_bridge import import_svg_shapes
        result = import_svg_shapes(source, output)
    elif task == "studio_export_lottie":
        from ttg_effectcraft_lottie_bridge import export_lottie
        result = export_lottie(TTGProject.load(source), output)
    elif task == "studio_import_lottie":
        from ttg_effectcraft_lottie_bridge import import_lottie
        result = import_lottie(source, output)
    elif task == "studio_import_lightcraft_raw":
        from ttg_lightcraft_raw_bridge import import_developed_raw
        preview = options.get("preview_png")
        if not isinstance(preview, str) or not Path(preview).is_absolute():
            raise CreativeJobError("LightCraft RAW intake requires absolute options.preview_png")
        result = import_developed_raw(source, Path(preview), output)
    elif task == "studio_develop_lightcraft_raw":
        from ttg_lightcraft_raw_bridge import develop_with_lightcraft
        binary = options.get("lightcraft_cli")
        if not isinstance(binary, str) or not Path(binary).is_absolute():
            raise CreativeJobError("RAW development requires explicit absolute options.lightcraft_cli")
        result = develop_with_lightcraft(
            source, output, lightcraft_cli=binary, exposure=options.get("exposure"),
        )
    elif task == "studio_import_dxf":
        from ttg_cadcraft_dxf_bridge import import_dxf
        result = import_dxf(
            source, output,
            canvas_width=options.get("width"),
            canvas_height=options.get("height"),
            units=options.get("units"),
        )
    elif task == "studio_export_dxf":
        from ttg_cadcraft_dxf_bridge import export_dxf
        result = export_dxf(TTGProject.load(source), output, units=options.get("units"))
    else:
        from ttg_material_texture_bridge import import_pbr_export_maps
        result = import_pbr_export_maps(
            Path(options.get("maps_dir") or source.parent),
            source, output, material_name=options.get("material_name", ""),
        )
    metadata = asdict(result) if is_dataclass(result) else result
    return {
        "ok": True,
        "jobId": str(job.get("jobId") or "studio_donor_interchange"),
        "task": task, "status": "complete",
        "outputPath": str(output), "meta": metadata,
    }


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise CreativeJobError(f"Invalid job JSON: {path} ({exc})") from exc


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TTG Creative Studio independent job CLI")
    parser.add_argument("--job", help="Path to an AI-authored Creative Studio job JSON")
    parser.add_argument("--catalog", action="store_true", help="Print shared agent tool contract")
    parser.add_argument("--result", default="", help="Optional result JSON path")
    args = parser.parse_args(argv)

    if args.catalog:
        schema=tool_catalog()
        schema["operations"].update({
            "creative_execute": {
                "state": "bounded_native_with_limited_natural_language",
                "requires": ["options.schema", "options.mode", "options.instruction", "output"],
                "modes": ["auto", "scene", "wall_sign", "edit_project", "campaign"],
                "scene_schema": "ttg.studio.scene-spec.v1",
                "scene_capabilities": creative_scene_contract(),
                "natural_language": "admitted typographic posters and unambiguous project edits; unsupported requests require an assistant-authored Studio scene spec",
                "auto_correct_layout": "opt-in bounded anchor corrections; does not certify photorealism or semantic quality",
                "acceptance_schema": "ttg.studio.creative-acceptance.v1",
                "acceptance_checks": "exact text/material values and actual per-layer visible pixel contribution",
                "visual_observer": "opt-in explicit local vision model, evidence-bound to rendered pixels; advisory only, no model means unavailable",
                "repair_expected_text": "opt-in constrained edits based on explicit assistant/user expectation; semantic/photographic review remains separate",
                "side_effects": "Create actual Studio project and image with pixel replay proof",
                "description": ("Accept an AI-authored bounded scene packet or project edits; "
                                "reuse existing Studio native rendering and campaign composer. "
                                "Unsupported instructions and unapproved assets fail closed; "
                                "no Tenfold/Cookpit execution is implied by this contract."),
            },
            "studio_produce": {
                "state": "native_available",
                "requires": ["options.instruction", "options.catalog_roots",
                             "output"],
                "side_effects": "Create a Studio-owned PNG, editable project and receipt",
                "description": ("Auto-select an exact reference composite, supported Studio "
                                "native scene or explicit gated neural-photo route. "
                                "Neural completion requires real provider pixels and visual review."),
            },
            "studio_produce_photoreal": {
                "state":"provider_optional_not_admitted_without_credentials",
                "requires":["options.instruction","options.phase","output"],
                "phases":["plan","submit","inspect","complete"],
                "side_effects":"plan none; submit paid provider; complete verified PNG + editable project",
                "description":"Production Director neural photo route using the existing Image Lab provider; never auto-bill or auto-accept visuals",
            },
            "image_generate_online": {"state":"online_opt_in",
                "requires":["options.prompt","options.paid_approval"],
                "side_effects":"paid online image prediction"},
            "image_status_online": {"state":"online",
                "requires":["options.prediction_id"],"side_effects":"none"},
            "image_cancel_online": {"state":"online",
                "requires":["options.prediction_id","options.cancel_approval"],
                "side_effects":"cancel remote prediction"},
            "image_download_online": {"state":"online",
                "requires":["options.prediction_id","output"],
                "side_effects":"verified PNG download"},
        })
        schema["operations"].update({
            task: {
                "state": "native_interchange_subset",
                "requires": ["task", "input", "output"],
                "side_effects": "Creates a new local interchange artifact; never overwrites inputs",
                "description": (
                    "PhotoCraft OpenRaster layers; FilmCraft OTIO clips; "
                    "EffectCraft Lottie shapes; VectorCraft SVG primitives; "
                     "or exported PBR texture mapset; LightCraft developed RAW source "
                    "and CADCraft bounded ASCII DXF presentation exchange "
                    "intake into the existing Studio project. Only explicitly "
                    "supported structures are admitted; no donor runtime, "
                    "model license or production authority is inferred."
                ),
            }
            for task in sorted(DONOR_TASKS)
        })
        print(json.dumps(schema, indent=2))
        return 0
    if not args.job:
        parser.error("--job is required unless --catalog is selected")
    job_path = Path(args.job).expanduser().resolve()
    result_path = Path(args.result).expanduser().resolve() if args.result else None

    try:
        job = _read_json(job_path)
        if job.get("task") == "studio_produce_photoreal":
            opts = job.get("options") or {}
            if not isinstance(opts, dict):
                raise CreativeJobError("Photoreal production options must be an object")
            output = Path(job.get("output") or job.get("outputPath") or "")
            if not output.is_absolute() or output.suffix.lower() != ".png":
                raise CreativeJobError("Photoreal production requires an absolute PNG output destination")
            director = ProfessionalImagePipeline(output.parent)
            phase = opts.get("phase","plan")
            if phase == "plan":
                receipt = director.plan(
                    opts.get("instruction",""),quality=opts.get("quality","auto"),
                    reference_image=opts.get("reference_image"),
                    aspect_ratio=opts.get("aspect_ratio","4:3"))
            elif phase == "submit":
                receipt = director.submit(
                    name=output.stem,prompt=opts.get("instruction",""),
                    quality=opts.get("quality","auto"),
                    reference_image=opts.get("reference_image"),
                    aspect_ratio=opts.get("aspect_ratio","4:3"),
                    paid_approval=opts.get("paid_approval",""),
                    previous_ticket=opts.get("previous_ticket"))
            elif phase == "inspect":
                receipt = director.inspect(output.stem)
            elif phase == "complete":
                receipt = director.complete(
                    ticket_name=output.stem,vision_model=opts.get("vision_model"),
                    question=opts.get("inspection_question",""))
            else:
                raise CreativeJobError("Unsupported photoreal production phase")
            result = {
                "ok":True,"jobId":str(job.get("jobId") or "professional_production"),
                "task":"studio_produce_photoreal",
                "status":receipt["state"],
                "outputPath":receipt.get("image"),
                "meta":receipt,
            }
        elif job.get("task") == "studio_produce":
            opts=job.get("options") or {}
            if not isinstance(opts,dict):
                raise CreativeJobError("studio_produce options must be an object")
            output=Path(job.get("output") or job.get("outputPath") or "")
            if not output.is_absolute() or output.suffix.lower()!=".png":
                raise CreativeJobError("studio_produce requires an absolute PNG output path")
            roots=opts.get("catalog_roots") or [str(output.parent)]
            if not isinstance(roots,list) or not all(isinstance(x,str) for x in roots):
                raise CreativeJobError("studio_produce catalog_roots must be approved paths")
            director=ProductionDirector([Path(x) for x in roots],output.parent)
            instruction=opts.get("instruction","")
            exact=opts.get("exact") is True
            reference=(Path(job.get("input") or job.get("inputPath"))
                       if (job.get("input") or job.get("inputPath")) else None)
            route=opts.get("route","auto")
            if route not in ("auto","native","neural"):
                raise CreativeJobError("Unknown Studio production route")
            decision=(director.choose_instruction_route(instruction,exact=exact,reference=reference)
                      if route=="auto" else {"route":"neural_photo" if route=="neural"
                                            else "studio_native_procedural_scene"})
            if decision["route"]=="neural_photo":
                if exact:
                    raise CreativeJobError("Exact image recreation is not generative photo mode")
                engine=ProfessionalImagePipeline(output.parent)
                phase=opts.get("phase","plan")
                quality=opts.get("quality",decision.get("quality","auto"))
                if phase=="plan":
                    receipt=engine.plan(instruction,quality=quality,
                        reference_image=opts.get("reference_image"),
                        aspect_ratio=opts.get("aspect_ratio","4:3"))
                elif phase=="submit":
                    receipt=engine.submit(name=output.stem,prompt=instruction,
                        quality=quality,reference_image=opts.get("reference_image"),
                        aspect_ratio=opts.get("aspect_ratio","4:3"),
                        paid_approval=opts.get("paid_approval",""),
                        previous_ticket=opts.get("previous_ticket"))
                elif phase=="inspect":
                    receipt=engine.inspect(output.stem)
                elif phase=="complete":
                    receipt=engine.complete(ticket_name=output.stem,
                        vision_model=opts.get("vision_model"),
                        question=opts.get("inspection_question",""))
                else:
                    raise CreativeJobError("Unsupported image-production phase")
                output_path=receipt.get("image")
            else:
                receipt=director.produce(
                    instruction=instruction,exact=exact,
                    reference=reference,output_name=output.stem,
                    dry_run=opts.get("dry_run") is True)
                output_path=receipt.get("output")
            result={"ok":True,"jobId":str(job.get("jobId") or "production"),
                    "task":"studio_produce","status":receipt["state"],
                    "outputPath":output_path,
                    "meta":{"selected_route":decision["route"],**receipt}}

        elif job.get("task") == "creative_execute":
            receipt=run_creative_instruction(job)
            result={"ok":receipt["state"] not in ("correction_required",
                     "needs_scene_compilation", "needs_edit_compilation", "visual_observer_unavailable"),
                     "jobId":str(job.get("jobId") or "creative_execution"),
                    "task":"creative_execute","status":receipt["state"],
                    "outputPath":receipt.get("output"),"meta":receipt}

        elif job.get("task") in DONOR_TASKS:
            result = run_donor_interchange_job(job)
        elif job.get("task") in VIDEO_TASKS:
            result=run_video_job(job)
        elif job.get("task") in ONLINE_IMAGE_TASKS:
            result=run_online_image_job(job)
        else:
            result=run_image_job(job)
        result["jobPath"] = str(job_path)
        if result_path:
            _write_json(result_path, result)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        error = {
            "ok": False,
            "status": "failed",
            "error": str(exc),
            "jobPath": str(job_path),
        }
        if result_path:
            _write_json(result_path, error)
        print(json.dumps(error, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
