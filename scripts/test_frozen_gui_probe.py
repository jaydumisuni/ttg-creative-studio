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
from unittest.mock import patch
sys.path.insert(0, str(ROOT / "src"))
from ttg_frozen_gui_probe import qualify_gui


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
        recorded = json.loads((destination / "gui-proof.json").read_text())
        font = recorded.get("ui_font_evidence", {})
        assert font.get("wide_advance", 0) > font.get("narrow_advance", 0) * 1.3
        assert font.get("narrow_advance", 0) > 0

        with tempfile.TemporaryDirectory(prefix="ttg-unreadable-font-") as no_font_dir:
            missing_font = Path(no_font_dir)
            with patch("ttg_frozen_gui_probe.QFontMetrics") as metrics:
                metrics.return_value.horizontalAdvance.return_value = 36
                try:
                    qualify_gui(missing_font)
                except AssertionError as exc:
                    assert "Unreadable/missing Windows UI font" in str(exc)
                else:
                    raise AssertionError("Missing font glyphs incorrectly passed GUI approval")
            assert not list(missing_font.iterdir())

        # Frozen windowed executables must return a bounded error receipt
        # rather than displaying a modal traceback and hanging CI.
        from unittest.mock import patch as mock_patch
        import launch_creative_studio
        with tempfile.TemporaryDirectory(prefix="ttg-gui-diagnostic-") as error_dir:
            with mock_patch.object(
                sys, "argv", ["TTG Creative Studio", "--qualify-gui", error_dir]
            ), mock_patch("ttg_frozen_gui_probe.qualify_gui",
                         side_effect=AssertionError("Unreadable/missing Windows UI font")):
                assert launch_creative_studio.main() == 3
            assert "Unreadable/missing Windows UI font" in (
                Path(error_dir) / "gui-failure.txt"
            ).read_text()

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
    # Installed Windows proof must use native font rasterization; an
    # offscreen-only Windows run previously accepted missing-glyph squares.
    script = (ROOT / "scripts" / "test_installer_windows.ps1").read_text()
    assert '$env:QT_QPA_PLATFORM = "windows"' in script
    print(json.dumps({"result": "PASS", "checks": [
        "real native GUI launch/edit/save/export/screenshot",
        "artifact SHA-256 verification",
        "reject replacing an existing proof",
        "reject image tampering",
        "reject unreadable Windows UI font glyphs",
        "windowed CI saves non-modal GUI failure diagnostic",
        "installed Windows GUI must exercise native font backend",
    ]}, indent=2))


if __name__ == "__main__":
    main()
