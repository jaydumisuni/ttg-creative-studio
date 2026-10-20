"""Professional image production owned by the existing Studio Production Director.

One provider route for general photographic prompts. Reuses Studio's existing
Replicate image provider, pixel validation, local Visual Inspector, editable
project schema and per-request paid consent. Never simulates real inference.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
from typing import Any

from PIL import Image

from ttg_online_image_provider import (
    APPROVAL, GENERATION_PROFILES, build_generation_input, readiness,
    submit_image, image_status, download_image,
)
from ttg_project_schema import Asset, Layer, TTGProject, Transform
from ttg_visual_understanding import LocalVisionServer, measure_image, suggest_adjustments

SCHEMA = "ttg.studio.professional.production.v1"
MAX_ATTEMPTS = 3
BRAND_TERMS = re.compile(
    r"\b(?:logo|wordmark|brand|branding|signage|lettering|typography|"
    r"business card|package design|packaging|billboard|product label|"
    r"app icon|shopfront sign|storefront sign)\b", re.I
)
IMAGE_TERMS = re.compile(
    r"\b(?:photo|photograph|portrait|interior|exterior|architecture|"
    r"food|product|fabric|glass|steel|studio|cinematic|lighting|"
    r"material|reflection|realistic|photorealistic|mockup)\b", re.I
)


class ProfessionalProductionError(RuntimeError):
    pass


def choose_quality(prompt: str, requested: str = "auto") -> str:
    """Deterministic auditable choice; not a guarantee of visual quality."""
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 2000:
        raise ProfessionalProductionError("Image instruction must be 1–2000 characters")
    if requested not in ("auto", "brand_pro", "photoreal", "fast"):
        raise ProfessionalProductionError("Unsupported image quality route")
    if requested != "auto":
        return requested
    return "brand_pro" if BRAND_TERMS.search(prompt) else "photoreal"


def _safe_name(name: str) -> str:
    if not isinstance(name, str) or not 1 <= len(name) <= 52 or not re.fullmatch(r"[a-zA-Z0-9_-]+", name):
        raise ProfessionalProductionError("Job name must contain only letters, digits, _ or -")
    return name


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for piece in iter(lambda: file.read(1024*1024), b""):
            h.update(piece)
    return h.hexdigest()


class ProfessionalImagePipeline:
    """No separate model engine: orchestrates existing Image Lab provider."""

    def __init__(self, output_root: Path):
        self.root = Path(output_root).expanduser().resolve(strict=True)
        if not self.root.is_dir():
            raise ProfessionalProductionError("Approved output root must be an existing directory")

    def _files(self, name: str) -> dict[str, Path]:
        name = _safe_name(name)
        return {
            "ticket": self.root/(name+".prediction.json"),
            "image": self.root/(name+".png"),
            "project": self.root/(name+".ttgstudio.json"),
            "receipt": self.root/(name+".production.json"),
        }

    def plan(self, prompt: str, *, quality: str = "auto",
             reference_image: str | None = None,
             aspect_ratio: str = "4:3") -> dict[str, Any]:
        selected = choose_quality(prompt, quality)
        options = {
            "prompt": prompt.strip(), "quality": selected,
            "aspect_ratio": aspect_ratio,
        }
        if reference_image:
            options["reference_image"] = reference_image
        # Reuse the provider's exact input schema without triggering inference.
        model, payload = build_generation_input(options)
        return {
            "schema": SCHEMA, "state": "planned_not_generated",
            "production_owner": "TTG Creative Studio",
            "requested_prompt": prompt.strip(), "quality": selected,
            "provider": "replicate", "model": model,
            "input_fields": sorted(payload),
            "reference_supplied": bool(reference_image),
            "has_semantic_visual_proof": False,
            "actual_neural_pixels_produced": False,
            "provider_readiness": readiness()["state"],
            "expected_cost": "provider_usage_billed_not_guaranteed",
            "approval_required": APPROVAL,
            "next": "Submit only with per-job consent and provider billing admission",
        }

    def submit(self, *, name: str, prompt: str, quality: str = "auto",
               reference_image: str | None = None, aspect_ratio: str = "4:3",
               paid_approval: str = "", previous_ticket: str | None = None) -> dict[str, Any]:
        paths = self._files(name)
        if any(x.exists() or x.is_symlink() for x in paths.values()):
            raise ProfessionalProductionError("Output or ticket exists; refusing overwrite")
        plan = self.plan(prompt, quality=quality, reference_image=reference_image,
                         aspect_ratio=aspect_ratio)
        if paid_approval != APPROVAL:
            raise ProfessionalProductionError("One explicit paid approval is required for each submission")
        attempt = 1
        if previous_ticket is not None:
            previous_name = _safe_name(previous_ticket)
            if previous_name == name:
                raise ProfessionalProductionError("A revision needs a new output name")
            prior = self._load_ticket(previous_name)
            attempt = int(prior["attempt"]) + 1
            if attempt > MAX_ATTEMPTS:
                raise ProfessionalProductionError("Correction retry budget exhausted (3 submissions)")
            completed_receipt = self._files(previous_name)["receipt"]
            if completed_receipt.exists():
                verified = json.loads(completed_receipt.read_text(encoding="utf-8"))
                if verified.get("state") != "visual_review_required":
                    raise ProfessionalProductionError("Prior image has no completed visual review")
            else:
                # Refuse repeated billable attempts while an earlier prediction
                # is still running. Failure is obtained from the actual provider.
                latest = image_status(prior["prediction_id"])
                if latest["status"] not in ("failed", "canceled"):
                    raise ProfessionalProductionError(
                        "Previous provider attempt still active or unreviewed"
                    )
        options = {
            "operation": "generate", "prompt": prompt.strip(),
            "quality": plan["quality"], "aspect_ratio": aspect_ratio,
            "paid_approval": paid_approval,
        }
        if reference_image:
            options["reference_image"] = reference_image
        # Actual provider call: absent credentials / operator admission fail
        # BEFORE any generated-image success or completion is asserted.
        reply = submit_image(options)
        ticket = {
            "schema": SCHEMA, "state": "submitted", "attempt": attempt,
            "model": reply["model"], "provider": reply["provider"],
            "prediction_id": reply["prediction_id"],
            "prompt": plan["requested_prompt"], "quality": plan["quality"],
            "reference_supplied": plan["reference_supplied"],
            "expected_output": str(paths["image"]),
            "previous_ticket": previous_ticket,
            "remote_status": reply["status"],
            "billable_submission": True,
            "real_output_verified": False,
        }
        if attempt > MAX_ATTEMPTS:
            raise AssertionError("Retry limit violated")
        self._atomic_json(paths["ticket"], ticket)
        return {"state":"submitted", "ticket":str(paths["ticket"]),
                "prediction_id":ticket["prediction_id"], "model":ticket["model"],
                "attempt":attempt, "actual_neural_pixels_produced":False}

    def _load_ticket(self, ticket_name: str) -> dict:
        name = _safe_name(ticket_name)
        p = self._files(name)["ticket"]
        if p.is_symlink() or not p.is_file():
            raise ProfessionalProductionError("Verified local prediction ticket missing")
        record = json.loads(p.read_text(encoding="utf-8"))
        if record.get("schema") != SCHEMA or record.get("provider") != "replicate":
            raise ProfessionalProductionError("Unrecognized production ticket")
        if not isinstance(record.get("prediction_id"), str) or not record.get("model"):
            raise ProfessionalProductionError("Incomplete provider evidence")
        if record.get("expected_output") != str(self._files(name)["image"]):
            raise ProfessionalProductionError("Production destination differs from ticket")
        return record

    def inspect(self, ticket_name: str) -> dict:
        ticket = self._load_ticket(ticket_name)
        current = image_status(ticket["prediction_id"])
        return {
            "schema": SCHEMA, "provider": ticket["provider"],
            "model_claim_source": "original provider submission receipt",
            "model": ticket["model"], "prediction_id": ticket["prediction_id"],
            "remote_status": current["status"],
            "real_output_verified": False,
            "state": "ready_for_download" if current["status"] == "succeeded"
                     else "provider_failed" if current["status"] in ("failed","canceled")
                     else "provider_processing",
        }

    @staticmethod
    def _atomic_json(path: Path, obj: dict) -> None:
        import tempfile
        import os
        fd, staged = tempfile.mkstemp(prefix=".studio-production-", suffix=".json.tmp",
                                      dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(obj, handle, indent=2, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            if path.exists():
                raise ProfessionalProductionError("Destination already exists")
            os.link(staged, path)
        finally:
            Path(staged).unlink(missing_ok=True)

    def complete(self, *, ticket_name: str, vision_model: str | None = None,
                 question: str = "", visual_approval: bool = False) -> dict:
        paths = self._files(ticket_name)
        ticket = self._load_ticket(ticket_name)
        if ticket["state"] != "submitted":
            raise ProfessionalProductionError("Ticket is not a pending generation")
        if any(x.exists() or x.is_symlink() for x in (paths["image"], paths["project"], paths["receipt"])):
            raise ProfessionalProductionError("Existing final artifact; refusing overwrite")
        observed = image_status(ticket["prediction_id"])
        if observed["status"] != "succeeded":
            raise ProfessionalProductionError("Provider output not succeeded: "+observed["status"])
        # Existing verified download validates pixel dimensions/format and SHA256.
        downloaded = download_image(ticket["prediction_id"], paths["image"])
        if downloaded["sha256"] != _sha256(paths["image"]):
            raise ProfessionalProductionError("Downloaded image checksum differs")
        metrics = measure_image(paths["image"])
        semantic = {
            "state": "unverified_without_local_vision",
            "description": None, "visual_review_required": True,
        }
        if vision_model:
            if not isinstance(vision_model, str) or len(vision_model)>160:
                raise ProfessionalProductionError("Invalid local vision model")
            # No remote URL option: only pre-existing default loopback endpoint.
            text = LocalVisionServer().describe(
                paths["image"], vision_model,
                (question or "Describe the visible objects, typography, anatomy, lighting and defects. Report uncertainty.")[:700]
            )
            semantic = {"state": "model_observations_review_required",
                        "model": vision_model, "description": text,
                        "visual_review_required": True}
        # Generated pixels form ONE editable transformable image layer.
        # The model's pixels are not misrepresented as separately editable objects.
        project = TTGProject(name="Professional image: "+ticket_name, project_type="image")
        project.canvas.width = downloaded["width"]
        project.canvas.height = downloaded["height"]
        project.assets = [Asset(
            id="generated_original",kind="image",name="Verified provider image",
            path=paths["image"].name,sha256=downloaded["sha256"],required=True,
        )]
        project.layers = [Layer(
            id="generated_raster", type="image", name="Verified AI-generated photograph",
            properties={"path":paths["image"].name,
                        "source_model":ticket["model"],
                        "source_prediction_id":ticket["prediction_id"]},
            transform=Transform(x=0,y=0),
        )]
        project.save(paths["project"])
        receipt = {
            "schema": SCHEMA,
            "state": "visual_review_required",
            "accepted": False,
            "visual_approval_requested": bool(visual_approval),
            "actual_neural_pixels_produced": True,
            "model_identity_evidence": "recorded from provider submission, not independently attested by model",
            "model": ticket["model"], "provider": "replicate",
            "prediction_id": ticket["prediction_id"],
            "prompt": ticket["prompt"], "attempt": ticket["attempt"],
            "image": str(paths["image"]), "project": str(paths["project"]),
            "sha256": downloaded["sha256"], "dimensions": [downloaded["width"],downloaded["height"]],
            "pixel_measurements": metrics,
            "nonsemantic_suggestions": suggest_adjustments(metrics),
            "semantic_inspection": semantic,
            "visual_review_required": True,
            "editable_scope": "raster layer, transforms, overlays; individual inferred objects not editable",
            "revision_policy": "Separate approved paid submission, maximum three total attempts",
        }
        self._atomic_json(paths["receipt"], receipt)
        return receipt
