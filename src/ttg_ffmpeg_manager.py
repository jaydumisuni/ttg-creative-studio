#!/usr/bin/env python3
"""FFmpeg detection and video-export pack handling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess


@dataclass
class FFmpegStatus:
    available: bool
    path: str | None
    version: str = ""
    message: str = ""


class FFmpegManager:
    def __init__(self, app_data_dir: str | Path | None = None) -> None:
        self.app_data_dir = Path(app_data_dir) if app_data_dir else Path.home() / "AppData" / "Local" / "TheTechGuyCreativeStudio"
        self.bin_dir = self.app_data_dir / "packs" / "video-export" / "bin"

    def candidates(self) -> list[str]:
        result: list[str] = []
        bundled = self.bin_dir / "ffmpeg.exe"
        if bundled.exists():
            result.append(str(bundled))
        found = shutil.which("ffmpeg")
        if found:
            result.append(found)
        return result

    def status(self) -> FFmpegStatus:
        for candidate in self.candidates():
            try:
                proc = subprocess.run([candidate, "-version"], capture_output=True, text=True, timeout=8)
                if proc.returncode == 0:
                    first = proc.stdout.splitlines()[0] if proc.stdout else "ffmpeg available"
                    return FFmpegStatus(True, candidate, first, "FFmpeg is ready.")
            except Exception:
                continue
        return FFmpegStatus(False, None, "", "Video Export Pack is required. Install FFmpeg or download the optional video-export pack.")

    def require(self) -> str:
        status = self.status()
        if not status.available or not status.path:
            raise RuntimeError(status.message)
        return status.path
