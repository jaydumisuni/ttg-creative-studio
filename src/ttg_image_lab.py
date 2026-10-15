#!/usr/bin/env python3
"""Non-destructive image effects and optional local ComfyUI inference for Studio.

No pretend AI output: generation raises a clear error unless a real local
ComfyUI service and installed model return an actual PNG.
"""
from __future__ import annotations

import io
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Literal

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

MAX_BYTES = 32 * 1024 * 1024
MAX_PIXELS = 28_000_000


def read_image(path: str | Path) -> Image.Image:
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("Image missing or exceeds 32 MiB")
    with Image.open(path) as src:
        if src.width * src.height > MAX_PIXELS:
            raise ValueError("Image exceeds 28 megapixels")
        return ImageOps.exif_transpose(src).convert("RGBA")


def selected_mask(size: tuple[int, int],
                  selection: tuple[int, int, int, int] | None = None,
                  strokes: list[tuple[list[tuple[int, int]], int]] | None = None,
                  feather: float = 0) -> Image.Image:
    """Editable grayscale selection/brush mask, full white when unselected."""
    width, height = size
    if width < 1 or height < 1 or width * height > MAX_PIXELS:
        raise ValueError("Invalid mask dimensions")
    mask = Image.new("L", size, 0 if selection or strokes else 255)
    draw = ImageDraw.Draw(mask)
    if selection:
        x0, y0, x1, y1 = selection
        draw.rectangle((max(0, x0), max(0, y0), min(width, x1),
                        min(height, y1)), fill=255)
    for points, brush in strokes or []:
        if not points or not (1 <= brush <= 512):
            raise ValueError("Brush size must be 1–512")
        draw.line(points, fill=255, width=brush, joint="curve")
        radius = brush / 2
        for x, y in points:
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=255)
    if feather:
        if not (0 <= feather <= 100):
            raise ValueError("Mask feather must be 0–100")
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
    return mask


def apply_adjustments(image: Image.Image, *, brightness: float = 1.0,
                      contrast: float = 1.0, saturation: float = 1.0,
                      sharpness: float = 1.0, mask: Image.Image | None = None) -> Image.Image:
    """Apply repeatable, alpha-preserving color adjustments within selection."""
    for value in (brightness, contrast, saturation, sharpness):
        if not math.isfinite(value) or not (0 <= value <= 4):
            raise ValueError("Adjustment controls must be finite, between 0 and 4")
    rgba = image.convert("RGBA")
    rgb = rgba.convert("RGB")
    rgb = ImageEnhance.Brightness(rgb).enhance(brightness)
    rgb = ImageEnhance.Contrast(rgb).enhance(contrast)
    rgb = ImageEnhance.Color(rgb).enhance(saturation)
    rgb = ImageEnhance.Sharpness(rgb).enhance(sharpness)
    transformed = rgb.convert("RGBA")
    transformed.putalpha(rgba.getchannel("A"))
    if mask is not None:
        if mask.size != rgba.size:
            raise ValueError("Selection mask and image dimensions differ")
        return Image.composite(transformed, rgba, mask.convert("L"))
    return transformed


def apply_layer_mask(image: Image.Image, mask: Image.Image,
                     invert: bool = False, feather: float = 0) -> Image.Image:
    if image.size != mask.size:
        mask = mask.resize(image.size, Image.Resampling.LANCZOS)
    alpha = mask.convert("L")
    if not (0 <= feather <= 100):
        raise ValueError("Invalid mask feather")
    if feather:
        alpha = alpha.filter(ImageFilter.GaussianBlur(feather))
    if invert:
        alpha = ImageOps.invert(alpha)
    image = image.convert("RGBA")
    image.putalpha(ImageChops.multiply(image.getchannel("A"), alpha))
    return image


class ComfyUIBackend:
    """Loopback ComfyUI server; checkpoint selection is explicit, never fabricated."""

    def __init__(self, url: str = "http://127.0.0.1:8188",
                 timeout_seconds: float = 120.0) -> None:
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
                or parsed.username or parsed.password or parsed.path not in ("", "/")
                or parsed.query or parsed.fragment):
            raise ValueError("Only local HTTP ComfyUI endpoints are allowed")
        if not (10 <= timeout_seconds <= 1800):
            raise ValueError("Inference timeout must be 10–1800 seconds")
        self.base = url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _request(self, endpoint: str, data: bytes | None = None,
                 mime: str = "application/json") -> bytes:
        req = urllib.request.Request(
            self.base + endpoint, data=data,
            headers={"Content-Type": mime, "Accept": "application/json, image/png"},
            method="POST" if data is not None else "GET",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            size = response.headers.get("Content-Length")
            if size is not None and int(size) > MAX_BYTES:
                raise ValueError("ComfyUI response exceeds 32 MiB")
            result = response.read(MAX_BYTES + 1)
        if len(result) > MAX_BYTES:
            raise ValueError("ComfyUI response exceeds 32 MiB")
        return result

    def available_models(self) -> list[str]:
        obj = json.loads(self._request("/object_info/CheckpointLoaderSimple"))
        return obj["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]

    def _upload_image(self, image: Image.Image, prefix: str) -> str:
        buff = io.BytesIO()
        image.save(buff, format="PNG")
        png = buff.getvalue()
        if len(png) > MAX_BYTES:
            raise ValueError("Image upload exceeds 32 MiB")
        boundary = "ttg" + uuid.uuid4().hex
        name = prefix + "-" + uuid.uuid4().hex + ".png"
        data = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\n"
            "Content-Type: image/png\r\n\r\n"
        ).encode() + png + f"\r\n--{boundary}--\r\n".encode()
        out = json.loads(self._request("/upload/image", data,
                                      "multipart/form-data; boundary=" + boundary))
        return str(out["name"])

    def generate(self, *, prompt: str, checkpoint: str,
                 width: int = 768, height: int = 768, steps: int = 22,
                 seed: int = 49, input_image: Image.Image | None = None,
                 mask: Image.Image | None = None,
                 denoise: float = 0.7) -> Image.Image:
        if not prompt.strip() or len(prompt) > 4000:
            raise ValueError("Provide a prompt of 1–4000 characters")
        if not checkpoint.strip():
            raise ValueError("Select an installed ComfyUI checkpoint")
        if width % 8 or height % 8 or not (256 <= width <= 1536 and 256 <= height <= 1536):
            raise ValueError("Image dimensions must be 256–1536, divisible by 8")
        if not (1 <= steps <= 80 and 0 <= seed <= 2**53 - 1 and 0 < denoise <= 1):
            raise ValueError("Invalid inference settings")
        if mask is not None and input_image is None:
            raise ValueError("Inpainting requires a source image")
        graph: dict[str, dict] = {
            "1": {"class_type": "CheckpointLoaderSimple",
                  "inputs": {"ckpt_name": checkpoint}},
            "2": {"class_type": "CLIPTextEncode",
                  "inputs": {"text": prompt, "clip": ["1", 1]}},
            "3": {"class_type": "CLIPTextEncode",
                  "inputs": {"text": "blurry, low quality, low resolution", "clip": ["1", 1]}},
        }
        if input_image is None:
            graph["4"] = {"class_type": "EmptyLatentImage",
                           "inputs": {"width": width, "height": height, "batch_size": 1}}
            latent = ["4", 0]
            denoise = 1.0
        else:
            source = input_image.convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)
            name = self._upload_image(source, "ttg-input")
            graph["4"] = {"class_type": "LoadImage", "inputs": {"image": name}}
            if mask is not None:
                alpha_mask = mask.convert("L").resize((width, height), Image.Resampling.LANCZOS)
                # ComfyUI inpaint convention: WHITE pixels indicate region to regenerate.
                mask_rgba = Image.new("RGBA", source.size, (0, 0, 0, 0))
                mask_rgba.putalpha(ImageOps.invert(alpha_mask))
                mask_name = self._upload_image(mask_rgba, "ttg-mask")
                graph["5"] = {"class_type": "LoadImage", "inputs": {"image": mask_name}}
                graph["6"] = {"class_type": "VAEEncodeForInpaint",
                              "inputs": {"pixels": ["4", 0], "vae": ["1", 2],
                                         "mask": ["5", 1], "grow_mask_by": 4}}
            else:
                graph["6"] = {"class_type": "VAEEncode",
                              "inputs": {"pixels": ["4", 0], "vae": ["1", 2]}}
            latent = ["6", 0]
        graph["7"] = {"class_type": "KSampler",
                      "inputs": {"model": ["1", 0], "positive": ["2", 0],
                                 "negative": ["3", 0], "latent_image": latent,
                                 "seed": seed, "steps": steps, "cfg": 7.0,
                                 "sampler_name": "euler", "scheduler": "normal",
                                 "denoise": denoise}}
        graph["8"] = {"class_type": "VAEDecode",
                      "inputs": {"samples": ["7", 0], "vae": ["1", 2]}}
        graph["9"] = {"class_type": "SaveImage",
                      "inputs": {"images": ["8", 0], "filename_prefix": "ttg_studio"}}
        result = json.loads(self._request("/prompt", json.dumps({
            "prompt": graph, "client_id": "ttg-creative-studio",
        }).encode()))
        job = result["prompt_id"]
        if not isinstance(job, str) or len(job) > 128:
            raise RuntimeError("Invalid ComfyUI job identifier")
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            response = json.loads(self._request("/history/" + urllib.parse.quote(job, safe="")))
            record = response.get(job, {})
            if record.get("status", {}).get("status_str") == "error":
                raise RuntimeError("ComfyUI failed to generate this image")
            images = record.get("outputs", {}).get("9", {}).get("images", [])
            if images:
                selection = images[0]
                query = urllib.parse.urlencode({
                    "filename": selection["filename"],
                    "subfolder": selection.get("subfolder", ""),
                    "type": selection.get("type", "output"),
                })
                data = self._request("/view?" + query)
                with Image.open(io.BytesIO(data)) as im:
                    if im.width * im.height > MAX_PIXELS:
                        raise ValueError("Generated image too large")
                    return im.convert("RGBA")
            time.sleep(.5)
        raise TimeoutError("ComfyUI generation did not complete before timeout")
