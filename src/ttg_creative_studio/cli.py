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
            "studio_produce": {
                "state": "native_available",
                "requires": ["options.instruction", "options.catalog_roots",
                             "output"],
                "side_effects": "Create a Studio-owned PNG, editable project and receipt",
                "description": ("Select existing matching editable reference assets "
                                "when exact=true, otherwise use Studio-native supported "
                                "procedural scenes. No model download or paid generation."),
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
        if job.get("task") == "studio_produce":
            opts=job.get("options") or {}
            if not isinstance(opts,dict):
                raise CreativeJobError("studio_produce options must be a dictionary")
            output=Path(job.get("output") or job.get("outputPath") or "")
            if not output.is_absolute() or output.suffix.lower()!=".png":
                raise CreativeJobError("studio_produce requires an absolute PNG output path")
            roots=opts.get("catalog_roots")
            if not isinstance(roots,list) or not roots or not all(
                isinstance(x,str) for x in roots
            ):
                raise CreativeJobError("studio_produce requires approved catalog_roots")
            director=ProductionDirector([Path(x) for x in roots],output.parent)
            receipt=director.produce(
                instruction=opts.get("instruction",""),
                exact=opts.get("exact") is True,
                reference=Path(job.get("input") or job.get("inputPath"))
                if (job.get("input") or job.get("inputPath")) else None,
                output_name=output.stem,
                dry_run=opts.get("dry_run") is True,
            )
            result={
                "ok":True,
                "jobId":str(job.get("jobId") or "production"),
                "task":"studio_produce",
                "status":receipt["state"],
                "outputPath":receipt.get("output"),
                "meta":receipt,
            }
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
