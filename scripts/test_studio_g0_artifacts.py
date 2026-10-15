#!/usr/bin/env python3
"""Negative-tests G0 artifact verification without executing signed/unsigned apps."""
from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "ttg_g0_artifacts", ROOT / "scripts" / "verify_studio_g0_artifacts.py"
)
assert spec and spec.loader
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


def run():
    with tempfile.TemporaryDirectory(prefix="ttg-g0-negative-") as tmp:
        fixture = Path(tmp)
        (fixture / "gui").mkdir()
        payload = fixture / "gui" / "gui-export.png"
        payload.write_bytes(b"\x89PNG\r\n\x1a\n" + b"example")
        import json
        (fixture / "gui" / "gui-proof.json").write_text(json.dumps({
            "schema": "ttg.creative.frozen-gui-qualification.v1",
            "result": "PASS", "checks": ["test" for _ in range(9)],
            "artifacts": {"gui-export.png": {
                "sha256": verify.sha(payload),
                "bytes": payload.stat().st_size,
            }},
        }))
        assert verify.verify_gui_proof(fixture / "gui")["status"] == "PASS"
        payload.write_bytes(payload.read_bytes() + b"tampered")
        try:
            verify.verify_gui_proof(fixture / "gui")
        except ValueError as error:
            assert "hash mismatch" in str(error)
        else:
            raise AssertionError("Tampered GUI screenshot accepted")

        fake = fixture / "not-a-signed-app.exe"
        fake.write_bytes(b"Not an executable")
        try:
            verify.check_pe_authenticode(fake)
        except ValueError:
            pass
        else:
            raise AssertionError("Non-PE input accepted")
        assert verify.verify_linux(fixture)["status"] == "PENDING_LOCAL_DOWNLOAD"

        # Unpinned archive cannot masquerade as a valid compiled application.
        (fixture / "linux-portable").mkdir()
        (fixture / "linux-portable" / "fake.tar.gz").write_bytes(b"not tar")
        try:
            verify.verify_linux(fixture)
        except ValueError as error:
            assert "identity mismatch" in str(error)
        else:
            raise AssertionError("Unpinned Linux archive accepted")

        print("G0 artifact verifier negative controls: 4/4 PASS")


if __name__ == "__main__":
    run()
