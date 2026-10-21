"""Studio-owned evidence checks for an assistant's *declared* creative brief.

Does not infer what the user meant from pixels or replace visual-model review.
Validates trusted requirements against actual editable project and rendered pixels.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from PIL import Image, ImageChops
from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_project_schema import TTGProject

SCHEMA = "ttg.studio.creative-acceptance.v1"

class AcceptanceError(ValueError):
    pass

def validate_acceptance(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise AcceptanceError("Creative acceptance schema is required")
    if set(value) - {"schema", "text", "materials"}:
        raise AcceptanceError("Unapproved creative acceptance requirement")
    checks: dict[str, Any] = {"schema": SCHEMA}
    for key, allowed in (("text", {"layer_id", "value"}), ("materials", {"layer_id", "value"})):
        items = value.get(key, [])
        if not isinstance(items, list) or len(items) > 20:
            raise AcceptanceError("Acceptance requires no more than 20 checks per category")
        rows = []
        seen = set()
        for row in items:
            if not isinstance(row, dict) or set(row) != allowed:
                raise AcceptanceError("Acceptance item must have layer_id and value only")
            layer_id, expected = row["layer_id"], row["value"]
            if not isinstance(layer_id, str) or not layer_id.isascii() or not (1 <= len(layer_id) <= 60) or not all(c.isalnum() or c in "-_" for c in layer_id):
                raise AcceptanceError("Invalid expected layer identifier")
            if not isinstance(expected, str) or not (1 <= len(expected) <= (70 if key == "materials" else 110)) or any(ord(c) < 32 for c in expected):
                raise AcceptanceError("Invalid expected content")
            if layer_id in seen:
                raise AcceptanceError("Duplicate acceptance target")
            seen.add(layer_id)
            rows.append({"layer_id": layer_id, "value": expected})
        checks[key] = rows
    if not checks["text"] and not checks["materials"]:
        raise AcceptanceError("Empty acceptance checks cannot certify a creative request")
    return checks

def apply_expected_text(project: TTGProject, spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Only when the caller explicitly requests source-backed spelling repair."""
    checks = validate_acceptance(spec)
    layers = {l.id: l for l in project.layers}
    edits: list[dict[str, Any]] = []
    for item in checks["text"]:
        layer = layers.get(item["layer_id"])
        if layer is None or layer.type not in ("text", "text3d") or layer.locked or not layer.visible:
            raise AcceptanceError("Cannot repair missing, locked, hidden or non-text layer")
        current = layer.properties.get("text")
        if current != item["value"]:
            edits.append({"layer_id": layer.id, "op": "replace_text",
                          "from": current, "to": item["value"],
                          "source": "explicit acceptance requirement"})
    # Validate all changes before making any; no partial edits.
    for item in edits:
        layers[item["layer_id"]].properties["text"] = item["to"]
    return edits

def inspect_acceptance(project: TTGProject, project_root: Path, image: Path,
                       spec: dict[str, Any]) -> dict[str, Any]:
    """Project contract + actual native Studio pixel visibility, not OCR or aesthetics."""
    checks = validate_acceptance(spec)
    with Image.open(image) as im:
        observed = im.convert("RGB")
    renderer = CanvasRenderer(RenderContext(project_root))
    layers = {l.id: l for l in project.layers}
    findings = []
    tested = []
    for kind in ("text", "materials"):
        for check in checks[kind]:
            layer = layers.get(check["layer_id"])
            if layer is None or not layer.visible:
                findings.append({"layer_id": check["layer_id"], "kind": kind, "reason": "required_layer_missing_or_hidden"})
                continue
            if kind == "text":
                actual = layer.properties.get("text") if layer.type in ("text", "text3d") else None
            else:
                actual = layer.properties.get("cinematic_material")
            if actual != check["value"]:
                findings.append({"layer_id": layer.id, "kind": kind,
                                 "reason": "declared_element_mismatch", "expected": check["value"], "observed": actual})
                continue
            layer.visible = False
            try:
                no_layer = renderer.render(project).convert("RGB")
            finally:
                layer.visible = True
            box = ImageChops.difference(observed, no_layer).getbbox()
            if box is None:
                findings.append({"layer_id": layer.id, "kind": kind, "reason": "no_visible_pixel_contribution"})
            else:
                tested.append({"layer_id": layer.id, "kind": kind, "pixel_contribution_bbox": list(box)})
    return {"state": "pass" if not findings else "correction_required",
            "checks": sum(len(checks[k]) for k in ("text", "materials")),
            "visible_checks": len(tested), "findings": findings, "visible_evidence": tested,
            "verification": "exact_source_contract_and_native_pixel_differential",
            "independent_semantic_review": "not_performed",
            "photorealism_certification": False}
