"""LightCraft developed-RAW to TTG editable image handoff.

Original camera RAW is never decoded, changed, renamed or silently replaced.
The importer verifies a real PNG render and source hashes. Actual RAW
development requires a user-selected installed lightcraft-cli executable;
no executable or pretrained model is downloaded or implicitly invoked.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

from PIL import Image
from ttg_project_schema import Asset, CanvasSpec, Layer, TTGProject

RAW_SUFFIXES = frozenset({
    ".dng", ".cr2", ".cr3", ".arw", ".nef",
    ".raf", ".rw2", ".orf", ".pef", ".srw",
})
MAX_RAW_BYTES = 300 * 1024 * 1024
MAX_PNG_BYTES = 64 * 1024 * 1024
MAX_PIXELS = 16_000_000


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _inspect_dng_ifd0(source: Path, file_bytes: int) -> dict:
    """Bounded TIFF IFD0/DNGVersion inspection, not a RAW demosaic.

    A TIFF magic prefix alone is not evidence that a .dng is a DNG.
    Validate the declared directory and image dimensions before admitting a
    developed external PNG as originating from this labeled file.
    """
    with source.open("rb") as stream:
        header=stream.read(8)
        endian = "<" if header[:2] == b"II" else ">" if header[:2] == b"MM" else None
        if endian is None or header[2:4] != struct.pack(endian+"H",42):
            raise ValueError("DNG requires classic TIFF byte order and magic")
        offset = struct.unpack(endian+"I",header[4:8])[0]
        if offset < 8 or offset > file_bytes-2:
            raise ValueError("DNG first IFD points outside source file")
        stream.seek(offset)
        count_data=stream.read(2)
        if len(count_data)!=2:
            raise ValueError("DNG IFD count is truncated")
        count=struct.unpack(endian+"H",count_data)[0]
        if not 3 <= count <= 1024 or offset+2+count*12+4 > file_bytes:
            raise ValueError("DNG IFD entry budget or boundary invalid")
        raw=stream.read(count*12+4)
        if len(raw)!=count*12+4:
            raise ValueError("DNG IFD entries truncated")
        tags={}
        for index in range(count):
            tag,kind,num,value=struct.unpack_from(endian+"HHII",raw,index*12)
            if tag in tags:
                raise ValueError("DNG duplicate IFD tag")
            if tag in (256,257,50706):
                tags[tag]=(kind,num,value,raw[index*12+8:index*12+12])
        if 50706 not in tags:
            raise ValueError("DNGVersion TIFF tag 50706 missing")
        kind,num,_,inline=tags[50706]
        if kind!=1 or num!=4 or inline[0]!=1 or inline[1]>7:
            raise ValueError("Unsupported or malformed DNGVersion")
        dims=[]
        for tag in (256,257):
            if tag not in tags:
                raise ValueError("DNG IFD lacks source image dimensions")
            kind,num,value,inline=tags[tag]
            if num!=1 or kind not in (3,4):
                raise ValueError("DNG image dimension has unsupported TIFF type")
            n=struct.unpack(endian+"H",inline[:2])[0] if kind==3 else value
            if not 1 <= n <= 100000:
                raise ValueError("DNG image dimension outside validity budget")
            dims.append(n)
        if dims[0]*dims[1] > 150_000_000:
            raise ValueError("DNG image pixel dimensions outside bound")
        return {
            "structural_level":"dng_tiff_ifd0", "tiff_byte_order": "II" if endian=="<" else "MM",
            "dng_version":list(tags[50706][3]),
            "declared_dimensions":dims, "first_ifd_offset":offset,
            "first_ifd_entries":count, "raw_pixel_data_decoded":False,
        }


def _validate_raw(source: Path) -> dict:
    if source.is_symlink() or not source.is_file() or source.suffix.lower() not in RAW_SUFFIXES:
        raise ValueError("Expected a real, non-symlink camera RAW file")
    size = source.stat().st_size
    if not 16 <= size <= MAX_RAW_BYTES:
        raise ValueError("RAW original outside supported size bounds")
    with source.open("rb") as handle:
        prefix = handle.read(24)
    ext = source.suffix.lower()
    tiff = prefix[:4] in (b"II*\x00", b"MM\x00*")
    signatures = {
        ".dng": tiff, ".cr2": tiff, ".arw": tiff, ".nef": tiff,
        ".pef": tiff, ".srw": tiff,
        ".cr3": prefix[4:8] == b"ftyp" and (b"crx" in prefix[:24] or b"CR3" in prefix[:24]),
        ".raf": prefix.startswith(b"FUJIFILMCCD-RAW"),
        ".rw2": prefix.startswith(b"IIU\x00"),
        ".orf": prefix[:4] in (b"IIRO", b"MMOR"),
    }
    if not signatures[ext]:
        raise ValueError("RAW header does not match claimed camera format")
    inspected = (_inspect_dng_ifd0(source,size) if ext==".dng" else {
        "structural_level":"format_magic_only", "raw_pixel_data_decoded":False,
    })
    return {"sha256": _digest(source), "bytes": size,
            "suffix": ext, "raw_structural_evidence": inspected}


def _validate_png(preview: Path) -> dict:
    if preview.is_symlink() or not preview.is_file() or preview.suffix.lower() != ".png":
        raise ValueError("Developed asset must be an actual PNG file")
    if not 0 < preview.stat().st_size <= MAX_PNG_BYTES:
        raise ValueError("Developed PNG exceeds byte limit")
    with Image.open(preview) as image:
        if image.format != "PNG" or image.width * image.height > MAX_PIXELS:
            raise ValueError("Rendered PNG exceeds pixel limit")
        if image.mode not in ("RGB", "RGBA"):
            raise ValueError("Rendered PNG must be RGB or RGBA, not an unreviewed color model")
        image.load()
        return {
            "sha256": _digest(preview),
            "bytes": preview.stat().st_size,
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "icc_embedded": bool(image.info.get("icc_profile")),
        }


def import_developed_raw(
    raw_path: str | Path,
    developed_png: str | Path,
    output_project: str | Path,
    *,
    developer: str = "user-supplied-render",
    lightcraft_cli_sha256: str | None = None,
) -> dict:
    """Admit verified rendered pixels as an editable Studio image layer.

    A file digest verifies bytes, not that the donor performed a correct
    demosaic or accurate color calibration. Those are separate qualifications.
    """
    source, preview, output = map(Path, (raw_path, developed_png, output_project))
    if not output.name.endswith(".ttgstudio.json"):
        raise ValueError("Output must be a new .ttgstudio.json project")
    if output.exists() or output.is_symlink():
        raise FileExistsError("Refuse to replace an existing Studio project")
    if not isinstance(developer, str) or not 1 <= len(developer) <= 80:
        raise ValueError("Developer identity must be explicit")
    original = _validate_raw(source)
    rendered = _validate_png(preview)
    directory = output.parent / (output.name.removesuffix(".ttgstudio.json") + "_raw_assets")
    if directory.exists() or directory.is_symlink():
        raise FileExistsError("Refuse to overwrite existing rendered asset directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=f".{directory.name}-", dir=output.parent))
    published = False
    try:
        render_path = temp / "developed.png"
        shutil.copyfile(preview, render_path)
        if _digest(render_path) != rendered["sha256"]:
            raise ValueError("Rendered image changed during intake")
        project = TTGProject(name=f"{source.stem} — LightCraft developed image", project_type="image")
        project.canvas = CanvasSpec(
            width=rendered["width"], height=rendered["height"], background="#00000000"
        )
        rel = f"{directory.name}/developed.png"
        project.assets = [
            Asset(id="lightcraft_developed_preview", kind="image", name=source.name,
                  path=rel, sha256=rendered["sha256"], required=True)
        ]
        project.layers = [
            Layer(id="lightcraft_editable_layer", type="image", name=source.stem,
                  properties={"path": rel, "source_kind": "external_raw_development"})
        ]
        project.export["lightcraft_raw_handoff"] = {
            "format": "ttg.studio.lightcraft-developed-raw.v1",
            "raw_source_path": str(source.resolve()),
            "raw_source_sha256": original["sha256"],
            "raw_source_bytes": original["bytes"],
            "raw_extension": original["suffix"],
            "raw_structural_evidence": original["raw_structural_evidence"],
            "rendered_png_sha256": rendered["sha256"],
            "rendered_dimensions": [rendered["width"], rendered["height"]],
            "rendered_mode": rendered["mode"],
            "embedded_icc_profile": rendered["icc_embedded"],
            "developer_label": developer,
            "lightcraft_executable_sha256": lightcraft_cli_sha256,
            "selected_executable_invoked": lightcraft_cli_sha256 is not None,
            "lightcraft_vendor_binary_identity_verified": False,
            "external_raw_preserved": True,
            "raw_demosaic_validated": False,
            "color_accuracy_independently_validated": False,
        }
        os.replace(temp, directory)
        published = True
        if output.exists() or output.is_symlink():
            raise FileExistsError("Project output appeared while staging")
        project.save(output)
    except BaseException:
        if published:
            shutil.rmtree(directory)
        raise
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return {
        "format": "lightcraft_developed_raw",
        "output": str(output),
        "original_raw_sha256": original["sha256"],
        "raw_structural_level": original["raw_structural_evidence"]["structural_level"],
        "rendered_png_sha256": rendered["sha256"],
        "project_sha256": _digest(output),
        "actual_raw_decode_certified": False,
        "external_raw_preserved": True,
    }


def develop_with_lightcraft(
    raw_path: str | Path,
    output_project: str | Path,
    *,
    lightcraft_cli: str | Path,
    exposure: float | None = None,
) -> dict:
    """Run the existing, explicitly selected offline LightCraft CLI once."""
    source = Path(raw_path)
    original = _validate_raw(source)
    binary = Path(lightcraft_cli)
    if binary.is_symlink() or not binary.is_file():
        raise FileNotFoundError("Install/select an actual LightCraft CLI executable first")
    if not os.access(binary, os.X_OK):
        raise PermissionError("Selected LightCraft CLI is not executable")
    exe_digest = _digest(binary)
    opts = []
    if exposure is not None:
        if isinstance(exposure, bool) or not isinstance(exposure, (float, int)) or not -5 <= float(exposure) <= 5:
            raise ValueError("Exposure must be a finite value in [-5, 5]")
        opts = ["--set", f"light.exposure={float(exposure):.4f}"]
    with tempfile.TemporaryDirectory(prefix="ttg-lightcraft-raw-") as staging:
        png = Path(staging) / "developed.png"
        argv = [str(binary.resolve()), "render", str(source.resolve()), "-o", str(png), *opts]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=180,
                                shell=False, cwd=str(source.resolve().parent))
        if result.returncode:
            raise RuntimeError("LightCraft CLI development failed: " + result.stderr[-700:])
        _validate_png(png)
        if _digest(source) != original["sha256"]:
            raise RuntimeError("RAW original changed during external development")
        return import_developed_raw(
            source, png, output_project,
            developer="lightcraft-cli render",
            lightcraft_cli_sha256=exe_digest,
        )
