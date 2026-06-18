#!/usr/bin/env python3
"""Build a small HTML index for the visual proof artifact package."""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
INDEX = OUT / "index.html"


def load_json(name: str) -> dict:
    path = OUT / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def file_card(name: str, label: str) -> str:
    path = OUT / name
    if not path.exists():
        return f"<li><strong>{html.escape(label)}</strong>: missing</li>"
    return f"<li><a href='{html.escape(name)}'>{html.escape(label)}</a> <small>({path.stat().st_size:,} bytes)</small></li>"


def main() -> int:
    still = load_json("ttg_reference_still_score.json")
    motion = load_json("reference_motion_score.json")
    manifest = load_json("ttg_visual_proof_manifest.json")
    body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>TTG Visual Proof Review</title>
<style>
body {{ margin:0; background:#050814; color:#eaf3ff; font-family:Segoe UI,Arial,sans-serif; }}
main {{ max-width:1100px; margin:0 auto; padding:28px; }}
.card {{ background:#0b1220; border:1px solid #1d3f80; border-radius:16px; padding:18px; margin:18px 0; box-shadow:0 0 24px #001b44; }}
h1,h2 {{ color:#9fd8ff; }}
a {{ color:#00e5ff; }}
img {{ max-width:100%; border-radius:14px; border:1px solid #18305f; }}
.badge {{ display:inline-block; padding:6px 10px; border-radius:999px; background:#16224d; border:1px solid #3f72ff; }}
.warning {{ color:#ffcf70; }}
</style>
</head>
<body>
<main>
<h1>TTG Creative Studio Visual Proof</h1>
<p class="badge">Human review required before video proof or release work.</p>
<div class="card">
<h2>Gate status</h2>
<ul>
<li>Automated status: {html.escape(str(manifest.get('automated_status', 'unknown')))}</li>
<li>Human approval: {html.escape(str(manifest.get('human_approval', 'pending')))}</li>
<li>Video export: {html.escape(str(manifest.get('video_export', 'blocked')))}</li>
<li>Release packaging: {html.escape(str(manifest.get('release_packaging', 'blocked')))}</li>
</ul>
</div>
<div class="card">
<h2>Scores</h2>
<ul>
<li>Still passed guardrails: {html.escape(str(still.get('passed', 'unknown')))}</li>
<li>Still contrast: {html.escape(str(still.get('contrast', 'n/a')))}</li>
<li>Still neon ratio: {html.escape(str(still.get('neon_ratio', 'n/a')))}</li>
<li>Motion passed guardrails: {html.escape(str(motion.get('passed', 'unknown')))}</li>
<li>Motion score: {html.escape(str(motion.get('motion_score', 'n/a')))}</li>
</ul>
</div>
<div class="card">
<h2>Review files</h2>
<ul>
{file_card('VISUAL_PROOF_REVIEW.md', 'Readable markdown review')}
{file_card('ttg_reference_still.jpg', 'Reference still')}
{file_card('reference_motion_contact_sheet.jpg', 'Motion contact sheet')}
{file_card('reference_motion_preview.gif', 'Animated GIF preview')}
{file_card('ttg_visual_proof_manifest.json', 'Proof manifest')}
{file_card('FAILURE_REPORT.md', 'Failure report if workflow crashed')}
</ul>
</div>
<div class="card">
<h2>Still preview</h2>
<img src="ttg_reference_still.jpg" alt="TTG reference still">
</div>
<div class="card">
<h2>Motion contact sheet</h2>
<img src="reference_motion_contact_sheet.jpg" alt="TTG motion contact sheet">
</div>
<p class="warning">If this does not look premium enough, improve the renderer/template first. Do not move to release packaging.</p>
</main>
</body>
</html>
"""
    OUT.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(body, encoding="utf-8")
    print(f"Saved artifact index: {INDEX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
