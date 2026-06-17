#!/usr/bin/env python3
"""Standalone TTG Creative Studio window."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QStatusBar

from ttg_creative_ui import CreativeStudioWidget


class CreativeStudioWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TTG Creative Studio")
        self.resize(1440, 820)
        self.setMinimumSize(1180, 680)
        self.setStatusBar(QStatusBar())
        self.setCentralWidget(CreativeStudioWidget())
        self.statusBar().showMessage("TTG Creative Studio ready")


def run() -> int:
    app = QApplication(sys.argv)
    window = CreativeStudioWindow()
    window.show()
    return app.exec()
