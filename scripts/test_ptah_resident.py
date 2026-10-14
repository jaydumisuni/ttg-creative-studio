#!/usr/bin/env python3
"""Physical Ptah A05 PTY resident-process lifecycle qualification (non-production)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / ".workspace" / "scratch"


def probe(label: str, binary: Path, parent: Path) -> dict:
    directory = parent / label
    directory.mkdir()
    requests = []
    for index in (1, 2):
        request = directory / f"req_{index}.json"
        request.write_text(
            json.dumps(
                {
                    "schema": "ttg.creative.ptah.request.v1",
                    "request_id": f"{label}_{index}",
                    "operation": "scene_edit",
                    "text": f"THE TECHGUY RESIDENT {index}",
                    "move_x": 50 + index * 17,
                }
            )
            + "\n"
        )
        requests.append(request)
    result = subprocess.run(
        [str(binary), str(directory), *(str(path) for path in requests)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=75,
    )
    if result.returncode:
        raise RuntimeError(
            f"resident probe {label} rejected: stdout={result.stdout[-1900:]} stderr={result.stderr[-1900:]}"
        )
    assert "PTAH_RESIDENT_PROOF_PASS" in result.stdout
    assert "PTAH_RESIDENT_DUPLICATE_REJECTED" in result.stdout
    proof = json.loads((directory / "resident_proof.json").read_text())
    assert proof["status"] == "PASS"
    assert len(proof["jobs"]) == 2
    assert proof["stale_provider_generation_rejected"] is True
    assert proof["duplicate_resident_request_rejected"] is True
    assert proof["shutdown_observed"] is True
    assert proof["node_enrollment"] == "not_proven"
    assert all(p["service_alive"] and p["verified"] for p in proof["jobs"])
    for job in proof["jobs"]:
        document = directory / "resident-jobs" / job["request_id"] / "editable.ttgstudio.json"
        assert document.is_file()
        assert (document.parent / "independent_verification.json").is_file()
    return {
        "label": label,
        "status": "PASS",
        "worker_lifetime_jobs": len(proof["jobs"]),
        "fenced_lease_rejected_after_generation_change": True,
        "duplicate_request_rejected": True,
        "graceful_shutdown": True,
        "proof_sha256": hashlib.sha256((directory / "resident_proof.json").read_bytes()).hexdigest(),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, default=None)
    args = parser.parse_args()
    root = (args.evidence_dir or SCRATCH / f"ptah-resident-{uuid.uuid4().hex[:12]}").resolve()
    assert root.is_relative_to((ROOT / ".workspace").resolve())
    if root.exists() and any(root.iterdir()):
        raise ValueError("evidence directory must be empty")
    root.mkdir(parents=True, exist_ok=True)
    target = SCRATCH / "ptah-adapter-target"
    target.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(target)
    built = subprocess.run(
        ["cargo", "build", "--offline", "--locked", "--manifest-path",
         str(ROOT / "integrations/ptah/Cargo.toml"), "--bin", "resident_probe"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=110,
    )
    if built.returncode:
        raise RuntimeError("resident binary build failed: " + built.stderr[-2000:])
    binary = target / "debug" / "resident_probe"
    runs = [probe("first", binary, root), probe("restart", binary, root)]
    result = {
        "schema": "ttg.creative.ptah.resident_qualification.v1",
        "status": "PASS",
        "runs": runs,
        "total_verified_jobs": 4,
        "resident_service_lifetimes": 2,
        "admission_scope": "development A05 native provider only, not Control-issued E02 lease",
        "no_hunter": True,
    }
    (root / "qualification_report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
