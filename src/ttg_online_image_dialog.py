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
from ttg_professional_image_production import choose_quality
from ttg_online_image_provider import (
    APPROVAL, GENERATION_PROFILES, readiness,submit_image,image_status,image_cancel,download_image,
    inline_image_url, compact_reference_image,
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
    def __init__(self,import_callback=None,parent=None,destination_dir:Path|None=None):
        super().__init__(parent)
        self.destination_dir=Path(destination_dir) if destination_dir is not None else None
        self.setWindowTitle("Creative Studio · Online Image AI")
        self.resize(670,540)
        self.import_callback=import_callback
        self._worker=None
        self._latest=None
        self._submitted=None
        self._pending_reference_sha=None
        self._local_source=None
        self._local_mask=None
        self._source_manifest=None
        root=QVBoxLayout(self)
        root.addWidget(QLabel(
            "Online AI image generation/editing · no model download on KRATOS. "
            "Provider charges are separate; each job needs approval."
        ))
        form=QFormLayout()
        self.operation=QComboBox()
        self.operation.addItem("Generate image · choose quality model","generate")
        self.operation.addItem("Edit image · FLUX Kontext Pro","edit")
        self.operation.addItem("Inpaint with mask · FLUX Fill Pro","inpaint")
        form.addRow("Operation",self.operation)
        self.quality=QComboBox()
        self.quality.addItem("Auto · Production Director selects model", "auto")
        self.quality.addItem("Premium branded mockup · Nano Banana Pro","brand_pro")
        self.quality.addItem("Photoreal image · FLUX.2 Pro","photoreal")
        self.quality.addItem("Fast preview · FLUX Schnell","fast")
        form.addRow("Generation quality",self.quality)
        self.operation.currentIndexChanged.connect(
            lambda _: self.quality.setEnabled(self.operation.currentData()=="generate")
        )
        self.prompt=QPlainTextEdit()
        self.prompt.setPlaceholderText("Describe the product image or editing instructions")
        self.prompt.setMaximumHeight(105)
        form.addRow("Prompt",self.prompt)
        recreate=QPushButton("Prepare THETECHGUY Reference Recreation")
        recreate.setToolTip(
            "Prepare a detailed prompt only. Does NOT submit to a model or charge a provider."
        )
        recreate.clicked.connect(self.prepare_wall_sign_recreation)
        form.addRow("Professional preset",recreate)
        self.ratio=QComboBox()
        for ratio in ("1:1","16:9","9:16","4:3","3:4","3:2","2:3","match_input_image"):
            self.ratio.addItem(ratio)
        form.addRow("Generation ratio",self.ratio)
        self.image_url=QLineEdit()
        self.image_url.setPlaceholderText("Optional generation reference / editing source HTTPS URL")
        self.image_url.textEdited.connect(lambda _: self._clear_inline("image"))
        source_row=QHBoxLayout()
        source_row.addWidget(self.image_url,1)
        source_button=QPushButton("Local Image")
        source_button.clicked.connect(self.select_local_source)
        source_row.addWidget(source_button)
        form.addRow("Source image",source_row)

        self.mask_url=QLineEdit()
        self.mask_url.setPlaceholderText("HTTPS mask URL or local black/white PNG (white = edit)")
        self.mask_url.textEdited.connect(lambda _: self._clear_inline("mask"))
        mask_row=QHBoxLayout()
        mask_row.addWidget(self.mask_url,1)
        mask_button=QPushButton("Local Mask")
        mask_button.clicked.connect(self.select_local_mask)
        mask_row.addWidget(mask_button)
        form.addRow("Inpainting mask",mask_row)
        self.local_info=QLabel("Reference photos are locally reduced for private, bounded transport. No upload before consent.")
        self.local_info.setWordWrap(True)
        form.addRow("Input privacy",self.local_info)
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

    def _clear_inline(self, which: str) -> None:
        if which=="image":
            self._local_source=None
            self._source_manifest=None
        else:
            self._local_mask=None

    def _choose_inline(self, which: str) -> None:
        filename,_=QFileDialog.getOpenFileName(
            self, "Select a small local source/mask", "",
            "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not filename:
            return
        try:
            if which=="image" and self.operation.currentData()=="generate":
                info=compact_reference_image(filename)
                uri=info["uri"]
            else:
                info=None
                uri=inline_image_url(filename)
        except Exception as exc:
            QMessageBox.warning(self,"Image size/privacy",str(exc))
            return
        if which=="image":
            self._local_source=uri
            self._source_manifest=info
            self.image_url.setText("")
            self.image_url.setPlaceholderText("Local source selected: "+Path(filename).name)
        else:
            self._local_mask=uri
            self.mask_url.setText("")
            self.mask_url.setPlaceholderText("Local mask selected: "+Path(filename).name)
        if info:
            self.local_info.setText(
                "Local reference prepared, not uploaded: "
                f"{info['transmitted_dimensions'][0]}×{info['transmitted_dimensions'][1]} "
                f"· {info['transmitted_bytes']:,} bytes. Original file unchanged. "
                "Provider receives only this compressed copy after paid confirmation."
            )
        else:
            self.local_info.setText(
                "Selected local image bytes will be transmitted to Replicate only "
                "if you approve the specific paid operation."
            )

    def select_local_source(self):
        self._choose_inline("image")

    def select_local_mask(self):
        self._choose_inline("mask")

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

    def prepare_wall_sign_recreation(self):
        """Author a photoreal recreation instruction without starting inference."""
        self.operation.setCurrentIndex(0)
        self.quality.setCurrentIndex(self.quality.findData("brand_pro"))
        self.ratio.setCurrentText("match_input_image" if (
            self._local_source or self.image_url.text().strip()) else "4:3")
        self.prompt.setPlainText(
            "Create a NEW photorealistic premium architectural lobby photograph "
            "matching the selected reference image's geometry, visual hierarchy "
            "and camera perspective. Center on a raised brushed stainless-steel "
            "TG monogram with physically plausible chamfered extrusion and precise "
            "thin electric-blue LED circuit traces; beneath it render the EXACT "
            "legible metal lettering 'THETECHGUY' and a smaller line "
            "'DIGITAL SOLUTIONS'. Retain the fine textured charcoal wall, "
            "floor-to-ceiling black-framed office glazing on the left, muted "
            "distant city, narrow dark wood slats at right, black glossy marble "
            "reception desk and green foreground foliage. Soft warm ceiling "
            "downlights, realistic wall contact shadows, metal anisotropic "
            "highlights, delicate blue light spill and marble reflections. "
            "Photographic realism, sophisticated interior-product photography, "
            "restrained optical depth, accurate scale, professional color grade. "
            "No extra lettering, no watermarks, no cartoon or vector appearance. "
            "Reference is a guide; generate new pixels rather than reusing "
            "the photograph as a finished background."
        )
        self.log.appendPlainText(
            "Prepared photoreal reference-recreation prompt. No provider called."
        )

    def generate(self):
        self.refresh_ready()
        if not self.consent.isChecked():
            QMessageBox.warning(self,"Paid Image AI","Approve the individual paid request first.")
            return
        if readiness()["state"]!="configured":
            QMessageBox.warning(self,"Provider unavailable",
                "Set REPLICATE_API_TOKEN and TTG_STUDIO_ENABLE_PAID_IMAGE=1 in an approved session.")
            return
        chosen_quality = (choose_quality(self.prompt.toPlainText(),self.quality.currentData())
                          if self.operation.currentData()=="generate"
                          else self.quality.currentData())
        model_name = (GENERATION_PROFILES[chosen_quality]["model"]
                      if self.operation.currentData()=="generate" else self.operation.currentText())
        if QMessageBox.question(
            self,"Confirm paid image generation",
            "Submit this prompt to Replicate using the selected model: "
            + str(model_name) + "? "
            "Any selected source/mask image data will also be sent. "
            "Review the model's current price; Studio cannot guarantee a spend ceiling."
        )!=QMessageBox.StandardButton.Yes:
            return
        selected=self._local_source or self.image_url.text().strip()
        if self.operation.currentData()=="generate" and selected and chosen_quality=="fast":
            QMessageBox.warning(
                self,"Reference model unavailable",
                "Fast preview cannot use a reference photo. Select Nano Banana Pro or FLUX.2 Pro."
            )
            return
        settings={"operation":self.operation.currentData(),
            "quality":chosen_quality,
            "prompt":self.prompt.toPlainText(),
            "aspect_ratio":self.ratio.currentText(),
            "reference_image":selected if self.operation.currentData()=="generate" else "",
            "input_image":selected if self.operation.currentData()!="generate" else "",
            "mask_image":self._local_mask or self.mask_url.text().strip(),
            "paid_approval":APPROVAL}
        self._pending_reference_sha=(
            self._source_manifest.get("source_sha256")
            if self.operation.currentData()=="generate" and self._source_manifest
            else None
        )
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
        # When used from an editable Studio project, keep the downloaded PNG
        # inside that project. Arbitrary Save As paths previously prevented
        # native layer import and could leak assets outside the workspace.
        if self.destination_dir is not None:
            from ttg_online_video_provider import PREDICTION
            ident=self.prediction.text().strip()
            if not PREDICTION.fullmatch(ident):
                self.log.appendPlainText("Invalid prediction ID")
                return
            self.destination_dir.mkdir(parents=True,exist_ok=True)
            path=str(self.destination_dir/("online-"+ident+".png"))
        else:
            path,_=QFileDialog.getSaveFileName(
                self,"Save AI image","creative-generated.png","PNG (*.png)"
            )
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
                    provenance={
                        "provider":"replicate",
                        "prediction_id":reply["prediction_id"],
                        "sha256":reply["sha256"],
                        "width":reply["width"],
                        "height":reply["height"],
                        "model_identity_verified":False,
                    }
                    if (self._submitted and
                        self._submitted.get("prediction_id")==reply["prediction_id"]):
                        # Recorded from the actual POST response, not a guess
                        # based on the currently displayed selector.
                        provenance.update({
                            "model":self._submitted["model"],
                            "quality":self._submitted.get("quality"),
                            "reference_supplied":self._submitted.get("reference_supplied",False),
                            "model_identity_verified":True,
                        })
                        if (self._submitted.get("reference_sha256")
                            and self._submitted.get("reference_supplied")):
                            provenance["reference_sha256"]=self._submitted["reference_sha256"]
                    self.import_callback(reply["path"],provenance)
                except Exception as exc:
                    self.log.appendPlainText("Import failed: "+str(exc))
            return
        self.prediction.setText(reply.get("prediction_id",""))
        self._latest=reply
        if kind=="submit":
            self._submitted=dict(reply)
            if self._pending_reference_sha and reply.get("reference_supplied"):
                self._submitted["reference_sha256"]=self._pending_reference_sha
            self._pending_reference_sha=None
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
