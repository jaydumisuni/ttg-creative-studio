#!/usr/bin/env python3
"""Prove real local ComfyUI checkpoint and image generation; never use mock receipts.

Readiness-only mode exits 2 when the service/installed model is absent.
An opt-in --infer operation requires a local checkpoint file and saves an
independently inspectable PNG, digest and timing receipt. No auto-downloads.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ttg_image_lab import ComfyUIBackend

EXPECTED_PUBLIC_CHECKPOINT = {
    "v1-5-pruned-emaonly.safetensors":
        "6ce0161689b3853acaa03779ec93eafe75a02f4ced659bee03f50797806fa2fa"
}


def file_digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def qualify(*, url: str, checkpoint_directory: Path,
            name: str | None, output: Path | None,
            prompt: str, verify_public_digest: bool = False) -> dict:
    if not checkpoint_directory.is_dir():
        raise RuntimeError("No local ComfyUI checkpoint directory is installed")
    backend = ComfyUIBackend(url, timeout_seconds=300)
    installed = backend.available_models()
    if not isinstance(installed, list) or not installed:
        raise RuntimeError("ComfyUI reported no installed checkpoints")
    names = [s for s in installed if isinstance(s, str) and s.strip()]
    if not names:
        raise RuntimeError("ComfyUI model list is empty")
    receipt: dict = {
        "schema": "ttg.creative.studio.local-inference-proof.v1",
        "status": "READY_FOR_REAL_INFERENCE",
        "model_count": len(names),
        "model_names": names,
        "endpoint": url,
        "host": socket.gethostname(),
    }
    if output is None:
        return receipt
    if name is None or name not in names:
        raise RuntimeError("Requested checkpoint is not advertised as installed by ComfyUI")
    if Path(name).name != name or name in (".", ".."):
        raise ValueError("Only one checkpoint filename is supported")
    source = checkpoint_directory / name
    if source.is_symlink() or not source.is_file():
        raise RuntimeError("No local checkpoint file for requested model")
    if source.stat().st_size < 100_000_000:
        raise RuntimeError("Checkpoint file is too small; refuse to claim real-model proof")
    if source.suffix.lower() not in (".safetensors", ".ckpt"):
        raise RuntimeError("Unsupported checkpoint file extension")
    if output.exists():
        raise FileExistsError("Refusing to replace an existing inference proof")
    if not output.parent.exists():
        raise FileNotFoundError("Create the intended authorized proof directory first")
    receipt["model"] = name
    receipt["checkpoint_file_bytes"] = source.stat().st_size
    if verify_public_digest:
        expected = EXPECTED_PUBLIC_CHECKPOINT.get(name)
        if not expected:
            raise RuntimeError("No pinned public SHA-256 for this checkpoint filename")
        actual = file_digest(source)
        if actual != expected:
            raise RuntimeError("Checkpoint SHA-256 does not match the published official model")
        receipt["checkpoint_sha256"] = actual
    start = time.monotonic()
    image = backend.generate(
        prompt=prompt, checkpoint=name, width=512, height=512,
        steps=20, seed=246810,
    )
    if image.size != (512, 512):
        raise RuntimeError("Generated image dimensions did not match the requested canvas")
    from PIL import Image
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    result = buffer.getvalue()
    if len(result) < 10_000:
        raise RuntimeError("Generated image is unexpectedly small")
    with Image.open(io.BytesIO(result)) as check:
        check.verify()
    output.write_bytes(result)
    receipt.update({
        "status": "REAL_IMAGE_GENERATED",
        "image_path": str(output),
        "image_sha256": hashlib.sha256(result).hexdigest(),
        "image_bytes": len(result),
        "dimensions": [512, 512],
        "elapsed_seconds": round(time.monotonic() - start, 2),
    })
    manifest = output.with_suffix(".proof.json")
    if manifest.exists():
        output.unlink(missing_ok=True)
        raise FileExistsError("Proof receipt already exists, refusing replacement")
    manifest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8188")
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--checkpoint")
    parser.add_argument("--infer", type=Path)
    parser.add_argument("--prompt", default="A single blue ceramic vase on a wooden table, professional soft studio photography")
    parser.add_argument("--verify-public-digest", action="store_true")
    args = parser.parse_args()
    try:
        result = qualify(
            url=args.url, checkpoint_directory=args.checkpoint_dir,
            name=args.checkpoint, output=args.infer, prompt=args.prompt,
            verify_public_digest=args.verify_public_digest,
        )
    except Exception as exc:
        print(json.dumps({"status": "NO_GO", "reason": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
