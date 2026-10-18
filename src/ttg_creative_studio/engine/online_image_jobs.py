"""Common Creative Studio image tools, for possible future AI clients.

Standalone UI does not need a client. Jobs are one-shot, explicit-approval
actions and never install model weights.
"""
from __future__ import annotations

from pathlib import Path
from ttg_creative_studio.engine.image_jobs import CreativeJobError, JobResult
from ttg_online_image_provider import (
    submit_image,image_status,image_cancel,download_image,readiness,
)

ONLINE_IMAGE_TASKS=frozenset({
    "image_generate_online", "image_status_online",
    "image_cancel_online", "image_download_online",
})


def run_online_image_job(job:dict) -> dict:
    task=job.get("task")
    if task not in ONLINE_IMAGE_TASKS:
        raise CreativeJobError("Unknown online image operation")
    options=job.get("options") or {}
    if not isinstance(options,dict):
        raise CreativeJobError("Image options must be an object")
    identifier=str(job.get("jobId") or job.get("job_id") or "image_job")
    if task=="image_generate_online":
        answer=submit_image(options)
        status="submitted"
        output=""
    elif task=="image_status_online":
        answer=image_status(options.get("prediction_id"))
        status=answer["status"]
        output=""
    elif task=="image_cancel_online":
        if options.get("cancel_approval")!="CANCEL_THIS_PREDICTION":
            raise CreativeJobError("Cancel requires per-request approval")
        answer=image_cancel(options.get("prediction_id"))
        status=answer["status"]
        output=""
    else:
        requested=job.get("output") or job.get("outputPath")
        if not isinstance(requested,str) or not requested.strip():
            raise CreativeJobError("Image output path required")
        answer=download_image(options.get("prediction_id"),requested)
        output=answer["path"]
        status=answer["status"]
    return JobResult(True,identifier,task,"",output,status,
                     "Online image provider operation performed",answer).to_dict()
