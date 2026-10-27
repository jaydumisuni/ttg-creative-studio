"""Verified handoff from a Ptah-staged Hunter R2 file to the *existing* Studio Director.

No transport, auth or image understanding is implemented here. Only Armour's
authorized staging action may populate the private inbox. This adapter checks
that source custody before asking the existing image job CLI for image_info.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from typing import Any

SCHEMA = "ttg.creative.workspace-handoff.v1"
ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
ACTOR = re.compile(r"^[A-Za-z0-9._@:-]{1,128}$")
HASH = re.compile(r"^[a-f0-9]{64}$")
ALLOWED = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_IMAGE_BYTES = 12_000_000
DEFAULT_ROOT = Path.home() / ".local/state/ptah/hunter-creative-inbox"
STUDIO_CLI = Path(__file__).resolve().parent / "cli.py"


class HandoffDenied(ValueError):
    pass


def _id(value: str, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise HandoffDenied(label + "_INVALID")
    return value


def _private_component(path: Path) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise HandoffDenied("WORKSPACE_STAGE_NOT_FOUND") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise HandoffDenied("WORKSPACE_SYMLINK_DENIED")
    if not stat.S_ISDIR(metadata.st_mode):
        raise HandoffDenied("WORKSPACE_DIRECTORY_REQUIRED")
    if metadata.st_uid != os.getuid():
        raise HandoffDenied("WORKSPACE_OWNER_MISMATCH")
    if metadata.st_mode & 0o077:
        raise HandoffDenied("WORKSPACE_PERMISSIONS_TOO_BROAD")


def _load_verified(
    root: Path, actor: str, workspace_id: str, file_id: str, expected_digest: str
) -> tuple[Path, dict[str, Any]]:
    actor = _id(actor, ACTOR, "ACTOR")
    workspace_id = _id(workspace_id, ID, "WORKSPACE_ID")
    file_id = _id(file_id, ID, "FILE_ID")
    expected_digest = _id(expected_digest, HASH, "DIGEST")
    for directory in [
        root, root / actor, root / actor / workspace_id,
        root / actor / workspace_id / file_id
    ]:
        _private_component(directory)
    directory = root / actor / workspace_id / file_id
    manifest_path = directory / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise HandoffDenied("SIGNED_STAGE_MANIFEST_REQUIRED")
    if manifest_path.stat().st_size > 8_192:
        raise HandoffDenied("MANIFEST_TOO_LARGE")
    try:
        manifest = json.loads(manifest_path.read_text("utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        raise HandoffDenied("MANIFEST_INVALID") from error
    if not isinstance(manifest, dict) or any(
        manifest.get(key) != value for key, value in {
            "actor": actor, "workspaceId": workspace_id, "fileId": file_id,
            "sha256": expected_digest, "source": "hunter-owner-r2-v1"
        }.items()
    ):
        raise HandoffDenied("STAGE_IDENTITY_MISMATCH")
    name = str(manifest.get("name", ""))
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED:
        raise HandoffDenied("STUDIO_IMAGE_FORMAT_NOT_ADMITTED")
    image = directory / ("input" + suffix)
    if image.is_symlink() or not image.is_file():
        raise HandoffDenied("STAGED_IMAGE_REQUIRED")
    size = image.stat().st_size
    if size <= 0 or size > MAX_IMAGE_BYTES or manifest.get("size") != size:
        raise HandoffDenied("STAGED_IMAGE_SIZE_MISMATCH")
    observed = hashlib.sha256(image.read_bytes()).hexdigest()
    if observed != expected_digest:
        raise HandoffDenied("STAGED_IMAGE_DIGEST_MISMATCH")
    return image, manifest


def inspect_staged_image(
    *, staging_root: Path, actor: str, workspace_id: str,
    file_id: str, expected_sha256: str, job_id: str
) -> dict[str, Any]:
    _id(job_id, ID, "JOB_ID")
    source, manifest = _load_verified(staging_root, actor, workspace_id, file_id, expected_sha256)
    # Studio's existing CLI/engine is the sole image processor. No second
    # PIL/vision parser or model is introduced by this handoff adapter.
    with tempfile.TemporaryDirectory(prefix="ttg-studio-handoff-") as temporary:
        base = Path(temporary)
        job = base / "job.json"
        result_file = base / "result.json"
        output = base / "metadata.json"
        job.write_text(json.dumps({
            "jobId": job_id, "task": "image_info", "input": str(source),
            "output": str(output), "options": {"overwrite": False}
        }), encoding="utf-8")
        executed = subprocess.run([
            sys.executable, str(STUDIO_CLI), "--job", str(job), "--result", str(result_file)
        ], cwd=str(STUDIO_CLI.parents[2]), capture_output=True, text=True, timeout=30)
        if executed.returncode or not result_file.is_file() or not output.is_file():
            raise HandoffDenied("STUDIO_DIRECTOR_RESULT_NOT_VERIFIED")
        result = json.loads(result_file.read_text("utf-8"))
        metadata = json.loads(output.read_text("utf-8"))
        if result.get("ok") is not True or result.get("task") != "image_info" or result.get("status") != "done":
            raise HandoffDenied("STUDIO_DIRECTOR_RESULT_INVALID")
        if not isinstance(metadata, dict) or not all(
            isinstance(metadata.get(key), int) for key in ("width", "height")
        ):
            raise HandoffDenied("STUDIO_METADATA_UNVERIFIED")
        return {
            "ok": True, "schemaVersion": SCHEMA, "studioTask": "image_info",
            "execution": "studio-existing-cli", "qualifiedMeaning": "image-metadata-only",
            "actor": actor, "workspaceId": workspace_id, "fileId": file_id,
            "sha256": expected_sha256, "bytes": manifest["size"],
            "jobId": job_id, "result": metadata, "semanticImageUnderstanding": False,
            "secretValuesExposed": False
        }
