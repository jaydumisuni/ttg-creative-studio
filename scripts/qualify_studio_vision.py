#!/usr/bin/env python3
"""Run actual local VLM evaluation (never a mocked service), with image receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ttg_visual_understanding import LocalVisionServer

CASES = (
    ("spatial", "Identify the colors and relative positions of the circle and square.",
     ("red", "blue", "left", "right")),
    ("reading", "Read the exact large letters printed on the card.",
     ("TTG",)),
    ("empty", "Are any people visible in the image? Answer YES or NO.",
     ("NO",)),
)


def make_examples(folder: Path) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    a = Image.new("RGB", (640, 400), "white")
    da = ImageDraw.Draw(a)
    da.ellipse((55, 95, 270, 310), fill="#db2032")
    da.rectangle((382, 95, 582, 310), fill="#1c57df")
    b = Image.new("RGB", (640, 400), "white")
    db = ImageDraw.Draw(b)
    font = None
    for family in ("DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        try:
            font = ImageFont.truetype(family, 190)
            break
        except OSError:
            continue
    if font is None:
        raise RuntimeError("No reliable large-font fixture available for VLM text reading")
    db.text((80, 75), "TTG", font=font, fill="black")
    c = Image.new("RGB", (640, 400), "#b0b0b0")
    out = []
    for name, image in zip(("spatial", "reading", "empty"), (a, b, c)):
        path = folder / (name + ".png")
        image.save(path)
        out.append(path)
    return out


def run(endpoint: str, model: str, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Refusing to overwrite vision acceptance evidence")
    if not output.parent.is_dir():
        raise FileNotFoundError("Create a permitted evidence directory first")
    server = LocalVisionServer(endpoint, timeout=240)
    if model not in server.installed_models():
        raise RuntimeError("No matching installed local vision-language model")
    folder = output.parent / (output.stem + "-images")
    if folder.exists():
        raise FileExistsError("Image receipt directory already exists")
    images = make_examples(folder)
    reports = []
    for (name, question, required), picture in zip(CASES, images):
        started = time.monotonic()
        reply = server.describe(picture, model, question)
        duration = round(time.monotonic() - started, 2)
        passed = all(word.lower() in reply.lower() for word in required)
        reports.append({
            "case": name, "source_sha256": hashlib.sha256(picture.read_bytes()).hexdigest(),
            "question": question, "response": reply, "expected_terms": list(required),
            "matched": passed, "duration_seconds": duration,
        })
    receipt = {
        "format": "ttg.studio.vision.acceptance.v1",
        "engine": "direct-local-multimodal",
        "model": model,
        "endpoint": endpoint,
        "real_inference": True,
        "cases": reports,
        "passed": sum(item["matched"] for item in reports),
        "total": len(reports),
        "qualification": "small synthetic acceptance set; not general visual understanding parity",
    }
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000")
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        proof = run(args.endpoint, args.model, args.output)
        print(json.dumps(proof, indent=2))
        if proof["passed"] != proof["total"]:
            raise SystemExit(2)
    except Exception as error:
        print(json.dumps({"status": "NO_GO", "reason": str(error)}))
        raise SystemExit(2)
