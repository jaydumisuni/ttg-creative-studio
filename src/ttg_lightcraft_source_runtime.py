"""Resolve the source-backed LightCraft runtime bundled by THETECHGUY Builder.

No PATH lookup, silent downloads, system installation, or ad-hoc compilation.
This is *runtime artifact provenance* and not production code signing.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

LOCK_RELATIVE = Path("build_config/donor-sources/lightcraft.json")
RECEIPT_RELATIVE = Path("build_config/donor-sources/lightcraft-builder-receipt.json")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


class LightCraftSourceRuntimeUnavailable(RuntimeError):
    """The project has no qualified Builder-staged donor-source runtime."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for block in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8192:
        raise LightCraftSourceRuntimeUnavailable(
            f"Missing or oversized Studio donor source lock/Builder receipt: {path.name}"
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise LightCraftSourceRuntimeUnavailable("Invalid Studio donor source manifest/receipt") from exc
    if not isinstance(data, dict):
        raise LightCraftSourceRuntimeUnavailable("Studio donor runtime record must be a JSON object")
    return data


def _root_directory(project_root: Path | str | None) -> Path:
    if project_root is not None:
        return Path(project_root).resolve(strict=True)
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS).resolve(strict=True)
    return Path(__file__).resolve().parents[1]


def resolve_builder_lightcraft_runtime(
    *, project_root: Path | str | None = None,
    windows: bool | None = None,
) -> dict:
    """Return the immutable identity of an existing, Builder-staged source runtime.

    Project-root override is only for tests/tools targeting a specific source
    root. The app's standard code path uses its own bundled project root.
    """
    root = _root_directory(project_root)
    lock_path = root / LOCK_RELATIVE
    receipt_path = root / RECEIPT_RELATIVE
    lock = _read_json(lock_path)
    if lock.get("schema") != "ttg.studio.lightcraft-donor-source-lock.v1":
        raise LightCraftSourceRuntimeUnavailable("Unsupported Studio LightCraft source lock")
    if lock.get("build_authority") != "thetechguy-software-builder":
        raise LightCraftSourceRuntimeUnavailable("Builder is the sole donor source build authority")
    donor = lock.get("sources")
    if not isinstance(donor, dict):
        raise LightCraftSourceRuntimeUnavailable("Source revisions not declared")
    for item in ("lightcraft", "craft_libs"):
        entry = donor.get(item)
        if not isinstance(entry, dict) or not _GIT_SHA.fullmatch(str(entry.get("commit", ""))):
            raise LightCraftSourceRuntimeUnavailable("Missing exact Git donor source revision")
    receipt = _read_json(receipt_path)
    if receipt.get("schema") != "ttg.builder.lightcraft-source-runtime-receipt.v1":
        raise LightCraftSourceRuntimeUnavailable("Unrecognized Builder source-runtime receipt")
    if receipt.get("builder") != "thetechguy-software-builder":
        raise LightCraftSourceRuntimeUnavailable("Runtime not attributed to the registered Builder")
    if receipt.get("source_lock_sha256") != _sha256(lock_path):
        raise LightCraftSourceRuntimeUnavailable("Builder runtime source lock has changed")
    versions = receipt.get("sources")
    if not isinstance(versions, dict):
        raise LightCraftSourceRuntimeUnavailable("Builder runtime source revision map missing")
    for item in ("lightcraft", "craft_libs"):
        if versions.get(item) != donor[item]["commit"]:
            raise LightCraftSourceRuntimeUnavailable("Compiled runtime source does not match locked donor")
    if windows is None:
        windows = os.name == "nt"
    paths = lock.get("artifacts")
    if not isinstance(paths, dict):
        raise LightCraftSourceRuntimeUnavailable("Builder output paths unspecified")
    relative = paths.get("windows" if windows else "linux")
    if not isinstance(relative, str):
        raise LightCraftSourceRuntimeUnavailable("Missing source-backed runtime for platform")
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts or relative_path.drive:
        raise LightCraftSourceRuntimeUnavailable("Builder runtime path escapes Studio")
    artifact = root / relative_path
    current = root
    for piece in relative_path.parts:
        current = current / piece
        if current.is_symlink():
            raise LightCraftSourceRuntimeUnavailable("Symlink in Builder runtime artifact path")
    try:
        st = artifact.stat()
    except OSError as exc:
        raise LightCraftSourceRuntimeUnavailable(
            "LightCraft source engine has not been built/staged by THETECHGUY Builder"
        ) from exc
    if not stat.S_ISREG(st.st_mode):
        raise LightCraftSourceRuntimeUnavailable("Builder runtime artifact is not a regular file")
    if st.st_size <= 0 or st.st_size > 512 * 1024 * 1024:
        raise LightCraftSourceRuntimeUnavailable("Builder runtime artifact outside size budget")
    stored_hash = receipt.get("artifact_sha256")
    if not isinstance(stored_hash, str) or not _SHA256.fullmatch(stored_hash):
        raise LightCraftSourceRuntimeUnavailable("Builder artifact SHA-256 missing or malformed")
    actual = _sha256(artifact)
    if actual != stored_hash:
        raise LightCraftSourceRuntimeUnavailable("Builder artifact bytes do not match source receipt")
    if not windows and not os.access(artifact, os.X_OK):
        raise LightCraftSourceRuntimeUnavailable("Builder runtime is not executable")
    return {
        "path": artifact,
        "artifact_sha256": actual,
        "lightcraft_source_commit": donor["lightcraft"]["commit"],
        "craft_libs_source_commit": donor["craft_libs"]["commit"],
        "source_lock_sha256": _sha256(lock_path),
        "builder_staged": True,
        "installed_donor_application_required": False,
        "production_signing_verified": False,
    }
