"""Bounded PhotoCraft/OpenRaster layer interchange for the existing TTG editor.

OpenRaster is used by PhotoCraft and other image editors. This bridge is a
native Studio codec, NOT a claim to import PSD/PSB or all PhotoCraft effects.
The original .ttgstudio project and input .ora are never overwritten.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from io import BytesIO
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from PIL import Image, ImageColor

from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_project_schema import CanvasSpec, Layer, TTGProject, Transform

MAX_CANVAS_PIXELS = 4_000_000
MAX_LAYERS = 128
MAX_ARCHIVE_BYTES = 160 * 1024 * 1024
MAX_LAYER_BYTES = 12 * 1024 * 1024
SUPPORTED = {"normal": "svg:src-over", "multiply": "svg:multiply", "screen": "svg:screen"}
INVERTED = {v: k for k, v in SUPPORTED.items()}
MIME = b"image/openraster"


@dataclass(frozen=True)
class InterchangeReceipt:
    source_format: str
    output: str
    layers: int
    sha256: str
    warnings: tuple[str, ...] = ()


def _read_png(data: bytes, canvas: tuple[int, int]) -> Image.Image:
    if len(data) > MAX_LAYER_BYTES:
        raise ValueError("OpenRaster layer PNG exceeds 12 MiB")
    with Image.open(BytesIO(data)) as handle:
        if handle.format != "PNG" or handle.width * handle.height > MAX_CANVAS_PIXELS:
            raise ValueError("Invalid or oversized OpenRaster layer PNG")
        if handle.width > canvas[0] or handle.height > canvas[1]:
            raise ValueError("OpenRaster layer exceeds canvas bounds")
        image = handle.convert("RGBA")
        image.load()
        return image


def _png(image: Image.Image) -> bytes:
    out = BytesIO()
    image.save(out, "PNG")
    payload = out.getvalue()
    if len(payload) > MAX_LAYER_BYTES:
        raise ValueError("Rendered OpenRaster layer exceeds byte limit")
    return payload


def _archive_member(name: str) -> None:
    p = PurePosixPath(name)
    if (not name.startswith("data/") or p.suffix.lower() != ".png"
            or p.is_absolute() or ".." in p.parts or "\\" in name
            or len(p.parts) != 2):
        raise ValueError("Unsupported or unsafe OpenRaster layer path")


def _project_dims(project: TTGProject) -> tuple[int, int]:
    width, height = int(project.canvas.width), int(project.canvas.height)
    if not (0 < width <= 4096 and 0 < height <= 4096
            and width * height <= MAX_CANVAS_PIXELS):
        raise ValueError("OpenRaster canvas exceeds bounded dimensions")
    return width, height


def export_openraster(
    project: TTGProject,
    output: str | Path,
    *,
    project_root: str | Path,
    time: float = 0.0,
) -> InterchangeReceipt:
    """Rasterize individual supported TTG layers; preserve order/alpha/blend.

    Unsupported dynamic layer kinds are rejected. Rendered text, effects and
    transforms are explicitly a snapshot: their TTG edit parameters are NOT
    represented by OpenRaster and must remain in the native source project.
    """
    dest = Path(output)
    if dest.suffix.lower() != ".ora" or dest.exists() or dest.is_symlink():
        raise ValueError("OpenRaster output must be a new .ora file")
    size = _project_dims(project)
    if len(project.layers) > MAX_LAYERS - 1:
        raise ValueError("Too many layers for bounded OpenRaster interchange")
    source = Path(project_root)
    renderer = CanvasRenderer(RenderContext(project_root=source))
    warnings: list[str] = []
    rendered: list[tuple[Layer, Image.Image]] = []
    background = ImageColor.getcolor(project.canvas.background, "RGBA")
    if background[3]:
        rendered.append((Layer(id="ttg_background", type="image",
                              name="TTG Canvas Background"),
                         Image.new("RGBA", size, background)))
    for layer in project.layers:
        if layer.type not in {"image", "shape", "text", "text3d"}:
            raise ValueError("OpenRaster cannot faithfully exchange layer kind " + layer.type)
        mode = layer.properties.get("blend_mode", "normal")
        if mode not in SUPPORTED:
            raise ValueError("Unsupported OpenRaster blending, not flattening: " + str(mode))
        if layer.type != "image" or layer.effects or layer.keyframes or layer.transform.rotation_z:
            warnings.append(f"{layer.id}: rendered snapshot; preserve TTG source for edits")
        if layer.type == "image":
            name = layer.properties.get("path") or layer.properties.get("asset_path")
            if not isinstance(name, str) or not name or not renderer.context.resolve_asset(name).is_file():
                raise FileNotFoundError(f"Image layer {layer.id} source unavailable")
        frame = Image.new("RGBA", size, (0, 0, 0, 0))
        renderer._draw_layer(frame, layer, time=time)
        rendered.append((layer, frame))
    if not rendered:
        raise ValueError("OpenRaster requires at least one rendered layer")

    document = ET.Element("image", {
        "w": str(size[0]), "h": str(size[1]),
        "name": project.name[:100], "version": "0.0.6",
    })
    stack = ET.SubElement(document, "stack")
    data: list[tuple[str, bytes]] = []
    # OpenRaster stacks top-to-bottom, TTG projects bottom-to-top.
    for index, (layer, image) in enumerate(reversed(rendered)):
        key = f"data/layer-{index:04d}.png"
        data.append((key, _png(image)))
        # Per-layer RGBA already includes opacity and effects; avoid applying
        # opacity twice in PhotoCraft.
        mode = (layer.properties.get("blend_mode", "normal")
                if layer.id != "ttg_background" else "normal")
        ET.SubElement(stack, "layer", {
            "name": layer.name[:150], "src": key, "x": "0", "y": "0",
            "opacity": "1", "visibility": "visible" if layer.visible else "hidden",
            "composite-op": SUPPORTED[mode],
        })
    xml = ET.tostring(document, encoding="utf-8", xml_declaration=True)
    if len(xml) > 1024 * 1024:
        raise ValueError("OpenRaster stack too large")
    # Preserve native alpha/blend semantics in the preview using TTG rendering.
    merged = renderer.render(project, time=time)
    preview = _png(merged)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, staging = tempfile.mkstemp(prefix=f".{dest.stem}-", suffix=".ora.tmp",
                                  dir=dest.parent)
    os.close(fd)
    try:
        with ZipFile(staging, "w", allowZip64=False) as archive:
            archive.writestr("mimetype", MIME, compress_type=ZIP_STORED)
            archive.writestr("stack.xml", xml, compress_type=ZIP_DEFLATED)
            for key, payload in data:
                archive.writestr(key, payload, compress_type=ZIP_DEFLATED)
            archive.writestr("mergedimage.png", preview, compress_type=ZIP_DEFLATED)
        if Path(staging).stat().st_size > MAX_ARCHIVE_BYTES:
            raise ValueError("OpenRaster output exceeds size limit")
        if dest.exists():
            raise FileExistsError("OpenRaster output appeared during export")
        os.replace(staging, dest)
    finally:
        Path(staging).unlink(missing_ok=True)
    return InterchangeReceipt("openraster", str(dest), len(rendered),
                              hashlib.sha256(dest.read_bytes()).hexdigest(),
                              tuple(warnings))


def import_openraster(input_ora: str | Path, output_project: str | Path) -> InterchangeReceipt:
    """Import actual editable OpenRaster pixel layers as TTG image layers.

    Unsupported nested groups and masks fail explicitly; no flattening or
    unsupported Photoshop capability is implied. Creates an asset directory
    and new canonical .ttgstudio JSON while preserving both originals.
    """
    source, dest = Path(input_ora), Path(output_project)
    if source.suffix.lower() != ".ora" or dest.suffix.lower() not in {".json", ".ttgstudio"}:
        raise ValueError("Expected .ora input and a .json/.ttgstudio output")
    if dest.exists() or dest.is_symlink():
        raise FileExistsError("Refuse overwrite of existing TTG project")
    if not source.is_file() or source.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("Missing or oversized OpenRaster source")
    if dest.parent.resolve() == source.resolve().parent and dest.stem == source.stem:
        pass
    dest.parent.mkdir(parents=True, exist_ok=True)
    assets_dir = dest.parent / (dest.stem + "_assets")
    if assets_dir.exists() or assets_dir.is_symlink():
        raise FileExistsError("Refuse overwrite of existing asset directory")
    images: list[tuple[Layer, bytes]] = []
    with ZipFile(source) as archive:
        members = archive.infolist()
        if len(members) > MAX_LAYERS + 8:
            raise ValueError("OpenRaster archive exceeds entry budget")
        byname = {i.filename: i for i in members}
        if len(byname) != len(members):
            raise ValueError("OpenRaster duplicate filenames forbidden")
        if sum(i.file_size for i in members) > MAX_ARCHIVE_BYTES:
            raise ValueError("Uncompressed OpenRaster exceeds budget")
        if byname.get("mimetype") is None or archive.read("mimetype") != MIME:
            raise ValueError("Not a valid OpenRaster archive")
        if "stack.xml" not in byname or byname["stack.xml"].file_size > 1024 * 1024:
            raise ValueError("Missing or oversized OpenRaster stack.xml")
        xml = archive.read("stack.xml")
        if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
            raise ValueError("OpenRaster XML declarations forbidden")
        tree = ET.fromstring(xml)
        if tree.tag != "image":
            raise ValueError("OpenRaster image root required")
        width, height = int(tree.get("w", "0")), int(tree.get("h", "0"))
        if not 0 < width <= 4096 or not 0 < height <= 4096 or width * height > MAX_CANVAS_PIXELS:
            raise ValueError("OpenRaster dimensions outside supported bounds")
        stacks = list(tree)
        if len(stacks) != 1 or stacks[0].tag != "stack":
            raise ValueError("Unsupported OpenRaster stack structure")
        if len(stacks[0]) > MAX_LAYERS:
            raise ValueError("OpenRaster layer count exceeds bound")
        for index, entry in enumerate(reversed(list(stacks[0]))):
            if entry.tag != "layer" or len(entry):
                raise ValueError("Nested groups/masks unsupported, refusing flatten")
            key = entry.get("src", "")
            _archive_member(key)
            if key not in byname or byname[key].file_size > MAX_LAYER_BYTES:
                raise ValueError("Missing or oversized OpenRaster layer image")
            op = entry.get("composite-op", "svg:src-over")
            if op not in INVERTED:
                raise ValueError("Unsupported OpenRaster blend mode: " + op)
            opacity = float(entry.get("opacity", "1"))
            if not 0 <= opacity <= 1:
                raise ValueError("OpenRaster opacity out of range")
            x, y = int(entry.get("x", "0")), int(entry.get("y", "0"))
            image = _read_png(archive.read(key), (width, height))
            # Pixel input is left intact; translate via native image transform.
            raw = _png(image)
            target = f"layer-{index:04d}.png"
            layer = Layer(
                id=f"ora_{index:04d}", type="image",
                name=entry.get("name", f"Layer {index}")[:150],
                visible=entry.get("visibility", "visible") == "visible",
                transform=Transform(x=x, y=y, opacity=opacity),
                properties={
                    "path": f"{assets_dir.name}/{target}",
                    "blend_mode": INVERTED[op],
                    "source_format": "openraster",
                },
            )
            images.append((layer, raw))
    project = TTGProject(name=tree.get("name", source.stem)[:100],
                         project_type="image")
    project.canvas = CanvasSpec(width=width, height=height, background="#00000000")
    project.layers = [layer for layer, _ in images]
    temporary = Path(tempfile.mkdtemp(prefix=f".{dest.stem}-", dir=dest.parent))
    published_assets = False
    try:
        for index, (_, payload) in enumerate(images):
            (temporary / f"layer-{index:04d}.png").write_bytes(payload)
        os.replace(temporary, assets_dir)
        published_assets = True
        project.save(dest)
    except BaseException:
        if published_assets:
            shutil.rmtree(assets_dir)
        raise
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return InterchangeReceipt("openraster", str(dest), len(images),
                              hashlib.sha256(dest.read_bytes()).hexdigest())
