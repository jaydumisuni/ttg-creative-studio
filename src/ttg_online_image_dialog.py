"""Standalone Creative Studio hosted AI image generation, explicitly opt-in.

Local image editing/ComfyUI remains independent. Cloud requests are only made
after owner approval and operator billing admission. No Hunter connection.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from ttg_online_image_provider import (
    APPROVAL, state, submit, status, cancel, download
)


class ImageCloudWorker(QThread):
    done = pyqtSignal(str, object)
    failed = pyqtSignal(str)

    def __init__(self, action: str, *, options: dict | None = None,
                 prediction_id: str = "", destination: Path | None = None):
        super().__init__()
        self.action = action
        self.options = dict(options or {})
        self.prediction_id = prediction_id
        self.destination = destination

    def run(self) -> None:
        try:
            if self.action == "submit":
                result = submit(self.options)
            elif self.action == "status":
                result = status(self.prediction_id)
            elif self.action == "cancel":
                result = cancel(self.prediction_id)
            elif self.action == "download":
                result = download(self.prediction_id, self.destination)
            else:
                raise ValueError("Invalid cloud image action")
            self.done.emit(self.action, result)
        except Exception as exc:
            self.failed.emit(str(exc))


class OnlineImageDialog(QDialog):
    completed = pyqtSignal(str)

    def __init__(self, output_directory: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Creative Studio · Online AI Image Lab")
        self.resize(760, 480)
        self.directory = Path(output_directory)
        self._worker: ImageCloudWorker | None = None
        self._result: dict | None = None
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Online AI image generation/editing · no model weights on KRATOS.\n"
            "External provider is usage-billed. Explicit permission for every request."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.mode = QComboBox()
        self.mode.addItem("Create new image · FLUX Schnell", "generate")
        self.mode.addItem("Edit existing public image · FLUX Kontext Pro", "edit")
        form.addRow("AI operation", self.mode)
        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText("Describe the desired image or changes")
        self.prompt.setMaximumHeight(95)
        form.addRow("Prompt", self.prompt)
        self.ratio = QComboBox()
        for ratio in ("1:1", "16:9", "9:16", "4:3", "3:4", "2:3", "3:2"):
            self.ratio.addItem(ratio)
        form.addRow("Aspect ratio", self.ratio)
        self.image_url = QLineEdit()
        self.image_url.setPlaceholderText(
            "Editing only: public HTTPS source image URL; never an internal file path"
        )
        form.addRow("Source image URL", self.image_url)
        layout.addLayout(form)
        self.approval = QCheckBox(
            "I authorize this specific externally billed AI image-generation request."
        )
        self.approval.setChecked(False)
        layout.addWidget(self.approval)
        self.readiness = QLabel()
        self.readiness.setWordWrap(True)
        layout.addWidget(self.readiness)
        self.refresh_readiness()
        controls = QHBoxLayout()
        self.generate_button = QPushButton("Generate Image (Paid)")
        self.generate_button.clicked.connect(self.generate)
        self.check_button = QPushButton("Check Prediction")
        self.check_button.clicked.connect(self.check)
        self.save_button = QPushButton("Save PNG to Project")
        self.save_button.clicked.connect(self.save)
        self.save_button.setEnabled(False)
        self.cancel_button = QPushButton("Cancel Job")
        self.cancel_button.clicked.connect(self.cancel_remote)
        for b in (self.generate_button, self.check_button,
                  self.save_button, self.cancel_button):
            controls.addWidget(b)
        layout.addLayout(controls)
        job = QFormLayout()
        self.job_id = QLineEdit()
        self.job_id.setPlaceholderText("Paste an existing cloud prediction ID here")
        job.addRow("Provider prediction ID", self.job_id)
        layout.addLayout(job)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

    def refresh_readiness(self) -> None:
        status_name = state()["online"]
        messages = {
            "configured": "Cloud account and operator billing permission detected.",
            "billing_disabled": "Cloud API token found; image billing disabled by the operator.",
            "credentials_required": "No cloud token configured. No paid image generation possible."
        }
        self.readiness.setText(messages[status_name] +
            " Local checkpoint downloads remain optional and disabled on KRATOS.")

    def _begin(self, action: str, **kwargs) -> None:
        if self._worker is not None and self._worker.isRunning():
            self.log.appendPlainText("A provider operation is already running.")
            return
        self._worker = ImageCloudWorker(action, **kwargs)
        self._worker.done.connect(self._completed)
        self._worker.failed.connect(self._failed)
        self.generate_button.setEnabled(False)
        self._worker.finished.connect(lambda: self.generate_button.setEnabled(True))
        self.log.appendPlainText("Requested: " + action)
        self._worker.start()

    def generate(self) -> None:
        self.refresh_readiness()
        if not self.approval.isChecked():
            QMessageBox.warning(self, "Paid AI image operation",
                                "Approve this specific billable request first.")
            return
        if state()["online"] != "configured":
            QMessageBox.warning(self, "Provider not available",
                                "Set an approved private API token and enable image billing.")
            return
        if QMessageBox.question(
            self, "Authorize external paid generation",
            "Send this prompt and any supplied public image URL to the "
            "Replicate image model for a paid request? Provider fees may apply."
        ) != QMessageBox.StandardButton.Yes:
            return
        args = {"mode":"online", "model":self.mode.currentData(),
                "prompt":self.prompt.toPlainText(),
                "aspect_ratio":self.ratio.currentText(),
                "paid_approval":APPROVAL}
        if self.mode.currentData()=="edit":
            args["input_image"]=self.image_url.text().strip()
        self.approval.setChecked(False)
        self._begin("submit", options=args)

    def check(self) -> None:
        if not self.job_id.text().strip():
            self.log.appendPlainText("Enter a prediction ID.")
            return
        self._begin("status", prediction_id=self.job_id.text().strip())

    def cancel_remote(self) -> None:
        ident=self.job_id.text().strip()
        if not ident:
            return
        if QMessageBox.question(
            self,"Cancel cloud job",
            "Request cancellation of this job? Provider charges may already have accrued."
        )!=QMessageBox.StandardButton.Yes:
            return
        self._begin("cancel",prediction_id=ident)

    def save(self) -> None:
        ident=self.job_id.text().strip()
        if not ident or not self._result or self._result.get("status")!="succeeded":
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        target=self.directory/("online-"+ident+".png")
        if target.exists():
            QMessageBox.warning(self,"Existing image","This result is already saved; refusing overwrite.")
            return
        self._begin("download", prediction_id=ident, destination=target)

    def _completed(self, action: str, response: dict) -> None:
        if action=="download":
            path=response["path"]
            self.log.appendPlainText(
                f"Verified real provider PNG saved: {path}, SHA-256 {response['sha256']}"
            )
            self.completed.emit(path)
            return
        if response.get("prediction_id"):
            self.job_id.setText(response["prediction_id"])
        self._result=response
        self.log.appendPlainText(
            action + ": " + response.get("status","unknown") + " / " +
            response.get("prediction_id","")
        )
        self.save_button.setEnabled(response.get("status")=="succeeded")

    def _failed(self, reason: str) -> None:
        self.log.appendPlainText("Not completed: " + reason)

    def closeEvent(self,event) -> None:
        if self._worker is not None and self._worker.isRunning():
            self.log.appendPlainText("Cloud operation still in progress; cannot close this job window yet.")
            event.ignore()
            return
        super().closeEvent(event)
