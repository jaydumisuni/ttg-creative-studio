"""Standalone Creative Studio online image generation and image-edit provider.

No local checkpoint is downloaded. Every billable request requires an
operator-level switch and separate per-request consent. Outputs are verified
as actual decoded pixels before becoming editable Studio assets.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import urllib.request

from PIL import Image, ImageOps
from ttg_online_video_provider import (
    APPROVAL, VideoProviderError, NoRedirect, _json_request, _output_url,
    _token, _is_private_host, validate_public_https, PREDICTION,
)

IMAGE_MODELS = {
    "generate": "black-forest-labs/flux-schnell",
    "edit": "black-forest-labs/flux-kontext-pro",
}
MAX_IMAGE_BYTES = 32 * 1024 * 1024
MAX_IMAGE_PIXELS = 28_000_000


def readiness() -> dict:
    return {
        "provider": "replicate",
        "state": ("configured" if os.environ.get("REPLICATE_API_TOKEN","").strip()
                 and os.environ.get("TTG_STUDIO_ENABLE_PAID_IMAGE") == "1"
                 else "billing_disabled" if os.environ.get("REPLICATE_API_TOKEN","").strip()
                 else "credentials_required"),
        "models": IMAGE_MODELS,
        "local_checkpoint_installed_by_studio": False,
        "local_model_download": "deferred_GT502_or_Spark",
        "pricing": {
            "generate": "https://replicate.com/black-forest-labs/flux-schnell",
            "edit": "https://replicate.com/black-forest-labs/flux-kontext-pro",
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
    if operation=="generate":
        ratio=options.get("aspect_ratio","1:1")
        if ratio not in ("1:1","16:9","9:16","4:3","3:4","3:2","2:3"):
            raise VideoProviderError("Unsupported image aspect ratio")
        data.update({"aspect_ratio":ratio,"num_outputs":1,"num_inference_steps":4})
    else:
        image=options.get("input_image")
        if not image:
            raise VideoProviderError("Online image editing requires a public HTTPS reference image")
        data["input_image"]=validate_public_https(image)
        data["aspect_ratio"]="match_input_image"
    reply=_image_record(_json_request(
        "POST","/v1/models/"+IMAGE_MODELS[operation]+"/predictions",{"input":data},
    ))
    reply["model"]=IMAGE_MODELS[operation]
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
