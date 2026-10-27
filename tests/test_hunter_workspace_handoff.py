from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from ttg_creative_studio.hunter_workspace_handoff import HandoffDenied, inspect_staged_image


class StudioWorkspaceHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ttg-handoff-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "inbox"
        self.folder = self.root / "owner-user" / "workspace1" / "file1"
        self.folder.mkdir(parents=True, mode=0o700)
        for part in [self.root, self.root / "owner-user", self.root / "owner-user/workspace1", self.folder]:
            part.chmod(0o700)
        self.image = self.folder / "input.png"
        Image.new("RGB", (5, 7), "purple").save(self.image)
        self.sha = hashlib.sha256(self.image.read_bytes()).hexdigest()
        self.manifest = {
            "actor": "owner-user", "workspaceId": "workspace1",
            "fileId": "file1", "sha256": self.sha,
            "name": "user-upload.png", "size": self.image.stat().st_size,
            "source": "hunter-owner-r2-v1"
        }
        (self.folder / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def inspect(self, **changes):
        args = dict(
            staging_root=self.root, actor="owner-user",
            workspace_id="workspace1", file_id="file1",
            expected_sha256=self.sha, job_id="job123"
        )
        args.update(changes)
        return inspect_staged_image(**args)

    def test_real_studio_director_receipt(self):
        result = self.inspect()
        self.assertTrue(result["ok"])
        self.assertEqual(result["studioTask"], "image_info")
        self.assertEqual(result["result"]["width"], 5)
        self.assertEqual(result["result"]["height"], 7)
        self.assertEqual(result["sha256"], self.sha)
        self.assertEqual(result["semanticImageUnderstanding"], False)
        self.assertNotIn("inputPath", result)

    def test_wrong_owner_denied(self):
        with self.assertRaises(HandoffDenied):
            self.inspect(actor="other-user")

    def test_digest_tampering_denied(self):
        self.image.write_bytes(self.image.read_bytes() + b"tamper")
        with self.assertRaises(HandoffDenied):
            self.inspect()

    def test_symlink_denied(self):
        target = self.folder / "saved.png"
        self.image.rename(target)
        self.image.symlink_to(target)
        with self.assertRaises(HandoffDenied):
            self.inspect()

    def test_traversal_denied(self):
        with self.assertRaises(HandoffDenied):
            self.inspect(file_id="../secret")

    def test_pdf_rejected_not_false_vision(self):
        self.image.unlink()
        self.manifest["name"] = "document.pdf"
        (self.folder / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        with self.assertRaises(HandoffDenied):
            self.inspect()

    def test_private_directory_required(self):
        self.root.chmod(0o755)
        with self.assertRaises(HandoffDenied):
            self.inspect()


if __name__ == "__main__":
    unittest.main()
