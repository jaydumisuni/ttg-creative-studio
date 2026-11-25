"""MaterialCraft/TextureCraft exported PBR map intake into TTG Studio assets.

Consumes actual exported image maps, not unreviewed native .mcmat/.tcraft
graphs. All channel, normal convention and colour-space metadata is explicit.
The existing TTG project stays editable and original donor assets untouched.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile

from PIL import Image

from ttg_project_schema import Asset, TTGProject, Layer, CanvasSpec

MAPS = frozenset({
    "base_color", "normal", "roughness", "metallic", "ambient_occlusion",
    "height", "emissive", "opacity",
})
COLOR = {"base_color": "srgb", "emissive": "srgb"}
MAX_IMAGE = 16_000_000
MAX_MAP_SIZE = 48 * 1024 * 1024


def _validated_manifest(source: Path, manifest: dict) -> list[tuple[str, Path, str, str]]:
    if not isinstance(manifest, dict) or manifest.get("schema") != "ttg.studio.pbr-export-mapset.v1":
        raise ValueError("Explicit TTG PBR exported-mapset manifest required")
    if manifest.get("normal_y") not in {"opengl", "directx"}:
        raise ValueError("PBR normal map Y convention must be opengl or directx")
    channels = manifest.get("channels")
    if not isinstance(channels, dict) or not channels or len(channels) > len(MAPS):
        raise ValueError("PBR map channels must be a nonempty mapping")
    if any(k not in MAPS for k in channels):
        raise ValueError("Unknown PBR channel; refusing to guess")
    if not source.is_dir():
        raise FileNotFoundError("Exported map source directory missing")
    rows: list[tuple[str, Path, str, str]] = []
    dimensions = set()
    for channel, description in sorted(channels.items()):
        if not isinstance(description, dict):
            raise ValueError("PBR channel declaration required")
        name = description.get("path")
        if not isinstance(name, str):
            raise ValueError("PBR channel missing real map file")
        member = PurePosixPath(name)
        if (member.is_absolute() or ".." in member.parts or "\\" in name
                or len(member.parts) != 1 or member.suffix.lower() != ".png"):
            raise ValueError("PBR map must be a single relative PNG filename")
        file = source / name
        if file.is_symlink() or not file.is_file() or file.stat().st_size > MAX_MAP_SIZE:
            raise ValueError(f"PBR source {channel} is unavailable or too large")
        colorspace = description.get("colorspace")
        required = COLOR.get(channel, "linear")
        if colorspace != required:
            raise ValueError(f"PBR {channel} requires explicit {required} color space")
        with Image.open(file) as image:
            if image.format != "PNG" or image.width * image.height > MAX_IMAGE:
                raise ValueError("Unsupported or oversized PBR image")
            if image.width < 1 or image.height < 1:
                raise ValueError("Empty PBR map")
            image.verify()
            dimensions.add((image.width, image.height))
        hash_claim = description.get("sha256")
        actual = hashlib.sha256(file.read_bytes()).hexdigest()
        if not isinstance(hash_claim, str) or hash_claim != actual:
            raise ValueError(f"PBR {channel} SHA256 mismatch")
        rows.append((channel, file, colorspace, actual))
    if len(dimensions) != 1:
        raise ValueError("PBR export maps must have matched dimensions")
    return rows



def _preview_png_from_maps(directory: Path, channels: dict[str, dict], normal_y: str) -> tuple[bytes, tuple[int, int]]:
    """Render an actual bounded swatch with fixed light and per-map semantics.

    This is an image-editor preview of exported PBR maps, not a claim of
    UV-mapped/physically certified mesh output or a native MaterialCraft graph.
    """
    from io import BytesIO
    import math
    from PIL import Image

    if "base_color" not in channels:
        raise ValueError("A PBR swatch requires a base_color map")
    with Image.open(directory / "base_color.png") as source:
        width, height = source.size
    width = max(1, round(width * min(1., 256 / max(width, height))))
    height = max(1, round(height * min(1., 256 / max(width, height))))
    images = {}
    for channel in channels:
        with Image.open(directory / (channel + ".png")) as raw:
            images[channel] = raw.convert("RGBA").resize(
                (width, height), Image.Resampling.BILINEAR
            )
    px = {channel: image.load() for channel, image in images.items()}
    dest = Image.new("RGBA", (width, height))
    put = dest.load()
    lx, ly, lz = (-0.42, -0.38, 0.824)
    ll = math.sqrt(lx*lx + ly*ly + lz*lz)
    lx,ly,lz = lx/ll,ly/ll,lz/ll
    hx,hy,hz = lx,ly,lz+1.
    hl = math.sqrt(hx*hx + hy*hy + hz*hz)
    hx,hy,hz = hx/hl,hy/hl,hz/hl
    y_flip = -1 if normal_y == "directx" else 1
    for y in range(height):
        for x in range(width):
            base = px["base_color"][x,y]
            r,g,b = (v / 255. for v in base[:3])
            sample = px.get("normal")
            if sample is None:
                nx,ny,nz = 0.,0.,1.
            else:
                nr,ng,nb,_ = sample[x,y]
                nx,ny,nz = nr/127.5-1.,(ng/127.5-1.)*y_flip,nb/127.5-1.
                nl = max(1e-8,math.sqrt(nx*nx+ny*ny+nz*nz))
                nx,ny,nz = nx/nl,ny/nl,nz/nl
            diffuse = max(0., nx*lx+ny*ly+nz*lz)
            halfdot = max(0.,nx*hx+ny*hy+nz*hz)
            rough = px["roughness"][x,y][0]/255. if "roughness" in px else .5
            metal = px["metallic"][x,y][0]/255. if "metallic" in px else 0.
            ao = px["ambient_occlusion"][x,y][0]/255. if "ambient_occlusion" in px else 1.
            visibility = .17 + .78 * diffuse * ao
            specular = (halfdot ** (2. + (1. - rough) * 90.)) * (1.15 - .25*rough)
            emission = px["emissive"][x,y] if "emissive" in px else (0,0,0,0)
            opacity = px["opacity"][x,y][0] if "opacity" in px else base[3]
            vals=[]
            for i,col in enumerate((r,g,b)):
                f0 = .04*(1.-metal)+col*metal
                energy = (1.-metal)*col*visibility + f0*specular + emission[i]/255.*.25
                vals.append(max(0,min(255,round(255*energy))))
            put[x,y]=(*vals,opacity)
    buffer=BytesIO()
    dest.save(buffer,format="PNG")
    return buffer.getvalue(),(width,height)

def import_pbr_export_maps(
    source_dir: str | Path,
    manifest_path: str | Path,
    output_project: str | Path,
    *,
    material_name: str,
) -> dict:
    source, manifest_file, out = Path(source_dir), Path(manifest_path), Path(output_project)
    if not 1 <= len(material_name.strip()) <= 100:
        raise ValueError("Material name required")
    if out.exists() or out.is_symlink() or not out.name.endswith(".ttgstudio.json"):
        raise FileExistsError("PBR import requires new .ttgstudio.json output")
    if not manifest_file.is_file() or manifest_file.stat().st_size > 32_768:
        raise ValueError("Missing or oversized PBR manifest")
    declaration = json.loads(manifest_file.read_text(encoding="utf-8"))
    rows = _validated_manifest(source, declaration)
    out.parent.mkdir(parents=True, exist_ok=True)
    assets_dir = out.parent / (out.name.removesuffix(".ttgstudio.json") + "_pbr")
    if assets_dir.exists() or assets_dir.is_symlink():
        raise FileExistsError("Refuse overwrite of existing PBR assets")
    temp = Path(tempfile.mkdtemp(prefix=f".{assets_dir.name}-", dir=out.parent))
    published = False
    try:
        channels: dict[str, dict] = {}
        assets = []
        for channel, file, colorspace, digest in rows:
            dest_name = channel + ".png"
            shutil.copyfile(file, temp / dest_name)
            if hashlib.sha256((temp / dest_name).read_bytes()).hexdigest() != digest:
                raise ValueError("Copied PBR source changed unexpectedly")
            relative = f"{assets_dir.name}/{dest_name}"
            assets.append(Asset(id=f"pbr_{channel}", kind="material_texture",
                                name=f"{material_name}: {channel}",
                                path=relative, sha256=digest, required=True))
            channels[channel] = {
                "asset_id": f"pbr_{channel}", "path": relative,
                "colorspace": colorspace, "sha256": digest,
            }
        # A visible, editable image layer uses the exact downloaded map bytes;
        # the original channels remain independent and hash-identical.
        preview_bytes, preview_size = _preview_png_from_maps(
            temp, channels, declaration["normal_y"])
        (temp / "material-preview.png").write_bytes(preview_bytes)
        preview_path = f"{assets_dir.name}/material-preview.png"
        project = TTGProject(name=f"{material_name} — PBR asset set", project_type="mixed")
        project.canvas = CanvasSpec(
            width=preview_size[0], height=preview_size[1], background="#101018"
        )
        project.layers = [Layer(
            id="pbr_material_preview", type="image",
            name=f"{material_name}: PBR lit swatch",
            properties={
                "path": preview_path,
                "source_format": "pbr_export_mapset",
                "preview_kind": "fixed_light_normal_roughness_metallic",
            },
        )]
        project.assets = assets
        project.export["pbr_materials"] = [{
            "name": material_name,
            "normal_y": declaration["normal_y"],
            "channels": channels,
            "origin": "MaterialCraft/TextureCraft exported map files",
            "native_graph_imported": False,
            "swatch_preview_path": preview_path,
            "swatch_preview_sha256": hashlib.sha256(preview_bytes).hexdigest(),
            "swatch_render_semantics": "fixed_light_reference_only",
            "mesh_uv_shader_certified": False,
        }]
        os.replace(temp, assets_dir)
        published = True
        project.save(out)
    except BaseException:
        if published:
            shutil.rmtree(assets_dir)
        raise
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return {
        "format": "pbr_mapset",
        "output": str(out),
        "asset_count": len(assets),
        "asset_sha256": {asset.id: asset.sha256 for asset in assets},
        "project_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "native_material_graph_imported": False,
        "material_surface_render_verified": False,
        "fixed_light_swatch_rendered": True,
        "preview_sha256": hashlib.sha256(preview_bytes).hexdigest(),
    }
