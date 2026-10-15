#!/usr/bin/env python3
"""Studio release candidate custody manifest, not a signature or production approval."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import posixpath
import re
import tarfile
from pathlib import Path

from verify_studio_g0_artifacts import check_pe_authenticode

SCHEMA = "ttg.creative.studio.release-custody.v1"
REPOSITORY = "jaydumisuni/ttg-creative-studio"
DEPS = ("Pillow", "PyQt6", "PyQt6-Qt6", "PyQt6-sip", "pyinstaller")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def classify(path: Path, kind: str) -> dict:
    if not path.is_file() or path.is_symlink() or path.stat().st_size <= 0:
        raise ValueError("Release artifact must be a non-empty regular file")
    if kind == "windows":
        if path.suffix.lower() != ".exe":
            raise ValueError("Expected Windows installer .exe")
        signed = check_pe_authenticode(path)
        return {"authenticode_embedded": signed,
                "trust_status": "UNVERIFIED_SIGNATURE" if signed else "UNSIGNED"}
    if kind == "linux":
        if not (path.name.endswith(".tar.gz") or path.name.endswith(".tgz")):
            raise ValueError("Expected portable .tar.gz")
        with tarfile.open(path, "r:gz") as archive:
            count = 0
            for item in archive:
                name = item.name
                normalized = posixpath.normpath(name)
                if (not name or name.startswith("/") or "\\" in name
                        or normalized.startswith("../") or normalized == ".."
                        or normalized.split("/")[0] != "TTG Creative Studio"
                        or item.islnk() or item.isdev() or item.isfifo()):
                    raise ValueError("Unsafe Linux archive path or entry")
                if item.issym():
                    # PyInstaller's one-folder Linux bundle may contain
                    # legitimate intra-bundle symlinks; disallow escapes.
                    link = item.linkname
                    destination = posixpath.normpath(
                        posixpath.join(posixpath.dirname(normalized), link))
                    if (not link or link.startswith("/") or "\\" in link
                            or destination.startswith("../")
                            or destination.split("/")[0] != "TTG Creative Studio"):
                        raise ValueError("Unsafe Linux symlink target")
                elif not (item.isfile() or item.isdir()):
                    raise ValueError("Unsupported Linux archive entry type")
                count += 1
                if count > 10000:
                    raise ValueError("Excessive Linux archive members")
            if count < 1:
                raise ValueError("Empty Linux application bundle")
        return {"safe_tar_entries": count, "trust_status": "UNSIGNED_ARCHIVE"}
    raise ValueError("Unsupported platform kind")


def create(artifact: Path, kind: str, source_sha: str, run_id: str) -> dict:
    if not re.fullmatch(r"[a-f0-9]{40}", source_sha):
        raise ValueError("A full exact Git source SHA is required")
    if not re.fullmatch(r"[0-9]{1,20}", run_id):
        raise ValueError("GitHub run ID must be numeric")
    details = classify(artifact, kind)
    deps = {}
    for name in DEPS:
        try:
            deps[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            deps[name] = "NOT_INSTALLED_IN_MANIFEST_ENV"
    return {
        "schema": SCHEMA,
        "repository": REPOSITORY,
        "source_sha": source_sha,
        "github_run_id": run_id,
        "platform": kind,
        "artifact": {
            "filename": artifact.name,
            "bytes": artifact.stat().st_size,
            "sha256": digest(artifact),
            **details,
        },
        "build_python_dependencies": deps,
        "qualification": "CANDIDATE_ONLY",
        "production_signature_validated": False,
        "owner_release_approved": False,
        "production_release_ready": False,
    }


def verify(manifest: Path, artifact: Path, source_sha: str | None = None) -> dict:
    if not manifest.is_file() or manifest.stat().st_size > 65536:
        raise ValueError("Missing or oversized release manifest")
    record = json.loads(manifest.read_text("utf-8"))
    if (record.get("schema") != SCHEMA or record.get("repository") != REPOSITORY
            or record.get("qualification") != "CANDIDATE_ONLY"):
        raise ValueError("Wrong release custody schema or claimed authority")
    identity = record.get("source_sha", "")
    if not isinstance(identity, str) or not re.fullmatch(r"[a-f0-9]{40}", identity):
        raise ValueError("Invalid source SHA")
    if source_sha is not None and identity != source_sha:
        raise ValueError("Source SHA mismatch")
    if (record.get("production_signature_validated") is not False
            or record.get("owner_release_approved") is not False
            or record.get("production_release_ready") is not False):
        raise ValueError("Unsigned test manifest cannot assert production release")
    kind = record.get("platform")
    if kind not in ("windows", "linux"):
        raise ValueError("Unexpected platform")
    observed = classify(artifact, kind)
    stamped = record.get("artifact")
    if not isinstance(stamped, dict):
        raise ValueError("Missing artifact identity")
    if (stamped.get("filename") != artifact.name
            or stamped.get("bytes") != artifact.stat().st_size
            or stamped.get("sha256") != digest(artifact)
            or any(stamped.get(key) != value for key, value in observed.items())):
        raise ValueError("Release binary, digest, or signature presence mismatch")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--kind", choices=("windows", "linux"))
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-sha")
    parser.add_argument("--run-id")
    args = parser.parse_args()
    try:
        if args.action == "create":
            if not args.kind or not args.source_sha or not args.run_id:
                raise ValueError("Create requires platform, source commit, GitHub run ID")
            if args.manifest.exists():
                raise FileExistsError("Release custody manifest already exists")
            report = create(args.artifact, args.kind, args.source_sha, args.run_id)
            args.manifest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                     encoding="utf-8")
        else:
            report = verify(args.manifest, args.artifact, args.source_sha)
    except (OSError, ValueError, tarfile.TarError, json.JSONDecodeError) as exc:
        print(json.dumps({"result": "NO_GO", "reason": str(exc)}))
        return 2
    print(json.dumps({"result": "PASS_CANDIDATE_CUSTODY",
                      "source_sha": report["source_sha"],
                      "sha256": report["artifact"]["sha256"],
                      "trust_status": report["artifact"]["trust_status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
