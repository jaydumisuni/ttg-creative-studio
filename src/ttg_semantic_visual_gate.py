"""Optional Studio-owned semantic observation on an actual rendered PNG.

This is a visual-observer transport/evidence gate, not an image renderer,
model installation, automatic visual acceptance, or authority for source edits.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ttg_visual_understanding import LocalVisionServer

SCHEMA = "ttg.studio.visual-observer.v1"


def validate_observer(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schema", "endpoint", "model", "question"}:
        raise ValueError("Visual observer requires exactly schema, endpoint, model and question")
    if value["schema"] != SCHEMA:
        raise ValueError("Unsupported visual observer schema")
    endpoint = value["endpoint"]
    model = value["model"]
    question = value["question"]
    if not isinstance(endpoint, str):
        raise ValueError("Visual observer endpoint must be a local URL")
    # Constructs the existing SSRF-restricted loopback-only client.
    LocalVisionServer(endpoint, timeout=30)
    if (not isinstance(model, str) or not 1 <= len(model) <= 160
            or any(ord(ch) < 32 for ch in model)):
        raise ValueError("Select an explicitly named local vision model")
    if (not isinstance(question, str) or not 1 <= len(question) <= 1000
            or any(ord(ch) < 32 for ch in question)):
        raise ValueError("Visual observation question is required")
    return {"schema": SCHEMA, "endpoint": endpoint,
            "model": model, "question": question}


def observe_render(image_path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    cfg = validate_observer(spec)
    before = hashlib.sha256(image_path.read_bytes()).hexdigest()
    outcome: dict[str, Any] = {
        "schema": SCHEMA,
        "image_sha256": before,
        "model": cfg["model"],
        "endpoint": cfg["endpoint"],
        "state": "visual_observer_unavailable",
        "acceptance_authority": False,
        "auto_edits_allowed": False,
    }
    try:
        content = LocalVisionServer(cfg["endpoint"], timeout=30).describe(
            image_path, cfg["model"], cfg["question"])
    except (OSError, ValueError, TimeoutError, KeyError, TypeError) as exc:
        # Do not mistake a missing observer for a visually approved image.
        outcome["reason"] = type(exc).__name__
        return outcome
    after = hashlib.sha256(image_path.read_bytes()).hexdigest()
    if after != before:
        outcome["state"] = "visual_observer_stale_image"
        outcome["reason"] = "image_changed_during_observation"
        return outcome
    outcome["state"] = "semantic_observation_returned_unverified"
    outcome["observation"] = content
    outcome["meaning"] = "Independent image-model advisory; factual claims and changes require separate verification"
    return outcome
