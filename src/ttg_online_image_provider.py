"""Standalone Creative Studio online image generation and image-edit provider.

No local checkpoint is downloaded. Every billable request requires an
operator-level switch and separate per-request consent. Outputs are verified
as actual decoded pixels before becoming editable Studio assets.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import urllib.request

from PIL import Image, ImageOps
from ttg_online_video_provider import (
    VideoProviderError, NoRedirect, _json_request, _output_url,
    _token, _is_private_host, validate_public_https, PREDICTION,
)

# Image consent is separate from video consent to prevent cross-product approval reuse.
APPROVAL = "APPROVE_PAID_IMAGE_GENERATION"

IMAGE_MODELS = {
    "generate": "black-forest-labs/flux-schnell",
    "edit": "black-forest-labs/flux-kontext-pro",
    "inpaint": "black-forest-labs/flux-fill-pro",
}
# Existing Replicate transport; model-specific payloads are not interchangeable.
# Quality routes remain usage-billed and per-job consent gated.
GENERATION_PROFILES = {
    "fast": {"model": IMAGE_MODELS["generate"],
             "label": "Fast preview · FLUX Schnell"},
    "photoreal": {"model": "black-forest-labs/flux-2-pro",
                  "label": "Professional photography · FLUX.2 Pro"},
    "brand_pro": {"model": "google/nano-banana-pro",
                  "label": "Premium branded mockups · Nano Banana Pro"},
}

MAX_IMAGE_BYTES = 32 * 1024 * 1024
MAX_IMAGE_PIXELS = 28_000_000
# Replicate recommends inline data URI for small assets; larger ones must be
# hosted by a user-approved public HTTPS source instead.
MAX_INLINE_BYTES = 235_000
MAX_INLINE_PIXELS = 16_000_000


def inline_image_url(path: str | Path) -> str:
    """Explicit user-selected image for provider upload, without persistent copies."""
    source = Path(path).expanduser()
    if source.is_symlink() or not source.is_file():
        raise VideoProviderError("Inline image must be a regular selected local file")
    if source.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        raise VideoProviderError("Use a PNG, JPEG or WEBP local input image")
    if source.stat().st_size > MAX_INLINE_BYTES:
        raise VideoProviderError("Local image exceeds 235 KB: use an approved HTTPS URL instead")
    raw = source.read_bytes()
    if not 1 <= len(raw) <= MAX_INLINE_BYTES:
        raise VideoProviderError("Local image must be nonempty and at most 235 KB")
    try:
        with Image.open(io.BytesIO(raw)) as pic:
            if pic.format not in ("PNG", "JPEG", "WEBP") or pic.width * pic.height > MAX_INLINE_PIXELS:
                raise VideoProviderError("Invalid local image format or decoded dimensions")
            pic.verify()
    except (ValueError,OSError,Image.DecompressionBombError):
        raise VideoProviderError("Selected local image is not a valid bounded image") from None
    mime = "image/png" if source.suffix.lower()==".png" else (
        "image/webp" if source.suffix.lower()==".webp" else "image/jpeg"
    )
    return "data:" + mime + ";base64," + base64.b64encode(raw).decode("ascii")


def compact_reference_image(path: str | Path) -> dict:
    """Prepare a visually grounded model reference without sharing local paths.

    Some excellent photographs greatly exceed Studio's conservative inline
    transport bound. Downscale/encode ONLY the transmitted copy in memory,
    preserve the source unchanged, and return auditable dimensions/digests.
    This does not transmit anything or incur any usage charge.
    """
    source=Path(path).expanduser()
    if source.is_symlink() or not source.is_file():
        raise VideoProviderError("Select a regular local image reference")
    if source.suffix.lower() not in (".png",".jpg",".jpeg",".webp"):
        raise VideoProviderError("Reference must be PNG, JPEG or WebP")
    if source.stat().st_size>MAX_IMAGE_BYTES:
        raise VideoProviderError("Reference exceeds 32 MiB local file limit")
    raw=source.read_bytes()
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if (image.format not in ("PNG","JPEG","WEBP")
                or image.width*image.height > MAX_INLINE_PIXELS):
                raise ValueError("Reference dimensions unsupported")
            image.load()
            original=(image.width,image.height)
            alpha=image.mode in ("RGBA","LA") or ("transparency" in image.info)
            working=ImageOps.exif_transpose(image).convert("RGBA" if alpha else "RGB")
    except (OSError,ValueError,Image.DecompressionBombError):
        raise VideoProviderError("Reference is not a valid bounded image") from None
    original_sha=hashlib.sha256(raw).hexdigest()
    if len(raw)<=MAX_INLINE_BYTES:
        mime={"PNG":"image/png","JPEG":"image/jpeg","WEBP":"image/webp"}[image.format]
        return {
            "uri":"data:"+mime+";base64,"+base64.b64encode(raw).decode("ascii"),
            "source_sha256":original_sha,
            "source_dimensions":list(original),
            "transmitted_dimensions":list(original),
            "transmitted_bytes":len(raw),
            "reference_compressed":False,
        }
    for bound in (1280,1024,896,768,640,512):
        preview=working.copy()
        preview.thumbnail((bound,bound),Image.Resampling.LANCZOS)
        for quality in (75,58):
            stream=io.BytesIO()
            preview.save(stream,format="WEBP",quality=quality,method=0)
            encoded=stream.getvalue()
            if 0<len(encoded)<=MAX_INLINE_BYTES:
                return {
                    "uri":"data:image/webp;base64,"+base64.b64encode(encoded).decode("ascii"),
                    "source_sha256":original_sha,
                    "source_dimensions":list(original),
                    "transmitted_dimensions":list(preview.size),
                    "transmitted_bytes":len(encoded),
                    "reference_compressed":(encoded!=raw),
                }
    raise VideoProviderError("Unable to encode selected reference within 235 KB")


def build_generation_input(options:dict) -> tuple[str,dict]:
    """Provider-schema-aware request construction with optional visual reference.

    Pure and non-billable: callers can audit exact model and payload offline.
    """
    ratio=options.get("aspect_ratio","1:1")
    quality=options.get("quality","fast")
    if quality not in GENERATION_PROFILES:
        raise VideoProviderError("Unsupported quality profile")
    reference=options.get("reference_image")
    if reference:
        if quality=="fast":
            raise VideoProviderError("Fast preview does not support reference-guided generation")
        ref=image_input_uri(reference)
        ratios=("match_input_image","1:1","16:9","9:16","4:3","3:4","3:2","2:3")
        if ratio not in ratios:
            raise VideoProviderError("Unsupported referenced image aspect ratio")
    else:
        if ratio not in ("1:1","16:9","9:16","4:3","3:4","3:2","2:3"):
            raise VideoProviderError("Match-input ratio requires a selected reference image")
        ref=None
    # Fail on unrecognized inputs rather than silently dropping a reference.
    payload={"prompt":options["prompt"].strip(),"output_format":"png"}
    if quality=="fast":
        payload.update({"aspect_ratio":ratio,"num_outputs":1,"num_inference_steps":4})
    elif quality=="photoreal":
        payload.update({"aspect_ratio":ratio,"resolution":"2 MP",
                        "input_images":[ref] if ref else []})
    else:
        # Nano Banana Pro official schema has image_input, not input_images.
        # No allow_fallback_model field: it is NOT in the published schema;
        # identity is fixed by the endpoint itself.
        payload.update({"aspect_ratio":ratio,"resolution":"2K",
                        "image_input":[ref] if ref else []})
    return GENERATION_PROFILES[quality]["model"],payload


def image_input_uri(reference: str) -> str:
    """Accept only safe HTTPS references or bounded decoded, validated data URIs."""
    if not isinstance(reference, str) or not reference:
        raise VideoProviderError("Inpainting requires a valid image and a separate mask")
    if not reference.startswith("data:"):
        return validate_public_https(reference)
    try:
        header, encoded = reference.split(",", 1)
        if header not in ("data:image/png;base64", "data:image/jpeg;base64",
                          "data:image/webp;base64") or len(encoded)>MAX_INLINE_BYTES*2:
            raise ValueError("Invalid inline media declaration")
        raw = base64.b64decode(encoded,validate=True)
        if not raw or len(raw)>MAX_INLINE_BYTES:
            raise ValueError("Inline media exceeds safe bound")
        with Image.open(io.BytesIO(raw)) as pic:
            if pic.format not in ("PNG","WEBP","JPEG") or pic.width*pic.height>MAX_INLINE_PIXELS:
                raise ValueError("Invalid inline image")
            pic.verify()
    except (ValueError,OSError,Image.DecompressionBombError,binascii.Error):
        raise VideoProviderError("Inline image must be a bounded valid PNG, JPEG or WebP") from None
    return reference



def _inline_dimensions(uri: str) -> tuple[int,int] | None:
    if not uri.startswith("data:"):
        return None
    binary=base64.b64decode(uri.split(",",1)[1],validate=True)
    with Image.open(io.BytesIO(binary)) as pic:
        return pic.width,pic.height


def readiness() -> dict:
    return {
        "provider": "replicate",
        "state": ("configured" if os.environ.get("REPLICATE_API_TOKEN","").strip()
                 and os.environ.get("TTG_STUDIO_ENABLE_PAID_IMAGE") == "1"
                 else "billing_disabled" if os.environ.get("REPLICATE_API_TOKEN","").strip()
                 else "credentials_required"),
        "models": IMAGE_MODELS,
        "generation_profiles": GENERATION_PROFILES,
        "local_checkpoint_installed_by_studio": False,
        "local_model_download": "deferred_GT502_or_Spark",
        "pricing": {
            "generate": "https://replicate.com/black-forest-labs/flux-schnell",
            "photoreal": "https://replicate.com/black-forest-labs/flux-2-pro",
            "brand_pro": "https://replicate.com/google/nano-banana-pro",
            "edit": "https://replicate.com/black-forest-labs/flux-kontext-pro",
            "inpaint": "https://replicate.com/black-forest-labs/flux-fill-pro",
        },
    }


def _image_record(value: dict) -> dict:
    identifier = value.get("id")
    status = value.get("status")
    if not isinstance(identifier,str) or not PREDICTION.fullmatch(identifier):
        raise VideoProviderError("Invalid image prediction ID")
    if status not in ("starting","processing","succeeded","failed","canceled"):
        raise VideoProviderError("Unrecognized image provider status")
    output = None
    if status=="succeeded":
        urls = value.get("output")
        if isinstance(urls,list):
            if len(urls)!=1:
                raise VideoProviderError("Expected exactly one generated image")
            urls=urls[0]
        output=_output_url(urls)
    return {
        "provider":"replicate", "prediction_id":identifier, "status":status,
        "done":status in ("succeeded","failed","canceled"),
        "output_url":output, "local_model_downloaded":False,
    }


def submit_image(options:dict) -> dict:
    if not isinstance(options,dict):
        raise VideoProviderError("Invalid image generation settings")
    if options.get("paid_approval") != APPROVAL:
        raise VideoProviderError("Paid image generation requires explicit approval of this request")
    operation=options.get("operation","generate")
    if operation not in IMAGE_MODELS:
        raise VideoProviderError("Unsupported image operation")
    prompt=options.get("prompt")
    if not isinstance(prompt,str) or not 1<=len(prompt.strip())<=2000:
        raise VideoProviderError("Nonempty prompt of at most 2000 characters required")
    _token()
    if os.environ.get("TTG_STUDIO_ENABLE_PAID_IMAGE")!="1":
        raise VideoProviderError("Paid image requests disabled by operator")
    data={"prompt":prompt.strip(), "output_format":"png"}
    model=IMAGE_MODELS[operation]
    if operation=="generate":
        model,data=build_generation_input(options)
        quality=options.get("quality","fast")
    elif operation=="edit":
        image=options.get("input_image")
        if not image:
            raise VideoProviderError("Online image editing requires an HTTPS or selected local reference image")
        data["input_image"]=image_input_uri(image)
        data["aspect_ratio"]="match_input_image"
    else:
        image=options.get("input_image")
        mask=options.get("mask_image")
        if not image or not mask:
            raise VideoProviderError("Masked inpainting requires both a source image and white/black mask")
        image_ref=image_input_uri(image)
        mask_ref=image_input_uri(mask)
        dimensions=_inline_dimensions(image_ref)
        mask_dimensions=_inline_dimensions(mask_ref)
        if dimensions is not None and mask_dimensions is not None and dimensions!=mask_dimensions:
            raise VideoProviderError("Source and mask must have matching pixel dimensions")
        data["image"]=image_ref
        data["mask"]=mask_ref
        data["steps"]=30
        # FLUX Fill respects white=edit, black=preserve. Never silently
        # substitute an unmasked semantic edit for a masking request.
        data["outpaint"]="None"
    reply=_image_record(_json_request(
        "POST","/v1/models/"+model+"/predictions",{"input":data},
    ))
    reply["model"]=model
    if operation=="generate":
        reply["quality"]=quality
        reply["reference_supplied"]=bool(options.get("reference_image"))
    reply["billing"]="external paid image generation"
    return reply


def image_status(prediction_id:str) -> dict:
    if not isinstance(prediction_id,str) or not PREDICTION.fullmatch(prediction_id):
        raise VideoProviderError("Invalid image prediction ID")
    return _image_record(_json_request("GET","/v1/predictions/"+prediction_id))


def image_cancel(prediction_id:str) -> dict:
    if not isinstance(prediction_id,str) or not PREDICTION.fullmatch(prediction_id):
        raise VideoProviderError("Invalid image prediction ID")
    return _image_record(_json_request("POST","/v1/predictions/"+prediction_id+"/cancel"))


def download_image(prediction_id:str, output_path:str|Path) -> dict:
    result=image_status(prediction_id)
    if result["status"]!="succeeded":
        raise VideoProviderError("Image is not ready yet")
    url=_output_url(result["output_url"])
    destination=Path(output_path).expanduser()
    if destination.is_symlink() or destination.suffix.lower()!=".png":
        raise VideoProviderError("Image destination must be a new PNG, not a symlink")
    destination=destination.resolve()
    if not destination.parent.is_dir() or destination.exists():
        raise VideoProviderError("Image output path must have an existing parent and be unused")
    req=urllib.request.Request(url,headers={"Accept":"image/png","User-Agent":"TTG-Creative-Studio/1.0"})
    data=io.BytesIO()
    opener=urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req,timeout=45) as response:
            while True:
                chunk=response.read(512*1024)
                if not chunk:
                    break
                if data.tell()+len(chunk)>MAX_IMAGE_BYTES:
                    raise VideoProviderError("Image exceeds 32 MiB transfer limit")
                data.write(chunk)
    except Exception as exc:
        if isinstance(exc,VideoProviderError):raise
        raise VideoProviderError("Image provider download failed") from None
    content=data.getvalue()
    try:
        with Image.open(io.BytesIO(content)) as decoded:
            if decoded.format not in ("PNG","WEBP","JPEG"):
                raise ValueError("Not supported image media")
            if decoded.width*decoded.height>MAX_IMAGE_PIXELS:
                raise ValueError("Image is too large")
            normalized=ImageOps.exif_transpose(decoded).convert("RGBA")
            out=io.BytesIO()
            normalized.save(out,format="PNG")
        result_bytes=out.getvalue()
    except (ValueError,OSError,Image.DecompressionBombError):
        raise VideoProviderError("Provider output was not a valid bounded image") from None
    tmp=None
    try:
        fd,tmp=tempfile.mkstemp(prefix=".ttg-cloud-image-",dir=destination.parent)
        with os.fdopen(fd,"wb") as file:
            file.write(result_bytes)
            file.flush()
            os.fsync(file.fileno())
        os.link(tmp,destination)
    except FileExistsError:
        raise VideoProviderError("Image file appeared concurrently, refusing overwrite") from None
    finally:
        if tmp:
            Path(tmp).unlink(missing_ok=True)
    return {
        "provider":"replicate","status":"downloaded_verified_pixels",
        "prediction_id":prediction_id,"path":str(destination),
        "bytes":len(result_bytes),"width":normalized.width,"height":normalized.height,
        "sha256":hashlib.sha256(result_bytes).hexdigest(),
    }
