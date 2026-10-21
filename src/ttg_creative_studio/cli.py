from __future__ import annotations

import argparse
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
from ttg_creative_instruction import run_creative_instruction
from ttg_professional_image_production import ProfessionalImagePipeline, choose_quality


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
                "natural_language": "admitted typographic posters and unambiguous project edits; unsupported requests require an assistant-authored Studio scene spec",
                "auto_correct_layout": "opt-in bounded anchor corrections; does not certify photorealism or semantic quality",
                "acceptance_schema": "ttg.studio.creative-acceptance.v1",
                "acceptance_checks": "exact text/material values and actual per-layer visible pixel contribution",
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
            result={"ok":True,"jobId":str(job.get("jobId") or "creative_execution"),
                    "task":"creative_execute","status":receipt["state"],
                    "outputPath":receipt.get("output"),"meta":receipt}

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
