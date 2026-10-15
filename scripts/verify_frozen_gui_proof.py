#!/usr/bin/env python3
"""Verify frozen Creative Studio GUI proof: schemas, output digests and PNGs."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


def validate(directory: Path) -> dict:
    directory = directory.resolve(strict=True)
    report = json.loads((directory / "gui-proof.json").read_text(encoding="utf-8"))
    if report.get("schema") != "ttg.creative.frozen-gui-qualification.v1":
        raise ValueError("Wrong proof schema")
    if report.get("result") != "PASS" or len(report.get("checks", [])) != 9:
        raise ValueError("Actual GUI tests did not pass")
    expected = {
        "gui-window.png", "gui-export.png", "gui-editable.ttgstudio.json"
    }
    if set(report.get("artifacts", {})) != expected:
        raise ValueError("Missing GUI proof evidence")
    for name in expected:
        path = directory / name
        data = path.read_bytes()
        assert len(data) == report["artifacts"][name]["bytes"], name
        assert hashlib.sha256(data).hexdigest() == report["artifacts"][name]["sha256"], name
        if name.endswith(".png"):
            if data[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError("Invalid PNG proof")
            width, height = struct.unpack(">II", data[16:24])
            if width < 1 or height < 1:
                raise ValueError("PNG dimensions invalid")
            if name == "gui-window.png" and (width < 1024 or height < 640):
                raise ValueError("Application screenshot is too small")
            if name == "gui-export.png" and (width, height) != (480, 320):
                raise ValueError("Export dimensions changed")
        elif name.endswith(".json"):
            doc = json.loads(data)
            if not any(
                layer.get("type") == "text" and
                layer.get("properties", {}).get("text") == "EDITED IN STUDIO"
                for layer in doc.get("layers", [])
            ):
                raise ValueError("Native editable project was not saved correctly")
    return {"result": "PASS", "checked_files": sorted(expected)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("proof_directory", type=Path)
    print(json.dumps(validate(parser.parse_args().proof_directory), indent=2))
