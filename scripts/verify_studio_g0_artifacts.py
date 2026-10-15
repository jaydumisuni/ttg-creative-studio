#!/usr/bin/env python3
"""Independent SHA/GUI/release-format audit for Creative Studio CI artifacts.

No network, signing, installation, code execution from artifacts or mutation.
Use only in an independently admitted engineering workspace with downloaded
GitHub Actions artifact *contents*. The GitHub artifact ZIP hashes in the
manifest are API metadata, not the hashes of extracted files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import tarfile
from pathlib import Path

EXPECTED_WINDOWS_SHA256 = "c82fee6eddf8fa03a93a0bf76e92e06ff9f76ec97b7924f73c9a6201700effc6"
EXPECTED_WINDOWS_SIZE = 51126236
EXPECTED_LINUX_TAR_SHA256 = "13bbee4c2e3822fffde3de4f1dcb7d4124fae02f4c1b918570f9458e5420fd75"
EXPECTED_LINUX_TAR_SIZE = 96212767


def sha(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def check_pe_authenticode(path: Path) -> bool:
    """Return whether the PE security-directory advertises a signature.

    This is not a chain or publisher trust verification; the signed
    Authenticode Windows release still requires an OS trust check.
    """
    with path.open("rb") as f:
        if f.read(2) != b"MZ":
            raise ValueError("Installer has no DOS MZ header")
        f.seek(60)
        pe = struct.unpack("<I", f.read(4))[0]
        if pe < 64 or pe > 16_777_216:
            raise ValueError("Invalid PE header offset")
        f.seek(pe)
        if f.read(4) != bytes((80, 69, 0, 0)):
            raise ValueError("Installer missing PE signature")
        f.seek(pe + 24)
        magic = struct.unpack("<H", f.read(2))[0]
        if magic not in (0x10B, 0x20B):
            raise ValueError("Not a supported PE optional header")
        f.seek(pe + 24 + (112 if magic == 0x20B else 96) + 8 * 4)
        _offset, certificate_size = struct.unpack("<II", f.read(8))
        return certificate_size > 0


def verify_gui_proof(folder: Path) -> dict:
    manifest = json.loads((folder / "gui-proof.json").read_text("utf-8"))
    if (manifest.get("schema") != "ttg.creative.frozen-gui-qualification.v1"
            or manifest.get("result") != "PASS"):
        raise ValueError("GUI proof does not claim a qualified Studio window")
    if len(manifest.get("checks", [])) < 9:
        raise ValueError("GUI proof is incomplete")
    for filename, record in manifest.get("artifacts", {}).items():
        if Path(filename).name != filename:
            raise ValueError("Invalid proof file name")
        source = folder / filename
        if not source.is_file():
            raise FileNotFoundError("GUI proof artifact missing: " + filename)
        if source.stat().st_size != record["bytes"] or sha(source) != record["sha256"]:
            raise ValueError("GUI proof payload hash mismatch: " + filename)
    return {"status": "PASS", "checks": len(manifest["checks"]),
            "files": sorted(manifest["artifacts"])}


def verify_windows(base: Path) -> dict:
    binary = base / "TTG-Creative-Studio-Windows-unsigned" / "TTG-Creative-Studio-Core-Setup.exe"
    if not binary.is_file():
        raise FileNotFoundError("Downloaded Windows installer is absent")
    digest = sha(binary)
    if (digest != EXPECTED_WINDOWS_SHA256
            or binary.stat().st_size != EXPECTED_WINDOWS_SIZE):
        raise ValueError("Installer identity mismatch")
    signed = check_pe_authenticode(binary)
    if signed:
        raise ValueError("Unsigned CI build unexpectedly has a signature; pin new artifact")
    return {"status": "PASS", "bytes": binary.stat().st_size,
            "sha256": digest, "authenticode_present": False,
            "gui_proof": verify_gui_proof(base / "windows-gui")}


def verify_linux(base: Path) -> dict:
    folder = base / "linux-portable"
    if not folder.exists():
        return {"status": "PENDING_LOCAL_DOWNLOAD"}
    archive = next(folder.glob("*.tar.gz"), None)
    if archive is None:
        return {"status": "PENDING_LOCAL_DOWNLOAD"}
    digest = sha(archive)
    if digest != EXPECTED_LINUX_TAR_SHA256 or archive.stat().st_size != EXPECTED_LINUX_TAR_SIZE:
        raise ValueError("Linux frozen bundle identity mismatch")
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        if len(names) > 5000:
            raise ValueError("Excessive entries in frozen app archive")
        if not any(x.endswith("TTG Creative Studio") for x in names):
            raise ValueError("Linux archive has no Studio executable")
        for name in names:
            path = Path(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Unsafe Linux archive entry")
    return {"status": "PASS", "sha256": digest,
            "bytes": archive.stat().st_size, "entry_count": len(names),
            "gui_proof": verify_gui_proof(base / "linux-gui")}


def main() -> int:
    arg = argparse.ArgumentParser()
    arg.add_argument("download_directory", type=Path)
    args = arg.parse_args()
    result = {
        "schema": "ttg.creative.studio.g0.artifact-audit.v1",
        "build_commit": "f6992bbcf7c3d8e7d58faae3b144af587469bdb5",
        "observed_main": "6f1fa428e1480fb3fa34f44630c1d19f9375fe1d",
        "workflow_run": 38721211493,
        "windows": verify_windows(args.download_directory),
        "linux": verify_linux(args.download_directory),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
