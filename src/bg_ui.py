#!/usr/bin/env python3
"""
Qt UI for TheTechGuy Image Editor.
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PyQt6.QtCore import QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QCloseEvent, QDragEnterEvent, QDropEvent, QIcon, QMovie, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from bg_core import (
    AI_MODELS,
    APP_NAME,
    WINDOW_TITLE,
    WINDOWS_APP_ID,
    app_root,
    build_mix_plan,
    build_trim_plan,
    loading_gif_path,
    parse_instruction,
    preferred_loading_gif_output,
    resource_path,
    run_startup_checks,
    run_local_processing,
    runtime_icon_path,
    save_copy,
)
from gif_builder import GifBuildOptions, PRESET_TEXT, build_preview_gif, save_loading_gif
from thetechguy_loading import LoadingOverlay, StartupSplash


def backend_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    if getattr(sys, "frozen", False):
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def backend_subprocess_command(*extra_args: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(app_root() / "TheTechGuy Image Editor Backend.exe"), *extra_args]
    return [sys.executable, str(app_root() / "bg_backend.py"), *extra_args]


def apply_windows_app_id() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except Exception:
        pass


class StartupCheckWorker(QThread):
    status = pyqtSignal(str)
    ready = pyqtSignal(object)
    error = pyqtSignal(str)

    def run(self) -> None:
        try:
            payload = run_startup_checks(self.status.emit)
            self.ready.emit(payload)
        except Exception as exc:
            self.error.emit(str(exc))


class AiProcessingWorker(QThread):
    progress = pyqtSignal(str)
    completed = pyqtSignal(str, object)
    error = pyqtSignal(str)

    def __init__(self, input_path: str, plan: dict[str, object]) -> None:
        super().__init__()
        self.input_path = input_path
        self.plan = dict(plan)

    def run(self) -> None:
        request_path: Path | None = None
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

        try:
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
                request_path = Path(handle.name)
                json.dump({"input_path": self.input_path, "plan": self.plan}, handle)

            process = subprocess.Popen(
                backend_subprocess_command("--process", str(request_path)),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
                cwd=str(app_root()),
                env=backend_subprocess_env(),
            )

            result: dict[str, object] | None = None
            assert process.stdout is not None
            for raw_line in process.stdout:
                line = raw_line.strip()
                if not line:
                    continue
                message = json.loads(line)
                message_type = message.get("type")
                if message_type == "status":
                    self.progress.emit(str(message["message"]))
                elif message_type == "result":
                    result = dict(message.get("payload", {}))
                elif message_type == "error":
                    raise RuntimeError(str(message.get("message", "AI processing failed.")))

            stderr = process.stderr.read().strip() if process.stderr is not None else ""
            exit_code = process.wait()
            if exit_code != 0:
                raise RuntimeError(stderr or "AI processing failed.")
            if result is None:
                raise RuntimeError("AI processing finished without a result.")
            self.completed.emit(str(result["output_path"]), result.get("plan", self.plan))
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            if request_path is not None:
                request_path.unlink(missing_ok=True)


class LocalProcessingWorker(QThread):
    progress = pyqtSignal(str)
    completed = pyqtSignal(str, object)
    error = pyqtSignal(str)

    def __init__(self, input_path: str, plan: dict[str, object]) -> None:
        super().__init__()
        self.input_path = input_path
        self.plan = dict(plan)

    def run(self) -> None:
        try:
            output_path = run_local_processing(self.input_path, self.plan, self.progress.emit)
            self.completed.emit(str(output_path), self.plan)
        except Exception as exc:
            self.error.emit(str(exc))


class SaveCopyWorker(QThread):
    progress = pyqtSignal(str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, source_path: str, destination_path: str) -> None:
        super().__init__()
        self.source_path = source_path
        self.destination_path = destination_path

    def run(self) -> None:
        try:
            self.progress.emit("Saving copy…")
            saved_path = save_copy(self.source_path, self.destination_path)
            self.completed.emit(saved_path)
        except Exception as exc:
            self.error.emit(str(exc))


class GifBuildWorker(QThread):
    progress = pyqtSignal(str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, options: GifBuildOptions, destination_path: str | None = None) -> None:
        super().__init__()
        self.options = options
        self.destination_path = destination_path

    def run(self) -> None:
        try:
            self.progress.emit("Rendering animated loading GIF…")
            if self.destination_path:
                output_path = save_loading_gif(self.options, self.destination_path)
            else:
                output_path = build_preview_gif(self.options)
            self.completed.emit(output_path)
        except Exception as exc:
            self.error.emit(str(exc))


class Bubble(QLabel):
    def __init__(self, text: str, role: str) -> None:
        super().__init__(text)
        self.setWordWrap(True)
        self.setMaximumWidth(280)

        if role == "user":
            self.setStyleSheet(
                """
                QLabel {
                    background: #122241;
                    color: #eef5ff;
                    border: 1px solid #55bfff;
                    border-radius: 13px;
                    padding: 8px 10px;
                    font-size: 12px;
                }
                """
            )
        elif role == "assistant":
            self.setStyleSheet(
                """
                QLabel {
                    background: #14111f;
                    color: #dee8ff;
                    border: 1px solid #355cf0;
                    border-radius: 13px;
                    padding: 8px 10px;
                    font-size: 12px;
                }
                """
            )
        else:
            self.setStyleSheet("color: #8edcff; font-size: 11px; padding: 2px 4px;")


class ImagePreviewPanel(QFrame):
    fileDropped = pyqtSignal(str)

    SUPPORTED = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"}

    def __init__(self) -> None:
        super().__init__()
        self._preview_path: str | None = None
        self._editor_mode = False
        self.setAcceptDrops(True)
        self.setObjectName("previewPanel")
        self.setMinimumSize(560, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setObjectName("previewCanvas")
        self.preview_label.setMinimumSize(520, 460)
        layout.addWidget(self.preview_label)

        self.overlay = LoadingOverlay(self, resource_path("logo.png"), loading_gif_path(), title="Processing…")
        self._set_idle()

        self._apply_panel_style()

    def _apply_panel_style(self) -> None:
        if self._editor_mode:
            panel_bg = "#1a1c20"
            panel_border = "#383d45"
            canvas_border = "#4b515c"
            canvas_bg = "#121418"
            text = "#d9dde5"
            panel_radius = "10px"
            canvas_radius = "6px"
        else:
            panel_bg = "#09111e"
            panel_border = "#18305f"
            canvas_border = "#1f3570"
            canvas_bg = "#07111d"
            text = "#c5d4ff"
            panel_radius = "24px"
            canvas_radius = "20px"

        self.setStyleSheet(
            f"""
            QFrame#previewPanel {{
                background: {panel_bg};
                border: 1px solid {panel_border};
                border-radius: {panel_radius};
            }}
            QLabel#previewCanvas {{
                border: 1px solid {canvas_border};
                border-radius: {canvas_radius};
                background: {canvas_bg};
                color: {text};
                font-size: 14px;
            }}
            """
        )

    def set_editor_mode(self, editor_mode: bool) -> None:
        self._editor_mode = editor_mode
        self._apply_panel_style()
        if self._preview_path:
            self._render_preview()

    def set_loading_assets(self) -> None:
        self.overlay.set_assets(resource_path("logo.png"), loading_gif_path())

    def _render_preview(self) -> None:
        if not self._preview_path:
            return
        pixmap = QPixmap(self._preview_path)
        if pixmap.isNull():
            self._set_idle()
            return

        size = self.preview_label.size()
        canvas = QPixmap(size)
        canvas.fill(Qt.GlobalColor.transparent)

        painter = QPainter(canvas)
        tile = 18
        for y in range(0, size.height(), tile):
            for x in range(0, size.width(), tile):
                if self._editor_mode:
                    colour = QColor("#23262b") if (x // tile + y // tile) % 2 == 0 else QColor("#171a1e")
                else:
                    colour = QColor("#163048") if (x // tile + y // tile) % 2 == 0 else QColor("#0c1828")
                painter.fillRect(x, y, tile, tile, colour)

        scaled = pixmap.scaled(
            size.width() - 28,
            size.height() - 28,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawPixmap(
            (size.width() - scaled.width()) // 2,
            (size.height() - scaled.height()) // 2,
            scaled,
        )
        painter.end()

        self.preview_label.setPixmap(canvas)
        self.preview_label.setText("")

    def _set_idle(self) -> None:
        self._preview_path = None
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText("Drop an image here\nor click to browse")

    def set_preview(self, path: str) -> None:
        self._preview_path = path
        self._render_preview()

    def clear(self) -> None:
        self._set_idle()

    def show_loading(self, title: str, status: str) -> None:
        self.overlay.show_message(title, status)

    def hide_loading(self) -> None:
        self.overlay.hide_overlay()

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        super().resizeEvent(event)
        self.overlay.setGeometry(self.rect())
        if self._preview_path:
            self._render_preview()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if not event.mimeData().hasUrls():
            return
        path = event.mimeData().urls()[0].toLocalFile()
        if Path(path).suffix.lower() in self.SUPPORTED:
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        path = event.mimeData().urls()[0].toLocalFile()
        if Path(path).suffix.lower() in self.SUPPORTED:
            self.fileDropped.emit(path)

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff)",
        )
        if path:
            self.fileDropped.emit(path)
        event.accept()


class GifBuilderDialog(QDialog):
    gifSaved = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Loading GIF")
        self.resize(980, 640)
        self.setMinimumSize(900, 600)

        self._preview_movie: QMovie | None = None
        self._preview_path: str | None = None
        self._preview_worker: GifBuildWorker | None = None
        self._save_worker: GifBuildWorker | None = None

        self._build_ui()
        self._build_menu_bar()
        self._apply_theme()
        QTimer.singleShot(0, self._render_preview)

    def _build_ui(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(14)

        controls_card = QFrame()
        controls_card.setObjectName("builderCard")
        controls_card.setFixedWidth(340)
        controls_layout = QVBoxLayout(controls_card)
        controls_layout.setContentsMargins(18, 18, 18, 18)
        controls_layout.setSpacing(10)

        title = QLabel("GIF Builder")
        title.setObjectName("panelTitle")
        controls_layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)

        source_row = QWidget()
        source_layout = QHBoxLayout(source_row)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.setSpacing(8)
        self.source_edit = QLineEdit(str(resource_path("logo.png")))
        source_layout.addWidget(self.source_edit, 1)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse_source)
        source_layout.addWidget(browse_button)
        form.addRow("Logo / image", source_row)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(PRESET_TEXT))
        self.preset_combo.currentTextChanged.connect(self._preset_changed)
        form.addRow("Preset", self.preset_combo)

        self.text_edit = QLineEdit(PRESET_TEXT["Loading"])
        form.addRow("Custom text", self.text_edit)

        size_row = QWidget()
        size_layout = QHBoxLayout(size_row)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.setSpacing(8)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(128, 1200)
        self.width_spin.setValue(600)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(128, 1200)
        self.height_spin.setValue(600)
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(QLabel("x"))
        size_layout.addWidget(self.height_spin)
        form.addRow("GIF size", size_row)

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(8, 30)
        self.fps_spin.setValue(18)
        form.addRow("FPS", self.fps_spin)

        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(1.2, 8.0)
        self.duration_spin.setSingleStep(0.2)
        self.duration_spin.setDecimals(1)
        self.duration_spin.setValue(2.6)
        form.addRow("Loop length", self.duration_spin)

        self.glow_spin = QDoubleSpinBox()
        self.glow_spin.setRange(0.0, 4.0)
        self.glow_spin.setSingleStep(0.1)
        self.glow_spin.setDecimals(1)
        self.glow_spin.setValue(1.2)
        form.addRow("Glow strength", self.glow_spin)

        self.pulse_spin = QDoubleSpinBox()
        self.pulse_spin.setRange(0.0, 0.35)
        self.pulse_spin.setSingleStep(0.01)
        self.pulse_spin.setDecimals(2)
        self.pulse_spin.setValue(0.11)
        form.addRow("Pulse strength", self.pulse_spin)

        self.background_combo = QComboBox()
        self.background_combo.addItem("Transparent", "transparent")
        self.background_combo.addItem("Dark", "dark")
        self.background_combo.addItem("Checkerboard Preview", "checkerboard")
        self.background_combo.currentIndexChanged.connect(self._update_preview_surface)
        form.addRow("Background", self.background_combo)

        self.ring_check = QCheckBox("Enable halo ring")
        self.ring_check.setChecked(True)
        form.addRow("", self.ring_check)

        controls_layout.addLayout(form)

        self.builder_status = QLabel("Preview the animation, then save it anywhere you want.")
        self.builder_status.setWordWrap(True)
        self.builder_status.setObjectName("hintText")
        controls_layout.addWidget(self.builder_status)

        button_grid = QGridLayout()
        button_grid.setHorizontalSpacing(8)
        button_grid.setVerticalSpacing(8)

        preview_button = QPushButton("Preview")
        preview_button.clicked.connect(self._render_preview)
        button_grid.addWidget(preview_button, 0, 0)

        replace_button = QPushButton("Replace App GIF")
        replace_button.clicked.connect(self._replace_app_gif)
        button_grid.addWidget(replace_button, 0, 1)

        save_button = QPushButton("Save As…")
        save_button.clicked.connect(self._save_as)
        button_grid.addWidget(save_button, 1, 0, 1, 2)

        controls_layout.addLayout(button_grid)
        controls_layout.addStretch()
        root_layout.addWidget(controls_card)

        preview_card = QFrame()
        preview_card.setObjectName("builderCard")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(18, 18, 18, 18)
        preview_layout.setSpacing(12)

        preview_title = QLabel("Animated Preview")
        preview_title.setObjectName("panelTitle")
        preview_layout.addWidget(preview_title)

        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("gifPreviewFrame")
        self.preview_frame.setMinimumSize(520, 520)
        self.preview_layout_inner = QVBoxLayout(self.preview_frame)
        self.preview_layout_inner.setContentsMargins(12, 12, 12, 12)
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_layout_inner.addWidget(self.preview_label)
        preview_layout.addWidget(self.preview_frame, 1)

        self.preview_overlay = LoadingOverlay(
            self.preview_frame,
            resource_path("logo.png"),
            loading_gif_path(),
            title="Building GIF…",
        )

        root_layout.addWidget(preview_card, 1)
        self._update_preview_surface()

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QDialog, QWidget {
                background: #060a14;
                color: #e9f1ff;
                font-family: "Segoe UI", "Bahnschrift";
                font-size: 13px;
            }
            QFrame#builderCard {
                background: #0b1220;
                border: 1px solid #18305f;
                border-radius: 22px;
            }
            QLabel#panelTitle {
                color: #f5f9ff;
                font-size: 18px;
                font-weight: 700;
            }
            QLabel#hintText {
                color: #9fd8ff;
                font-size: 12px;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background: #10182a;
                color: #f1f7ff;
                border: 1px solid #2444da;
                border-radius: 10px;
                padding: 7px 10px;
            }
            QPushButton {
                background: #182552;
                color: #f1f7ff;
                border: 1px solid #3f72ff;
                border-radius: 10px;
                padding: 9px 16px;
            }
            QPushButton:hover {
                background: #22346e;
                border-color: #72ddff;
            }
            QFrame#gifPreviewFrame {
                background: #08111d;
                border: 1px solid #1d356c;
                border-radius: 18px;
            }
            """
        )

    def _browse_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Logo or Image",
            self.source_edit.text(),
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff)",
        )
        if path:
            self.source_edit.setText(path)
            self._render_preview()

    def _preset_changed(self, preset: str) -> None:
        if not self.text_edit.text().strip() or self.text_edit.text().strip() in PRESET_TEXT.values():
            self.text_edit.setText(PRESET_TEXT.get(preset, preset))
        self._render_preview()

    def _background_value(self) -> str:
        raw_value = str(self.background_combo.currentData())
        return "transparent" if raw_value == "checkerboard" else raw_value

    def _options(self) -> GifBuildOptions:
        return GifBuildOptions(
            source_path=self.source_edit.text().strip() or str(resource_path("logo.png")),
            text=self.text_edit.text().strip() or PRESET_TEXT.get(self.preset_combo.currentText(), "Loading"),
            preset=self.preset_combo.currentText(),
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            fps=self.fps_spin.value(),
            duration_seconds=self.duration_spin.value(),
            glow_strength=self.glow_spin.value(),
            pulse_strength=self.pulse_spin.value(),
            background=self._background_value(),
            ring_enabled=self.ring_check.isChecked(),
        )

    def _clear_preview_movie(self) -> None:
        if self._preview_movie is not None:
            self._preview_movie.stop()
            self._preview_movie.deleteLater()
            self._preview_movie = None

    def _update_preview_surface(self, *_args) -> None:
        if str(self.background_combo.currentData()) == "checkerboard":
            self.preview_frame.setStyleSheet(
                """
                QFrame#gifPreviewFrame {
                    border: 1px solid #1d356c;
                    border-radius: 18px;
                    background-color: #08111d;
                    background-image:
                        linear-gradient(45deg, #173149 25%, transparent 25%),
                        linear-gradient(-45deg, #173149 25%, transparent 25%),
                        linear-gradient(45deg, transparent 75%, #0e1e32 75%),
                        linear-gradient(-45deg, transparent 75%, #0e1e32 75%);
                    background-size: 28px 28px;
                    background-position: 0 0, 0 14px, 14px -14px, -14px 0;
                }
                """
            )
        else:
            self.preview_frame.setStyleSheet(
                """
                QFrame#gifPreviewFrame {
                    border: 1px solid #1d356c;
                    border-radius: 18px;
                    background: #08111d;
                }
                """
            )

    def _render_preview(self) -> None:
        if self._preview_worker is not None and self._preview_worker.isRunning():
            return
        if not Path(self._options().source_path).exists():
            self.builder_status.setText("Select a valid logo or image before rendering the preview.")
            return

        self.preview_overlay.show_message("Building GIF…", "Rendering animated preview…")
        self.builder_status.setText("Rendering preview…")
        self._preview_worker = GifBuildWorker(self._options())
        self._preview_worker.progress.connect(
            lambda message: self.preview_overlay.show_message("Building GIF…", message)
        )
        self._preview_worker.completed.connect(self._preview_ready)
        self._preview_worker.error.connect(self._worker_error)
        self._preview_worker.start()

    def _preview_ready(self, preview_path: str) -> None:
        self._preview_path = preview_path
        self._clear_preview_movie()
        movie = QMovie(preview_path)
        movie.setScaledSize(self.preview_label.size())
        self.preview_label.setMovie(movie)
        self._preview_movie = movie
        movie.start()
        self.preview_overlay.hide_overlay()
        self.builder_status.setText("Preview ready.")

    def _default_save_target(self) -> str:
        return str(preferred_loading_gif_output())

    def _replace_app_gif(self) -> None:
        self._save_to(self._default_save_target())

    def _save_as(self) -> None:
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Save Loading GIF",
            self._default_save_target(),
            "GIF Image (*.gif)",
        )
        if not target:
            return
        if not target.lower().endswith(".gif"):
            target = f"{target}.gif"
        self._save_to(target)

    def _save_to(self, target: str) -> None:
        if self._save_worker is not None and self._save_worker.isRunning():
            return
        if not Path(self._options().source_path).exists():
            self.builder_status.setText("Select a valid logo or image before saving.")
            return

        self.preview_overlay.show_message("Saving…", "Writing animated GIF…")
        self.builder_status.setText(f"Saving to {target}…")
        self._save_worker = GifBuildWorker(self._options(), target)
        self._save_worker.progress.connect(
            lambda message: self.preview_overlay.show_message("Saving…", message)
        )
        self._save_worker.completed.connect(self._save_ready)
        self._save_worker.error.connect(self._worker_error)
        self._save_worker.start()

    def _save_ready(self, path: str) -> None:
        self.preview_overlay.hide_overlay()
        self.builder_status.setText(f"Saved animated GIF to {path}")
        self.gifSaved.emit(path)

    def _worker_error(self, message: str) -> None:
        self.preview_overlay.hide_overlay()
        self.builder_status.setText(f"Error: {message}")
        QMessageBox.critical(self, "GIF Builder", message)

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        super().resizeEvent(event)
        self.preview_overlay.setGeometry(self.preview_frame.rect())
        if self._preview_movie is not None:
            self._preview_movie.setScaledSize(self.preview_label.size())


class MainWindow(QMainWindow):
    def __init__(self, startup_info: dict[str, object] | None = None) -> None:
        super().__init__()
        self.startup_info = startup_info or {}
        self.ai_available = bool(self.startup_info.get("ai_available", True))
        self.ai_error = str(self.startup_info.get("ai_error") or "").strip()
        self._input_path: str | None = None
        self._output_path: str | None = None
        self._display_path: str | None = None
        self._mix_output_path: str | None = None
        self._last_plan: dict[str, object] | None = None
        self._active_plan: dict[str, object] | None = None
        self._worker: QThread | None = None
        self._save_worker: SaveCopyWorker | None = None
        self._logo_pixmap = QPixmap(str(resource_path("logo.png")))

        self.setWindowTitle(APP_NAME)
        self.resize(1380, 680)
        self.setMinimumSize(1180, 620)
        self.setStatusBar(QStatusBar())

        icon_path = runtime_icon_path()
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_ui()
        self._build_menu_bar()
        self._apply_theme()
        self._bind_simple_actions()
        self._update_trim_labels()
        self._update_mix_labels()
        if not self.ai_available:
            self.engine_combo.setCurrentIndex(1)
        self._mode_switch_changed()
        self._update_mode_controls()
        self._add_activity("Drop an image to start, or use the Simple tools on the left.", "assistant")
        if not self.ai_available:
            self._add_activity(f"AI is unavailable right now. {self.ai_error}", "assistant")
            self.result_summary.setText(
                "AI background removal is unavailable right now. Quick Trim and Color mode still work."
            )
            self.summary_chip.setText("AI unavailable")
        self._set_busy(False)
        self.statusBar().showMessage("Ready.")

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer_layout = QVBoxLayout(root)
        outer_layout.setContentsMargins(14, 14, 14, 14)
        outer_layout.setSpacing(12)
        self.outer_layout = outer_layout

        self.header = QFrame()
        self.header.setObjectName("headerCard")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(12)

        self.logo_label = QLabel()
        header_layout.addWidget(self.logo_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.title_label = QLabel(APP_NAME)
        self.title_label.setObjectName("headerTitle")
        self.subtitle_label = QLabel("Simple actions on the left. Full editing control in Advanced.")
        self.subtitle_label.setObjectName("headerSubtitle")
        self.tagline_label = QLabel(
            "Offline AI cutouts, quick trim cleanup, reusable loading GIFs, and focused editing tools."
        )
        self.tagline_label.setObjectName("headerTagline")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)
        title_col.addWidget(self.tagline_label)
        header_layout.addLayout(title_col, 1)

        self.simple_button = QPushButton("Simple")
        self.simple_button.setCheckable(True)
        self.advanced_button = QPushButton("Advanced")
        self.advanced_button.setCheckable(True)

        self.mode_switch_group = QButtonGroup(self)
        self.mode_switch_group.setExclusive(True)
        self.mode_switch_group.addButton(self.simple_button, 0)
        self.mode_switch_group.addButton(self.advanced_button, 1)
        self.simple_button.setChecked(True)
        self.mode_switch_group.buttonClicked.connect(self._mode_switch_changed)

        switch_row = QHBoxLayout()
        switch_row.setSpacing(8)
        switch_row.addWidget(self.simple_button)
        switch_row.addWidget(self.advanced_button)

        gif_builder_button = QPushButton("Create Loading GIF")
        gif_builder_button.clicked.connect(self._open_gif_builder)
        switch_row.addWidget(gif_builder_button)
        header_layout.addLayout(switch_row)
        outer_layout.addWidget(self.header)

        self.advanced_toolbar = QFrame()
        self.advanced_toolbar.setObjectName("editorBar")
        advanced_toolbar_layout = QHBoxLayout(self.advanced_toolbar)
        advanced_toolbar_layout.setContentsMargins(12, 8, 12, 8)
        advanced_toolbar_layout.setSpacing(10)

        toolbar_brand = QLabel(APP_NAME)
        toolbar_brand.setObjectName("editorBrand")
        advanced_toolbar_layout.addWidget(toolbar_brand)

        for label in ("File", "Edit", "Image", "Layer", "Select", "Filter", "View", "Window", "Help"):
            menu_label = QLabel(label)
            menu_label.setObjectName("editorMenuLabel")
            advanced_toolbar_layout.addWidget(menu_label)

        advanced_toolbar_layout.addStretch()

        self.toolbar_load_button = QPushButton("Open")
        self.toolbar_load_button.setObjectName("toolbarButton")
        self.toolbar_load_button.clicked.connect(self._browse_image)
        advanced_toolbar_layout.addWidget(self.toolbar_load_button)

        self.toolbar_run_button = QPushButton("Run")
        self.toolbar_run_button.setObjectName("toolbarButton")
        self.toolbar_run_button.clicked.connect(self._run_advanced)
        advanced_toolbar_layout.addWidget(self.toolbar_run_button)

        self.toolbar_reprocess_button = QPushButton("Re-process")
        self.toolbar_reprocess_button.setObjectName("toolbarButton")
        self.toolbar_reprocess_button.clicked.connect(self._reprocess)
        advanced_toolbar_layout.addWidget(self.toolbar_reprocess_button)

        self.toolbar_save_button = QPushButton("Save")
        self.toolbar_save_button.setObjectName("toolbarButton")
        self.toolbar_save_button.clicked.connect(self._save_as)
        advanced_toolbar_layout.addWidget(self.toolbar_save_button)

        self.toolbar_gif_button = QPushButton("GIF Builder")
        self.toolbar_gif_button.setObjectName("toolbarButton")
        self.toolbar_gif_button.clicked.connect(self._open_gif_builder)
        advanced_toolbar_layout.addWidget(self.toolbar_gif_button)

        self.advanced_toolbar.hide()
        outer_layout.addWidget(self.advanced_toolbar)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        outer_layout.addWidget(self.main_splitter, 1)

        self.sidebar = QScrollArea()
        self.sidebar.setWidgetResizable(True)
        self.sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar.setObjectName("sidebarArea")
        sidebar_host = QWidget()
        self.sidebar_layout = QVBoxLayout(sidebar_host)
        self.sidebar_layout.setContentsMargins(0, 0, 8, 0)
        self.sidebar_layout.setSpacing(12)
        self.sidebar.setWidget(sidebar_host)
        self.main_splitter.addWidget(self.sidebar)

        self.simple_page = self._build_simple_page()
        self.sidebar_layout.addWidget(self.simple_page)
        self.sidebar_layout.addStretch()

        self.work_card = QFrame()
        self.work_card.setObjectName("workCard")
        right_layout = QVBoxLayout(self.work_card)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(12)
        self.work_layout = right_layout

        info_row = QHBoxLayout()
        self.file_title = QLabel("No image loaded")
        self.file_title.setObjectName("panelTitle")
        info_row.addWidget(self.file_title, 1)

        self.summary_chip = QLabel("Ready")
        self.summary_chip.setObjectName("summaryChip")
        info_row.addWidget(self.summary_chip, 0, Qt.AlignmentFlag.AlignRight)
        right_layout.addLayout(info_row)

        self.editor_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.editor_splitter.setChildrenCollapsible(False)
        right_layout.addWidget(self.editor_splitter, 1)

        preview_host = QWidget()
        preview_layout = QVBoxLayout(preview_host)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(12)

        self.canvas_shell = QWidget()
        canvas_shell_layout = QHBoxLayout(self.canvas_shell)
        canvas_shell_layout.setContentsMargins(0, 0, 0, 0)
        canvas_shell_layout.setSpacing(12)

        self.tool_rail = QFrame()
        self.tool_rail.setObjectName("toolRail")
        self.tool_rail.setFixedWidth(64)
        tool_rail_layout = QVBoxLayout(self.tool_rail)
        tool_rail_layout.setContentsMargins(8, 10, 8, 10)
        tool_rail_layout.setSpacing(8)

        self.tool_open_button = QPushButton("Op")
        self.tool_open_button.setObjectName("toolRailButton")
        self.tool_open_button.clicked.connect(self._browse_image)
        tool_rail_layout.addWidget(self.tool_open_button)

        self.tool_ai_button = QPushButton("AI")
        self.tool_ai_button.setObjectName("toolRailButton")
        self.tool_ai_button.setCheckable(True)
        self.tool_ai_button.clicked.connect(lambda: self._set_editor_engine("ai"))
        tool_rail_layout.addWidget(self.tool_ai_button)

        self.tool_colour_button = QPushButton("BG")
        self.tool_colour_button.setObjectName("toolRailButton")
        self.tool_colour_button.setCheckable(True)
        self.tool_colour_button.clicked.connect(lambda: self._set_editor_engine("colour"))
        tool_rail_layout.addWidget(self.tool_colour_button)

        self.tool_trim_button = QPushButton("Tr")
        self.tool_trim_button.setObjectName("toolRailButton")
        self.tool_trim_button.setCheckable(True)
        self.tool_trim_button.clicked.connect(lambda: self._set_editor_engine("trim"))
        tool_rail_layout.addWidget(self.tool_trim_button)

        self.tool_gif_button = QPushButton("GF")
        self.tool_gif_button.setObjectName("toolRailButton")
        self.tool_gif_button.clicked.connect(self._open_gif_builder)
        tool_rail_layout.addWidget(self.tool_gif_button)
        tool_rail_layout.addStretch()
        canvas_shell_layout.addWidget(self.tool_rail)

        self.preview_panel = ImagePreviewPanel()
        self.preview_panel.fileDropped.connect(self._on_file)
        canvas_shell_layout.addWidget(self.preview_panel, 1)
        preview_layout.addWidget(self.canvas_shell, 1)

        self.result_summary = QLabel(
            "Load an image, run a quick action in Simple mode, or switch to Advanced for direct control."
        )
        self.result_summary.setWordWrap(True)
        self.result_summary.setObjectName("hintText")
        preview_layout.addWidget(self.result_summary)
        self.editor_splitter.addWidget(preview_host)

        self.inspector_card = QFrame()
        self.inspector_card.setObjectName("inspectorCard")
        self.inspector_card.setMinimumWidth(250)
        inspector_layout = QVBoxLayout(self.inspector_card)
        inspector_layout.setContentsMargins(16, 16, 16, 16)
        inspector_layout.setSpacing(10)

        self.properties_card = QFrame()
        self.properties_card.setObjectName("dockCard")
        properties_layout = QVBoxLayout(self.properties_card)
        properties_layout.setContentsMargins(12, 12, 12, 12)
        properties_layout.setSpacing(8)

        properties_title = QLabel("Properties")
        properties_title.setObjectName("miniTitle")
        properties_layout.addWidget(properties_title)

        self.inspector_note = QLabel("Mode hints, activity, and run status appear here while you work.")
        self.inspector_note.setWordWrap(True)
        self.inspector_note.setObjectName("hintText")
        properties_layout.addWidget(self.inspector_note)

        self.advanced_page = self._build_advanced_page()
        properties_layout.addWidget(self.advanced_page)
        inspector_layout.addWidget(self.properties_card, 3)

        self.history_card = QFrame()
        self.history_card.setObjectName("dockCard")
        history_layout = QVBoxLayout(self.history_card)
        history_layout.setContentsMargins(12, 12, 12, 12)
        history_layout.setSpacing(8)

        history_title = QLabel("History")
        history_title.setObjectName("miniTitle")
        history_layout.addWidget(history_title)

        self.activity_scroll = QScrollArea()
        self.activity_scroll.setWidgetResizable(True)
        self.activity_inner = QWidget()
        self.activity_layout = QVBoxLayout(self.activity_inner)
        self.activity_layout.setContentsMargins(8, 8, 8, 8)
        self.activity_layout.setSpacing(7)
        self.activity_layout.addStretch()
        self.activity_scroll.setWidget(self.activity_inner)
        history_layout.addWidget(self.activity_scroll, 1)
        inspector_layout.addWidget(self.history_card, 2)
        self.editor_splitter.addWidget(self.inspector_card)

        self.footer_bar = QWidget()
        footer_row = QHBoxLayout(self.footer_bar)
        footer_row.setSpacing(10)
        footer_row.setContentsMargins(0, 0, 0, 0)

        self.load_button = QPushButton("Load Image")
        self.load_button.clicked.connect(self._browse_image)
        footer_row.addWidget(self.load_button)

        self.reprocess_button = QPushButton("Re-process")
        self.reprocess_button.clicked.connect(self._reprocess)
        footer_row.addWidget(self.reprocess_button)

        self.save_button = QPushButton("Save As…")
        self.save_button.clicked.connect(self._save_as)
        footer_row.addWidget(self.save_button)
        footer_row.addStretch()
        right_layout.addWidget(self.footer_bar)

        self.main_splitter.addWidget(self.work_card)
        self.main_splitter.setSizes([320, 960])
        self.editor_splitter.setSizes([760, 260])
        self._refresh_header_branding(False)

    def _build_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(False)

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self._make_menu_action("Open Image…", self._browse_image, "Ctrl+O"))
        file_menu.addAction(self._make_menu_action("Save As…", self._save_as, "Ctrl+S"))
        file_menu.addAction(self._make_menu_action("Create Loading GIF…", self._open_gif_builder))
        file_menu.addSeparator()
        file_menu.addAction(self._make_menu_action("Exit", self.close, "Alt+F4"))

        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self._make_menu_action("Re-process", self._reprocess, "Ctrl+R"))
        edit_menu.addAction(self._make_menu_action("Re-process Quick Trim", self._reprocess_trim))

        image_menu = menu_bar.addMenu("&Image")
        image_menu.addAction(self._make_menu_action("Remove Background", lambda: self._run_simple_instruction("remove the background")))
        image_menu.addAction(self._make_menu_action("Keep Subject", lambda: self._run_simple_instruction("keep only the subject")))
        image_menu.addAction(self._make_menu_action("Remove White Background", self._run_simple_white_background))
        image_menu.addAction(self._make_menu_action("Quick Trim", self._run_simple_trim))
        image_menu.addAction(self._make_menu_action("Preview Canvas Compose", self._run_simple_mix_preview))

        layer_menu = menu_bar.addMenu("&Layer")
        layer_menu.addAction(self._make_menu_action("Preview Canvas Compose", self._run_simple_mix_preview))
        layer_menu.addAction(self._make_menu_action("Save Composed As...", self._save_mixed_as))

        select_menu = menu_bar.addMenu("&Select")
        select_menu.addAction(self._make_menu_action("AI Mode", lambda: self._set_editor_engine("ai")))
        select_menu.addAction(self._make_menu_action("Color Mode", lambda: self._set_editor_engine("colour")))
        select_menu.addAction(self._make_menu_action("Quick Trim Mode", lambda: self._set_editor_engine("trim")))

        filter_menu = menu_bar.addMenu("&Filter")
        filter_menu.addAction(self._make_menu_action("Quick Trim", self._run_simple_trim))
        filter_menu.addAction(self._make_menu_action("Re-process Quick Trim", self._reprocess_trim))
        filter_menu.addAction(self._make_menu_action("Remove White Background", self._run_simple_white_background))

        adjust_menu = menu_bar.addMenu("&Adjust")
        adjust_menu.addAction(self._make_menu_action("Threshold +", lambda: self._nudge_trim_threshold(4)))
        adjust_menu.addAction(self._make_menu_action("Threshold -", lambda: self._nudge_trim_threshold(-4)))
        adjust_menu.addAction(self._make_menu_action("Softness +", lambda: self._nudge_trim_softness(1)))
        adjust_menu.addAction(self._make_menu_action("Softness -", lambda: self._nudge_trim_softness(-1)))

        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self._make_menu_action("Simple Workspace", self._activate_simple_mode))
        view_menu.addAction(self._make_menu_action("Advanced Workspace", self._activate_advanced_mode))
        view_menu.addAction(self._make_menu_action("Reset Workspace Layout", self._reset_workspace_layout))

        window_menu = menu_bar.addMenu("&Window")
        self.toggle_inspector_action = self._make_menu_action("Show Inspector", self._toggle_inspector)
        self.toggle_inspector_action.setCheckable(True)
        self.toggle_inspector_action.setChecked(True)
        window_menu.addAction(self.toggle_inspector_action)

        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(self._make_menu_action("Model Status", self._show_model_status))
        help_menu.addAction(self._make_menu_action("About", self._show_about_dialog))

    def _make_menu_action(self, text: str, slot: callable, shortcut: str | None = None) -> QAction:
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        return action

    def _build_simple_page(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sidebarCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("Simple")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        hint = QLabel("Load an image, use ready-made actions, or just trim, save, and move on.")
        hint.setWordWrap(True)
        hint.setObjectName("hintText")
        layout.addWidget(hint)

        self.simple_load_button = QPushButton("Load Image")
        layout.addWidget(self.simple_load_button)

        self.simple_remove_bg_button = QPushButton("Remove Background")
        layout.addWidget(self.simple_remove_bg_button)

        self.simple_keep_subject_button = QPushButton("Keep Subject")
        layout.addWidget(self.simple_keep_subject_button)

        self.simple_remove_white_button = QPushButton("Remove White Background")
        layout.addWidget(self.simple_remove_white_button)

        self.simple_quick_trim_button = QPushButton("Quick Trim")
        layout.addWidget(self.simple_quick_trim_button)

        trim_title = QLabel("Quick Trim Controls")
        trim_title.setObjectName("miniTitle")
        layout.addWidget(trim_title)

        self.simple_trim_card = QFrame()
        self.simple_trim_card.setObjectName("controlCard")
        simple_trim_layout = QVBoxLayout(self.simple_trim_card)
        simple_trim_layout.setContentsMargins(12, 12, 12, 12)
        simple_trim_layout.setSpacing(8)

        simple_threshold_row = QHBoxLayout()
        simple_threshold_row.addWidget(QLabel("Threshold"))
        self.simple_trim_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.simple_trim_threshold_slider.setRange(8, 120)
        self.simple_trim_threshold_slider.setValue(36)
        self.simple_trim_threshold_slider.valueChanged.connect(self._sync_trim_threshold_from_simple)
        simple_threshold_row.addWidget(self.simple_trim_threshold_slider, 1)
        self.simple_trim_threshold_label = QLabel("36")
        simple_threshold_row.addWidget(self.simple_trim_threshold_label)
        simple_trim_layout.addLayout(simple_threshold_row)

        simple_softness_row = QHBoxLayout()
        simple_softness_row.addWidget(QLabel("Softness"))
        self.simple_trim_softness_slider = QSlider(Qt.Orientation.Horizontal)
        self.simple_trim_softness_slider.setRange(0, 12)
        self.simple_trim_softness_slider.setValue(2)
        self.simple_trim_softness_slider.valueChanged.connect(self._sync_trim_softness_from_simple)
        simple_softness_row.addWidget(self.simple_trim_softness_slider, 1)
        self.simple_trim_softness_label = QLabel("2")
        simple_softness_row.addWidget(self.simple_trim_softness_label)
        simple_trim_layout.addLayout(simple_softness_row)

        self.simple_trim_reprocess_button = QPushButton("Re-process Quick Trim")
        self.simple_trim_reprocess_button.clicked.connect(self._reprocess_trim)
        simple_trim_layout.addWidget(self.simple_trim_reprocess_button)
        layout.addWidget(self.simple_trim_card)

        self.simple_save_button = QPushButton("Save As…")
        layout.addWidget(self.simple_save_button)

        mix_title = QLabel("Canvas Compose")
        mix_title.setObjectName("miniTitle")
        layout.addWidget(mix_title)

        self.simple_mix_card = QFrame()
        self.simple_mix_card.setObjectName("controlCard")
        mix_layout = QFormLayout(self.simple_mix_card)
        mix_layout.setContentsMargins(12, 12, 12, 12)
        mix_layout.setVerticalSpacing(10)

        self.mix_background_combo = QComboBox()
        self.mix_background_combo.addItem("Blue Gradient", "blue")
        self.mix_background_combo.addItem("Dark Studio", "dark")
        self.mix_background_combo.addItem("White Canvas", "white")
        self.mix_background_combo.addItem("Warm Gradient", "warm")
        self.mix_background_combo.addItem("Transparent", "transparent")
        mix_layout.addRow("Background", self.mix_background_combo)

        mix_scale_row = QWidget()
        mix_scale_layout = QHBoxLayout(mix_scale_row)
        mix_scale_layout.setContentsMargins(0, 0, 0, 0)
        mix_scale_layout.setSpacing(8)
        self.mix_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.mix_scale_slider.setRange(40, 140)
        self.mix_scale_slider.setValue(100)
        self.mix_scale_slider.valueChanged.connect(self._update_mix_labels)
        mix_scale_layout.addWidget(self.mix_scale_slider, 1)
        self.mix_scale_label = QLabel("100%")
        mix_scale_layout.addWidget(self.mix_scale_label)
        mix_layout.addRow("Scale", mix_scale_row)

        mix_padding_row = QWidget()
        mix_padding_layout = QHBoxLayout(mix_padding_row)
        mix_padding_layout.setContentsMargins(0, 0, 0, 0)
        mix_padding_layout.setSpacing(8)
        self.mix_padding_slider = QSlider(Qt.Orientation.Horizontal)
        self.mix_padding_slider.setRange(0, 35)
        self.mix_padding_slider.setValue(8)
        self.mix_padding_slider.valueChanged.connect(self._update_mix_labels)
        mix_padding_layout.addWidget(self.mix_padding_slider, 1)
        self.mix_padding_label = QLabel("8%")
        mix_padding_layout.addWidget(self.mix_padding_label)
        mix_layout.addRow("Padding", mix_padding_row)

        mix_shadow_row = QWidget()
        mix_shadow_layout = QHBoxLayout(mix_shadow_row)
        mix_shadow_layout.setContentsMargins(0, 0, 0, 0)
        mix_shadow_layout.setSpacing(8)
        self.mix_shadow_slider = QSlider(Qt.Orientation.Horizontal)
        self.mix_shadow_slider.setRange(0, 20)
        self.mix_shadow_slider.setValue(8)
        self.mix_shadow_slider.valueChanged.connect(self._update_mix_labels)
        mix_shadow_layout.addWidget(self.mix_shadow_slider, 1)
        self.mix_shadow_label = QLabel("8")
        mix_shadow_layout.addWidget(self.mix_shadow_label)
        mix_layout.addRow("Shadow", mix_shadow_row)

        self.simple_mix_preview_button = QPushButton("Preview Canvas Compose")
        self.simple_mix_preview_button.clicked.connect(self._run_simple_mix_preview)
        mix_layout.addRow(self.simple_mix_preview_button)

        self.simple_mix_save_button = QPushButton("Save Composed As…")
        self.simple_mix_save_button.clicked.connect(self._save_mixed_as)
        mix_layout.addRow(self.simple_mix_save_button)
        layout.addWidget(self.simple_mix_card)

        simple_prompt_label = QLabel("Optional custom instruction")
        simple_prompt_label.setObjectName("miniTitle")
        layout.addWidget(simple_prompt_label)

        self.simple_prompt = QLineEdit()
        self.simple_prompt.setPlaceholderText('Try "remove the background" or "remove the person"')
        self.simple_prompt.returnPressed.connect(self._run_simple_prompt)
        layout.addWidget(self.simple_prompt)

        self.simple_prompt_button = QPushButton("Run Custom Instruction")
        self.simple_prompt_button.clicked.connect(self._run_simple_prompt)
        layout.addWidget(self.simple_prompt_button)

        self.simple_gif_button = QPushButton("Create Loading GIF")
        layout.addWidget(self.simple_gif_button)

        return card

    def _build_advanced_page(self) -> QFrame:
        card = QFrame()
        card.setObjectName("sidebarCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Workspace")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        self.mode_hint = QLabel()
        self.mode_hint.setWordWrap(True)
        self.mode_hint.setObjectName("hintText")
        layout.addWidget(self.mode_hint)

        self.engine_combo = QComboBox()
        self.engine_combo.addItem("AI subject detection", "ai")
        self.engine_combo.addItem("Color flood-fill", "colour")
        self.engine_combo.addItem("Quick Trim", "trim")
        self.engine_combo.currentIndexChanged.connect(self._update_mode_controls)

        self.model_combo = QComboBox()
        self.model_combo.addItem("Auto", "auto")
        self.model_combo.addItem("General", "general")
        self.model_combo.addItem("People / portraits", "people")
        self.model_combo.addItem("Anime / illustrations", "anime")
        self.model_combo.addItem("Fast", "fast")

        form = QFormLayout()
        form.setVerticalSpacing(10)
        form.addRow("Engine", self.engine_combo)
        form.addRow("AI model", self.model_combo)
        layout.addLayout(form)

        self.invert_check = QCheckBox("Remove subject instead of background")
        layout.addWidget(self.invert_check)

        self.colour_card = QFrame()
        self.colour_card.setObjectName("controlCard")
        colour_layout = QFormLayout(self.colour_card)
        colour_layout.setContentsMargins(12, 12, 12, 12)
        self.tolerance_spin = QSpinBox()
        self.tolerance_spin.setRange(8, 120)
        self.tolerance_spin.setValue(42)
        self.colour_blur_spin = QDoubleSpinBox()
        self.colour_blur_spin.setRange(0.0, 10.0)
        self.colour_blur_spin.setSingleStep(0.2)
        self.colour_blur_spin.setDecimals(1)
        self.colour_blur_spin.setValue(1.2)
        colour_layout.addRow("Tolerance", self.tolerance_spin)
        colour_layout.addRow("Edge softness", self.colour_blur_spin)
        layout.addWidget(self.colour_card)

        self.trim_card = QFrame()
        self.trim_card.setObjectName("controlCard")
        trim_layout = QVBoxLayout(self.trim_card)
        trim_layout.setContentsMargins(12, 12, 12, 12)
        trim_layout.setSpacing(8)

        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel("Threshold"))
        self.trim_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.trim_threshold_slider.setRange(8, 120)
        self.trim_threshold_slider.setValue(36)
        self.trim_threshold_slider.valueChanged.connect(self._sync_trim_threshold_from_advanced)
        threshold_row.addWidget(self.trim_threshold_slider, 1)
        self.trim_threshold_label = QLabel("36")
        threshold_row.addWidget(self.trim_threshold_label)
        trim_layout.addLayout(threshold_row)

        softness_row = QHBoxLayout()
        softness_row.addWidget(QLabel("Softness"))
        self.trim_softness_slider = QSlider(Qt.Orientation.Horizontal)
        self.trim_softness_slider.setRange(0, 12)
        self.trim_softness_slider.setValue(2)
        self.trim_softness_slider.valueChanged.connect(self._sync_trim_softness_from_advanced)
        softness_row.addWidget(self.trim_softness_slider, 1)
        self.trim_softness_label = QLabel("2")
        softness_row.addWidget(self.trim_softness_label)
        trim_layout.addLayout(softness_row)
        layout.addWidget(self.trim_card)

        prompt_label = QLabel("Instruction")
        prompt_label.setObjectName("miniTitle")
        layout.addWidget(prompt_label)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText('Try "remove the background", "remove the person", or "keep only the logo"')
        self.prompt_input.returnPressed.connect(self._run_advanced)
        layout.addWidget(self.prompt_input)

        button_row = QHBoxLayout()
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self._run_advanced)
        button_row.addWidget(self.run_button)
        advanced_gif_button = QPushButton("GIF Builder")
        advanced_gif_button.clicked.connect(self._open_gif_builder)
        button_row.addWidget(advanced_gif_button)
        layout.addLayout(button_row)
        return card

    def _apply_theme(self) -> None:
        advanced_mode = self.advanced_button.isChecked() if hasattr(self, "advanced_button") else False
        card_radius = "10px" if advanced_mode else "24px"
        button_radius = "6px" if advanced_mode else "11px"
        colors = {
            "window": "#16181d" if advanced_mode else "#050912",
            "panel": "#20242b" if advanced_mode else "#09111d",
            "panel_alt": "#252a31" if advanced_mode else "#10182a",
            "chrome": "#2a2d33" if advanced_mode else "#10182a",
            "canvas": "#101114" if advanced_mode else "#09111d",
            "border": "#373d48" if advanced_mode else "#18305f",
            "border_alt": "#4a90ff" if advanced_mode else "#2444da",
            "accent": "#4a90ff" if advanced_mode else "#3f73ff",
            "accent_soft": "#8fc7ff" if advanced_mode else "#72ddff",
            "text": "#eef1f5" if advanced_mode else "#e9f2ff",
            "text_muted": "#9ea7b3" if advanced_mode else "#9ab8d9",
            "chip_bg": "#2b3240" if advanced_mode else "#13234a",
            "chip_border": "#4a90ff" if advanced_mode else "#3b6fff",
            "button": "#2b3038" if advanced_mode else "#182552",
            "button_hover": "#343a45" if advanced_mode else "#22346e",
            "button_checked": "#1f3c63" if advanced_mode else "#0f254e",
            "status": "#11151b" if advanced_mode else "#070d18",
            "splitter": "#2a3038" if advanced_mode else "#18305f",
        }
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{
                background: {colors["window"]};
                color: {colors["text"]};
                font-family: "Segoe UI", "Bahnschrift";
                font-size: 13px;
            }}
            QFrame#headerCard, QFrame#workCard, QFrame#sidebarCard, QFrame#controlCard, QFrame#inspectorCard {{
                background: {colors["panel"]};
                border: 1px solid {colors["border"]};
                border-radius: {card_radius};
            }}
            QFrame#editorBar, QFrame#toolRail, QFrame#dockCard {{
                background: {colors["chrome"]};
                border: 1px solid {colors["border"]};
                border-radius: {card_radius};
            }}
            QLabel#headerTitle {{
                color: {colors["text"]};
                font-size: {"20px" if advanced_mode else "23px"};
                font-weight: 700;
            }}
            QLabel#headerSubtitle {{
                color: {colors["accent_soft"]};
                font-size: 13px;
                font-weight: 600;
            }}
            QLabel#headerTagline, QLabel#hintText {{
                color: {colors["text_muted"]};
                font-size: 12px;
            }}
            QLabel#panelTitle {{
                color: {colors["text"]};
                font-size: 18px;
                font-weight: 700;
            }}
            QLabel#miniTitle {{
                color: {colors["accent_soft"]};
                font-size: 12px;
                font-weight: 600;
            }}
            QLabel#editorBrand {{
                color: {colors["text"]};
                font-size: 13px;
                font-weight: 700;
                padding-right: 8px;
            }}
            QLabel#editorMenuLabel {{
                color: {colors["text_muted"]};
                font-size: 12px;
                padding: 2px 4px;
            }}
            QMenuBar {{
                background: {colors["chrome"]};
                color: {colors["text"]};
                border-bottom: 1px solid {colors["border"]};
                padding: 2px 6px;
            }}
            QMenuBar::item {{
                background: transparent;
                padding: 4px 10px;
                margin: 1px 2px;
            }}
            QMenuBar::item:selected {{
                background: {colors["button_hover"]};
            }}
            QMenu {{
                background: {colors["chrome"]};
                color: {colors["text"]};
                border: 1px solid {colors["border"]};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 18px 6px 12px;
            }}
            QMenu::item:selected {{
                background: {colors["button_hover"]};
            }}
            QLabel#summaryChip {{
                background: {colors["chip_bg"]};
                color: {colors["accent_soft"]};
                border: 1px solid {colors["chip_border"]};
                border-radius: 12px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                background: {colors["panel_alt"]};
                color: {colors["text"]};
                border: 1px solid {colors["border_alt"]};
                border-radius: 10px;
                padding: 7px 10px;
                min-height: 20px;
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: {colors["accent_soft"]};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QPushButton {{
                background: {colors["button"]};
                color: {colors["text"]};
                border: 1px solid {colors["chip_border"]};
                border-radius: {button_radius};
                padding: 9px 16px;
            }}
            QPushButton#toolbarButton {{
                padding: 6px 12px;
                min-width: 78px;
            }}
            QPushButton#toolRailButton {{
                padding: 4px;
                min-width: 42px;
                max-width: 42px;
                min-height: 34px;
                max-height: 34px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {colors["button_hover"]};
                border-color: {colors["accent_soft"]};
            }}
            QPushButton:pressed {{
                background: {colors["accent"]};
                color: white;
            }}
            QPushButton:disabled {{
                color: #7483a9;
                background: {colors["status"]};
                border-color: {colors["border"]};
            }}
            QPushButton:checked {{
                background: {colors["button_checked"]};
                border-color: {colors["accent_soft"]};
            }}
            QScrollArea#sidebarArea, QScrollArea {{
                border: none;
                background: transparent;
            }}
            QSlider::groove:horizontal {{
                height: 5px;
                background: {colors["border"]};
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {colors["accent"]};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {colors["accent_soft"]};
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSplitter::handle {{
                background: {colors["splitter"]};
            }}
            QStatusBar {{
                background: {colors["status"]};
                border-top: 1px solid {colors["border"]};
                color: {colors["accent_soft"]};
            }}
            """
        )

    def _bind_simple_actions(self) -> None:
        self.simple_load_button.clicked.connect(self._browse_image)
        self.simple_remove_bg_button.clicked.connect(
            lambda: self._run_simple_instruction("remove the background")
        )
        self.simple_keep_subject_button.clicked.connect(
            lambda: self._run_simple_instruction("keep only the subject")
        )
        self.simple_remove_white_button.clicked.connect(self._run_simple_white_background)
        self.simple_quick_trim_button.clicked.connect(self._run_simple_trim)
        self.simple_gif_button.clicked.connect(self._open_gif_builder)
        self.simple_save_button.clicked.connect(self._save_as)

    def _activate_simple_mode(self) -> None:
        self.simple_button.setChecked(True)
        self._mode_switch_changed()

    def _activate_advanced_mode(self) -> None:
        self.advanced_button.setChecked(True)
        self._mode_switch_changed()

    def _toggle_inspector(self) -> None:
        visible = not self.inspector_card.isVisible()
        self.inspector_card.setVisible(visible)
        if hasattr(self, "toggle_inspector_action"):
            self.toggle_inspector_action.setChecked(visible)

    def _reset_workspace_layout(self) -> None:
        if self.simple_button.isChecked():
            self.main_splitter.setSizes([300, 980])
            self.editor_splitter.setSizes([980, 0])
        else:
            self.main_splitter.setSizes([0, 1380])
            self.editor_splitter.setSizes([860, 320])
            self.inspector_card.setVisible(True)
            if hasattr(self, "toggle_inspector_action"):
                self.toggle_inspector_action.setChecked(True)

    def _show_model_status(self) -> None:
        message = "AI ready." if self.ai_available else f"AI unavailable.\n\n{self.ai_error}"
        QMessageBox.information(self, "Model Status", message)

    def _show_about_dialog(self) -> None:
        QMessageBox.information(
            self,
            APP_NAME,
            "TheTechGuy Image Editor\n\nOffline background removal, quick trim cleanup, GIF building, and canvas mix exports.",
        )

    def _set_trim_threshold_value(self, value: int) -> None:
        self.trim_threshold_slider.blockSignals(True)
        self.simple_trim_threshold_slider.blockSignals(True)
        self.trim_threshold_slider.setValue(int(value))
        self.simple_trim_threshold_slider.setValue(int(value))
        self.trim_threshold_slider.blockSignals(False)
        self.simple_trim_threshold_slider.blockSignals(False)
        self._update_trim_labels()

    def _set_trim_softness_value(self, value: int) -> None:
        self.trim_softness_slider.blockSignals(True)
        self.simple_trim_softness_slider.blockSignals(True)
        self.trim_softness_slider.setValue(int(value))
        self.simple_trim_softness_slider.setValue(int(value))
        self.trim_softness_slider.blockSignals(False)
        self.simple_trim_softness_slider.blockSignals(False)
        self._update_trim_labels()

    def _sync_trim_threshold_from_simple(self, value: int) -> None:
        self._set_trim_threshold_value(value)

    def _sync_trim_softness_from_simple(self, value: int) -> None:
        self._set_trim_softness_value(value)

    def _sync_trim_threshold_from_advanced(self, value: int) -> None:
        self._set_trim_threshold_value(value)

    def _sync_trim_softness_from_advanced(self, value: int) -> None:
        self._set_trim_softness_value(value)

    def _nudge_trim_threshold(self, delta: int) -> None:
        self._set_trim_threshold_value(self.trim_threshold_slider.value() + delta)

    def _nudge_trim_softness(self, delta: int) -> None:
        self._set_trim_softness_value(self.trim_softness_slider.value() + delta)

    def _update_mix_labels(self, *_args) -> None:
        self.mix_scale_label.setText(f"{self.mix_scale_slider.value()}%")
        self.mix_padding_label.setText(f"{self.mix_padding_slider.value()}%")
        self.mix_shadow_label.setText(str(self.mix_shadow_slider.value()))

    def _current_display_source(self) -> str | None:
        return self._display_path or self._output_path or self._input_path

    def _set_editor_engine(self, engine_key: str) -> None:
        index = self.engine_combo.findData(engine_key)
        if index >= 0:
            self.engine_combo.setCurrentIndex(index)
            self._update_mode_controls()

    def _refresh_header_branding(self, advanced_mode: bool) -> None:
        if not self._logo_pixmap.isNull():
            icon_size = 46 if advanced_mode else 72
            self.logo_label.setPixmap(
                self._logo_pixmap.scaled(
                    icon_size,
                    icon_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        header_layout = self.header.layout()
        if isinstance(header_layout, QHBoxLayout):
            header_layout.setContentsMargins(14, 12, 14, 12)
            header_layout.setSpacing(10 if advanced_mode else 12)

        self.subtitle_label.setText(
            "Focused editing workspace with direct controls and repeat passes."
            if advanced_mode
            else "Simple actions on the left. Full editing control in Advanced."
        )
        self.tagline_label.setVisible(not advanced_mode)
        self.header.setMaximumHeight(90 if advanced_mode else 16777215)

    def _mode_switch_changed(self, *_args) -> None:
        simple_mode = self.simple_button.isChecked()
        self.simple_page.setVisible(simple_mode)
        self.advanced_page.setVisible(not simple_mode)
        self.menuBar().setVisible(not simple_mode)
        self.header.setVisible(simple_mode)
        self.advanced_toolbar.setVisible(not simple_mode)
        self.sidebar.setVisible(simple_mode)
        self.sidebar.setMaximumWidth(16777215 if simple_mode else 0)
        self.tool_rail.setVisible(not simple_mode)
        self.inspector_card.setVisible(not simple_mode)
        self.footer_bar.setVisible(simple_mode)
        if hasattr(self, "toggle_inspector_action"):
            self.toggle_inspector_action.setChecked(not simple_mode and self.inspector_card.isVisible())
        self.summary_chip.setText("Simple workspace" if simple_mode else "Advanced workspace")
        self.sidebar.setMinimumWidth(280)
        self.work_layout.setContentsMargins(
            18 if simple_mode else 10,
            18 if simple_mode else 10,
            18 if simple_mode else 10,
            18 if simple_mode else 10,
        )
        self.outer_layout.setContentsMargins(
            14 if simple_mode else 0,
            14 if simple_mode else 0,
            14 if simple_mode else 0,
            14 if simple_mode else 0,
        )
        self.outer_layout.setSpacing(12 if simple_mode else 0)
        if not self._input_path and not self._output_path:
            self.result_summary.setText(
                "Load an image, run a quick action, or trim and save."
                if simple_mode
                else "Use the tool rail and properties dock, keep the canvas centered, and re-run changes as needed."
            )
        self.inspector_note.setText(
            "Mode hints, activity, and run status appear here while you work."
            if simple_mode
            else "Advanced mode uses an editor layout: tool rail on the left, canvas in the center, and properties on the right."
        )
        self.main_splitter.setSizes([300, 980] if simple_mode else [0, 1380])
        self.editor_splitter.setSizes([980, 0] if simple_mode else [860, 320])
        self.preview_panel.set_editor_mode(not simple_mode)
        self._refresh_header_branding(not simple_mode)
        self._apply_theme()

    def _engine_key(self) -> str:
        return str(self.engine_combo.currentData())

    def _model_key(self) -> str:
        return str(self.model_combo.currentData())

    def _update_trim_labels(self, *_args) -> None:
        threshold = self.trim_threshold_slider.value()
        softness = self.trim_softness_slider.value()
        self.trim_threshold_label.setText(str(threshold))
        self.simple_trim_threshold_label.setText(str(threshold))
        self.trim_softness_label.setText(str(softness))
        self.simple_trim_softness_label.setText(str(softness))

    def _update_mode_controls(self, *_args) -> None:
        mode = self._engine_key()
        self.colour_card.setVisible(mode == "colour")
        self.trim_card.setVisible(mode == "trim")
        self.model_combo.setEnabled(mode == "ai" and self.ai_available)
        self.invert_check.setVisible(mode == "ai")
        self.tool_ai_button.setChecked(mode == "ai")
        self.tool_colour_button.setChecked(mode == "colour")
        self.tool_trim_button.setChecked(mode == "trim")

        if mode == "ai":
            if self.ai_available:
                self.mode_hint.setText(
                    "AI cutout controls for difficult backgrounds, subject isolation, and cleaner repeat passes."
                )
            else:
                self.mode_hint.setText(
                    "AI is unavailable in this build right now. Use Color mode or Quick Trim."
                )
            self.prompt_input.setPlaceholderText(
                'Try "remove the background", "remove the person", or "keep only the logo"'
            )
            self.inspector_note.setText(
                "AI mode isolates the main subject with the selected local model. Use the log below to watch each pass."
            )
        elif mode == "colour":
            self.mode_hint.setText(
                "Fast flat-background cleanup for quick exports, solid backdrops, and white-background cleanup."
            )
            self.prompt_input.setPlaceholderText(
                'Try "remove the white background" or "remove the black background"'
            )
            self.inspector_note.setText(
                "Color mode is quickest on flat backgrounds. Raise tolerance for light backdrops and soften edges if halos remain."
            )
        else:
            self.mode_hint.setText("Fast manual trim for quick cleanup, light backgrounds, and trim-save-move-on work.")
            self.prompt_input.setPlaceholderText("Quick Trim uses the threshold and softness controls above.")
            self.inspector_note.setText(
                "Quick Trim gives manual control over cutoff and edge softness. Use it when AI is unnecessary or when white edges need a tighter pass."
            )

    def _add_activity(self, text: str, role: str) -> None:
        bubble = Bubble(text, role)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if role == "user":
            row.addStretch()
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch()
        self.activity_layout.insertLayout(self.activity_layout.count() - 1, row)
        QTimer.singleShot(0, self._scroll_activity_bottom)

    def _scroll_activity_bottom(self) -> None:
        scroll_bar = self.activity_scroll.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())

    def _set_busy(self, busy: bool) -> None:
        has_input = self._input_path is not None
        has_cutout = self._output_path is not None
        has_display = self._display_path is not None
        self.simple_load_button.setEnabled(not busy)
        self.simple_remove_bg_button.setEnabled(not busy and self.ai_available)
        self.simple_keep_subject_button.setEnabled(not busy and self.ai_available and has_input)
        self.simple_remove_white_button.setEnabled(not busy and has_input)
        self.simple_quick_trim_button.setEnabled(not busy and has_input)
        self.simple_gif_button.setEnabled(not busy)
        self.simple_save_button.setEnabled(not busy and has_display)
        self.simple_trim_reprocess_button.setEnabled(not busy and has_input)
        self.simple_mix_preview_button.setEnabled(not busy and (has_cutout or has_input))
        self.simple_mix_save_button.setEnabled(not busy and self._mix_output_path is not None)
        self.simple_prompt.setEnabled(not busy)
        self.simple_prompt_button.setEnabled(not busy)

        self.load_button.setEnabled(not busy)
        self.toolbar_load_button.setEnabled(not busy)
        self.toolbar_gif_button.setEnabled(not busy)
        self.tool_open_button.setEnabled(not busy)
        self.tool_ai_button.setEnabled(not busy and self.ai_available)
        self.tool_colour_button.setEnabled(not busy and has_input)
        self.tool_trim_button.setEnabled(not busy and has_input)
        self.tool_gif_button.setEnabled(not busy)

        self.engine_combo.setEnabled(not busy)
        self.model_combo.setEnabled(not busy and (self._engine_key() != "ai" or self.ai_available))
        self.invert_check.setEnabled(not busy and self.ai_available)
        self.tolerance_spin.setEnabled(not busy)
        self.colour_blur_spin.setEnabled(not busy)
        self.trim_threshold_slider.setEnabled(not busy)
        self.trim_softness_slider.setEnabled(not busy)
        self.prompt_input.setEnabled(not busy)
        self.run_button.setEnabled(not busy and (self._engine_key() != "ai" or self.ai_available))
        self.toolbar_run_button.setEnabled(not busy and (self._engine_key() != "ai" or self.ai_available))
        self.reprocess_button.setEnabled(not busy and has_input)
        self.toolbar_reprocess_button.setEnabled(not busy and has_input)
        self.save_button.setEnabled(not busy and has_display)
        self.toolbar_save_button.setEnabled(not busy and has_display)

    def _can_run_plan(self, plan: dict[str, object]) -> bool:
        if str(plan.get("method")) != "ai" or self.ai_available:
            return True

        message = self.ai_error or "The AI backend could not be loaded."
        self.summary_chip.setText("AI unavailable")
        self.result_summary.setText(
            f"AI background removal is unavailable. {message} Use Color mode or Quick Trim."
        )
        self.statusBar().showMessage(message)
        self._add_activity(f"AI unavailable: {message}", "assistant")
        return False

    def _browse_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff)",
        )
        if path:
            self._on_file(path)

    def _on_file(self, path: str) -> None:
        self._input_path = path
        self._output_path = None
        self._display_path = path
        self._mix_output_path = None
        self.file_title.setText(Path(path).name)
        self.preview_panel.set_preview(path)
        self.result_summary.setText("Image loaded. Choose a quick action or switch to Advanced for direct control.")
        self.summary_chip.setText("Image loaded")
        self.statusBar().showMessage(f"Loaded {path}")
        self._set_busy(False)
        self._add_activity(f"Loaded image: {Path(path).name}", "user")

    def _run_simple_instruction(self, instruction: str) -> None:
        if not self._input_path:
            self._add_activity("Load an image first.", "assistant")
            return

        plan = parse_instruction(
            instruction,
            "ai",
            self._model_key(),
            self.tolerance_spin.value(),
            self.colour_blur_spin.value(),
            False,
        )
        if not self._can_run_plan(plan):
            return
        self._add_activity(instruction, "user")
        self._start_processing(plan)

    def _run_simple_prompt(self) -> None:
        prompt = self.simple_prompt.text().strip()
        if not prompt:
            return
        if not self._input_path:
            self._add_activity("Load an image first.", "assistant")
            return

        plan = parse_instruction(
            prompt,
            "ai",
            self._model_key(),
            self.tolerance_spin.value(),
            self.colour_blur_spin.value(),
            False,
        )
        if not self._can_run_plan(plan):
            return
        self.simple_prompt.clear()
        self._add_activity(prompt, "user")
        self._start_processing(plan)

    def _run_simple_white_background(self) -> None:
        if not self._input_path:
            self._add_activity("Load an image first.", "assistant")
            return
        plan = {
            "method": "colour",
            "engine_label": "Color mode",
            "tolerance": max(60, self.tolerance_spin.value()),
            "blur": max(1.0, self.colour_blur_spin.value()),
            "detected": "white",
            "reply": "Removing the white background with color matching.",
            "status": "Color mode | tuned for white backgrounds",
        }
        self._add_activity("Remove white background", "user")
        self._start_processing(plan)

    def _run_simple_trim(self) -> None:
        if not self._input_path:
            self._add_activity("Load an image first.", "assistant")
            return
        self._add_activity("Quick Trim", "user")
        self._start_processing(build_trim_plan(self.trim_threshold_slider.value(), self.trim_softness_slider.value()))

    def _reprocess_trim(self) -> None:
        if not self._input_path:
            self._add_activity("Load an image first.", "assistant")
            return
        self._add_activity("Re-process Quick Trim", "user")
        self._start_processing(build_trim_plan(self.trim_threshold_slider.value(), self.trim_softness_slider.value()))

    def _run_simple_mix_preview(self) -> None:
        source_path = self._current_display_source()
        if not source_path:
            self._add_activity("Load or process an image first.", "assistant")
            return
        plan = build_mix_plan(
            str(self.mix_background_combo.currentData()),
            self.mix_scale_slider.value(),
            self.mix_padding_slider.value(),
            self.mix_shadow_slider.value(),
        )
        self._add_activity("Preview canvas compose", "user")
        self._start_processing(plan, source_path=source_path, track_last_plan=False)

    def _save_mixed_as(self) -> None:
        if self._mix_output_path and Path(self._mix_output_path).exists():
            self._save_as(preferred_path=self._mix_output_path)
            return
        self._run_simple_mix_preview()

    def _run_advanced(self) -> None:
        if not self._input_path:
            self._add_activity("Load an image first.", "assistant")
            return

        mode = self._engine_key()
        if mode == "trim":
            self._add_activity("Quick Trim", "user")
            self._start_processing(
                build_trim_plan(self.trim_threshold_slider.value(), self.trim_softness_slider.value())
            )
            return

        instruction = self.prompt_input.text().strip()
        if not instruction:
            if mode == "colour":
                instruction = "remove the background"
            else:
                self._add_activity("Enter an instruction first.", "assistant")
                return

        plan = parse_instruction(
            instruction,
            mode,
            self._model_key(),
            self.tolerance_spin.value(),
            self.colour_blur_spin.value(),
            self.invert_check.isChecked(),
        )
        if not self._can_run_plan(plan):
            return
        self.prompt_input.clear()
        self._add_activity(instruction, "user")
        self._start_processing(plan)

    def _start_processing(
        self,
        plan: dict[str, object],
        source_path: str | None = None,
        track_last_plan: bool = True,
    ) -> None:
        processing_source = source_path or self._input_path
        if not processing_source:
            return
        if self._worker is not None and self._worker.isRunning():
            return

        if track_last_plan and str(plan.get("method")) != "mix":
            self._last_plan = dict(plan)
        self._active_plan = dict(plan)
        self._set_busy(True)
        self.summary_chip.setText(str(plan.get("engine_label", "Working")))
        self.result_summary.setText(str(plan.get("reply", "Processing image…")))
        title = "Preparing AI…" if plan["method"] == "ai" else "Processing…"
        self.preview_panel.show_loading(title, str(plan["status"]))
        self.statusBar().showMessage(str(plan["status"]))

        if plan["method"] == "ai":
            worker: QThread = AiProcessingWorker(processing_source, plan)
        else:
            worker = LocalProcessingWorker(processing_source, plan)
        self._worker = worker
        worker.progress.connect(self._on_worker_progress)
        worker.completed.connect(self._on_processing_done)
        worker.error.connect(self._on_worker_error)
        worker.start()

    def _on_worker_progress(self, message: str) -> None:
        title = "Preparing AI…" if self._active_plan and self._active_plan.get("method") == "ai" else "Processing…"
        self.preview_panel.show_loading(title, message)
        self.statusBar().showMessage(message)
        self._add_activity(message, "status")

    def _on_processing_done(self, output_path: str, plan: object) -> None:
        self._worker = None
        self._active_plan = None
        self.preview_panel.hide_loading()
        plan_dict = plan if isinstance(plan, dict) else {}
        method = str(plan_dict.get("method", ""))
        if method == "mix":
            self._mix_output_path = output_path
            self._display_path = output_path
        else:
            self._output_path = output_path
            self._display_path = output_path
            self._mix_output_path = None
        self.preview_panel.set_preview(output_path)
        self._set_busy(False)

        if method == "ai":
            message = (
                f"Finished with {plan_dict['ai_label']} AI. Kept the {plan_dict['detected']} and saved the PNG."
            )
        elif method == "colour":
            message = f"Finished with color cleanup. Matched the {plan_dict['detected']} background."
        elif method == "mix":
            message = f"Canvas compose ready with the {plan_dict['background_style']} background style."
        else:
            message = "Quick Trim finished with the updated threshold and edge softness."

        self.summary_chip.setText("Result ready")
        self.result_summary.setText(f"{message} Use Re-process or Save As if you want another pass.")
        self.statusBar().showMessage(f"Saved result to {output_path}")
        self._add_activity(message, "assistant")

    def _on_worker_error(self, message: str) -> None:
        self._worker = None
        self._active_plan = None
        self.preview_panel.hide_loading()
        self._set_busy(False)
        self.statusBar().showMessage(f"Error: {message}")
        self.result_summary.setText(f"Error: {message}")
        self.summary_chip.setText("Error")
        self._add_activity(f"Error: {message}", "assistant")
        if self._display_path and Path(self._display_path).exists():
            self.preview_panel.set_preview(self._display_path)
        elif self._output_path and Path(self._output_path).exists():
            self.preview_panel.set_preview(self._output_path)
        elif self._input_path and Path(self._input_path).exists():
            self.preview_panel.set_preview(self._input_path)
        else:
            self.preview_panel.clear()

    def _reprocess(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        if self._last_plan is not None and self._input_path:
            if str(self._last_plan.get("method")) == "trim":
                self._start_processing(build_trim_plan(self.trim_threshold_slider.value(), self.trim_softness_slider.value()))
                return
            self._start_processing(dict(self._last_plan))
            return
        self._run_advanced()

    def _save_as(self, preferred_path: str | None = None) -> None:
        source_path = preferred_path or self._display_path or self._output_path
        if not source_path:
            self._add_activity("Process an image first, then save a copy.", "assistant")
            return
        if self._save_worker is not None and self._save_worker.isRunning():
            return

        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Save Transparent PNG",
            source_path,
            "PNG Image (*.png)",
        )
        if not destination:
            return
        if not destination.lower().endswith(".png"):
            destination = f"{destination}.png"

        self._save_worker = SaveCopyWorker(source_path, destination)
        self._set_busy(True)
        self.preview_panel.show_loading("Saving…", "Copying PNG to the selected location…")
        self._save_worker.progress.connect(
            lambda message: self.preview_panel.show_loading("Saving…", message)
        )
        self._save_worker.completed.connect(self._on_save_done)
        self._save_worker.error.connect(self._on_save_error)
        self._save_worker.start()

    def _on_save_done(self, path: str) -> None:
        self._save_worker = None
        self._set_busy(False)
        self.preview_panel.hide_loading()
        self.statusBar().showMessage(f"Saved copy to {path}")
        self.result_summary.setText(f"Saved a copy to {path}")
        self._add_activity(f"Saved a copy to {path}", "assistant")

    def _on_save_error(self, message: str) -> None:
        self._save_worker = None
        self._set_busy(False)
        self.preview_panel.hide_loading()
        self.statusBar().showMessage(f"Save error: {message}")
        self._add_activity(f"Save error: {message}", "assistant")

    def _open_gif_builder(self) -> None:
        dialog = GifBuilderDialog(self)
        dialog.gifSaved.connect(self._on_gif_saved)
        dialog.exec()

    def _on_gif_saved(self, path: str) -> None:
        self.preview_panel.set_loading_assets()
        self.result_summary.setText(f"Loading GIF ready at {path}")
        self.statusBar().showMessage(f"Loading GIF ready at {path}")
        self._add_activity(f"Updated loading GIF: {path}", "assistant")

    def closeEvent(self, event: QCloseEvent) -> None:
        if (self._worker is not None and self._worker.isRunning()) or (
            self._save_worker is not None and self._save_worker.isRunning()
        ):
            self.statusBar().showMessage("Wait for the current task to finish before closing.")
            event.ignore()
            return
        super().closeEvent(event)


def run_ui(startup_info: dict[str, object] | None = None) -> int:
    apply_windows_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    icon_path = runtime_icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    splash = StartupSplash(resource_path("logo.png"), loading_gif_path())
    splash.show()
    app.processEvents()

    startup_worker = StartupCheckWorker()
    app._startup_worker = startup_worker  # type: ignore[attr-defined]
    app._main_window = None  # type: ignore[attr-defined]

    def handle_ready(payload: object) -> None:
        splash.set_status(f"Starting {APP_NAME}…")
        window = MainWindow(payload if isinstance(payload, dict) else None)
        app._main_window = window  # type: ignore[attr-defined]
        window.show()
        splash.close()

    def handle_error(message: str) -> None:
        splash.set_title("Startup failed")
        splash.set_status(message)
        QMessageBox.critical(splash, "Startup Error", message)
        app.quit()

    startup_worker.status.connect(splash.set_status)
    startup_worker.ready.connect(handle_ready)
    startup_worker.error.connect(handle_error)
    startup_worker.start()
    return app.exec()
