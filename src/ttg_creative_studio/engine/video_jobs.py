"""Model-agnostic video tools for Creative Studio's existing Hunter job CLI.

Read-only analysis and planning are model-free. Semantic descriptions optionally
reuse Studio's local vision service. Rendering uses Studio's native timeline.
No AI agent is allowed to substitute a fake generated video for a real backend.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageOps, ImageStat

from ttg_creative_studio.engine.image_jobs import CreativeJobError, JobResult
from ttg_ffmpeg_manager import FFmpegManager
from ttg_motion_exporter import MotionExporter
from ttg_canvas_engine import RenderContext
from ttg_project_schema import TTGProject
from ttg_visual_understanding import LocalVisionServer
from ttg_online_video_provider import (
    availability as cloud_video_availability,
    submit_video, status_video, cancel_video, download_video,
)

MAX_VIDEO_SIZE = 2 * 1024**3
MAX_JSON_BYTES = 200_000
SCHEMA = "ttg.creative.video-agent.v1"
VIDEO_TASKS = frozenset({
    "video_capabilities", "video_info", "video_understand",
    "video_plan", "video_render", "video_generate",
    "video_generation_status", "video_generation_download",
    "video_generation_cancel",
})


def tool_catalog() -> dict[str, Any]:
    """Schema-discoverable tools, consumable by Hunter or any other AI client."""
    return {
        "schema": SCHEMA, "transport": "local-json-cli",
        "entrypoint": "python src/ttg_creative_studio/cli.py --job JOB.json --result RESULT.json",
        "operations": {
            "video_capabilities": {
                "requires": [], "side_effects": "none",
                "description": "List video analysis/rendering backends and missing dependencies",
            },
            "video_info": {
                "requires": ["input"], "side_effects": "report only",
                "description": "Read observed duration, frame rate, resolution, streams and SHA256",
            },
            "video_understand": {
                "requires": ["input"], "side_effects": "report only",
                "options": {"question": "optional string", "vision_model": "optional installed model id",
                            "vision_endpoint": "optional explicit loopback URL"},
                "description": "Inspect sampled frame pixels; optionally ask installed local VLM. No invented objects",
            },
            "video_plan": {
                "requires": ["output", "options.scenes"], "side_effects": "storyboard JSON",
                "description": "Create a reviewable, timestamped storyboard from supplied scenes, no inference",
            },
            "video_render": {
                "requires": ["input", "output"], "side_effects": "final MP4",
                "description": "Render an actual .ttgstudio project with Studio timeline and FFmpeg",
            },
            "video_generate": {
                "state": "online_opt_in", "side_effects": "billable cloud generation",
                "requires": ["options.prompt", "options.paid_approval"],
                "description": "Replicate-hosted Seedance; requires API token and explicit paid approval",
            },
            "video_generation_status": {
                "state": "online", "side_effects": "none",
                "requires": ["options.prediction_id"],
                "description": "Read actual external generation status, without downloading anything",
            },
            "video_generation_cancel": {
                "state": "online", "side_effects": "cancel provider job",
                "requires": ["options.prediction_id", "options.cancel_approval"],
                "description": "Explicitly cancel the exact provider job",
            },
            "video_generation_download": {
                "state": "online", "side_effects": "bounded new MP4",
                "requires": ["options.prediction_id", "output"],
                "description": "Download a successful real MP4; never overwrite files",
            },
            "video_local_install": {
                "state": "future_GT502_Spark", "side_effects": "none",
                "description": "User-choice 92GiB-class FreeVideo model install, disabled on KRATOS",
            },
        },
        "safety": {
            "human_or_policy_approval_required_for": [
                "external_video_generation", "publishing", "exporting_to_untrusted_destinations"
            ],
            "no_implicit_model_download": True,
            "cloud_inference": "optional, explicitly approved paid request",
            "local_inference": "disabled_pending_GT502_Spark",
            "no_local_model_download": True,
            "no_source_overwrite": True,
        },
    }


def _file(path: Any, *, suffixes: tuple[str, ...] = ()) -> Path:
    if not isinstance(path, str) or not path.strip():
        raise CreativeJobError("Input file path required")
    candidate = Path(path).expanduser()
    if candidate.is_symlink():
        raise CreativeJobError("Input symbolic links are not allowed for AI jobs")
    p = candidate.resolve(strict=True)
    if not p.is_file():
        raise CreativeJobError("Input must be a normal file")
    if suffixes and p.suffix.lower() not in suffixes:
        raise CreativeJobError("Unsupported input extension")
    if p.stat().st_size > MAX_VIDEO_SIZE:
        raise CreativeJobError("Input exceeds 2 GiB agent limit")
    return p


def _output(path: Any, extension: str) -> Path:
    if not isinstance(path, str) or not path.strip():
        raise CreativeJobError("Output path required")
    candidate = Path(path).expanduser()
    if candidate.is_symlink():
        raise CreativeJobError("Output symbolic links are not allowed")
    p = candidate.resolve()
    if p.suffix.lower() != extension:
        raise CreativeJobError("Unexpected output extension")
    if p.exists():
        raise CreativeJobError("Agent will not overwrite any existing output")
    if not p.parent.is_dir():
        raise CreativeJobError("Create the authorized output directory before execution")
    return p


def _ffprobe() -> str:
    found = shutil.which("ffprobe")
    if not found:
        ffmpeg = FFmpegManager().status().path
        if ffmpeg:
            near = Path(ffmpeg).with_name("ffprobe.exe" if Path(ffmpeg).suffix == ".exe" else "ffprobe")
            if near.is_file():
                found = str(near)
    if not found:
        raise CreativeJobError("ffprobe required for measured video metadata")
    return found


def _ffmpeg() -> str:
    try:
        return FFmpegManager().require()
    except RuntimeError as exc:
        raise CreativeJobError(str(exc)) from exc


def _probe(path: Path) -> dict[str, Any]:
    process = subprocess.run(
        [_ffprobe(), "-v", "error", "-show_streams", "-show_format",
         "-of", "json", str(path)],
        capture_output=True, timeout=20, check=False,
    )
    if process.returncode or len(process.stdout) > MAX_JSON_BYTES:
        raise CreativeJobError("Unable to probe bounded video metadata")
    record = json.loads(process.stdout)
    streams = record.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video:
        raise CreativeJobError("No real video stream found")
    raw_duration = record.get("format", {}).get("duration") or video.get("duration")
    duration = float(raw_duration or 0)
    width, height = int(video.get("width", 0)), int(video.get("height", 0))
    if not math.isfinite(duration) or not (0.01 < duration <= 1800):
        raise CreativeJobError("Video duration must be measurable and at most 30 minutes")
    if width < 1 or height < 1 or width*height > 16_000_000:
        raise CreativeJobError("Video dimensions exceed supported bounds")
    frame_rate = video.get("avg_frame_rate") or "0/1"
    return {
        "duration_seconds": round(duration, 4), "width": width, "height": height,
        "frame_rate": frame_rate, "video_codec": video.get("codec_name"),
        "audio_streams": sum(s.get("codec_type") == "audio" for s in streams),
        "size_bytes": path.stat().st_size,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest()
        if path.stat().st_size <= 32*1024**2 else _sha256_stream(path),
        "evidence": "ffprobe stream metadata and physical source file",
    }


def _sha256_stream(p: Path) -> str:
    digest = hashlib.sha256()
    with p.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frame(path: Path, timestamp: float) -> Image.Image:
    proc = subprocess.run(
        [_ffmpeg(), "-hide_banner", "-loglevel", "error", "-ss", f"{timestamp:.4f}",
         "-i", str(path), "-frames:v", "1",
         "-vf", "scale=w=320:h=320:force_original_aspect_ratio=decrease",
         "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True, timeout=25, check=False,
    )
    if proc.returncode or not proc.stdout or len(proc.stdout)>3*1024**2:
        raise CreativeJobError("Could not decode bounded sample frame")
    with Image.open(io.BytesIO(proc.stdout)) as file:
        return file.convert("RGB")


def _analyze_frame(image: Image.Image) -> dict[str, Any]:
    gray = ImageOps.grayscale(image)
    stats = ImageStat.Stat(gray)
    edge = gray.filter(ImageFilter.FIND_EDGES)
    return {
        "dimensions": list(image.size),
        "luminance_mean_0_255": round(stats.mean[0], 2),
        "contrast_stddev_0_255": round(stats.stddev[0], 2),
        "edge_energy_0_255": round(ImageStat.Stat(edge).mean[0], 2),
        "evidence": "Pillow observed sampled frame pixels, not object recognition",
    }


def _storyboard(job: dict[str, Any]) -> dict[str, Any]:
    options = job.get("options") or {}
    scenes = options.get("scenes")
    if not isinstance(scenes, list) or not (1 <= len(scenes) <= 12):
        raise CreativeJobError("Storyboard needs 1–12 authored scene descriptions")
    fps = options.get("fps", 24)
    if type(fps) is not int or not (1 <= fps <= 60):
        raise CreativeJobError("FPS must be an integer 1–60")
    timeline, elapsed = [], 0.
    for i, obj in enumerate(scenes):
        if not isinstance(obj, dict):
            raise CreativeJobError("Scene must be an object")
        prompt = obj.get("description")
        dur = obj.get("seconds")
        if not isinstance(prompt, str) or not (1 <= len(prompt.strip()) <= 1200):
            raise CreativeJobError("Each scene needs a real description")
        if type(dur) not in (int, float) or not math.isfinite(dur) or not .2 <= dur <= 30:
            raise CreativeJobError("Scene duration must be 0.2–30 seconds")
        timeline.append({"index": i, "start_seconds": round(elapsed, 3),
                         "duration_seconds": dur, "description": prompt.strip(),
                         "status": "planned_not_generated"})
        elapsed += dur
    if elapsed > 180:
        raise CreativeJobError("Storyboard total duration limited to 180 seconds")
    return {"schema": SCHEMA, "status": "review_required",
            "scenes": timeline, "fps": fps,
            "duration_seconds": round(elapsed,3),
            "generation_backend": "unassigned",
            "note": "The storyboard contains authored descriptions; no frames were generated"}


def _atomic_json(path: Path, record: dict[str, Any]) -> None:
    import os
    import tempfile
    fd, temporary = tempfile.mkstemp(prefix=".studio-video-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        if path.exists():
            raise CreativeJobError("Output created concurrently; refusing overwrite")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def run_video_job(job: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(job, dict):
        raise CreativeJobError("Video job must be a JSON object")
    task = job.get("task")
    if task not in VIDEO_TASKS:
        raise CreativeJobError("Unsupported video operation")
    job_id = str(job.get("jobId") or job.get("job_id") or "video_job")
    if len(job_id) > 120:
        raise CreativeJobError("Invalid job id")
    options = job.get("options") or {}
    if not isinstance(options, dict):
        raise CreativeJobError("options must be an object")
    if task == "video_capabilities":
        ffmpeg = FFmpegManager().status().available
        provider_state = cloud_video_availability()
        return {"ok": True, "jobId": job_id, "task": task, "status": "done",
                "meta": {"catalog": tool_catalog(), "ffmpeg": ffmpeg,
                         "ffprobe": bool(shutil.which("ffprobe")),
                         "generation": provider_state,
                         "local_video_generation": "awaiting_GT502_or_Spark"}}
    if task == "video_generate":
        reply = submit_video(options)
        return JobResult(True, job_id, task, "", "", "submitted",
                         "Actual billable online prediction submitted", reply).to_dict()
    if task == "video_generation_status":
        reply = status_video(options.get("prediction_id"))
        return JobResult(True, job_id, task, "", "", reply["status"],
                         "External provider prediction status", reply).to_dict()
    if task == "video_generation_cancel":
        if options.get("cancel_approval") != "CANCEL_THIS_PREDICTION":
            raise CreativeJobError("Cancellation requires explicit approval")
        reply = cancel_video(options.get("prediction_id"))
        return JobResult(True, job_id, task, "", "", reply["status"],
                         "Sent cancellation request to provider", reply).to_dict()
    if task == "video_generation_download":
        out = _output(job.get("output") or job.get("outputPath"), ".mp4")
        reply = download_video(options.get("prediction_id"), out)
        return JobResult(True, job_id, task, "", str(out), "downloaded",
                         "Downloaded external MP4; import via Video Lab to edit", reply).to_dict()
    out = _output(job.get("output") or job.get("outputPath"),
                  ".mp4" if task == "video_render" else ".json")
    if task == "video_plan":
        result = _storyboard(job)
    else:
        path = _file(job.get("input") or job.get("inputPath"),
                     suffixes=(".ttgstudio", ".json") if task == "video_render"
                     else (".mp4", ".mov", ".mkv", ".webm"))
        if task == "video_render":
            project = TTGProject.load(path)
            if project.project_type not in ("motion","mixed"):
                raise CreativeJobError("Native video render requires a motion project")
            with tempfile.TemporaryDirectory(prefix="studio-video-",dir=out.parent) as work:
                MotionExporter(RenderContext(path.parent)).export_mp4(project, out, work)
            return JobResult(True,job_id,task,str(path),str(out),"done",
                             "Native timeline actually rendered as MP4",
                             {"size_bytes": out.stat().st_size,
                              "sha256": _sha256_stream(out)}).to_dict()
        result = _probe(path)
        if task == "video_understand":
            duration = result["duration_seconds"]
            points = [max(0, (duration-.02)*fraction) for fraction in (.15,.5,.85)]
            samples = []
            for second in points:
                frame = _frame(path,second)
                evidence = _analyze_frame(frame)
                evidence["timestamp_seconds"] = round(second,3)
                samples.append(evidence)
            result["frame_samples"] = samples
            result["interpretation"] = "pixel_measurements_only"
            model = options.get("vision_model")
            if model:
                if not isinstance(model,str) or len(model)>160:
                    raise CreativeJobError("Invalid vision model")
                endpoint=options.get("vision_endpoint","http://127.0.0.1:8000")
                vision=LocalVisionServer(endpoint)
                interpretations=[]
                with tempfile.TemporaryDirectory(prefix="studio-frame-") as temporary:
                    for i,(second) in enumerate(points):
                        frame=_frame(path,second)
                        frame_path=Path(temporary)/f"sample_{i}.png"
                        frame.save(frame_path)
                        interpretation=vision.describe(frame_path,model,options.get("question","Describe the visible scene"))
                        interpretations.append({"timestamp_seconds":round(second,3),
                                                "description":interpretation,
                                                "source":"installed_local_vision_model"})
                result["semantic_evidence"]=interpretations
                result["interpretation"]="local_model_observations_requiring_review"
    _atomic_json(out,result)
    return JobResult(True,job_id,task,str(job.get("input") or ""),str(out),"done",
                     "Creative Studio video tool completed; see evidence",
                     result).to_dict()
