from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image, ImageOps


class CreativeJobError(RuntimeError):
    """Raised when a Creative Studio job cannot be completed safely."""


@dataclass
class JobResult:
    ok: bool
    job_id: str
    task: str
    input_path: str
    output_path: str
    status: str
    message: str = ""
    meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "ok": self.ok,
            "jobId": self.job_id,
            "task": self.task,
            "inputPath": self.input_path,
            "outputPath": self.output_path,
            "status": self.status,
            "message": self.message,
            "meta": self.meta or {},
            "completedAtUnix": int(time.time()),
        }
        return data


def _path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise CreativeJobError(f"{label} is required")
    return Path(value).expanduser().resolve()


def _ensure_input(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise CreativeJobError(f"Input file not found: {path}")


def _prepare_output(path: Path, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise CreativeJobError(f"Output file exists and overwrite=false: {path}")


def _open_image(path: Path) -> Image.Image:
    try:
        return Image.open(path)
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise CreativeJobError(f"Could not open image: {path} ({exc})") from exc


def _save_image(img: Image.Image, output: Path, options: Dict[str, Any]) -> None:
    fmt = options.get("format")
    save_kwargs: Dict[str, Any] = {}
    if isinstance(options.get("quality"), int):
        save_kwargs["quality"] = max(1, min(int(options["quality"]), 100))
    if isinstance(fmt, str) and fmt.strip():
        save_kwargs["format"] = fmt.strip().upper()
    img.save(output, **save_kwargs)


def remove_background(input_path: Path, output_path: Path, options: Dict[str, Any]) -> JobResult:
    try:
        from rembg import remove
    except Exception as exc:  # pragma: no cover - depends on installed package/model
        raise CreativeJobError("rembg is not installed or could not be loaded") from exc

    with input_path.open("rb") as f:
        input_bytes = f.read()
    output_bytes = remove(input_bytes)
    output_path.write_bytes(output_bytes)
    return JobResult(
        ok=True,
        job_id=str(options.get("jobId") or options.get("job_id") or "creative_job"),
        task="remove_background",
        input_path=str(input_path),
        output_path=str(output_path),
        status="done",
        message="Background removed.",
        meta={"engine": "rembg"},
    )


def resize_image(input_path: Path, output_path: Path, options: Dict[str, Any]) -> JobResult:
    width = int(options.get("width") or 0)
    height = int(options.get("height") or 0)
    if width <= 0 and height <= 0:
        raise CreativeJobError("resize_image requires width or height")

    with _open_image(input_path) as img:
        img = ImageOps.exif_transpose(img)
        src_w, src_h = img.size
        if width <= 0:
            width = max(1, int(src_w * (height / src_h)))
        if height <= 0:
            height = max(1, int(src_h * (width / src_w)))
        resized = img.resize((width, height), Image.LANCZOS)
        _save_image(resized, output_path, options)

    return JobResult(
        ok=True,
        job_id=str(options.get("jobId") or options.get("job_id") or "creative_job"),
        task="resize_image",
        input_path=str(input_path),
        output_path=str(output_path),
        status="done",
        message=f"Image resized to {width}x{height}.",
        meta={"width": width, "height": height},
    )


def convert_image(input_path: Path, output_path: Path, options: Dict[str, Any]) -> JobResult:
    mode = str(options.get("mode") or "").strip()
    with _open_image(input_path) as img:
        img = ImageOps.exif_transpose(img)
        if mode:
            img = img.convert(mode)
        _save_image(img, output_path, options)
    return JobResult(
        ok=True,
        job_id=str(options.get("jobId") or options.get("job_id") or "creative_job"),
        task="convert_image",
        input_path=str(input_path),
        output_path=str(output_path),
        status="done",
        message="Image converted/exported.",
        meta={"mode": mode or "preserved"},
    )


def image_info(input_path: Path, output_path: Path, options: Dict[str, Any]) -> JobResult:
    with _open_image(input_path) as img:
        meta = {
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "animated": bool(getattr(img, "is_animated", False)),
            "frames": int(getattr(img, "n_frames", 1)),
        }
    output_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return JobResult(
        ok=True,
        job_id=str(options.get("jobId") or options.get("job_id") or "creative_job"),
        task="image_info",
        input_path=str(input_path),
        output_path=str(output_path),
        status="done",
        message="Image info written.",
        meta=meta,
    )


def run_image_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Run a Hunter/Creative Studio image job.

    Expected job shape:
    {
      "jobId": "job_...",
      "task": "remove_background|resize_image|convert_image|image_info",
      "input": "D:/path/input.png",
      "output": "D:/path/output.png",
      "options": { "overwrite": false, ... }
    }
    """

    if not isinstance(job, dict):
        raise CreativeJobError("Job must be a JSON object")

    task = str(job.get("task") or "").strip().lower()
    options = dict(job.get("options") or {})
    options.setdefault("jobId", job.get("jobId") or job.get("job_id") or f"creative_{int(time.time())}")

    input_path = _path(job.get("input") or job.get("inputPath"), "input")
    output_path = _path(job.get("output") or job.get("outputPath"), "output")
    overwrite = bool(options.get("overwrite", False))

    _ensure_input(input_path)
    _prepare_output(output_path, overwrite=overwrite)

    if task == "remove_background":
        result = remove_background(input_path, output_path, options)
    elif task == "resize_image":
        result = resize_image(input_path, output_path, options)
    elif task == "convert_image":
        result = convert_image(input_path, output_path, options)
    elif task == "image_info":
        result = image_info(input_path, output_path, options)
    else:
        raise CreativeJobError(f"Unsupported task: {task}")

    return result.to_dict()
