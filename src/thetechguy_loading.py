#!/usr/bin/env python3
"""
Reusable branded loading components for TheTechGuy desktop tools.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QDialog, QFrame, QLabel, QVBoxLayout, QWidget
from PyQt6.QtGui import QMovie


class LoadingVisual(QFrame):
    def __init__(
        self,
        logo_path: str | Path,
        gif_path: str | Path,
        title: str = "Loading…",
        status: str = "Please wait…",
        animation_size: int = 150,
        compact: bool = False,
    ) -> None:
        super().__init__()
        self._logo_path = Path(logo_path)
        self._gif_path = Path(gif_path)
        self._animation_size = animation_size
        self._movie: QMovie | None = None

        self.setObjectName("loadingCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(10 if compact else 12)

        self.animation_label = QLabel()
        self.animation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.animation_label.setMinimumHeight(animation_size)
        layout.addWidget(self.animation_label)

        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setObjectName("loadingTitle")
        layout.addWidget(self.title_label)

        self.status_label = QLabel(status)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("loadingStatus")
        layout.addWidget(self.status_label)

        self.setStyleSheet(
            """
            QFrame#loadingCard {
                background: rgba(8, 14, 28, 232);
                border: 1px solid rgba(83, 164, 255, 180);
                border-radius: 22px;
            }
            QLabel#loadingTitle {
                color: #f4f8ff;
                font-size: 18px;
                font-weight: 700;
            }
            QLabel#loadingStatus {
                color: #9fdfff;
                font-size: 12px;
            }
            """
        )
        self.refresh_media()

    def refresh_media(self) -> None:
        if self._movie is not None:
            self._movie.stop()
            self._movie.deleteLater()
            self._movie = None

        if self._gif_path.exists():
            movie = QMovie(str(self._gif_path))
            movie.setScaledSize(QSize(self._animation_size, self._animation_size))
            movie.start()
            self.animation_label.setMovie(movie)
            self._movie = movie
            return

        pixmap = QPixmap(str(self._logo_path))
        if not pixmap.isNull():
            self.animation_label.setPixmap(
                pixmap.scaled(
                    self._animation_size,
                    self._animation_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def set_status(self, status: str) -> None:
        self.status_label.setText(status)

    def set_assets(self, logo_path: str | Path, gif_path: str | Path) -> None:
        self._logo_path = Path(logo_path)
        self._gif_path = Path(gif_path)
        self.refresh_media()


class LoadingOverlay(QWidget):
    def __init__(
        self,
        parent: QWidget,
        logo_path: str | Path,
        gif_path: str | Path,
        title: str = "Processing…",
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(3, 7, 14, 170);")
        self.card = LoadingVisual(logo_path, gif_path, title=title, status="", animation_size=130, compact=True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 34, 34, 34)
        layout.addStretch()
        layout.addWidget(self.card, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        self.hide()

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        super().resizeEvent(event)
        self.setGeometry(self.parentWidget().rect())

    def show_message(self, title: str, status: str) -> None:
        self.card.set_title(title)
        self.card.set_status(status)
        self.raise_()
        self.show()

    def set_assets(self, logo_path: str | Path, gif_path: str | Path) -> None:
        self.card.set_assets(logo_path, gif_path)

    def hide_overlay(self) -> None:
        self.hide()


class StartupSplash(QDialog):
    def __init__(self, logo_path: str | Path, gif_path: str | Path) -> None:
        super().__init__(None, Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.setObjectName("startupSplash")
        self.setFixedSize(460, 370)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        self.visual = LoadingVisual(
            logo_path,
            gif_path,
            title="Starting…",
            status="Loading interface…",
            animation_size=180,
        )
        layout.addWidget(self.visual)

        self.setStyleSheet(
            """
            QDialog#startupSplash {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #040813, stop: 0.55 #091325, stop: 1 #120822
                );
                border: 1px solid rgba(83, 164, 255, 120);
                border-radius: 24px;
            }
            """
        )

    def set_status(self, status: str) -> None:
        self.visual.set_status(status)

    def set_title(self, title: str) -> None:
        self.visual.set_title(title)

    def set_assets(self, logo_path: str | Path, gif_path: str | Path) -> None:
        self.visual.set_assets(logo_path, gif_path)
