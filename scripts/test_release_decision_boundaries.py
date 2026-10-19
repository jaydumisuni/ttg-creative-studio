#!/usr/bin/env python3
"""Ensure AI-approved visual proof cannot be reported as owner release authority."""
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent/"build_release_decision.py"
spec = importlib.util.spec_from_file_location("ttg_release_decision_test", SCRIPT)
assert spec and spec.loader
decision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decision)


def run():
    checks = []
    with tempfile.TemporaryDirectory(prefix="studio-release-boundary-") as temp:
        root = Path(temp)
        out = root/"outputs"
        out.mkdir()
        (out/"ad_workflow").mkdir()
        (out/"ad_workflow"/"ttg_ad_contact_sheet.jpg").write_bytes(b"REAL NONEMPTY PLACEHOLDER FOR GATE TEST")
        (out/"still.jpg").write_bytes(b"reference fixture")
        (out/"ttg_reference_still_score.json").write_text(json.dumps({"passed":True}))
        (out/"reference_motion_score.json").write_text(json.dumps({"passed":True}))
        (out/"ttg_visual_proof_manifest.json").write_text(json.dumps({
            "automated_status": "passed",
            "human_approval": "approved",
            "visual_reviewer": "OpenAI GPT-5.6 Thinking visual review",
        }))
        decision.ROOT = root
        decision.OUTPUTS = out
        decision.REPORT = out/"RELEASE_DECISION.md"
        decision.REQUIRED_SOURCE = []
        decision.REQUIRED_OUTPUTS = ["still.jpg"]
        assert decision.main() == 0
        contents=(out/"RELEASE_DECISION.md").read_text()
        assert "Visual reference reviewer: OpenAI GPT-5.6" in contents
        assert "Visual reference review: PASS" in contents
        checks.append("AI visual review is correctly described as a reference review")
        assert "Human visual approval: PASS" not in contents
        assert "Owner commercial release approval: NOT VERIFIED BY THIS REPORT" in contents
        checks.append("AI reference approval cannot masquerade as human owner authorization")
        assert "Trusted signing and physical-device acceptance: NOT VERIFIED BY THIS REPORT" in contents
        checks.append("Candidate report never grants independent signing or workstation admission")
        assert "Release-candidate decision (engineering only): PASS" in contents
        checks.append("Engineering review candidate remains valid when its actual tests pass")
        (out/"ttg_visual_proof_manifest.json").write_text(json.dumps({
            "automated_status": "passed",
            "human_approval": "pending",
            "visual_reviewer": "pending",
        }))
        assert decision.main() == 1
        contents=(out/"RELEASE_DECISION.md").read_text()
        assert "Visual reference review: PENDING" in contents
        assert "Release-candidate decision (engineering only): BLOCKED" in contents
        checks.append("Review gate still fails closed when review evidence is absent")
    print(json.dumps({"result":"PASS","checks_count":len(checks),"checks":checks},indent=2))


if __name__=="__main__":
    run()
