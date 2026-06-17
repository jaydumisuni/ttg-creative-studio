#!/usr/bin/env python3
"""Motion preview/export for TTG Creative Studio."""

from __future__ import annotations

from pathlib import Path
import subprocess

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
            version=project.version,
            project_type=project.project_type,
            name=project.name,
            canvas=project.canvas,
            brand=project.brand,
            assets=project.assets,
            audio_markers=project.audio_markers,
            export=project.export,
        )
        animated.layers = [self.timeline.apply_to_layer(layer, time) for layer in project.layers]
        return CanvasRenderer(self.context).render(animated, time=time)

    def export_frames(self, project: TTGProject, output_dir: str | Path, limit_frames: int | None = None) -> list[Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        total = int(project.canvas.duration * project.canvas.fps)
        if limit_frames is not None:
            total = min(total, limit_frames)
        result = []
        for index in range(total):
            time = index / project.canvas.fps
            frame = self.render_frame(project, time).convert("RGB")
            path = output_dir / f"frame_{index:05d}.jpg"
            frame.save(path, quality=92)
            result.append(path)
        return result

    def export_mp4(self, project: TTGProject, output_path: str | Path, work_dir: str | Path) -> Path:
        ffmpeg = FFmpegManager().require()
        work_dir = Path(work_dir)
        frames_dir = work_dir / "frames"
        self.export_frames(project, frames_dir)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            ffmpeg,
            "-y",
            "-framerate",
            str(project.canvas.fps),
            "-i",
            str(frames_dir / "frame_%05d.jpg"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(project.canvas.fps),
            str(output_path),
        ], check=True)
        return output_path
