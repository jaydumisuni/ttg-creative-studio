"""Paid online video generation UI, optional and independent of Hunter.

Cloud requests are asynchronous. No secrets are stored in projects or config.
An unavailable future local provider is visibly disabled, not emulated.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
    QPushButton, QSpinBox, QVBoxLayout,
)
from ttg_online_video_provider import (
    APPROVAL, availability, submit_video, status_video,
    download_video, cancel_video,
)


class VideoCloudWorker(QThread):
    done = pyqtSignal(str, object)
    failed = pyqtSignal(str)

    def __init__(self, operation: str, *, payload: dict | None = None,
                 prediction_id: str = "", destination: str = ""):
        super().__init__()
        self.operation = operation
        self.payload = dict(payload or {})
        self.prediction_id = prediction_id
        self.destination = destination

    def run(self) -> None:
        try:
            if self.operation == "submit":
                result = submit_video(self.payload)
            elif self.operation == "status":
                result = status_video(self.prediction_id)
            elif self.operation == "download":
                result = download_video(self.prediction_id, self.destination)
            elif self.operation == "cancel":
                result = cancel_video(self.prediction_id)
            else:
                raise ValueError("Unrecognized video cloud operation")
            self.done.emit(self.operation, result)
        except Exception as exc:
            self.failed.emit(str(exc))


class OnlineVideoDialog(QDialog):
    def __init__(self, import_callback=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Creative Studio · Online Video Generation")
        self.resize(750, 610)
        self.import_callback = import_callback
        self._worker: VideoCloudWorker | None = None
        self._latest_result: dict | None = None
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Online video generation · no model downloads to KRATOS.\n"
            "External model usage may incur charges. Each generation requires explicit approval."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        self.backend = QComboBox()
        self.backend.addItem("Online · Replicate (usage billed)", "online")
        self.backend.addItem("Local · FreeVideo (GT502/Spark later)", "local")
        self.backend.model().item(1).setEnabled(False)
        form.addRow("Generation backend", self.backend)

        self.variant = QComboBox()
        self.variant.addItem("Faster / lower-cost candidate", "fast")
        self.variant.addItem("Higher-quality candidate", "quality")
        form.addRow("Model selection", self.variant)

        self.duration = QSpinBox()
        self.duration.setRange(2, 12)
        self.duration.setValue(5)
        form.addRow("Duration (seconds)", self.duration)
        self.resolution = QComboBox()
        for value in ("480p", "720p", "1080p"):
            self.resolution.addItem(value)
        form.addRow("Resolution", self.resolution)
        self.aspect = QComboBox()
        for ratio in ("16:9", "9:16", "1:1", "4:3", "3:4"):
            self.aspect.addItem(ratio)
        form.addRow("Aspect ratio", self.aspect)

        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText("Describe the scene, subject, camera movement and desired motion")
        self.prompt.setMaximumHeight(115)
        form.addRow("Video prompt", self.prompt)
        self.image_url = QLineEdit()
        self.image_url.setPlaceholderText(
            "Optional public HTTPS image link (for image-to-video); leave empty for text-to-video"
        )
        form.addRow("Starting image", self.image_url)
        layout.addLayout(form)

        self.billing_approval = QCheckBox(
            "I approve one paid online video-generation request using the chosen model/settings."
        )
        layout.addWidget(self.billing_approval)
        self.provider_state = QLabel()
        self.provider_state.setWordWrap(True)
        layout.addWidget(self.provider_state)
        self.refresh_state()

        buttons = QHBoxLayout()
        self.submit_button = QPushButton("Generate Online (Paid)")
        self.submit_button.clicked.connect(self.generate)
        self.refresh_button = QPushButton("Check Status")
        self.refresh_button.clicked.connect(self.check_status)
        self.cancel_button = QPushButton("Cancel Job")
        self.cancel_button.clicked.connect(self.cancel_job)
        self.download_button = QPushButton("Save MP4 / Import to Studio")
        self.download_button.clicked.connect(self.save_result)
        self.download_button.setEnabled(False)
        for item in (self.submit_button, self.refresh_button,
                     self.cancel_button, self.download_button):
            buttons.addWidget(item)
        layout.addLayout(buttons)

        self.job_id = QLineEdit()
        self.job_id.setPlaceholderText("Prediction ID (recover a previous session here)")
        form2 = QFormLayout()
        form2.addRow("Remote prediction ID", self.job_id)
        layout.addLayout(form2)
        self.event_log = QPlainTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setMaximumHeight(150)
        layout.addWidget(self.event_log)

        actions = QHBoxLayout()
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        actions.addStretch()
        actions.addWidget(close)
        layout.addLayout(actions)

    def refresh_state(self) -> None:
        info = availability()
        state = info["online"]["state"]
        self.provider_state.setText(
            ("Replicate credentials and operator billing admission detected."
             if state == "configured"
             else "Provider credentials are available but operator billing is disabled. "
                  "Set TTG_STUDIO_ENABLE_PAID_VIDEO=1 in an approved session to authorize paid requests."
                  if state == "billing_disabled"
             else "No REPLICATE_API_TOKEN configured. You may prepare prompts; "
                  "billable generation stays blocked until you privately configure the provider.")
            + "\nLocal FreeVideo model download is reserved for GT502/Spark; "
              "no model is downloaded or installed on KRATOS."
        )

    def _begin(self, operation: str, **kwargs) -> None:
        if self._worker is not None and self._worker.isRunning():
            self.event_log.appendPlainText("A video request is already running.")
            return
        self._worker = VideoCloudWorker(operation, **kwargs)
        self._worker.done.connect(self._complete)
        self._worker.failed.connect(self._failed)
        self.submit_button.setEnabled(False)
        self._worker.finished.connect(lambda: self.submit_button.setEnabled(True))
        self.event_log.appendPlainText("Request: " + operation + " (no local model used)")
        self._worker.start()

    def generate(self) -> None:
        self.refresh_state()
        if not self.billing_approval.isChecked():
            QMessageBox.warning(self, "Paid video generation",
                                "Approve the per-request billable generation before submitting.")
            return
        if self.backend.currentData() != "online":
            QMessageBox.information(self, "Local inference unavailable",
                                    "Local FreeVideo is reserved for GT502/Spark.")
            return
        if availability()["online"]["state"] != "configured":
            QMessageBox.warning(self, "Provider not connected",
                                "Configure REPLICATE_API_TOKEN privately before submitting.")
            return
        approve = QMessageBox.question(
            self, "Confirm external paid inference",
            "Send this prompt and optional public image URL to Replicate for "
            "usage-billed video generation?\n\nCreative Studio cannot guarantee a "
            "cost ceiling. Review the current model price on Replicate first."
        )
        if approve != QMessageBox.StandardButton.Yes:
            return
        payload = {
            "mode": "online", "model": self.variant.currentData(),
            "duration": self.duration.value(),
            "resolution": self.resolution.currentText(),
            "aspect_ratio": self.aspect.currentText(),
            "prompt": self.prompt.toPlainText(),
            "image_url": self.image_url.text().strip(),
            "paid_approval": APPROVAL,
        }
        # Approval is consumed on a single submission, not left checked.
        self.billing_approval.setChecked(False)
        self._begin("submit", payload=payload)

    def _current_prediction(self) -> str:
        return self.job_id.text().strip()

    def check_status(self) -> None:
        if not self._current_prediction():
            self.event_log.appendPlainText("Enter a prediction ID to check.")
            return
        self._begin("status", prediction_id=self._current_prediction())

    def cancel_job(self) -> None:
        if not self._current_prediction():
            return
        if QMessageBox.question(
            self, "Cancel remote job",
            "Request cancellation of this provider prediction? Charges may already have accrued."
        ) != QMessageBox.StandardButton.Yes:
            return
        self._begin("cancel", prediction_id=self._current_prediction())

    def save_result(self) -> None:
        if not self._latest_result or self._latest_result.get("status") != "succeeded":
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Generated Video", "generated-video.mp4", "MP4 video (*.mp4)"
        )
        if not filename:
            return
        if not filename.lower().endswith(".mp4"):
            filename += ".mp4"
        if Path(filename).exists():
            QMessageBox.warning(self, "Output already exists",
                                "Choose an unused filename. This action never overwrites.")
            return
        self._begin("download", prediction_id=self._current_prediction(),
                    destination=filename)

    def _complete(self, operation: str, response: dict) -> None:
        if operation == "download":
            path = response["path"]
            self.event_log.appendPlainText(
                f"Real provider MP4 saved: {path} ({response['bytes']} bytes)"
            )
            # Only actual downloaded media is imported; the existing Video
            # Lab re-probes it rather than assuming the cloud response is valid.
            if self.import_callback is not None:
                try:
                    self.import_callback(Path(path))
                except Exception as exc:
                    self.event_log.appendPlainText(
                        "Saved file was not imported automatically: " + str(exc)
                    )
            return
        if response.get("prediction_id"):
            self.job_id.setText(response["prediction_id"])
        self._latest_result = response
        self.event_log.appendPlainText(
            f"{operation}: {response.get('status')} / {response.get('prediction_id', '')}"
        )
        self.download_button.setEnabled(response.get("status") == "succeeded")

    def _failed(self, reason: str) -> None:
        self.event_log.appendPlainText("Not completed: " + reason)

    def closeEvent(self, event) -> None:
        if self._worker is not None and self._worker.isRunning():
            self.event_log.appendPlainText(
                "Complete the request before closing. Remote generation may still be billable."
            )
            event.ignore()
            return
        super().closeEvent(event)
