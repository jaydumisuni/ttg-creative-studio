#!/usr/bin/env python3
"""Asset and template browser widgets for TTG Creative Studio."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QListWidget, QVBoxLayout, QWidget


@dataclass
class BrowserItem:
    id: str
    name: str
    kind: str
    path: str = ""


class AssetTemplateBrowser(QWidget):
    assetSelected = pyqtSignal(str)
    templateSelected = pyqtSignal(str)

    def __init__(self, project_root: str | Path) -> None:
        super().__init__()
        self.project_root = Path(project_root)
        self.list = QListWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        self.items: list[BrowserItem] = []
        self.reload()
        self.list.itemDoubleClicked.connect(self._activate)

    def reload(self) -> None:
        self.items.clear()
        self.list.clear()
        self.items.extend([
            BrowserItem("template:ttg_cinematic", "THETECHGUY Cinematic Intro", "template"),
            BrowserItem("template:basic_intro", "Basic Intro", "template"),
            BrowserItem("asset:ghost", "Official TTG Ghost Logo", "asset", "resources/logo.png"),
            BrowserItem("asset:loading", "TTG Loading Animation", "asset", "resources/loding.gif"),
        ])
        for path in sorted((self.project_root / "resources").glob("*.png")):
            item_id = f"asset:{path.stem}"
            if not any(item.id == item_id for item in self.items):
                self.items.append(BrowserItem(item_id, path.stem, "asset", str(path)))
        for item in self.items:
            self.list.addItem(f"{item.kind.upper()} | {item.name}")

    def _activate(self, item) -> None:  # noqa: ANN001
        row = self.list.row(item)
        if row < 0 or row >= len(self.items):
            return
        selected = self.items[row]
        if selected.kind == "template":
            self.templateSelected.emit(selected.id)
        else:
            self.assetSelected.emit(selected.path)
