"""Standalone Creative Studio optional paid online Image Lab.

This dialog is independent of Hunter. Requests never run from the GUI thread,
credentials are environment-only, and nothing installs model weights locally.
"""
from __future__ import annotations

from pathlib import Path
from PyQt6.QtCore import QThread,pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,QComboBox,QDialog,QFileDialog,QFormLayout,QHBoxLayout,
    QLabel,QLineEdit,QMessageBox,QPlainTextEdit,QPushButton,QVBoxLayout,
)
from ttg_online_video_provider import APPROVAL
from ttg_online_image_provider import (
    readiness,submit_image,image_status,image_cancel,download_image,
)


class ImageCloudWorker(QThread):
    completed=pyqtSignal(str,object)
    failed=pyqtSignal(str)

    def __init__(self,operation:str,settings=None,job_id:str="",destination:str=""):
        super().__init__()
        self.operation=operation
        self.settings=dict(settings or {})
        self.job_id=job_id
        self.destination=destination

    def run(self):
        try:
            if self.operation=="submit":
                reply=submit_image(self.settings)
            elif self.operation=="status":
                reply=image_status(self.job_id)
            elif self.operation=="cancel":
                reply=image_cancel(self.job_id)
            elif self.operation=="download":
                reply=download_image(self.job_id,self.destination)
            else:
                raise ValueError("Unsupported image cloud operation")
            self.completed.emit(self.operation,reply)
        except Exception as error:
            self.failed.emit(str(error))


class OnlineImageDialog(QDialog):
    def __init__(self,import_callback=None,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Creative Studio · Online Image AI")
        self.resize(670,540)
        self.import_callback=import_callback
        self._worker=None
        self._latest=None
        root=QVBoxLayout(self)
        root.addWidget(QLabel(
            "Online AI image generation/editing · no model download on KRATOS. "
            "Provider charges are separate; each job needs approval."
        ))
        form=QFormLayout()
        self.operation=QComboBox()
        self.operation.addItem("Generate image · FLUX Schnell","generate")
        self.operation.addItem("Edit image · FLUX Kontext Pro","edit")
        form.addRow("Operation",self.operation)
        self.prompt=QPlainTextEdit()
        self.prompt.setPlaceholderText("Describe the product image or editing instructions")
        self.prompt.setMaximumHeight(105)
        form.addRow("Prompt",self.prompt)
        self.ratio=QComboBox()
        for ratio in ("1:1","16:9","9:16","4:3","3:4","3:2","2:3"):
            self.ratio.addItem(ratio)
        form.addRow("Generation ratio",self.ratio)
        self.image_url=QLineEdit()
        self.image_url.setPlaceholderText("Public HTTPS image URL required for online edits")
        form.addRow("Image reference",self.image_url)
        root.addLayout(form)
        self.consent=QCheckBox("I authorize ONE paid image generation/edit request.")
        root.addWidget(self.consent)
        self.ready=QLabel()
        self.ready.setWordWrap(True)
        root.addWidget(self.ready)
        self.refresh_ready()

        buttons=QHBoxLayout()
        self.generate_button=QPushButton("Create Online · Paid")
        self.generate_button.clicked.connect(self.generate)
        self.check_button=QPushButton("Check Status")
        self.check_button.clicked.connect(self.check_status)
        self.cancel_button=QPushButton("Cancel Prediction")
        self.cancel_button.clicked.connect(self.cancel_prediction)
        self.download_button=QPushButton("Save & Edit Image in Studio")
        self.download_button.clicked.connect(self.save_image)
        self.download_button.setEnabled(False)
        for item in (self.generate_button,self.check_button,
                     self.cancel_button,self.download_button):
            buttons.addWidget(item)
        root.addLayout(buttons)
        self.prediction=QLineEdit()
        self.prediction.setPlaceholderText("Provider prediction ID for checking an earlier job")
        root.addWidget(self.prediction)
        self.log=QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(115)
        root.addWidget(self.log)
        close=QPushButton("Close")
        close.clicked.connect(self.close)
        root.addWidget(close)

    def refresh_ready(self):
        state=readiness()["state"]
        self.ready.setText({
            "configured":"Provider credentials and billing admission available.",
            "billing_disabled":"Provider credentials found; operator billing remains disabled.",
            "credentials_required":"No provider token configured. Local image edits remain available.",
        }[state]+"\nFuture large offline models are reserved for GT502/Spark.")

    def _start(self,kind,**kwargs):
        if self._worker and self._worker.isRunning():
            self.log.appendPlainText("An image request is still running.")
            return
        self._worker=ImageCloudWorker(kind,**kwargs)
        self._worker.completed.connect(self._completed)
        self._worker.failed.connect(self._failed)
        self.generate_button.setEnabled(False)
        self._worker.finished.connect(lambda:self.generate_button.setEnabled(True))
        self._worker.start()

    def generate(self):
        self.refresh_ready()
        if not self.consent.isChecked():
            QMessageBox.warning(self,"Paid Image AI","Approve the individual paid request first.")
            return
        if readiness()["state"]!="configured":
            QMessageBox.warning(self,"Provider unavailable",
                "Set REPLICATE_API_TOKEN and TTG_STUDIO_ENABLE_PAID_IMAGE=1 in an approved session.")
            return
        if QMessageBox.question(
            self,"Confirm paid image generation",
            "Submit this prompt and any reference-image URL to Replicate? "
            "Review the current model price first; Studio cannot guarantee a spend ceiling."
        )!=QMessageBox.StandardButton.Yes:
            return
        settings={"operation":self.operation.currentData(),
            "prompt":self.prompt.toPlainText(),
            "aspect_ratio":self.ratio.currentText(),
            "input_image":self.image_url.text().strip(),
            "paid_approval":APPROVAL}
        self.consent.setChecked(False)
        self._start("submit",settings=settings)

    def check_status(self):
        if self.prediction.text().strip():
            self._start("status",job_id=self.prediction.text().strip())

    def cancel_prediction(self):
        ident=self.prediction.text().strip()
        if ident and QMessageBox.question(
            self,"Cancel image job","Cancel this prediction? Usage charges may already have accrued."
        )==QMessageBox.StandardButton.Yes:
            self._start("cancel",job_id=ident)

    def save_image(self):
        if not self._latest or self._latest.get("status")!="succeeded":
            return
        path,_=QFileDialog.getSaveFileName(self,"Save AI image",
                                          "creative-generated.png","PNG (*.png)")
        if not path:
            return
        if not path.lower().endswith(".png"):
            path+=".png"
        if Path(path).exists():
            QMessageBox.warning(self,"Choose new filename","Never overwrite an existing file.")
            return
        self._start("download",job_id=self.prediction.text().strip(),destination=path)

    def _completed(self,kind,reply):
        if kind=="download":
            self.log.appendPlainText("Verified image saved: "+reply["path"])
            if self.import_callback:
                try:
                    self.import_callback(reply["path"])
                except Exception as exc:
                    self.log.appendPlainText("Import failed: "+str(exc))
            return
        self.prediction.setText(reply.get("prediction_id",""))
        self._latest=reply
        self.log.appendPlainText(kind+": "+str(reply.get("status")))
        self.download_button.setEnabled(reply.get("status")=="succeeded")

    def _failed(self,message):
        self.log.appendPlainText("Not completed: "+message)

    def closeEvent(self,event):
        if self._worker and self._worker.isRunning():
            self.log.appendPlainText("Active request is not finished; cannot close yet.")
            event.ignore()
            return
        super().closeEvent(event)
