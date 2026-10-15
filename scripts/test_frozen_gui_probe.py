"""Source and installed Studio GUI proof contract regression."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_frozen_gui_proof import validate


def main():
    with tempfile.TemporaryDirectory(prefix="ttg-real-gui-proof-") as temp:
        destination = Path(temp)
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        run = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts" / "launch_creative_studio.py"),
             "--qualify-gui", str(destination)],
            cwd=ROOT, capture_output=True, text=True, env=env, timeout=45,
        )
        assert run.returncode == 0, run.stdout + run.stderr
        proof = validate(destination)
        assert proof["result"] == "PASS"
        assert len(proof["checked_files"]) == 3

        # A fresh operation must never overwrite existing proof artifacts.
        second = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts" / "launch_creative_studio.py"),
             "--qualify-gui", str(destination)],
            cwd=ROOT, capture_output=True, text=True, env=env, timeout=40,
        )
        assert second.returncode != 0
        assert len(list(destination.iterdir())) == 4

        # Mutating the exported image invalidates the immutable receipt.
        picture = destination / "gui-export.png"
        content = picture.read_bytes()
        picture.write_bytes(content + b"tamper")
        try:
            validate(destination)
        except AssertionError:
            pass
        else:
            raise AssertionError("Tampered GUI proof passed signature-free hash validation")
    print(json.dumps({"result": "PASS", "checks": [
        "real native GUI launch/edit/save/export/screenshot",
        "artifact SHA-256 verification",
        "reject replacing an existing proof",
        "reject image tampering",
    ]}, indent=2))


if __name__ == "__main__":
    main()
