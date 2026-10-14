#!/usr/bin/env python3
"""Bounded real Ptah + Creative Studio integration and adversarial qualification."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "integrations" / "ptah"
SCRATCH = ROOT / ".workspace" / "scratch"
SCHEMA = "ttg.creative.ptah.request.v1"


def execute(argv: list[str], *, timeout: int = 80) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def check(results: dict[str, object], label: str, passed: bool) -> None:
    results[label] = bool(passed)
    if not passed:
        raise AssertionError(f"qualification failure: {label}")


def ledger_count(path: Path) -> int:
    with sqlite3.connect(path) as conn:
        return conn.execute("SELECT COUNT(*) FROM ptah_entity_records").fetchone()[0]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, default=None)
    args = parser.parse_args()
    target = SCRATCH / "ptah-adapter-target"
    target.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(target)
    built = subprocess.run(
        ["cargo", "build", "--offline", "--manifest-path", str(INTEGRATION / "Cargo.toml")],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120,
    )
    if built.returncode:
        print(built.stderr[-3500:], file=sys.stderr)
        return 1
    binary = target / "debug" / "ttg-creative-ptah-adapter"
    proof = args.evidence_dir or SCRATCH / f"ptah-regression-{uuid.uuid4().hex[:10]}"
    proof = proof.resolve()
    if not proof.is_relative_to((ROOT / ".workspace").resolve()):
        raise ValueError("qualification must remain in Creative Studio .workspace")
    if proof.exists() and any(proof.iterdir()):
        raise ValueError("evidence directory must be empty")
    inputs = proof / "inputs"
    runs = proof / "runs"
    assets = inputs / "assets"
    assets.mkdir(parents=True)
    runs.mkdir()
    for i, background in enumerate([(36, 56, 92), (84, 40, 98), (24, 108, 123)], start=1):
        img = Image.new("RGB", (560, 820), background)
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((40, 60, 510, 700), radius=30, outline=(240, 220, 160), width=6)
        draw.ellipse((130, 170, 440, 510), fill=(180, 80 + 30 * i, 100 + 20 * i))
        img.save(assets / f"scene_{i:02}.png")
    requests = {
        "scene": {"schema": SCHEMA, "request_id": "scene_regression", "operation": "scene_edit",
                  "text": "THETECHGUY", "move_x": 108},
        "ad": {"schema": SCHEMA, "request_id": "ad_regression", "operation": "ad_from_assets",
               "asset_dir": str(assets), "title": "THETECHGUY DIGITAL SOLUTIONS"},
    }
    result: dict[str, object] = {
        "schema": "ttg.creative.ptah.qualification.v1",
        "source_head": execute(["git", "rev-parse", "HEAD"]).stdout.strip(),
        "checks": {}, "proof_dir": str(proof), "artifacts": {},
    }
    checks: dict[str, object] = result["checks"]  # type: ignore[assignment]
    desc = execute([str(binary), "--describe"])
    manifest = json.loads(desc.stdout) if desc.returncode == 0 else {}
    check(checks, "manifest_discovery", manifest.get("schema") == "ttg.creative.ptah.specialist.v1")
    for label, payload in requests.items():
        request = inputs / f"{label}.json"
        request.write_text(json.dumps(payload, indent=2) + "\n")
        run = runs / label
        command = [str(binary), "--request", str(request), "--run-dir", str(run)]
        first = execute(command, timeout=90)
        check(checks, label + "_ptah_execution", first.returncode == 0 and "PTAH_DIRECT_E2E_PASS" in first.stdout)
        proof_json = json.loads((run / "ptah_proof_manifest.json").read_text())
        check(checks, label + "_artifact_count", proof_json.get("artifact_count") == 3 and
              all(e["readback"] == "verified" for e in proof_json["artifacts"]))
        for entry in proof_json["artifacts"]:
            name, sha = entry["name"], entry["sha256"]
            original = (run / "output" / name).read_bytes()
            stored = (run / "ptah-cas" / "sha256" / sha[:2] / sha).read_bytes()
            check(checks, label + "_" + name + "_cas_readback",
                  original == stored and digest(stored) == sha)
        before = ledger_count(run / "ptah-ledger.sqlite3")
        retry = execute(command + ["--resume"])
        after = ledger_count(run / "ptah-ledger.sqlite3")
        check(checks, label + "_resume_idempotent",
              retry.returncode == 0 and "PTAH_RESUME_REUSED_VERIFIED" in retry.stdout and before == after)
        duplicate = execute(command)
        check(checks, label + "_no_implicit_retry",
              duplicate.returncode != 0 and "reconciliation" in duplicate.stderr)
        result["artifacts"][label] = {
            "workspace_id": proof_json["workspace_id"],
            "activity_id": proof_json["activity_id"],
            "artifact_ids": [a["artifact_id"] for a in proof_json["artifacts"]],
            "manifest_sha256": digest((run / "ptah_proof_manifest.json").read_bytes()),
            "ledger_records": before,
        }
    # Bad result must be rejected independently of Ptah, then by Ptah replay.
    original = runs / "scene"
    copied = runs / "scene_corrupted"
    shutil.copytree(original, copied)
    preview = copied / "output" / "preview.png"
    preview.write_bytes(preview.read_bytes() + b"tampered")
    fail = execute([str(binary), "--request", str(inputs / "scene.json"),
                    "--run-dir", str(copied), "--resume"])
    check(checks, "tampered_artifact_rejected", fail.returncode != 0 and "verification failed" in fail.stderr)
    # Input currentness after a completed ad must be independently rechecked.
    input_image = assets / "scene_01.png"
    saved = input_image.read_bytes()
    try:
        input_image.write_bytes(saved + b"changed-input")
        stale = execute([str(binary), "--request", str(inputs / "ad.json"),
                         "--run-dir", str(runs / "ad"), "--resume"])
        check(checks, "changed_source_rejected", stale.returncode != 0 and "input asset" in stale.stderr)
    finally:
        input_image.write_bytes(saved)
    check(checks, "source_restored", input_image.read_bytes() == saved)
    # Adding a fourth scene also invalidates a previously accepted folder request.
    added = assets / "scene_04.png"
    Image.new("RGB", (560, 820), (20, 30, 40)).save(added)
    try:
        inventory = execute([str(binary), "--request", str(inputs / "ad.json"),
                             "--run-dir", str(runs / "ad"), "--resume"])
        check(checks, "added_source_rejected",
              inventory.returncode != 0 and "inventory changed" in inventory.stderr)
    finally:
        added.unlink()
    # A malicious output symlink must not redirect Studio's Ptah worker writes.
    redirect = runs / "output_redirect"
    redirect.mkdir()
    hidden = runs / "output_redirect_target"
    hidden.mkdir()
    (redirect / "output").symlink_to(hidden, target_is_directory=True)
    redirected = execute([str(binary), "--request", str(inputs / "scene.json"),
                          "--run-dir", str(redirect)])
    check(checks, "output_symlink_rejected",
          redirected.returncode != 0 and "output symlink" in redirected.stderr)
    check(checks, "output_redirect_target_unmodified", not any(hidden.iterdir()))
    # Partial run receipt cannot be mistaken for success or auto-rerun.
    incomplete = runs / "incomplete"
    incomplete.mkdir()
    (incomplete / "ptah-ledger.sqlite3").write_bytes(b"incomplete")
    blocked = execute([str(binary), "--request", str(inputs / "scene.json"),
                       "--run-dir", str(incomplete)])
    check(checks, "partial_execution_blocked", blocked.returncode != 0 and "reconciliation" in blocked.stderr)
    # Direct creative-domain verifier must reject semantic mismatch.
    semantic = runs / "semantic_corruption"
    semantic.mkdir()
    for file in (runs / "scene" / "output").iterdir():
        if file.is_file():
            shutil.copy2(file, semantic / file.name)
    editable = semantic / "editable.ttgstudio.json"
    document = json.loads(editable.read_text())
    document["layers"][0]["properties"]["text"] = "WRONG LOGO"
    editable.write_text(json.dumps(document))
    rejected = execute([sys.executable, "-B", str(INTEGRATION / "verify_output.py"),
                        "--request", str(inputs / "scene.json"), "--output", str(semantic)])
    check(checks, "wrong_text_rejected", rejected.returncode != 0)
    result["passed"] = all(checks.values())
    result["checks_count"] = len(checks)
    (proof / "qualification_report.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
