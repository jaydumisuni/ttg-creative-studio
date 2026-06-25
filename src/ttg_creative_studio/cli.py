from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ttg_creative_studio.engine import run_image_job
from ttg_creative_studio.engine.image_jobs import CreativeJobError


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise CreativeJobError(f"Invalid job JSON: {path} ({exc})") from exc


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TTG Creative Studio Hunter CLI")
    parser.add_argument("--job", required=True, help="Path to Hunter creative job JSON")
    parser.add_argument("--result", default="", help="Optional result JSON path")
    args = parser.parse_args(argv)

    job_path = Path(args.job).expanduser().resolve()
    result_path = Path(args.result).expanduser().resolve() if args.result else None

    try:
        job = _read_json(job_path)
        result = run_image_job(job)
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
