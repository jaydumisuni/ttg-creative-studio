#!/usr/bin/env python3
"""Studio-native brief-to-editable-campaign dialogue; no AI or cloud dependency."""
from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from ttg_campaign_composer import CampaignBrief, FORMATS, compose_campaign


class CampaignDesignerDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Design a Campaign · TTG Creative Studio")
        self.resize(850, 750)
        self.setMinimumSize(570, 520)
        # Keep the brief legible in both light and dark desktop Qt themes.
        # Without an explicit dialog background the white hero heading is
        # nearly invisible under Windows' default light QDialog palette.
        self.setStyleSheet("""
            QDialog {background-color:#101a2b;color:#ecf4fa;}
            QLabel {color:#d2e1ec;}
            QLineEdit, QComboBox {
                background-color:#19293c;color:#f6fbff;
                border:1px solid #456079;border-radius:6px;
                padding:5px 9px;min-height:23px;
            }
            QLineEdit:focus, QComboBox:focus {border:1px solid #66e8d8;}
            QComboBox QAbstractItemView {
                background:#19293c;color:#f6fbff;
                selection-background-color:#28636a;
            }
            QPushButton {
                background-color:#243c54;color:#eefbff;
                border:1px solid #50758d;border-radius:6px;
                padding:6px 12px;min-height:22px;
            }
            QPushButton:hover {background-color:#305671;border-color:#81dacf;}
            QPushButton#createCampaign {
                background-color:#146f69;color:#ffffff;
                border:1px solid #73e6d8;font-weight:700;
            }
            QPushButton#createCampaign:hover {background-color:#1c8981;}
            QPushButton:disabled {color:#839aa8;background-color:#263447;}
        """)
        self._temp = tempfile.TemporaryDirectory(prefix="ttg-campaign-preview-")
        self._preview_version = 0
        base = QVBoxLayout(self)
        title = QLabel("CREATE SOMETHING EXTRAORDINARY")
        title.setStyleSheet("font-weight:700;font-size:20px;color:#f6fcff;padding:8px 2px")
        base.addWidget(title)
        hint = QLabel("Create a layered, editable campaign. Works fully offline; no AI provider required.")
        hint.setWordWrap(True)
        base.addWidget(hint)

        self.layout_choice = QComboBox()
        for key, (name, w, h) in FORMATS.items():
            self.layout_choice.addItem(f"{name}    {w} × {h}", key)
        self.brand = QLineEdit("THETECHGUY")
        self.headline = QLineEdit("BEYOND THE ORDINARY.")
        self.subhead = QLineEdit("Designed to make your next move extraordinary.")
        self.product = QLineEdit("NEXT GENERATION")
        self.cta = QLineEdit("DISCOVER MORE")
        self.website = QLineEdit("thetechguyds.com")
        self.accent = QComboBox()
        self.accent.addItem("Aqua / Electric", "aqua")
        self.accent.addItem("Violet / Luxe", "violet")
        self.accent.addItem("Amber / Editorial", "amber")
        self.image = QLineEdit()
        self.image.setPlaceholderText("Optional product PNG / JPEG (leave blank for original illustration)")
        picker = QPushButton("Browse…")
        picker.clicked.connect(self.browse_image)
        image_line = QWidget()
        image_layout = QHBoxLayout(image_line)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.addWidget(self.image, 1)
        image_layout.addWidget(picker)
        form = QFormLayout()
        for label, widget in [
            ("Canvas", self.layout_choice), ("Brand", self.brand),
            ("Headline", self.headline), ("Supporting copy", self.subhead),
            ("Product label", self.product), ("Action button", self.cta),
            ("Website", self.website), ("Color story", self.accent),
            ("Product image", image_line),
        ]:
            form.addRow(label, widget)
        base.addLayout(form)

        self.preview = QLabel("Select your layout and press Preview to see the actual Studio render.")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(180)
        self.preview.setStyleSheet(
            "background:#070d1b;border:1px solid #35536c;border-radius:12px;color:#a5c2d1"
        )
        base.addWidget(self.preview, 1)
        note = QLabel("After creation you can drag, resize, replace, edit and export each layer in Studio.")
        note.setWordWrap(True)
        base.addWidget(note)
        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.make_preview = QPushButton("Preview Design")
        self.make_preview.clicked.connect(self.render_preview)
        self.create_button = QPushButton("Create Editable Campaign")
        self.create_button.setObjectName("createCampaign")
        self.create_button.clicked.connect(self.validate_and_accept)
        controls.addButton(self.make_preview, QDialogButtonBox.ButtonRole.ActionRole)
        controls.addButton(self.create_button, QDialogButtonBox.ButtonRole.AcceptRole)
        controls.rejected.connect(self.reject)
        base.addWidget(controls)

    def browse_image(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Choose product image", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if filename:
            self.image.setText(filename)

    def brief(self) -> CampaignBrief:
        value = CampaignBrief(
            layout=str(self.layout_choice.currentData()),
            brand=self.brand.text().strip(),
            headline=self.headline.text().strip(),
            subhead=self.subhead.text().strip(),
            product_name=self.product.text().strip(),
            cta=self.cta.text().strip(),
            website=self.website.text().strip(),
            accent=str(self.accent.currentData()),
            image_path=self.image.text().strip() or None,
        )
        value.validate()
        return value

    def render_preview(self) -> None:
        try:
            brief = self.brief()
            self._preview_version += 1
            root = Path(self._temp.name)/str(self._preview_version)
            self.make_preview.setEnabled(False)
            self.preview.setText("Rendering with the real Creative Studio engine…")
            result = compose_campaign(brief, root)
            pixmap = QPixmap(str(result["preview"]))
            if pixmap.isNull():
                raise RuntimeError("Studio failed to load the rendered image")
            self.preview.setPixmap(
                pixmap.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
            )
        except Exception as exc:
            self.preview.setText("Preview unavailable")
            QMessageBox.warning(self, "Campaign Preview", str(exc))
        finally:
            self.make_preview.setEnabled(True)

    def validate_and_accept(self) -> None:
        try:
            self.brief()
        except Exception as exc:
            QMessageBox.warning(self, "Campaign Brief", str(exc))
            return
        self.accept()

    def closeEvent(self, event) -> None:  # noqa: ANN001
        self._temp.cleanup()
        super().closeEvent(event)
