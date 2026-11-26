"""Synthetic *structural* DNG fixture. No genuine camera pixels or demosaic proof."""
from __future__ import annotations
from pathlib import Path
import struct


def write_synthetic_dng(path: Path, *, big_endian: bool = False) -> None:
    endian = ">" if big_endian else "<"
    marker = b"MM" if big_endian else b"II"
    header = marker + struct.pack(endian + "HI", 42, 8)
    entries = [
        struct.pack(endian + "HHII", 256, 4, 1, 32),
        struct.pack(endian + "HHII", 257, 4, 1, 24),
        struct.pack(endian + "HHI", 50706, 1, 4) + b"\x01\x04\x00\x00",
    ]
    ifd = struct.pack(endian + "H", len(entries)) + b"".join(entries)
    data = header + ifd + struct.pack(endian + "I", 0) + b"synthetic-not-a-camera-payload"
    path.write_bytes(data)
