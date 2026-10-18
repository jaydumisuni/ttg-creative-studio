"""Opt-in cloud AI images for standalone Creative Studio; no local weights.

Uses the existing protected Replicate transport from online-video integration.
Never submits paid work without operator admission AND request consent.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.request

from PIL import Image

from ttg_online_video_provider import (
    NoRedirect, VideoProviderError, _json_request, _output_url, _token,
    PREDICTION, ACCEPTED_STATES, FINAL_STATES, validate_public_https,
)
from ttg_creative_studio.engine.image_jobs import CreativeJobError, JobResult

IMAGE_MODELS = {
    "generate": "black-forest-labs/flux-schnell",
    "edit": "black-forest-labs/flux-kontext-pro",
}
APPROVAL = "APPROVE_PAID_IMAGE_GENERATION"
MAX_IMAGE_BYTES = 24 * 1024 * 1024
MAX_PIXELS = 16_000_000
IMAGE_TASKS = frozenset({
    "image_generate_online", "image_generation_status",
    "image_generation_download", "image_generation_cancel"
})


def state() -> dict:
    token = bool(os.environ.get("REPLICATE_API_TOKEN", "").strip())
    enabled = os.environ.get("TTG_STUDIO_ENABLE_PAID_IMAGE", "") == "1"
    return {
        "provider": "replicate",
        "online": "configured" if token and enabled else
                  "billing_disabled" if token else "credentials_required",
        "models": IMAGE_MODELS,
        "local": "optional_ComfyUI_not_required_on_KRATOS",
        "operator_approval_required": True,
        "per_request_approval_required": True,
        "weights_downloaded_by_studio": False,
    }


def _id(value: object) -> str:
    if not isinstance(value, str) or not PREDICTION.fullmatch(value):
        raise CreativeJobError("Invalid image prediction ID")
    return value


def _result(response: dict) -> dict:
    ident = _id(response.get("id"))
    progress = response.get("status")
    if progress not in ACCEPTED_STATES:
        raise CreativeJobError("Image provider returned unsupported status")
    url = None
    if progress == "succeeded":
        outputs = response.get("output")
        if isinstance(outputs, list) and len(outputs) == 1:
            outputs = outputs[0]
        url = _output_url(outputs)
    return {"provider": "replicate", "prediction_id": ident, "status": progress,
            "done": progress in FINAL_STATES, "output_url": url,
            "local_model_downloaded": False,
            "provider_page": "https://replicate.com/p/" + ident}


def submit(options: dict) -> dict:
    if not isinstance(options, dict):
        raise CreativeJobError("Image options must be a dictionary")
    if options.get("paid_approval") != APPROVAL:
        raise CreativeJobError("Paid image generation requires explicit approval for this request")
    if options.get("mode", "online") != "online":
        raise CreativeJobError("Local ComfyUI generation requires an installed checkpoint on qualified hardware")
    variant = options.get("model", "generate")
    if variant not in IMAGE_MODELS:
        raise CreativeJobError("Unsupported image model; select generate or edit")
    prompt = options.get("prompt")
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 2200:
        raise CreativeJobError("A prompt of 1–2200 characters is required")
    ratio = options.get("aspect_ratio", "1:1")
    if ratio not in ("1:1", "16:9", "9:16", "4:3", "3:4", "2:3", "3:2", "match_input_image"):
        raise CreativeJobError("Unsupported aspect ratio")
    image_url = options.get("input_image", "")
    if variant == "edit" and not image_url:
        raise CreativeJobError("Cloud image editing needs an explicitly supplied public HTTPS source image URL")
    if variant == "generate" and image_url:
        raise CreativeJobError("Use image edit mode when an input image is supplied")
    if variant == "generate":
        if ratio == "match_input_image":
            raise CreativeJobError("Cannot match an input image in text-only generation")
        model_input = {"prompt": prompt.strip(), "num_outputs": 1,
                       "aspect_ratio": ratio, "output_format": "png",
                       "num_inference_steps": 4}
    else:
        validated = validate_public_https(image_url)
        model_input = {"prompt": prompt.strip(), "input_image": validated,
                       "aspect_ratio": ratio, "output_format": "png"}
    _token()
    if os.environ.get("TTG_STUDIO_ENABLE_PAID_IMAGE", "") != "1":
        raise CreativeJobError("Paid image inference disabled by operator; set TTG_STUDIO_ENABLE_PAID_IMAGE=1 after authorization")
    outcome = _json_request("POST", "/v1/models/" + IMAGE_MODELS[variant] +
                            "/predictions", {"input": model_input})
    record = _result(outcome)
    record["model"] = IMAGE_MODELS[variant]
    record["billing"] = "external_paid_provider_prediction_submitted"
    return record


def status(prediction_id: str) -> dict:
    return _result(_json_request("GET", "/v1/predictions/" + _id(prediction_id)))


def cancel(prediction_id: str) -> dict:
    return _result(_json_request("POST", "/v1/predictions/" + _id(prediction_id) + "/cancel"))


def download(prediction_id: str, destination: str | Path) -> dict:
    report = status(prediction_id)
    if report["status"] != "succeeded":
        raise CreativeJobError("Image prediction is not yet complete")
    url = _output_url(report["output_url"])
    candidate = Path(destination).expanduser()
    if candidate.is_symlink() or candidate.suffix.lower() != ".png":
        raise CreativeJobError("Cloud image output must be a new PNG file, not a symlink")
    target = candidate.resolve()
    if not target.parent.is_dir() or target.exists():
        raise CreativeJobError("Create an approved output directory and select an unused PNG path")
    request = urllib.request.Request(
        url, headers={"Accept": "image/png", "User-Agent": "TTG-Creative-Studio/1.0"}
    )
    temporary = None
    total = 0
    digest = hashlib.sha256()
    try:
        try:
            remote = urllib.request.build_opener(NoRedirect).open(request, timeout=50)
        except urllib.error.HTTPError as exc:
            raise CreativeJobError("Image delivery failed with HTTP " + str(exc.code)) from None
        with remote:
            fd, temporary = tempfile.mkstemp(prefix=".ttg-online-image-", dir=target.parent)
            with os.fdopen(fd, "wb") as handle:
                first = b""
                while True:
                    chunk = remote.read(1024*1024)
                    if not chunk:
                        break
                    if total == 0:
                        first = chunk[:8]
                    total += len(chunk)
                    if total > MAX_IMAGE_BYTES:
                        raise CreativeJobError("Image exceeds 24 MiB download limit")
                    handle.write(chunk)
                    digest.update(chunk)
                if total < 100 or first != b"\x89PNG\r\n\x1a\n":
                    raise CreativeJobError("Image provider did not return a PNG")
                handle.flush()
                os.fsync(handle.fileno())
        with Image.open(temporary) as image:
            width, height = image.size
            if not (1 <= width * height <= MAX_PIXELS):
                raise CreativeJobError("Image resolution exceeds 16 megapixels")
            image.verify()
        os.link(temporary, target)
        return {"provider": "replicate", "prediction_id": prediction_id,
                "path": str(target), "width": width, "height": height,
                "bytes": total, "sha256": digest.hexdigest(),
                "status": "downloaded_verified_png"}
    except FileExistsError:
        raise CreativeJobError("Image destination created concurrently; refusing overwrite") from None
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)


def run_image_cloud_job(job: dict) -> dict:
    if not isinstance(job, dict):
        raise CreativeJobError("Image job must be an object")
    task = job.get("task")
    if task not in IMAGE_TASKS:
        raise CreativeJobError("Unsupported online image operation")
    options = job.get("options") or {}
    if not isinstance(options, dict):
        raise CreativeJobError("Image cloud options must be an object")
    job_id = str(job.get("jobId") or job.get("job_id") or "image_cloud_job")
    if len(job_id) > 120:
        raise CreativeJobError("Image job ID too long")
    if task == "image_generate_online":
        result = submit(options)
        path = ""
        status_name = "submitted"
    elif task == "image_generation_status":
        result = status(options.get("prediction_id"))
        path = ""
        status_name = result["status"]
    elif task == "image_generation_cancel":
        if options.get("cancel_approval") != "CANCEL_THIS_PREDICTION":
            raise CreativeJobError("Image cancellation requires explicit approval")
        result = cancel(options.get("prediction_id"))
        path = ""
        status_name = result["status"]
    else:
        requested = job.get("output") or job.get("outputPath")
        if not isinstance(requested, str):
            raise CreativeJobError("Image download output path required")
        result = download(options.get("prediction_id"), requested)
        path = result["path"]
        status_name = "downloaded"
    return JobResult(True, job_id, task, "", path, status_name,
                     "Creative Studio cloud image provider returned actual job evidence",
                     result).to_dict()
