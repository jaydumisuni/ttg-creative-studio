"""Evidence-based local image understanding for Creative Studio.

Pillow measurements are actual pixel observations, not object recognition.
Optional vision-language interpretation uses an owner-hosted OpenAI-compatible
multimodal server on loopback. No remote upload, silent model download, or
unreviewed model-generated editing commands.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageOps, ImageStat

from ttg_image_lab import read_image

MAX_IMAGE_PIXELS = 28_000_000
MAX_RESPONSE_BYTES = 128 * 1024
MAX_MODEL_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_EFFECTS = frozenset(("brightness", "contrast", "saturation", "sharpen"))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Local vision service redirects are prohibited")


def _channel_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def measure_image(path: str | Path) -> dict[str, Any]:
    """Deterministic properties, never invented semantic image contents."""
    path = Path(path)
    image = read_image(path)
    source_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    sample = image.copy()
    sample.thumbnail((320, 320), Image.Resampling.LANCZOS)
    rgb = sample.convert("RGB")
    gray = ImageOps.grayscale(rgb)
    lum = ImageStat.Stat(gray)
    mean_luminance = round(lum.mean[0], 2)
    deviation = round(lum.stddev[0], 2)
    edge = gray.filter(ImageFilter.FIND_EDGES)
    edge_energy = round(ImageStat.Stat(edge).mean[0], 2)
    # Count actual pixels rather than attributing a guessed scene object.
    quantized = rgb.quantize(colors=5, method=Image.Quantize.MEDIANCUT).convert("RGB")
    colors = quantized.getcolors(sample.width * sample.height) or []
    palette = [
        {"color": _channel_hex(tuple(color)), "share": round(n / (sample.width * sample.height), 3)}
        for n, color in sorted(colors, key=lambda x: x[0], reverse=True)[:5]
    ]
    alpha_extrema = image.getchannel("A").getextrema()
    width, height = image.size
    orientation = "square" if width == height else ("landscape" if width > height else "portrait")
    return {
        "source": str(path.resolve()),
        "source_sha256": source_sha,
        "dimensions": [width, height],
        "orientation": orientation,
        "luminance_mean_0_255": mean_luminance,
        "luminance_stddev_0_255": deviation,
        "edge_energy_0_255": edge_energy,
        "has_transparency": alpha_extrema[0] < 255,
        "dominant_colors": palette,
        "measurement_method": "Pillow pixel samples; no semantic object detection",
    }


def suggest_adjustments(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    """Deterministic safe suggestions; do not touch source image or project."""
    suggestions: list[dict[str, Any]] = []
    brightness = float(metrics["luminance_mean_0_255"])
    contrast = float(metrics["luminance_stddev_0_255"])
    if brightness < 65:
        suggestions.append({"action": "image_effect", "effect": "brightness", "amount": 1.25,
                            "reason": "Measured image luminance is low", "review_required": True})
    elif brightness > 207:
        suggestions.append({"action": "image_effect", "effect": "brightness", "amount": 0.88,
                            "reason": "Measured image luminance is high", "review_required": True})
    if contrast < 28:
        suggestions.append({"action": "image_effect", "effect": "contrast", "amount": 1.3,
                            "reason": "Measured luminance variation is low", "review_required": True})
    if float(metrics["edge_energy_0_255"]) < 12:
        suggestions.append({"action": "image_effect", "effect": "sharpen", "amount": 1.3,
                            "reason": "Measured local edge detail is low; check before applying", "review_required": True})
    return suggestions


class LocalVisionServer:
    """Direct local OpenAI-compatible multimodal inference, with no model manager.

    Studio speaks directly to an image-capable llama.cpp/vLLM-style HTTP
    server the owner controls. The server/model are optional; measured pixels
    remain available if no model is installed. No dependency on Hunter or an external model manager.
    """

    def __init__(self, url: str = "http://127.0.0.1:8000",
                 timeout: int = 180):
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme != "http" or parsed.hostname not in
                ("127.0.0.1", "localhost", "::1") or parsed.username or
                parsed.password or parsed.path not in ("", "/") or
                parsed.query or parsed.fragment or
                parsed.port is None or not 1 <= parsed.port <= 65535):
            raise ValueError("Only an explicit local multimodal HTTP endpoint is accepted")
        if not 10 <= timeout <= 600:
            raise ValueError("Local vision timeout outside safe bounds")
        self.url = url.rstrip("/")
        self.timeout = timeout
        # Do not allow proxy environment variables to redirect local images.
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect
        )

    def _fetch(self, endpoint: str, payload: dict | None = None) -> dict:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            self.url + endpoint, data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST" if data is not None else "GET",
        )
        with self._opener.open(req, timeout=self.timeout) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError("Local vision response exceeds limit")
        value = json.loads(body)
        if not isinstance(value, dict):
            raise ValueError("Invalid local vision response")
        return value

    def installed_models(self) -> list[str]:
        data = self._fetch("/v1/models")
        models = data.get("data", [])
        if not isinstance(models, list):
            raise ValueError("Unexpected local vision model list")
        return [m["id"] for m in models
                if isinstance(m, dict) and isinstance(m.get("id"), str)
                and 0 < len(m["id"]) <= 160][:100]

    def describe(self, image_path: str | Path, model: str, question: str = "") -> str:
        if not isinstance(model, str) or not model or len(model) > 160:
            raise ValueError("Select an installed image-capable vision model")
        if model not in self.installed_models():
            raise ValueError("Model is not advertised by the local vision server")
        if len(question) > 2000:
            raise ValueError("Question exceeds 2000 characters")
        image = read_image(image_path)
        image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        data = io.BytesIO()
        image.convert("RGB").save(data, "JPEG", quality=86)
        if data.tell() > MAX_MODEL_IMAGE_BYTES:
            raise ValueError("Model image is too large")
        prompt = (
            "Analyze only visible evidence in the supplied image. Describe visible "
            "objects, object count and relative positions, composition, colors and "
            "any clearly legible text. Do not guess unseen content, identities, "
            "brands or illegible text. State uncertainties. Suggestions are "
            "advisory; no edit has been made. User question: " +
            (question.strip() or "Describe and critique this image.")
        )
        response = self._fetch("/v1/chat/completions", {
            "model": model, "stream": False, "temperature": 0.1,
            "max_tokens": 640,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": "data:image/jpeg;base64," +
                               base64.b64encode(data.getvalue()).decode("ascii")
                    }},
                ],
            }],
        })
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("No model reply from local vision service")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            # Some local OpenAI-compatible servers return typed text sections.
            if any(not isinstance(item, dict) or item.get("type") != "text"
                   for item in content):
                raise ValueError("Unrecognized local vision output sections")
            content = "\n".join(str(part.get("text", "")) for part in content)
        if not isinstance(content, str) or not content.strip() or len(content) > 12000:
            raise ValueError("No meaningful vision-model description received")
        return content.strip()
