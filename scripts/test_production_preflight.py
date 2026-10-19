#!/usr/bin/env python3
"""Adversarial, no-network-escape product preflight tests for release and local AI."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ttg_image_lab import ComfyUIBackend


class RedirectFixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", "https://example.invalid/private?source=image")
        self.end_headers()


def load_qualifier():
    path = ROOT / "scripts" / "qualify_local_ai.py"
    spec = importlib.util.spec_from_file_location("studio_local_ai_qualifier", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    passed = []
    service = ThreadingHTTPServer(("127.0.0.1", 0), RedirectFixture)
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()
    try:
        client = ComfyUIBackend(f"http://127.0.0.1:{service.server_port}")
        try:
            client.available_models()
        except ValueError as error:
            assert "redirect blocked" in str(error)
        else:
            raise AssertionError("Local inference followed remote redirect")
        passed.append("block prompt/asset HTTP redirects")
    finally:
        service.shutdown()
        service.server_close()
        thread.join(3)

    qualifier = load_qualifier()
    with tempfile.TemporaryDirectory(prefix="studio-prod-preflight-") as tmp:
        root = Path(tmp)
        missing = root / "missing"
        try:
            qualifier.qualify(
                url="http://127.0.0.1:8188", checkpoint_directory=missing,
                name=None, output=None, prompt="studio product"
            )
        except RuntimeError as error:
            assert "checkpoint directory" in str(error)
        else:
            raise AssertionError("Readiness falsely passed with no model directory")
        passed.append("missing checkpoint directory fails closed")

        candidates = root / "models"
        candidates.mkdir()
        with patch.object(qualifier, "ComfyUIBackend") as fake:
            fake.return_value.available_models.return_value = []
            try:
                qualifier.qualify(
                    url="http://127.0.0.1:8188",
                    checkpoint_directory=candidates, name=None, output=None,
                    prompt="studio product"
                )
            except RuntimeError as error:
                assert "no installed checkpoints" in str(error)
            else:
                raise AssertionError("Model readiness falsely passed empty list")
        passed.append("ComfyUI no-model enumeration fails closed")

        sample = candidates / "tiny.safetensors"
        sample.write_bytes(b"not a model")
        with patch.object(qualifier, "ComfyUIBackend") as fake:
            fake.return_value.available_models.return_value = ["tiny.safetensors"]
            try:
                qualifier.qualify(
                    url="http://127.0.0.1:8188", checkpoint_directory=candidates,
                    name="tiny.safetensors", output=root / "proof.png",
                    prompt="studio product"
                )
            except RuntimeError as error:
                assert "too small" in str(error)
            else:
                raise AssertionError("Tiny file promoted as real diffusion checkpoint")
            assert not fake.return_value.generate.called
        passed.append("placeholder checkpoint cannot pass physical inference")

        run = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts" / "qualify_local_ai.py"),
             "--checkpoint-dir", str(missing)],
            cwd=ROOT, capture_output=True, text=True, timeout=12,
        )
        assert run.returncode == 2
        assert json.loads(run.stdout)["status"] == "NO_GO"
        passed.append("CLI no-service/no-model returns NO_GO and exit 2")

    workflow = (ROOT / ".github/workflows/studio-release-candidate.yml").read_text()
    windows_script = (ROOT / "scripts/test_installer_windows.ps1").read_text()
    assert 'test_installer_windows.ps1' in workflow
    # YAML ampersands are anchors unless the PowerShell invocation is in a
    # literal block. Require the actual block scalar.
    assert '        run: |\n          & ".\\scripts\\test_installer_windows.ps1"' in workflow
    assert "native-desktop" in workflow
    for token in ("unins000.exe", "TTG Creative Studio.exe", "--self-check",
                  "/VERYSILENT", "Start-Process"):
        assert token in windows_script, token
    assert "Invoke-BoundedInstallerStep" in windows_script
    assert windows_script.count("Invoke-BoundedInstallerStep -FilePath") == 4
    assert "WaitForExit($TimeoutSeconds * 1000)" in windows_script
    assert "Stop-Process -Id $process.Id -Force" in windows_script
    assert " -Wait -PassThru" not in windows_script
    passed.append("CI exercises bounded real Windows install+GUI+smoke+uninstall")
    print(json.dumps({"result": "PASS", "checks": len(passed),
                      "evidence": passed}, indent=2))


if __name__ == "__main__":
    main()
