#!/usr/bin/env python3
"""
TheTechGuy Image Editor entrypoint with backend subprocess commands and Qt UI startup.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def emit(message_type: str, **payload: object) -> None:
    print(json.dumps({"type": message_type, **payload}), flush=True)


def run_backend_check() -> int:
    try:
        from bg_core import run_startup_checks

        payload = run_startup_checks(lambda message: emit("status", message=message))
        emit("ready", payload=payload)
        return 0
    except Exception as exc:
        emit("error", message=str(exc))
        return 1


def run_backend_process(request_file: str) -> int:
    try:
        request_path = Path(request_file)
        request = json.loads(request_path.read_text(encoding="utf-8"))
        input_path = str(request["input_path"])
        plan = dict(request["plan"])

        if str(plan.get("method")) == "ai":
            import onnxruntime  # noqa: F401

        from bg_core import run_local_processing

        output_path = run_local_processing(input_path, plan, lambda message: emit("status", message=message))
        emit("result", payload={"output_path": str(output_path), "plan": plan})
        return 0
    except Exception as exc:
        emit("error", message=str(exc))
        return 1


def main() -> int:
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command in {"--check", "--backend-check"}:
            return run_backend_check()
        if command in {"--process", "--backend-process"}:
            if len(sys.argv) < 3:
                emit("error", message="Missing request file for backend processing.")
                return 1
            return run_backend_process(sys.argv[2])

    from bg_ui import run_ui

    return run_ui()


if __name__ == "__main__":
    raise SystemExit(main())
