#!/usr/bin/env python3
"""Standalone app window."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QStatusBar

from ttg_creative_workspace import CreativeWorkspace


class CreativeStudioWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TTG Creative Studio")
        self.resize(1280, 760)
        self.setMinimumSize(1024, 640)
        self.setStatusBar(QStatusBar())
        self.setCentralWidget(CreativeWorkspace())
        self.statusBar().showMessage("Ready")


def run() -> int:
    app = QApplication(sys.argv)
    window = CreativeStudioWindow()
    window.show()
    return app.exec()
