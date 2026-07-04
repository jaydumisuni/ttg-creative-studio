#!/usr/bin/env python3
"""Compile-gate review for TTG Creative Studio.

This is a reviewer proof step: every Python file in src/ and scripts/ must parse
before runtime workflow tests are trusted.
"""

from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [ROOT / "src", ROOT / "scripts"]


def main() -> int:
    failures: list[tuple[Path, str]] = []
    checked = 0
    for folder in TARGETS:
        for path in sorted(folder.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            checked += 1
            try:
                py_compile.compile(str(path), doraise=True)
            except py_compile.PyCompileError as exc:
                failures.append((path.relative_to(ROOT), str(exc)))
    print("TTG review compile gate")
    print("=======================")
    print(f"Python files checked: {checked}")
    if failures:
        print("Compile failures:")
        for path, error in failures:
            print(f"- {path}: {error}")
        return 1
    print("Compile gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
