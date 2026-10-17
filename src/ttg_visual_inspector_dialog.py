"""Asynchronous visual inspector with explicit review before editing."""
from __future__ import annotations

from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton,
    QTextEdit, QListWidget, QMessageBox, QFormLayout,
)

from ttg_image_intelligence import (
    ImageIntelligenceRequest, ImageIntelligenceTask, ImageIntelligenceWorker,
)


class AnalysisJob(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, source: Path, prompt: str, model: str, endpoint: str, parent=None):
        super().__init__(parent)
        self.source = source
        self.prompt = prompt
        self.model = model.strip()
        self.endpoint = endpoint

    def run(self) -> None:
        try:
            worker = ImageIntelligenceWorker(
                vision_model=self.model or None, vision_endpoint=self.endpoint
            )
            result = worker.run(ImageIntelligenceRequest(
                task=ImageIntelligenceTask.SUGGEST_EDITS,
                image_paths=[str(self.source)], prompt=self.prompt
            ))
            self.succeeded.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class ModelDiscoveryJob(QThread):
    succeeded = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, endpoint: str, parent=None):
        super().__init__(parent)
        self.endpoint = endpoint

    def run(self) -> None:
        try:
            from ttg_visual_understanding import LocalVisionServer
            found = LocalVisionServer(self.endpoint, timeout=12).installed_models()
            self.succeeded.emit(found)
        except Exception as exc:
            self.failed.emit(str(exc))


class VisualInspectorDialog(QDialog):
    applySuggestion = pyqtSignal(object)

    def __init__(self, image_path: Path, parent=None, can_apply: bool = False):
        super().__init__(parent)
        self.source = Path(image_path)
        self.setWindowTitle("Creative Studio · Visual Inspector")
        self.resize(640, 660)
        self.setStyleSheet("""
            QDialog {background:#101a2b;color:#eff8ff;}
            QLabel {color:#d5e5ee;}
            QLineEdit,QTextEdit,QListWidget {
                color:#f4faff;background:#1a293d;border:1px solid #486278;
                border-radius:5px;padding:5px;
            }
            QPushButton {color:white;background:#23506a;border-radius:5px;padding:7px;}
            QPushButton:disabled {color:#8091a3;background:#263445;}
            QPushButton:hover {background:#277178;}
        """)
        self.job: AnalysisJob | None = None
        self.model_probe: ModelDiscoveryJob | None = None
        self.result = None
        self.can_apply = can_apply
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("VISUAL INSPECTOR · REAL IMAGE ANALYSIS"))
        self.file_label = QLabel(self.source.name)
        layout.addWidget(self.file_label)
        form = QFormLayout()
        self.prompt = QLineEdit("Describe visible objects, layout, and possible improvements.")
        self.model = QLineEdit()
        self.model.setPlaceholderText("Installed local image-capable model ID (optional)")
        self.endpoint = QLineEdit("http://127.0.0.1:8000")
        form.addRow("Question", self.prompt)
        form.addRow("Vision model", self.model)
        form.addRow("Local inference", self.endpoint)
        layout.addLayout(form)
        self.detect_models_button = QPushButton("Discover Installed Vision Models")
        self.detect_models_button.clicked.connect(self.discover_models)
        layout.addWidget(self.detect_models_button)
        layout.addWidget(QLabel(
            "Pixel measurements work offline. Semantic understanding requires a real "
            "installed vision model. Analysis does not change the source image."
        ))
        self.analyze_button = QPushButton("Analyze Image")
        self.analyze_button.clicked.connect(self.start_analysis)
        layout.addWidget(self.analyze_button)
        self.report = QTextEdit()
        self.report.setReadOnly(True)
        self.report.setPlainText("Ready to inspect selected image or current canvas.")
        layout.addWidget(self.report, 1)
        layout.addWidget(QLabel("REVIEWED EDIT SUGGESTIONS"))
        self.suggestions = QListWidget()
        layout.addWidget(self.suggestions)
        actions = QHBoxLayout()
        self.apply_button = QPushButton("Apply Selected Edit to Image Layer")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply_selected)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        actions.addWidget(self.apply_button)
        actions.addWidget(close)
        layout.addLayout(actions)

    def discover_models(self) -> None:
        if self.model_probe is not None and self.model_probe.isRunning():
            return
        self.detect_models_button.setEnabled(False)
        self.report.setPlainText("Checking the direct local multimodal service…")
        self.model_probe = ModelDiscoveryJob(self.endpoint.text(), self)
        self.model_probe.succeeded.connect(self._models_found)
        self.model_probe.failed.connect(self._model_probe_failed)
        self.model_probe.start()

    def _models_found(self, models: list) -> None:
        self.detect_models_button.setEnabled(True)
        if models:
            self.model.setText(str(models[0]))
            self.report.setPlainText(
                "Local models advertised: " + ", ".join(models) +
                "\nConfirm this model supports image input before trusting its interpretation."
            )
        else:
            self.report.setPlainText("Local vision server is reachable but has no installed model.")

    def _model_probe_failed(self, message: str) -> None:
        self.detect_models_button.setEnabled(True)
        self.report.setPlainText(
            "No local vision model is available: " + message +
            "\nMeasured image analysis still works without it."
        )

    def start_analysis(self) -> None:
        if self.job is not None and self.job.isRunning():
            return
        self.report.setPlainText("Analyzing…")
        self.suggestions.clear()
        self.apply_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.job = AnalysisJob(
            self.source, self.prompt.text(), self.model.text(), self.endpoint.text(), self
        )
        self.job.succeeded.connect(self._completed)
        self.job.failed.connect(self._failed)
        self.job.start()

    def _completed(self, result) -> None:
        self.result = result
        self.analyze_button.setEnabled(True)
        details = result.project_updates.get("pixel_evidence", [])
        lines = [result.message, f"Status: {result.status}"]
        if details:
            info = details[0]
            lines += [
                f"Image: {info['dimensions'][0]} × {info['dimensions'][1]} ({info['orientation']})",
                f"Average brightness: {info['luminance_mean_0_255']}/255",
                f"Brightness variation: {info['luminance_stddev_0_255']}/255",
                f"Edge detail: {info['edge_energy_0_255']}/255",
                "Dominant pixel colors: " +
                ", ".join(f"{x['color']} ({x['share']:.0%})" for x in info['dominant_colors']),
            ]
        descriptions = result.project_updates.get("visual_descriptions", [])
        if descriptions:
            lines += ["", "LOCAL VISION MODEL INTERPRETATION (REVIEW REQUIRED)", *descriptions]
        if result.project_updates.get("model_unavailable"):
            lines += ["", "Model unavailable: " + result.project_updates["model_unavailable"]]
        self.report.setPlainText("\n".join(lines))
        self.suggestions.clear()
        for suggestion in result.suggested_actions:
            self.suggestions.addItem(
                f"{suggestion['effect'].title()} × {suggestion['amount']:.2f} — "
                f"{suggestion['reason']}"
            )
        self.apply_button.setEnabled(self.can_apply and bool(result.suggested_actions))

    def _failed(self, message: str) -> None:
        self.analyze_button.setEnabled(True)
        self.report.setPlainText("Could not analyze image: " + message)
        self.apply_button.setEnabled(False)

    def apply_selected(self) -> None:
        if not self.can_apply or self.result is None:
            return
        index = self.suggestions.currentRow()
        if not (0 <= index < len(self.result.suggested_actions)):
            QMessageBox.information(self, "Visual Inspector", "Select a proposed edit first.")
            return
        proposal = self.result.suggested_actions[index]
        if proposal.get("action") != "image_effect" or not proposal.get("review_required"):
            raise ValueError("Only reviewed native image-effect proposals may be applied")
        self.applySuggestion.emit(proposal)

    def closeEvent(self, event) -> None:
        if ((self.job is not None and self.job.isRunning()) or
                (self.model_probe is not None and self.model_probe.isRunning())):
            QMessageBox.information(
                self, "Visual Inspector", "Wait for image analysis to complete."
            )
            event.ignore()
            return
        super().closeEvent(event)
