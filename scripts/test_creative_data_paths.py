"""Regression: default pack paths follow each OS, not Windows on Linux."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BASE))

from ttg_studio_paths import creative_studio_data_dir
from ttg_ffmpeg_manager import FFmpegManager
from ttg_pack_downloader import PackDownloader
from ttg_pack_status import PackStatusReader


def run():
    with TemporaryDirectory() as folder:
        directory = Path(folder)
        with patch.dict(os.environ, {"XDG_DATA_HOME": str(directory / "xdg")}, clear=False):
            with patch("ttg_studio_paths.sys.platform", "linux"):
                expected = directory / "xdg" / "TheTechGuyCreativeStudio"
                assert creative_studio_data_dir() == expected
                assert FFmpegManager().app_data_dir == expected
                assert PackStatusReader(directory).app_data_dir == expected
                downloader = PackDownloader(directory)
                assert downloader.app_data_dir == expected
                assert (expected / "manifests").is_dir()
                assert (expected / "packs").is_dir()
        with patch.dict(os.environ, {"XDG_DATA_HOME": "relative/not/allowed"}, clear=False):
            with patch("ttg_studio_paths.sys.platform", "linux"):
                assert creative_studio_data_dir() == Path.home() / ".local" / "share" / "TheTechGuyCreativeStudio"
        override = directory / "explicit"
        assert FFmpegManager(override).app_data_dir == override
        assert PackStatusReader(directory, override).app_data_dir == override
        assert PackDownloader(directory, override).app_data_dir == override
        assert not (directory / "AppData").exists()
    print("CREATIVE_STUDIO_XDG_PATH_TESTS_PASS")


if __name__ == "__main__":
    run()
