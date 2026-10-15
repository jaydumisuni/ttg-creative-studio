"""Platform-correct persistent asset-pack location for Creative Studio.

Explicit app_data_dir supplied by the caller always overrides this default.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def creative_studio_data_dir() -> Path:
    """Return a user-owned application data directory without creating it."""
    home = Path.home()
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        base = Path(local) if local else home / "AppData" / "Local"
    elif sys.platform == "darwin":
        base = home / "Library" / "Application Support"
    else:
        xdg = os.environ.get("XDG_DATA_HOME", "")
        base = Path(xdg) if xdg and Path(xdg).is_absolute() else home / ".local" / "share"
    return base / "TheTechGuyCreativeStudio"
