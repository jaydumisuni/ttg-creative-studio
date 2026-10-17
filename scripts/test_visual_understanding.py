#!/usr/bin/env python3
"""Real pixel evidence, authenticated local-only VLM protocol and GUI approval."""
from __future__ import annotations

import base64
import io
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ttg_visual_understanding import measure_image, suggest_adjustments, LocalOllamaVision
from ttg_image_intelligence import ImageIntelligenceWorker, ImageIntelligenceTask, ImageIntelligenceRequest

checks = []


def accept(name, cond):
    assert cond, name
    checks.append(name)


class VLMFixture(BaseHTTPRequestHandler):
    seen_image = False
    seen_question = False
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path != "/api/tags":
            self.send_error(404); return
        value = {"models": [{"name": "fake-vlm:test"}]}
        self._send(value)

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404); return
        n = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(n))
        items = body["messages"][0]["images"]
        with Image.open(io.BytesIO(base64.b64decode(items[0], validate=True))) as im:
            self.__class__.seen_image = im.size == (80, 60)
        self.__class__.seen_question = "Which colors" in body["messages"][0]["content"]
        self._send({"message": {"content": "The supplied test image is predominantly blue."}})

    def _send(self, obj):
        data = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class RedirectFixture(VLMFixture):
    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", "https://example.invalid/secret-image")
        self.end_headers()


def execute():
    with tempfile.TemporaryDirectory(prefix="ttg-visual-test-") as temp:
        root = Path(temp)
        image = root/"sample.png"
        Image.new("RGBA", (80, 60), (20, 70, 150, 255)).save(image)
        evidence = measure_image(image)
        accept("real image dimensions/orientation",
               evidence["dimensions"] == [80, 60] and evidence["orientation"] == "landscape")
        accept("real brightness and measurable palette",
               0 < evidence["luminance_mean_0_255"] < 150
               and len(evidence["dominant_colors"]) >= 1)
        accept("source image SHA-256 is complete", len(evidence["source_sha256"]) == 64)
        proposals = suggest_adjustments(evidence)
        accept("suggestions are review-required native effects",
               all(item["review_required"] and item["action"] == "image_effect"
                   for item in proposals))
        no_file = ImageIntelligenceWorker().run(ImageIntelligenceRequest(
            task=ImageIntelligenceTask.UNDERSTAND_IMAGE))
        accept("absent image never fabricates visual interpretation",
               no_file.status == "missing_image" and not no_file.generated_assets)
        analyzed = ImageIntelligenceWorker().run(ImageIntelligenceRequest(
            task=ImageIntelligenceTask.SUGGEST_EDITS, image_paths=[str(image)]))
        accept("native pixel evidence reported honestly",
               analyzed.status == "measured_only"
               and analyzed.project_updates["pixel_evidence"][0]["source_sha256"] ==
               evidence["source_sha256"])
        planned = ImageIntelligenceWorker().run(ImageIntelligenceRequest(
            task=ImageIntelligenceTask.REMOVE_BACKGROUND, image_paths=[str(image)]))
        accept("unexecuted background removal never claims assets",
               not planned.generated_assets and planned.status == "review_only")

        server = ThreadingHTTPServer(("127.0.0.1", 0), VLMFixture)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            local = LocalOllamaVision(f"http://127.0.0.1:{server.server_port}")
            accept("installed local VLM model discovery", local.installed_models() == ["fake-vlm:test"])
            note = local.describe(image, "fake-vlm:test", "Which colors are visible?")
            accept("real encoded image and question delivered to local model",
                   VLMFixture.seen_image and VLMFixture.seen_question
                   and "blue" in note)
            result = ImageIntelligenceWorker(
                vision_model="fake-vlm:test", vision_endpoint=local.url
            ).run(ImageIntelligenceRequest(task=ImageIntelligenceTask.UNDERSTAND_IMAGE,
                                           image_paths=[str(image)]))
            accept("vision response is explicitly marked as unreviewed interpretation",
                   result.status == "model_vision_review_required"
                   and bool(result.project_updates.get("visual_descriptions"))
                   and not result.generated_assets)
            try:
                local.describe(image, "not-installed", "question")
            except ValueError:
                checks.append("reject uninstalled model name")
            else:
                raise AssertionError("uninstalled model accepted")
        finally:
            server.shutdown()
            server.server_close()
            worker.join(3)

        for url in ("https://evil.invalid:11434", "http://10.0.0.5:11434",
                    "file:///tmp/steal", "http://127.0.0.1:11434@evil.invalid:11434"):
            try:
                LocalOllamaVision(url)
            except ValueError:
                continue
            raise AssertionError("Untrusted vision endpoint accepted")
        checks.append("vision HTTP restricted to local loopback")

        redirect = ThreadingHTTPServer(("127.0.0.1", 0), RedirectFixture)
        running = threading.Thread(target=redirect.serve_forever, daemon=True)
        running.start()
        try:
            try:
                LocalOllamaVision(f"http://127.0.0.1:{redirect.server_port}").installed_models()
            except ValueError:
                checks.append("block external redirects for image content")
            else:
                raise AssertionError("Vision server redirect allowed")
        finally:
            redirect.shutdown()
            redirect.server_close()
            running.join(3)

        from PyQt6.QtWidgets import QApplication
        from ttg_visual_inspector_dialog import VisualInspectorDialog
        from ttg_creative_workspace import CreativeWorkspace
        app = QApplication.instance() or QApplication([])
        inspector = VisualInspectorDialog(image, can_apply=True)
        inspector.start_analysis()
        deadline = time.monotonic() + 12
        while inspector.job and inspector.job.isRunning() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.03)
        app.processEvents()
        accept("GUI shows real measured evidence without model",
               inspector.result and inspector.result.status == "measured_only"
               and "80 × 60" in inspector.report.toPlainText())
        inspector.close()
        workspace = CreativeWorkspace(root)
        workspace.new_project()
        layer = workspace.action.add_image(workspace.project, str(image), 0, 0)
        workspace.selected_layer_id = layer.id
        workspace.refresh_all()
        chosen = analyzed.suggested_actions[0]
        original_count = len(layer.effects)
        workspace.apply_inspector_edit(chosen, layer.id, image, evidence["source_sha256"])
        accept("reviewed suggestion actually alters editable layer",
               len(layer.effects) == original_count + 1)
        workspace.undo()
        accept("inspector edits undoable", len(workspace.selected_layer().effects) == original_count)
        try:
            workspace.apply_inspector_edit(
                {**chosen, "effect": "delete_files"}, layer.id, image, evidence["source_sha256"])
        except ValueError:
            checks.append("untrusted model action rejected before execution")
        else:
            raise AssertionError("Unauthorized model effect accepted")
        workspace.close()
    return {"result": "PASS", "checks": len(checks), "names": checks}


if __name__ == "__main__":
    print(json.dumps(execute(), indent=2))
