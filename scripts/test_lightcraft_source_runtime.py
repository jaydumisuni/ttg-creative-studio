"""Builder source-locked LightCraft runtime; no system-installed donor needed."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch
import shutil
import sys

from PIL import Image
from _synthetic_dng_fixture import write_synthetic_dng

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ttg_lightcraft_source_runtime import (
    LightCraftSourceRuntimeUnavailable,
    resolve_builder_lightcraft_runtime,
)
from ttg_lightcraft_raw_bridge import develop_with_lightcraft
from ttg_project_schema import TTGProject


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BuilderSourceRuntimeTests(TestCase):
    def source_fixture(self, root: Path, *, windows: bool = False):
        lock_src = ROOT / "build_config/donor-sources/lightcraft.json"
        lock_dest = root / "build_config/donor-sources/lightcraft.json"
        lock_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(lock_src, lock_dest)
        lock = json.loads(lock_dest.read_text())
        artifact = root / lock["artifacts"]["windows" if windows else "linux"]
        artifact.parent.mkdir(parents=True, exist_ok=True)
        if windows:
            artifact.write_bytes(b"MZ" + b"test-only-fake-builder-artifact")
        else:
            artifact.write_text(
                "#!/usr/bin/env python3\n"
                "from PIL import Image\n"
                "import sys\n"
                "assert sys.argv[1]=='render' and sys.argv[3]=='-o'\n"
                "assert sys.argv[5:] == ['--set', 'light.exposure=0.5000']\n"
                "Image.new('RGB',(15,11),(25,75,125)).save(sys.argv[4])\n"
            )
            artifact.chmod(0o700)
        receipt = root / "build_config/donor-sources/lightcraft-builder-receipt.json"
        record = {
            "schema": "ttg.builder.lightcraft-source-runtime-receipt.v1",
            "builder": "thetechguy-software-builder",
            "source_lock_sha256": digest(lock_dest),
            "sources": {
                "lightcraft": lock["sources"]["lightcraft"]["commit"],
                "craft_libs": lock["sources"]["craft_libs"]["commit"],
            },
            "artifact_sha256": digest(artifact),
        }
        receipt.write_text(json.dumps(record))
        return artifact, receipt, lock_dest

    def test_default_resolves_only_registered_builder_bundle_and_source_revision(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            artifact, _, lock = self.source_fixture(root)
            result = resolve_builder_lightcraft_runtime(project_root=root, windows=False)
            self.assertEqual(result["path"], artifact)
            self.assertTrue(result["builder_staged"])
            self.assertFalse(result["installed_donor_application_required"])
            self.assertEqual(result["lightcraft_source_commit"], json.loads(lock.read_text())["sources"]["lightcraft"]["commit"])
            self.assertFalse(result["production_signing_verified"])

    def test_missing_builder_receipt_is_not_installation_instruction_or_path_fallback(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            artifact, receipt, _ = self.source_fixture(root)
            receipt.unlink()
            with patch.dict(os.environ, {"PATH": str(artifact.parent)}, clear=False):
                with self.assertRaisesRegex(LightCraftSourceRuntimeUnavailable, "Builder receipt"):
                    resolve_builder_lightcraft_runtime(project_root=root, windows=False)

    def test_tampered_artifact_and_source_lock_fail_closed(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            artifact, receipt, lock = self.source_fixture(root)
            artifact.write_bytes(artifact.read_bytes()+b"modification")
            with self.assertRaisesRegex(LightCraftSourceRuntimeUnavailable, "do not match"):
                resolve_builder_lightcraft_runtime(project_root=root, windows=False)
            artifact, receipt, lock = self.source_fixture(root)
            lock.write_bytes(lock.read_bytes()+b"\n")
            with self.assertRaisesRegex(LightCraftSourceRuntimeUnavailable, "source lock has changed"):
                resolve_builder_lightcraft_runtime(project_root=root, windows=False)

    def test_wrong_source_revision_and_symlink_refused(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            artifact, receipt, lock = self.source_fixture(root)
            record=json.loads(receipt.read_text())
            record["sources"]["craft_libs"]="0"*40
            receipt.write_text(json.dumps(record))
            with self.assertRaisesRegex(LightCraftSourceRuntimeUnavailable, "locked donor"):
                resolve_builder_lightcraft_runtime(project_root=root, windows=False)
            self.source_fixture(root)
            other=root/"other"
            other.write_bytes(artifact.read_bytes())
            artifact.unlink()
            try:
                artifact.symlink_to(other)
            except (OSError, NotImplementedError):
                self.skipTest("Current host disallows symbolic links")
            with self.assertRaisesRegex(LightCraftSourceRuntimeUnavailable,"Symlink"):
                resolve_builder_lightcraft_runtime(project_root=root, windows=False)

    def test_windows_bundle_uses_platform_binary_without_install(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            artifact,_,_=self.source_fixture(root,windows=True)
            result=resolve_builder_lightcraft_runtime(project_root=root,windows=True)
            self.assertEqual(result["path"],artifact)
            self.assertTrue(str(artifact).endswith(".exe"))
            self.assertFalse(result["installed_donor_application_required"])

    def test_source_bundle_enters_actual_existing_studio_editable_layer(self):
        if os.name == "nt":
            self.skipTest("Stub is POSIX script; Windows resolver and real Studio Qt tested separately")
        with TemporaryDirectory() as d:
            root=Path(d)
            artifact,receipt,lock=self.source_fixture(root)
            raw=root/"camera.dng"
            write_synthetic_dng(raw)
            original=raw.read_bytes()
            dest=root/"editable.ttgstudio.json"
            with patch("ttg_lightcraft_source_runtime._root_directory",return_value=root):
                result=develop_with_lightcraft(raw,dest,exposure=0.5)
            self.assertTrue(dest.exists())
            project=TTGProject.load(dest)
            self.assertEqual(project.canvas.width,15)
            self.assertEqual(project.canvas.height,11)
            proof=project.export["lightcraft_raw_handoff"]
            self.assertTrue(proof["donor_staged_by_registered_builder"])
            self.assertFalse(proof["separate_lightcraft_install_required"])
            self.assertFalse(proof["raw_demosaic_validated"])
            self.assertFalse(proof["lightcraft_vendor_binary_identity_verified"])
            self.assertEqual(proof["donor_source_provenance"]["lightcraft_source_commit"],
                             json.loads(lock.read_text())["sources"]["lightcraft"]["commit"])
            self.assertEqual(raw.read_bytes(),original)
            self.assertEqual(result["original_raw_sha256"],hashlib.sha256(original).hexdigest())


if __name__=="__main__":
    main()
