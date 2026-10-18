"""Native bounded video clip probing and frame extraction for Creative Studio.

This module does not require an AI model, external provider, or an agent.
Imported clips are ordinary editable project layers; decoded frames are
real media observations and are never silently simulated.
"""
from __future__ import annotations

from functools import lru_cache
import io
import json
import math
import re
from pathlib import Path
import shutil
import subprocess

from PIL import Image

from ttg_ffmpeg_manager import FFmpegManager

MAX_CLIP_BYTES = 2 * 1024**3
MAX_CLIP_PIXELS = 16_000_000
MAX_SAMPLE_PIXELS = 1920 * 1080


def ffprobe_executable() -> str:
    candidate = shutil.which("ffprobe")
    if not candidate:
        ffmpeg = FFmpegManager().status().path
        if ffmpeg:
            near = Path(ffmpeg).with_name(
                "ffprobe.exe" if Path(ffmpeg).suffix.lower() == ".exe" else "ffprobe"
            )
            if near.is_file():
                candidate = str(near)
    if not candidate:
        raise RuntimeError("FFprobe is required to import and inspect video clips")
    return candidate


def _checked_media(path: Path) -> Path:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError("Video source must be a regular local file")
    if path.suffix.lower() not in (".mp4", ".mov", ".mkv", ".webm"):
        raise ValueError("Unsupported video extension")
    size = path.stat().st_size
    if not 64 <= size <= MAX_CLIP_BYTES:
        raise ValueError("Video is empty or exceeds Studio's 2 GiB clip limit")
    return path.resolve()


def _probe_via_ffmpeg(path: str, size: int) -> dict:
    """Fallback for existing Studio Video Export Packs that bundle FFmpeg only.

    We inspect actual FFmpeg stream diagnostics, not filename guesses.
    Ambiguous files are rejected rather than fabricating duration or dimensions.
    """
    ffmpeg = FFmpegManager().require()
    process = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", path],
        capture_output=True, timeout=25, check=False,
    )
    diagnostics = process.stderr.decode("utf-8", errors="replace")[:60_000]
    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", diagnostics)
    video_line = next((line for line in diagnostics.splitlines()
                       if re.search(r"Stream #\d+:\d+.*Video:", line)), "")
    size_match = re.search(r"\b(\d{2,5})x(\d{2,5})\b", video_line)
    if not duration_match or not size_match:
        raise RuntimeError("FFmpeg found no reliable video duration and dimensions")
    hh, mm, ss = duration_match.groups()
    duration = int(hh)*3600 + int(mm)*60 + float(ss)
    width, height = int(size_match[1]), int(size_match[2])
    if not math.isfinite(duration) or not 0.02 < duration <= 1800:
        raise ValueError("Source video duration exceeds supported bounds")
    if width < 1 or height < 1 or width*height > MAX_CLIP_PIXELS:
        raise ValueError("Video dimensions exceed supported bounds")
    codec_match = re.search(r"Video:\s*([\w-]+)", video_line)
    fps_match = re.search(r"(\d+(?:\.\d+)?)\s+fps", video_line)
    return {
        "duration": round(duration, 4), "width": width, "height": height,
        "audio_streams": sum(bool(re.search(r"Stream #\d+:\d+.*Audio:", line))
                             for line in diagnostics.splitlines()),
        "video_codec": codec_match[1] if codec_match else "undetermined",
        "fps": fps_match[1] if fps_match else "undetermined",
        "size_bytes": size, "probe_method": "ffmpeg_stream_diagnostics",
    }


@lru_cache(maxsize=24)
def _probe_cached(path: str, size: int, mtime_ns: int) -> dict:
    try:
        probe = ffprobe_executable()
    except RuntimeError:
        return _probe_via_ffmpeg(path, size)
    result = subprocess.run(
        [probe, "-v", "error", "-show_streams", "-show_format",
         "-of", "json", path],
        capture_output=True, timeout=25, check=False,
    )
    if result.returncode or len(result.stdout) > 200_000:
        raise RuntimeError("FFprobe could not inspect this media file")
    info = json.loads(result.stdout)
    streams = info.get("streams", [])
    visual = next((s for s in streams if s.get("codec_type") == "video"), None)
    if visual is None:
        raise ValueError("Video has no valid visual stream")
    width, height = int(visual.get("width", 0)), int(visual.get("height", 0))
    duration = float(info.get("format", {}).get("duration") or visual.get("duration") or 0)
    if not 0.02 < duration <= 1800 or not math.isfinite(duration):
        raise ValueError("Video duration must be between 0.02 and 1800 seconds")
    if width < 1 or height < 1 or width * height > MAX_CLIP_PIXELS:
        raise ValueError("Video exceeds Studio's 16 megapixel decode limit")
    return {
        "duration": round(duration, 4), "width": width, "height": height,
        "audio_streams": sum(x.get("codec_type") == "audio" for x in streams),
        "video_codec": visual.get("codec_name"),
        "fps": str(visual.get("avg_frame_rate") or "0/1"),
        "size_bytes": size,
    }


def probe_video(path: str | Path) -> dict:
    source = _checked_media(Path(path))
    info = source.stat()
    return {
        **_probe_cached(str(source), info.st_size, info.st_mtime_ns),
        "mtime_ns": info.st_mtime_ns,
    }


@lru_cache(maxsize=8)
def _frame_cached(path: str, mtime_ns: int, size: int,
                  timestamp_ms: int) -> Image.Image:
    ffmpeg = FFmpegManager().require()
    # Decode a single bounded frame. Limit both decoded pixel and pipe bytes.
    common = [ffmpeg, "-hide_banner", "-loglevel", "error",
              "-threads", "1", "-filter_threads", "1"]
    output = ["-frames:v", "1", "-vf",
              "scale=w=1920:h=1080:force_original_aspect_ratio=decrease",
              "-f", "image2pipe", "-vcodec", "png", "-"]
    # Container duration can include audio padding after the last video
    # frame. Hold the last *real decoded* frame at those tails, rather than
    # crashing an entire MP4 export or claiming a fabricated frame.
    data = None
    last_reason = ""
    for delta in (0, 250, 500, 1000):
        seek_ms = max(0, timestamp_ms - delta)
        for accurate in (False, True):
            timing = ["-ss", f"{seek_ms/1000:.3f}"]
            cmd = ([*common, "-i", path, *timing, *output] if accurate else
                   [*common, *timing, "-i", path, *output])
            data = subprocess.run(cmd, capture_output=True,
                                  timeout=25, check=False)
            if data.returncode == 0 and 0 < len(data.stdout) <= 8*1024**2:
                break
            last_reason = data.stderr.decode("utf-8", errors="replace")[-300:]
        if data.returncode == 0 and 0 < len(data.stdout) <= 8*1024**2:
            break
    if data is None or data.returncode or not data.stdout or len(data.stdout)>8*1024**2:
        raise RuntimeError(
            f"FFmpeg could not decode a real video frame near {timestamp_ms/1000:.3f}s: "
            + last_reason
        )
    with Image.open(io.BytesIO(data.stdout)) as opened:
        if opened.width * opened.height > MAX_SAMPLE_PIXELS:
            raise ValueError("Decoded frame exceeds supported pixel limit")
        return opened.convert("RGBA")


def video_frame(path: str | Path, timestamp: float) -> Image.Image:
    source = _checked_media(Path(path))
    metadata = probe_video(source)
    if not math.isfinite(timestamp) or timestamp < 0 or timestamp >= metadata["duration"]:
        raise ValueError("Requested frame is outside the source clip")
    stat = source.stat()
    return _frame_cached(str(source), stat.st_mtime_ns, stat.st_size,
                         int(timestamp * 1000)).copy()


def clip_source_time(properties: dict, project_time: float) -> float | None:
    start = float(properties.get("start", 0))
    source_in = float(properties.get("source_in", 0))
    source_out = float(properties.get("source_out", 0))
    speed = float(properties.get("speed", 1))
    if not all(map(math.isfinite, (start, source_in, source_out, speed))):
        raise ValueError("Video clip timing values must be finite")
    if start < 0 or source_in < 0 or source_out <= source_in or not 0.25 <= speed <= 4:
        raise ValueError("Invalid video clip start, trim or speed")
    if project_time < start:
        return None
    clip_time = source_in + (project_time - start) * speed
    if clip_time >= source_out - 0.0001:
        return None
    return clip_time
