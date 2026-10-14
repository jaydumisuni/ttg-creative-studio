#!/usr/bin/env python3
"""Read-only Ptah production admission preflight for Creative Studio.

Never issues identities, enrolls Nodes, requests credentials or upgrades a
development A05 lease to Control-issued E02 authority.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PTAH = ROOT.parent / "Ptah-space"
EXPECTED_CONTROL = "ptah-control"
EXPECTED_NODE = "ptah-node"


def process_names() -> set[str]:
    result = subprocess.run(
        ["ps", "-eo", "comm="], check=True, capture_output=True, text=True, timeout=7
    )
    return {x.strip() for x in result.stdout.splitlines() if x.strip()}


def inspect() -> dict:
    ptah_git = subprocess.run(
        ["git", "-C", str(PTAH), "rev-parse", "origin/main"],
        capture_output=True, text=True, timeout=9,
    )
    source = PTAH / "services/ptah-node/src/main.rs"
    node_bin_deployable = False
    if source.exists():
        code = source.read_text(encoding="utf-8")
        node_bin_deployable = "deployment connection configuration is required" not in code
    processes = process_names()
    physical = PTAH / "conformance/e05/physical-linux-current-node-2026-09-23.json"
    physical_record = json.loads(physical.read_text()) if physical.exists() else {}
    e05_admitted = physical_record.get("e05_admission_status") == "admitted" and (
        physical_record.get("runtime_authorized") is True
    )
    control_present = EXPECTED_CONTROL in processes
    node_present = EXPECTED_NODE in processes
    # Process presence is not proof of mutual TLS session, current A02 Node identity,
    # Control-issued lease or a valid current-platform admission.
    result = {
        "schema": "ttg.creative.ptah.production_preflight.v1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "ptah_candidate_head": ptah_git.stdout.strip() if ptah_git.returncode == 0 else None,
        "ptah_node_executable_is_deployable": node_bin_deployable,
        "ptah_control_process_observed": control_present,
        "ptah_node_process_observed": node_present,
        "historical_e05_linux_observation": {
            "source_file": physical.name if physical.exists() else None,
            "recorded_status": physical_record.get("e05_admission_status"),
            "recorded_blocker": physical_record.get("e05_admission_blocker"),
            "runtime_authorized": physical_record.get("runtime_authorized"),
            "not_current_enrollment_evidence": True,
        },
        "e01_authenticated_control_node_session_proven": False,
        "e02_control_issued_reservation_lease_fence_proven": False,
        "e05_current_physical_node_admission_proven": False,
        "creative_resident_a05_proof_is_production_enrollment": False,
        "status": "BLOCKED",
        "required_proof": [
            "Current Ptah A02 approved Node identity and E01 mutual-TLS Control session",
            "Current E05 platform/role admission for the actual host",
            "Control-owned E02 Reservation, Lease and Fence bound to the exact A04 Attempt",
            "Node-side Fence verification before the resident Provider invocation",
            "Authenticated remote completion, retained Artifact receipts and restart/recovery verification",
        ],
        "limitations": [
            "Read-only host and archived-evidence survey; no authority token inspection",
            "Running process identity alone cannot satisfy E01/E02/E05",
            "The released ptah-control HTTP shell is not the E02 dispatch authority by itself",
        ],
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    result = inspect()
    if args.report:
        dest = args.report.resolve()
        assert dest.is_relative_to((ROOT / ".workspace").resolve())
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 2 if args.strict and result["status"] != "ADMITTED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
