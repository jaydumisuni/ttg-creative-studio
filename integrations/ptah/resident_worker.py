#!/usr/bin/env python3
"""Development-only resident Creative Studio specialist server.

Ptah A05 owns this OS process and a fenced PTY control lease. Commands are
bounded JSON-lines; no network listener, shell, arbitrary path or credentials.
Not a production Control/Node enrollment endpoint.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

STUDIO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from creative_worker import read_request, require_in_workspace, run


def emit(obj: dict) -> None:
    print("TTG_RESIDENT_EVENT " + json.dumps(obj, sort_keys=True), flush=True)


def serve(run_root: Path) -> int:
    run_root = require_in_workspace(run_root)
    run_root.mkdir(parents=True, exist_ok=True)
    emit({"event": "ready", "schema": "ttg.creative.resident.v1"})
    for line in sys.stdin:
        try:
            if len(line) > 8192:
                raise ValueError("command line exceeds 8192 characters")
            command = json.loads(line)
            if not isinstance(command, dict):
                raise ValueError("command must be an object")
            op = command.get("command")
            if op == "shutdown":
                emit({"event": "stopped"})
                return 0
            if op != "run":
                raise ValueError("unsupported resident command")
            request_path = require_in_workspace(Path(str(command["request"])))
            request = read_request(request_path)
            request_id = request["request_id"]
            if not request_id.isascii() or not 3 <= len(request_id) <= 80:
                raise ValueError("invalid request identity")
            if not all(c.isalnum() or c in "-_" for c in request_id):
                raise ValueError("unsafe request identity")
            destination = run_root / request_id
            if destination.exists():
                raise ValueError("duplicate resident job refused")
            destination.mkdir()
            product = run(request_path, destination)
            verified = subprocess.run(
                [sys.executable, "-B",
                 str(STUDIO / "integrations/ptah/verify_output.py"),
                 "--request", str(request_path), "--output", str(destination)],
                cwd=STUDIO, capture_output=True, text=True, timeout=40, check=False,
            )
            if verified.returncode:
                raise ValueError("independent verifier rejected output: "
                                 + verified.stderr[-700:])
            record = json.loads((destination / "independent_verification.json").read_text())
            if not record.get("passed"):
                raise ValueError("independent verifier did not pass")
            emit({"event": "job_verified", "request_id": request_id,
                  "operation": product["operation"],
                  "checks": len(record["checks"]),
                  "output": str(destination),
                  "files": record["registered_files"]})
        except Exception as error:
            emit({"event": "job_rejected", "reason": str(error)[:850]})
    emit({"event": "stdin_closed"})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    return serve(args.run_root)


if __name__ == "__main__":
    raise SystemExit(main())
