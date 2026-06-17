#!/usr/bin/env python3
"""Standalone TTG Creative Studio window."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QStatusBar

from ttg_creative_workspace import CreativeWorkspace


class CreativeStudioWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TTG Creative Studio")
        self.resize(1540, 900)
        self.setMinimumSize(1240, 720)
        self.setStatusBar(QStatusBar())
        self.setCentralWidget(CreativeWorkspace())
        self.statusBar().showMessage("TTG Creative Studio ready")


def run() -> int:
    app = QApplication(sys.argv)
    window = CreativeStudioWindow()
    window.show()
    return app.exec()
