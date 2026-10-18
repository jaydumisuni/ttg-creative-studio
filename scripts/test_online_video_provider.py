#!/usr/bin/env python3
"""Provider contract tests: NO live account calls, no billable inference.

Fixtures deliberately simulate the HTTP protocol; these tests are NOT evidence
of a real generated video, real credentials or local model installation.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ttg_online_video_provider import (
    APPROVAL, MODELS, VideoProviderError, availability, submit_video,
    status_video, cancel_video, download_video, validate_public_https,
)
from ttg_creative_studio.engine.video_jobs import run_video_job
from PyQt6.QtWidgets import QApplication
from ttg_online_video_dialog import OnlineVideoDialog
from ttg_creative_workspace import CreativeWorkspace

checks: list[str] = []


def check(expr, description):
    assert expr, description
    checks.append(description)


def refuses(callback, match: str):
    try:
        callback()
    except (VideoProviderError, RuntimeError) as exc:
        check(match.lower() in str(exc).lower(),
              "Fail closed: " + match)
    else:
        raise AssertionError("Unexpectedly allowed " + match)


class Response:
    def __init__(self, payload: bytes):
        self.payload = io.BytesIO(payload)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.payload.close()

    def read(self, size: int = -1) -> bytes:
        return self.payload.read(size)


class FakeOpener:
    def __init__(self, requests: list, record: dict, payload: bytes):
        self.requests = requests
        self.record = record
        self.payload = payload

    def open(self, request, timeout=None):
        self.requests.append({
            "url": request.full_url,
            "method": request.get_method(),
            "body": request.data,
            "timeout": timeout,
            "headers": dict(request.headers),
        })
        if request.full_url.startswith("https://replicate.delivery/"):
            return Response(self.payload)
        return Response(json.dumps(self.record).encode())


def main():
    workflow=(ROOT/".github/workflows/studio-online-video-provider.yml").read_text()
    check("runs-on: $"+"{{ matrix.os }}" in workflow,
          "Windows/Linux CI uses real matrix interpolation")
    old = os.environ.pop("REPLICATE_API_TOKEN", None)
    old_paid = os.environ.pop("TTG_STUDIO_ENABLE_PAID_VIDEO", None)
    try:
        state = availability()
        check(state["online"]["state"] == "credentials_required",
              "Unconnected online provider accurately reports missing API token")
        check(state["offline"]["state"] == "awaiting_GT502_or_Spark",
              "Offline model remains explicitly reserved for later hardware")
        check(not state["offline"]["model_files_installed_by_studio"],
              "No hidden local model download/install declared")

        refuses(lambda: submit_video({"prompt": "Film", "duration": 5}),
                "explicit approval")
        refuses(lambda: submit_video({"prompt": "Film", "paid_approval": APPROVAL,
                                      "mode": "local"}), "disabled")
        refuses(lambda: submit_video({"prompt": "Film", "paid_approval": APPROVAL,
                                      "duration": 70}), "duration")
        refuses(lambda: submit_video({"prompt": "Film", "paid_approval": APPROVAL,
                                      "model": "untrusted"}), "unsupported")
        refuses(lambda: validate_public_https("http://127.0.0.1/private"),
                "public HTTPS")
        refuses(lambda: validate_public_https("https://localhost/private"),
                "public HTTPS")
        refuses(lambda: submit_video({"prompt": "Film",
                                      "paid_approval": APPROVAL}),
                "REPLICATE_API_TOKEN")

        # A previously hard-disabled video_generate may now be prepared for
        # the cloud, but never executes a prediction without consent/token.
        refuses(lambda: run_video_job({"task": "video_generate", "options": {}}),
                "explicit approval")
        catalog = run_video_job({"task":"video_capabilities"})
        check(catalog["meta"]["generation"]["online"]["state"] == "credentials_required",
              "Video tool contract discovers provider configuration and pricing guard")
        check(catalog["meta"]["catalog"]["operations"]["video_generate"]["state"] ==
              "online_opt_in", "Cloud generation advertised as opt-in, not fake local model")

        test_record = {
            "id": "abcd1234xyz8", "status": "starting",
            "urls": {"get": "https://api.replicate.com/v1/predictions/abcd1234xyz8"},
        }
        calls = []
        body = b"\x00\x00\x00\x18ftypisom" + (b"studio-video-fixture" * 100)
        fake = FakeOpener(calls, test_record, body)
        os.environ["REPLICATE_API_TOKEN"] = "fake-test-token-never-billed"
        refuses(lambda: submit_video({"prompt":"A scene","duration":5,
                                      "paid_approval":APPROVAL}),
                "operator")
        os.environ["TTG_STUDIO_ENABLE_PAID_VIDEO"] = "1"
        with patch("urllib.request.build_opener", return_value=fake):
            reply = submit_video({
                "prompt": "A rotating phone shown on a clean studio backdrop",
                "paid_approval": APPROVAL, "model": "fast",
                "duration": 5, "resolution": "480p",
                "aspect_ratio": "16:9",
            })
            check(reply["status"] == "starting" and reply["prediction_id"] == "abcd1234xyz8",
                  "Async cloud prediction ID returned correctly")
            check(calls[0]["url"] ==
                  "https://api.replicate.com/v1/models/bytedance/seedance-1-pro-fast/predictions",
                  "Only approved official provider endpoint used")
            sent=json.loads(calls[0]["body"])
            check(sent["input"]["duration"]==5 and "paid_approval" not in sent["input"],
                  "Only validated model inputs sent, never approval metadata")

            test_record["status"] = "processing"
            check(status_video("abcd1234xyz8")["status"] == "processing",
                  "Asynchronous status refresh observes provider progress")
            test_record["status"] = "succeeded"
            test_record["output"] = "https://replicate.delivery/pbx/sample.mp4"
            check(status_video("abcd1234xyz8")["status"] == "succeeded",
                  "Completed provider response recognizes verified output host")

            with tempfile.TemporaryDirectory(prefix="ttg-online-test-") as workspace:
                destination = Path(workspace) / "actual-from-provider.mp4"
                receipt = download_video("abcd1234xyz8", destination)
                check(destination.read_bytes()==body and receipt["sha256"] ==
                      hashlib.sha256(body).hexdigest(),
                      "Provider MP4 streamed once, bounded and checksummed")
                refuses(lambda: download_video("abcd1234xyz8", destination),
                        "must be new")
                test_record["output"] = "https://evil.invalid/capture.mp4"
                refuses(lambda: download_video("abcd1234xyz8",Path(workspace)/"bad.mp4"),
                        "approved provider delivery domain")
                test_record["output"] = "https://replicate.delivery/pbx/sample.mp4"

                import ttg_online_video_provider as module
                with patch.object(module, "MAX_DOWNLOAD", 1000):
                    refuses(lambda: download_video("abcd1234xyz8",
                                                  Path(workspace)/"large.mp4"),
                            "exceeds")
                    check(not (Path(workspace)/"large.mp4").exists(),
                          "Oversized response cleans temporary bytes")

            test_record["status"] = "canceled"
            del test_record["output"]
            check(cancel_video("abcd1234xyz8")["status"] == "canceled",
                  "Explicit cancellation routed to one provider job")

        check(all("fake-test-token-never-billed" not in str(entry["url"])
                  for entry in calls), "API secrets not written to URLs or receipts")
        check(not any(call["method"]=="POST" for call in calls[1:] if
                      not call["url"].endswith("/cancel")),
              "Status and downloads cannot submit a new paid prediction")

        app=QApplication.instance() or QApplication([])
        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": ""}):
            dialog=OnlineVideoDialog()
            check(not dialog.backend.model().item(1).isEnabled(),
                  "Standalone GUI visibly disables FreeVideo local download")
            check(not dialog.billing_approval.isChecked(),
                  "Billable approval checkbox always defaults to unchecked")
            check("No REPLICATE_API_TOKEN" in dialog.provider_state.text(),
                  "Missing credentials shown clearly in standalone GUI")
            dialog.close()
        project = CreativeWorkspace()
        check(hasattr(project,"open_online_video") and
              hasattr(project,"import_online_video"),
              "Online provider connected to Creative Studio desktop, not Hunter")
        project.close()
    finally:
        if old is not None:
            os.environ["REPLICATE_API_TOKEN"] = old
        else:
            os.environ.pop("REPLICATE_API_TOKEN", None)
        if old_paid is not None:
            os.environ["TTG_STUDIO_ENABLE_PAID_VIDEO"] = old_paid
        else:
            os.environ.pop("TTG_STUDIO_ENABLE_PAID_VIDEO", None)
    print(json.dumps({"result":"PASS","checks":len(checks),"names":checks},indent=2))


if __name__ == "__main__":
    main()
