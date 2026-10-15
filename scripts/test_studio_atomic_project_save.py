#!/usr/bin/env python3
"""Cross-platform Studio project Save: atomic publication and fail-closed tests."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ttg_action_engine import ActionEngine
from ttg_project_schema import TTGProject

checks: list[str] = []


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def assert_clean(folder: Path) -> None:
    check("no abandoned project temp file", not list(folder.glob(".*.tmp")))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ttg-atomic-project-") as tmp:
        folder = Path(tmp)
        destination = folder / "editable.ttgstudio.json"
        project = ActionEngine().new_project("Approved project", "image")
        project.canvas.width = 1280
        ActionEngine().add_shape(project, "rectangle", 20, 20)
        project.save(destination)
        previous = destination.read_bytes()
        check("initial project save is valid JSON", json.loads(previous)["name"] == "Approved project")
        check("initial native project loads", TTGProject.load(destination).name == project.name)

        project.name = "Edited but not committed"
        with patch("ttg_project_schema.os.replace", side_effect=OSError(28, "disk full")):
            try:
                project.save(destination)
            except OSError:
                checks.append("failed atomic rename propagates")
            else:
                raise AssertionError("Atomic rename failure was hidden")
        check("rename failure retains original project bytes", destination.read_bytes() == previous)
        assert_clean(folder)

        with patch("ttg_project_schema.os.fsync", side_effect=OSError(5, "write failure")):
            try:
                project.save(destination)
            except OSError:
                checks.append("failed staged-file fsync propagates")
            else:
                raise AssertionError("Fsync failure was hidden")
        check("write failure retains original project bytes", destination.read_bytes() == previous)
        assert_clean(folder)

        with patch("ttg_project_schema.json.dumps", side_effect=TypeError("unserializable data")):
            try:
                project.save(destination)
            except TypeError:
                checks.append("serialization failure propagates before writing")
            else:
                raise AssertionError("Serialization error was hidden")
        check("serialization failure preserves existing saved project", destination.read_bytes() == previous)
        assert_clean(folder)

        project.name = "Latest approved revision"
        project.save(str(destination))
        final = destination.read_bytes()
        check("successful commit replaces complete project", final != previous and
              TTGProject.load(destination).name == project.name)
        check("previous dimensions and editable layer preserved",
              TTGProject.load(destination).canvas.width == 1280 and
              len(TTGProject.load(destination).layers) == 1)
        assert_clean(folder)

        sibling = folder / "second.ttgstudio.json"
        project.name = "Independent second project"
        project.save(sibling)
        check("independent project created without modifying first",
              destination.read_bytes() == final and
              TTGProject.load(sibling).name == project.name)
        assert_clean(folder)

        nowhere = folder / "missing" / "project.ttgstudio.json"
        try:
            project.save(nowhere)
        except FileNotFoundError:
            checks.append("missing destination directory rejected without side effects")
        else:
            raise AssertionError("Missing destination silently created")
        check("missing folder not created", not nowhere.parent.exists())

    print(json.dumps({"result": "PASS", "checks_count": len(checks),
                      "checks": checks}, indent=2))


if __name__ == "__main__":
    main()
