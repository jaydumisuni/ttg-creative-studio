#!/usr/bin/env python3
"""
Generate a Windows .ico file from the single logo source image.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


def main() -> int:
    project_root = Path(__file__).resolve().parent
    source = project_root / "resources" / "logo.png"
    target = project_root / "build_icon.ico"

    if not source.exists():
        raise FileNotFoundError(source)

    image = Image.open(source).convert("RGBA")

    canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    fitted = ImageOps.contain(image, (1024, 1024), Image.Resampling.LANCZOS)
    offset = ((1024 - fitted.width) // 2, (1024 - fitted.height) // 2)
    canvas.alpha_composite(fitted, offset)

    canvas.save(
        target,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
