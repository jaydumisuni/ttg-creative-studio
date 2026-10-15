#!/usr/bin/env python3
"""Bounded, deterministic frame/MP4 exports for TTG Creative Studio."""
from __future__ import annotations

import math
import os
from pathlib import Path
import subprocess
import tempfile

from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_ffmpeg_manager import FFmpegManager
from ttg_project_schema import TTGProject
from ttg_timeline_engine import TimelineEngine


class MotionExporter:
    def __init__(self, context: RenderContext):
        self.context = context
        self.timeline = TimelineEngine()

    def render_frame(self, project: TTGProject, time: float):
        animated = TTGProject(
            version=project.version, project_type=project.project_type,
            name=project.name, canvas=project.canvas, brand=project.brand,
            assets=project.assets, audio_markers=project.audio_markers,
            export=project.export,
        )
        animated.layers = [self.timeline.apply_to_layer(layer, time) for layer in project.layers]
        return CanvasRenderer(self.context).render(animated, time=time)

    @staticmethod
    def _frame_total(project: TTGProject, limit_frames: int | None) -> int:
        duration, fps = project.canvas.duration, project.canvas.fps
        if not math.isfinite(duration) or not (0.1 <= duration <= 600):
            raise ValueError("Duration must be between 0.1 and 600 seconds")
        if not (1 <= fps <= 60):
            raise ValueError("FPS must be 1–60")
        count = int(math.ceil(duration * fps))
        if limit_frames is not None:
            if limit_frames < 1:
                raise ValueError("Frame limit must be positive")
            count = min(count, limit_frames)
        if count > 18_000 or project.canvas.width*project.canvas.height > 16_000_000:
            raise ValueError("Export exceeds bounded frame or pixel budget")
        return count

    def export_frames(self, project: TTGProject, output_dir: str | Path,
                      limit_frames: int | None = None) -> list[Path]:
        total = self._frame_total(project, limit_frames)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        frames = []
        for index in range(total):
            frame = self.render_frame(project, index/project.canvas.fps).convert("RGB")
            target = output_dir/f"frame_{index:05d}.jpg"
            frame.save(target, quality=92)
            frames.append(target)
        return frames

    def _audio_inputs(self, project: TTGProject) -> tuple[list[str], list[str], str | None]:
        args: list[str] = []
        filters: list[str] = []
        refs = []
        for index, marker in enumerate(project.audio_markers):
            if index >= 8:
                raise ValueError("Maximum 8 audio tracks per export")
            if "path" not in marker:
                continue  # non-file beat/scene audio markers are metadata.
            path = self.context.resolve_asset(str(marker["path"]))
            if not path.is_file():
                raise FileNotFoundError(f"Missing audio file: {path}")
            start = float(marker.get("start", 0))
            duration = float(marker.get("duration", project.canvas.duration-start))
            volume = float(marker.get("volume", 1))
            if (not all(math.isfinite(x) for x in (start,duration,volume))
                    or start < 0 or duration <= 0 or not (0 <= volume <= 3)
                    or start >= project.canvas.duration):
                raise ValueError("Invalid audio start, duration or volume")
            args += ["-i", str(path)]
            delay_ms = int(start*1000)
            filters.append(
                f"[{len(refs)+1}:a]atrim=duration={duration:.3f},"
                f"asetpts=PTS-STARTPTS,volume={volume:.3f},"
                f"adelay={delay_ms}:all=1[a{index}]"
            )
            refs.append(f"[a{index}]")
        if not refs:
            return args, filters, None
        filters.append(
            "".join(refs)+f"amix=inputs={len(refs)}:duration=longest:normalize=0,"
            "aresample=async=1[aout]"
        )
        return args, filters, "[aout]"

    def export_mp4(self, project: TTGProject, output_path: str | Path,
                   work_dir: str | Path) -> Path:
        total = self._frame_total(project, None)
        ffmpeg = FFmpegManager().require()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        # A unique frame directory prevents stale frames contaminating exports.
        with tempfile.TemporaryDirectory(prefix="ttg-render-",dir=work_dir) as tmp:
            frames_dir = Path(tmp)
            written = self.export_frames(project, frames_dir)
            if len(written) != total:
                raise RuntimeError("Incomplete frame export")
            audio_args, filters, audio_label = self._audio_inputs(project)
            cmd = [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-framerate", str(project.canvas.fps),
                "-i", str(frames_dir/"frame_%05d.jpg"),
                *audio_args,
            ]
            if filters:
                # Audio is permitted to end before the animation. -shortest
                # silently truncated the entire video to the shortest audio
                # clip. Keep the animation at its authored frame duration;
                # -t caps long audio, while -frames:v caps visual frames.
                cmd += ["-filter_complex", ";".join(filters), "-map", "0:v",
                        "-map", audio_label or "[aout]", "-c:a", "aac",
                        "-b:a", "160k",
                        "-t", f"{total/project.canvas.fps:.6f}"]
            # Encode into a *different* filename on the destination volume.
            # An interrupted FFmpeg job must never corrupt the prior export.
            fd, temporary_name = tempfile.mkstemp(
                prefix=f".{output_path.stem}-", suffix=".mp4",
                dir=output_path.parent,
            )
            os.close(fd)
            temporary_path = Path(temporary_name)
            try:
                cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-r", str(project.canvas.fps), "-frames:v", str(total),
                        "-movflags", "+faststart", str(temporary_path)]
                subprocess.run(cmd, check=True, timeout=max(120, total*3))
                if temporary_path.stat().st_size == 0:
                    raise RuntimeError("FFmpeg exited without producing an MP4")
                # Flush the encoded file before publishing its name.
                with temporary_path.open("rb") as handle:
                    os.fsync(handle.fileno())
                os.replace(temporary_path, output_path)
            finally:
                temporary_path.unlink(missing_ok=True)
        return output_path
