#!/usr/bin/env python3
"""Repository validation for TTG Creative Studio."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_project_schema import TTGProject
from ttg_validation import ProjectValidator


def main() -> int:
    errors = []
    validator = ProjectValidator()
    for path in sorted((ROOT / "templates").glob("*.ttgstudio.json")):
        try:
            project = TTGProject.load(path)
            messages = validator.validate(project, ROOT)
            blocking = [item for item in messages if item.level == "error"]
            if blocking:
                errors.append(f"{path}: {len(blocking)} validation errors")
        except Exception as exc:
            errors.append(f"{path}: {exc}")
    for path in sorted((ROOT / "packs" / "manifests").glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for key in ["id", "name", "version", "kind", "files"]:
                if key not in data:
                    errors.append(f"{path}: missing {key}")
        except Exception as exc:
            errors.append(f"{path}: {exc}")
    if errors:
        print("Repository validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Repository validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
