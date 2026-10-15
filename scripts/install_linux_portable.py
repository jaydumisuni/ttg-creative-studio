#!/usr/bin/env python3
"""Install a previously compiled Linux Creative Studio bundle to a user prefix."""
from __future__ import annotations
import argparse
import os
import shutil
import stat
from pathlib import Path


def install_bundle(bundle: Path, prefix: Path) -> Path:
    bundle = bundle.resolve(strict=True)
    executable = bundle / "TTG Creative Studio"
    if not executable.is_file():
        raise FileNotFoundError("Built Creative Studio executable missing")
    prefix = prefix.expanduser().resolve()
    target = prefix / "lib" / "ttg-creative-studio"
    if target.exists():
        raise FileExistsError("Refusing to overwrite existing installation")
    (prefix/"lib").mkdir(parents=True, exist_ok=True)
    (prefix/"bin").mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle, target, symlinks=False)
    program = target / "TTG Creative Studio"
    program.chmod(program.stat().st_mode | stat.S_IXUSR)
    launcher = prefix / "bin" / "ttg-creative-studio"
    launcher.write_text(
        '#!/bin/sh\nexec "' + str(program) + '" "$@"\n', encoding="utf-8"
    )
    launcher.chmod(0o755)
    return launcher


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("bundle", type=Path)
    p.add_argument("--prefix", type=Path,
                   default=Path.home()/".local"/"opt")
    args = p.parse_args()
    print(install_bundle(args.bundle, args.prefix))


if __name__ == "__main__":
    main()
