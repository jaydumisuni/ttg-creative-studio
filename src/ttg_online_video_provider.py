"""Online-first generative video provider for standalone TTG Creative Studio.

Zero local diffusion weights. Paid submission is NEVER implicit. Future local
inference stays unadmitted until GT502/Spark qualification. Credentials live
only in the user's environment (not in projects, job files, or receipts).
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API_BASE = "https://api.replicate.com/v1"
MODELS = {
    "fast": "bytedance/seedance-1-pro-fast",
    "quality": "bytedance/seedance-1-pro",
}
OUTPUT_HOSTS = ("replicate.delivery", "replicateusercontent.com")
MAX_DOWNLOAD = 125 * 1024 * 1024
APPROVAL = "APPROVE_PAID_VIDEO_GENERATION"
PREDICTION = re.compile(r"^[a-zA-Z0-9]{8,90}$")
FINAL_STATES = frozenset(("succeeded", "failed", "canceled"))
ACCEPTED_STATES = FINAL_STATES | frozenset(("starting", "processing"))


class VideoProviderError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise VideoProviderError("Remote redirect refused to protect video and provider secrets")


def _is_private_host(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
        return not ip.is_global
    except ValueError:
        return (host == "localhost" or host.endswith((".localhost", ".local", ".internal")) or
                "." not in host)


def validate_public_https(url: str) -> str:
    if not isinstance(url, str) or len(url) > 4096:
        raise VideoProviderError("Invalid public HTTPS URL")
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or "").lower().rstrip(".")
    try:
        port = parts.port
    except ValueError as exc:
        raise VideoProviderError("Invalid public URL port") from exc
    if (parts.scheme != "https" or not host or _is_private_host(host)
            or parts.username or parts.password or port not in (None, 443)
            or parts.fragment or "\\" in url or "@" in parts.netloc):
        raise VideoProviderError("Image input requires a public HTTPS URL without embedded credentials")
    return url


def _output_url(url: Any) -> str:
    if not isinstance(url, str):
        raise VideoProviderError("Completed job has no video output URL")
    validate_public_https(url)
    host = urllib.parse.urlsplit(url).hostname.lower().rstrip(".")
    if not any(host == domain or host.endswith("." + domain) for domain in OUTPUT_HOSTS):
        raise VideoProviderError("Video output must be hosted by the approved provider delivery domain")
    return url


def availability() -> dict[str, Any]:
    """Report capacity without making a network call or downloading models."""
    configured = bool(os.environ.get("REPLICATE_API_TOKEN", "").strip())
    paid_enabled = os.environ.get("TTG_STUDIO_ENABLE_PAID_VIDEO", "").strip() == "1"
    return {
        "online": {
            "provider": "replicate",
            "state": ("configured" if configured and paid_enabled else
                      "billing_disabled" if configured else "credentials_required"),
            "models": MODELS,
            "pricing_url": "https://replicate.com/bytedance/seedance-1-pro-fast",
            "billing": "external usage-based, no guaranteed budget cap at Studio layer",
            "approval_required": True,
        },
        "offline": {
            "state": "awaiting_GT502_or_Spark",
            "optional_provider": "FreeVideo",
            "model_files_installed_by_studio": False,
            "download_default": False,
            "future_model_storage_gib": "up to approximately 92 GiB for previously inspected full manifest",
        },
    }


def _token() -> str:
    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        raise VideoProviderError("Online provider not configured: set REPLICATE_API_TOKEN privately")
    return token


def _json_request(method: str, path: str, payload: dict | None = None) -> dict:
    if not path.startswith("/v1/") or "?" in path or ".." in path:
        raise VideoProviderError("Unexpected API path")
    url = "https://api.replicate.com" + path
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url, data=data, method=method,
        headers={"Authorization": "Bearer " + _token(),
                 "Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "TTG-Creative-Studio/1.0"},
    )
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=25) as response:
            raw = response.read(200_001)
            if len(raw) > 200_000:
                raise VideoProviderError("Provider response too large")
    except urllib.error.HTTPError as exc:
        # Never echo raw provider responses, which may contain private fields.
        raise VideoProviderError("Provider API returned HTTP " + str(exc.code)) from None
    except urllib.error.URLError as exc:
        raise VideoProviderError("Provider unreachable: " + str(exc.reason)[:180]) from None
    try:
        record = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise VideoProviderError("Provider response was not valid JSON") from None
    if not isinstance(record, dict):
        raise VideoProviderError("Unexpected provider response type")
    return record


def _record(data: dict) -> dict:
    identifier = data.get("id")
    status = data.get("status")
    if not isinstance(identifier, str) or not PREDICTION.fullmatch(identifier):
        raise VideoProviderError("Provider returned invalid prediction ID")
    if status not in ACCEPTED_STATES:
        raise VideoProviderError("Provider returned unsupported job status")
    output = None
    if status == "succeeded":
        value = data.get("output")
        if isinstance(value, list):
            value = value[0] if len(value) == 1 else None
        output = _output_url(value)
    return {
        "provider": "replicate", "prediction_id": identifier,
        "status": status, "done": status in FINAL_STATES,
        "output_url": output,
        "provider_page": "https://replicate.com/p/" + identifier,
        "local_model_downloaded": False,
    }


def submit_video(options: dict) -> dict:
    """Billable action. Never submit without per-request explicit approval."""
    if not isinstance(options, dict):
        raise VideoProviderError("Video options must be a dictionary")
    if options.get("paid_approval") != APPROVAL:
        raise VideoProviderError("Paid cloud video generation requires explicit approval of this request")
    mode = options.get("mode", "online")
    if mode != "online":
        raise VideoProviderError("Offline model generation is disabled until GT502/Spark admission")
    variant = options.get("model", "fast")
    if variant not in MODELS:
        raise VideoProviderError("Unsupported or unapproved cloud model")
    prompt = options.get("prompt", "")
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 2200:
        raise VideoProviderError("A prompt of 1–2200 characters is required")
    duration = options.get("duration", 5)
    if type(duration) is not int or not 2 <= duration <= 12:
        raise VideoProviderError("Duration must be an integer from 2 to 12 seconds")
    res = options.get("resolution", "480p")
    if res not in ("480p", "720p", "1080p"):
        raise VideoProviderError("Unsupported output resolution")
    ratio = options.get("aspect_ratio", "16:9")
    if ratio not in ("16:9", "9:16", "1:1", "4:3", "3:4"):
        raise VideoProviderError("Unsupported aspect ratio")
    data = {"prompt": prompt.strip(), "duration": duration,
            "resolution": res, "aspect_ratio": ratio, "fps": 24}
    if options.get("image_url"):
        data["image"] = validate_public_https(options["image_url"])
    if options.get("camera_fixed") is True:
        data["camera_fixed"] = True
    # Require separate machine-level billing admission as well as per-job
    # consent. A model or assistant cannot enable spending from JSON alone.
    _token()
    if os.environ.get("TTG_STUDIO_ENABLE_PAID_VIDEO", "").strip() != "1":
        raise VideoProviderError("Paid inference disabled by operator; set TTG_STUDIO_ENABLE_PAID_VIDEO=1 only when authorized")
    record = _json_request(
        "POST", "/v1/models/" + MODELS[variant] + "/predictions", {"input": data}
    )
    response = _record(record)
    response.update({"model": MODELS[variant], "billing": "submitted_to_external_paid_provider"})
    return response


def status_video(prediction_id: str) -> dict:
    if not isinstance(prediction_id, str) or not PREDICTION.fullmatch(prediction_id):
        raise VideoProviderError("Invalid provider prediction ID")
    return _record(_json_request("GET", "/v1/predictions/" + prediction_id))


def cancel_video(prediction_id: str) -> dict:
    if not isinstance(prediction_id, str) or not PREDICTION.fullmatch(prediction_id):
        raise VideoProviderError("Invalid provider prediction ID")
    return _record(_json_request("POST", "/v1/predictions/" + prediction_id + "/cancel"))


def download_video(prediction_id: str, destination: str | Path) -> dict:
    """No arbitrary URLs. Download completed provider video only, bounded, no overwrite."""
    status = status_video(prediction_id)
    if status["status"] != "succeeded":
        raise VideoProviderError("Prediction has not succeeded")
    link = _output_url(status["output_url"])
    target = Path(destination).expanduser()
    if target.is_symlink() or target.suffix.lower() != ".mp4":
        raise VideoProviderError("Download target must be a new MP4, not a symlink")
    target = target.resolve()
    if not target.parent.is_dir() or target.exists():
        raise VideoProviderError("Destination directory must exist and final MP4 must be new")
    req = urllib.request.Request(link, headers={"Accept": "video/mp4",
                                "User-Agent": "TTG-Creative-Studio/1.0"})
    scratch = None
    total = 0
    digest = hashlib.sha256()
    try:
        try:
            response = urllib.request.build_opener(NoRedirect).open(req, timeout=50)
        except urllib.error.HTTPError as exc:
            raise VideoProviderError("Video delivery returned HTTP " + str(exc.code)) from None
        with response:
            fd, scratch = tempfile.mkstemp(prefix=".ttg-cloud-video-", dir=target.parent)
            with os.fdopen(fd, "wb") as handle:
                first = b""
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    if total == 0:
                        first = chunk[:32]
                    total += len(chunk)
                    if total > MAX_DOWNLOAD:
                        raise VideoProviderError("Video download exceeds 125 MiB limit")
                    handle.write(chunk)
                    digest.update(chunk)
                if total < 1024 or first[4:8] != b"ftyp":
                    raise VideoProviderError("Provider did not return an actual MP4 container")
                handle.flush()
                os.fsync(handle.fileno())
        # Atomic publication without overwriting an existing project file.
        os.link(scratch, target)
    except FileExistsError:
        raise VideoProviderError("Download destination was created concurrently") from None
    finally:
        if scratch:
            Path(scratch).unlink(missing_ok=True)
    return {
        "provider": "replicate", "prediction_id": prediction_id,
        "path": str(target), "bytes": total, "sha256": digest.hexdigest(),
        "status": "downloaded_unverified_decoding", "source_url": link,
    }
