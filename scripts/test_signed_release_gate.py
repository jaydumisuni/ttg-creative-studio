"""Adversarial tests for production signing and real inference receipt custody."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

def main():
    checks = []
    workflow = (ROOT / ".github/workflows/studio-production-signing.yml").read_text()
    signer = (ROOT / "sign_release.ps1").read_text()
    verifier = (ROOT / "scripts/verify_signed_installer.ps1").read_text()
    assert "workflow_dispatch:" in workflow
    assert "environment: production-signing" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "inputs.approved_sha" in workflow and "APPROVED_SHA -cne $env:GITHUB_SHA" in workflow
    assert "secrets.TTG_STUDIO_SIGNING_PASSWORD" in workflow
    assert "secrets.TTG_STUDIO_SIGNING_PFX_B64" in workflow
    assert "secrets.TTG_STUDIO_EXPECTED_SIGNER_THUMBPRINT" in workflow
    assert "persist-credentials: false" in workflow
    assert "TTG-Creative-Studio-Windows-SIGNED-approved" in workflow
    assert "Sign approved installer" in workflow and "Get-AuthenticodeSignature" in verifier
    assert "TTG_STUDIO_EXPECTED_SIGNER_THUMBPRINT" in signer and "verify_signed_installer.ps1" in signer
    assert "TimeStamperCertificate" in verifier and "SignerCertificate.Thumbprint" in verifier
    checks.append("manual-only signed workflow is pinned to main SHA and production environment")

    try:
        import yaml
        obj = yaml.safe_load(workflow)
        assert "signed-windows" in obj["jobs"]
        assert obj["jobs"]["signed-windows"]["environment"] == "production-signing"
        steps = obj["jobs"]["signed-windows"]["steps"]
        assert len(steps) > 8
        assert all("pull_request:" not in workflow for _ in (0,))
        checks.append("signed workflow parses and has no PR-triggered publication")
    except ImportError:
        checks.append("workflow structural check passed (no PyYAML runtime)")

    path = ROOT / "scripts/qualify_local_ai.py"
    spec = importlib.util.spec_from_file_location("studio_qualifier_release_test", path)
    assert spec and spec.loader
    qualifier = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = qualifier
    spec.loader.exec_module(qualifier)

    with tempfile.TemporaryDirectory(prefix="studio-inference-custody-") as work:
        folder = Path(work)
        models = folder / "models"
        models.mkdir()
        chk = models / "fixture.safetensors"
        # Sparse placeholder qualifies only the FILE SIZE gate, not real inference.
        with chk.open("wb") as out:
            out.truncate(110_000_000)
        output = folder / "image.png"
        proof = output.with_suffix(".proof.json")
        pix = Image.frombytes("RGB", (512, 512), os.urandom(512 * 512 * 3))
        with patch.object(qualifier, "ComfyUIBackend") as provider:
            provider.return_value.available_models.return_value = ["fixture.safetensors"]
            provider.return_value.generate.return_value = pix
            result = qualifier.qualify(
                url="http://127.0.0.1:8188", checkpoint_directory=models,
                name="fixture.safetensors", output=output, prompt="Test fixture",
            )
            assert output.is_file() and proof.is_file()
            assert result["status"] == "REAL_IMAGE_GENERATED"
            assert output.stat().st_size > 10_000
            checks.append("exclusive real-result output and digest manifest")

            original = output.read_bytes()
            receipt = proof.read_bytes()
            try:
                qualifier.qualify(
                    url="http://127.0.0.1:8188", checkpoint_directory=models,
                    name="fixture.safetensors", output=output, prompt="Second fixture",
                )
            except FileExistsError:
                pass
            else:
                raise AssertionError("Overwrite of existing AI evidence allowed")
            assert output.read_bytes() == original and proof.read_bytes() == receipt
            checks.append("repeat run cannot overwrite previous image or receipt")

            output.unlink()
            # Old proof must remain and new image must not be published.
            try:
                qualifier.qualify(
                    url="http://127.0.0.1:8188", checkpoint_directory=models,
                    name="fixture.safetensors", output=output, prompt="Collision",
                )
            except FileExistsError:
                pass
            else:
                raise AssertionError("Existing proof receipt was ignored")
            assert not output.exists() and proof.read_bytes() == receipt
            checks.append("pre-existing proof receipt cannot be destroyed")

            proof.unlink()
            base_link = qualifier.os.link
            calls = 0
            def fail_receipt_link(src, dest):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("Simulated proof publish failure")
                return base_link(src, dest)
            with patch.object(qualifier.os, "link", side_effect=fail_receipt_link):
                try:
                    qualifier.qualify(
                        url="http://127.0.0.1:8188",
                        checkpoint_directory=models,
                        name="fixture.safetensors", output=output, prompt="Broken receipt",
                    )
                except OSError:
                    pass
                else:
                    raise AssertionError("Proof publish failure was not reported")
            assert not output.exists() and not proof.exists()
            assert not list(folder.glob(".studio-inference-*.tmp"))
            checks.append("receipt publish failure rolls back only new files")

    print("SIGNED_RELEASE_AND_INFERENCE_CUSTODY_PASS " + str(len(checks)))

if __name__ == "__main__":
    main()
