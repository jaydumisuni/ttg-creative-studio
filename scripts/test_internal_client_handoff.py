#!/usr/bin/env python3
"""Studio-only client handoff acceptance: no Hunter, secrets, paid calls or weights.

Proves the existing versioned JSON contract is sufficient for a later authorized
agent client while keeping production releases independently blocked.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "src" / "ttg_creative_studio" / "cli.py"
CHECKS: list[str] = []


def verify(condition: bool, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def runner(args: list[str]):
    # Never inherit credentials that could make a fixture unexpectedly billable.
    env = os.environ.copy()
    for name in ("REPLICATE_API_TOKEN", "TTG_STUDIO_ENABLE_PAID_VIDEO",
                 "TTG_STUDIO_ENABLE_PAID_IMAGE", "OPENAI_API_KEY"):
        env.pop(name, None)
    return subprocess.run([sys.executable, "-B", str(CLI), *args],
                          cwd=ROOT, env=env, capture_output=True, text=True,
                          timeout=30, check=False)


def dispatch(directory: Path, suffix: str, task: dict) -> tuple[int, dict]:
    job = directory / (suffix + ".job.json")
    receipt = directory / (suffix + ".result.json")
    job.write_text(json.dumps(task), encoding="utf-8")
    proc = runner(["--job", str(job), "--result", str(receipt)])
    verify(receipt.is_file(), "Machine-readable result written: " + suffix)
    return proc.returncode, json.loads(receipt.read_text(encoding="utf-8"))


def main():
    discovery = runner(["--catalog"])
    verify(discovery.returncode == 0, "Standalone CLI advertises its shared catalog")
    contract = json.loads(discovery.stdout)
    tasks = contract["operations"]
    for name in ("video_capabilities", "video_plan", "video_render", "video_generate",
                 "image_generate_online", "image_status_online"):
        verify(name in tasks, "Catalog contains independently callable " + name)
    verify(tasks["video_local_install"]["state"] == "future_GT502_Spark",
           "FreeVideo model download is deferred")
    with tempfile.TemporaryDirectory(prefix="studio-internal-handoff-") as temp:
        folder = Path(temp)
        image = folder / "source.png"
        Image.new("RGB", (40, 30), (24, 91, 180)).save(image)
        rc, result = dispatch(folder, "image-info",
                              {"task": "image_info", "input": str(image),
                               "output": str(folder / "image-info.json")})
        verify(rc == 0 and result["ok"] and result["meta"]["width"] == 40,
               "Native image understanding runs with no AI assistant")
        rc, result = dispatch(folder, "image-resize",
                              {"task": "resize_image", "input": str(image),
                               "output": str(folder / "resized.png"),
                               "options": {"width": 20, "height": 15}})
        with Image.open(folder / "resized.png") as output:
            verify(rc == 0 and result["ok"] and output.size == (20, 15),
                   "Editable image processing produces actual output")
        rc, result = dispatch(folder, "video-capabilities",
                              {"task": "video_capabilities"})
        verify(rc == 0 and result["ok"] and
               "local_video_generation" in result["meta"] and
               result["meta"]["generation"]["offline"]["model_files_installed_by_studio"] is False,
               "Video generation availability is reported without weight installation")
        rc, result = dispatch(folder, "video-storyboard",
                              {"task": "video_plan", "output": str(folder/"storyboard.json"),
                               "options": {"scenes": [
                                   {"description": "Show the product", "seconds": 1.5},
                                   {"description": "Show a detail", "seconds": 1.0}
                               ]}})
        plan = json.loads((folder / "storyboard.json").read_text())
        verify(rc == 0 and result["ok"] and plan["status"] == "review_required" and
               all(s["status"] == "planned_not_generated" for s in plan["scenes"]),
               "Real timeline planning does not masquerade as generated video")
        rc, result = dispatch(folder, "video-deny",
                              {"task": "video_generate", "options": {
                                  "prompt": "A cinematic scene", "duration": 5}})
        verify(rc != 0 and result["ok"] is False and
               "explicit approval" in result["error"].lower(),
               "Cloud video cannot be charged without explicit consent")
        rc, result = dispatch(folder, "image-deny",
                              {"task": "image_generate_online",
                               "options": {"prompt": "An advertisement"}})
        verify(rc != 0 and result["ok"] is False,
               "Cloud image cannot be charged without explicit consent")
        verify(not any(folder.glob("*.safetensors")) and
               not any(folder.glob("*.ckpt")),
               "No model weights created during handoff proof")

    print(json.dumps({
        "status": "INTERNAL_CLIENT_CONTRACT_READY_NOT_HUNTER_CONNECTED",
        "checks": len(CHECKS), "names": CHECKS,
        "production_release": "NOT_AUTHORIZED",
        "external_inference": "NOT_QUALIFIED",
    }, indent=2))


if __name__ == "__main__":
    main()
