"""Settings dialog and persistence (JSON config file)."""

from __future__ import annotations

import json
import platform
import shutil
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

CONFIG_DIR = Path.home() / ".crackers_toolkit"
CONFIG_FILE = CONFIG_DIR / "settings.json"

DEFAULTS: dict[str, Any] = {
    "hashcat_path": "",
    "prince_path": "",
    "python_path": "python",
    "default_output_dir": str(Path.home() / "crackers_output"),
    "hash_rate": 1_000_000_000,
    "terminal_linux": "auto",
    "terminal_windows": "cmd",
    "theme": "dark",
}


def _detect_tools(base: Path) -> dict[str, str]:
    """Try to auto-detect tool paths relative to the workspace."""
    found: dict[str, str] = {}

    # Hashcat
    for name in ("hashcat.exe", "hashcat.bin", "hashcat"):
        candidates = list(base.glob(f"hashcat-*/{name}"))
        if candidates:
            found["hashcat_path"] = str(candidates[0])
            break

    # PRINCE — search recursively for any pp binary
    _src_ext = {".c", ".h", ".py", ".txt", ".md"}
    for name in ("pp64.exe", "pp.exe", "pp64.bin", "pp.bin", "pp"):
        candidates = [
            p for p in base.glob(f"Scripts_to_use/princeprocessor-master/**/{name}")
            if p.suffix.lower() not in _src_ext
        ]
        if candidates:
            found["prince_path"] = str(candidates[0])
            break

    return found


class Settings:
    """Application settings backed by a JSON file."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._base_dir = base_dir
        self.load()
        if base_dir:
            detected = _detect_tools(base_dir)
            for k, v in detected.items():
                if not self._data.get(k):
                    self._data[k] = v

    def load(self) -> None:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                self._data.update(stored)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str) -> Any:
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get_terminal_command(self) -> list[str]:
        """Return the OS-appropriate terminal launch prefix."""
        if platform.system() == "Windows":
            choice = self.get("terminal_windows")
            if choice == "powershell":
                return ["powershell", "-NoExit", "-Command"]
            return ["cmd", "/c", "start", "cmd", "/k"]
        else:
            choice = self.get("terminal_linux")
            if choice != "auto":
                return [choice, "--"]
            for term in ("gnome-terminal", "xfce4-terminal", "konsole", "xterm"):
                if shutil.which(term):
                    if term == "konsole":
                        return [term, "-e"]
                    return [term, "--"]
            return ["xterm", "-e"]


class SettingsDialog(QDialog):
    """Modal dialog exposing all application settings."""

    @staticmethod
    def _info_icon(tooltip: str) -> QLabel:
        icon = QLabel("ⓘ")
        icon.setToolTip(tooltip)
        icon.setFixedWidth(16)
        icon.setStyleSheet(
            "color: #89b4fa; font-weight: bold; font-size: 13px; "
            "qproperty-alignment: AlignCenter;"
        )
        icon.setCursor(Qt.CursorShape.WhatsThisCursor)
        return icon

    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self._settings = settings
        self._edits: dict[str, Any] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Path settings with browse buttons
        self._edits["hashcat_path"] = self._path_row(form, "Hashcat binary:", self._settings.get("hashcat_path"))
        self._edits["prince_path"] = self._path_row(form, "PRINCE binary:", self._settings.get("prince_path"))
        self._edits["python_path"] = self._path_row(form, "Python interpreter:", self._settings.get("python_path"))
        self._edits["default_output_dir"] = self._path_row(
            form, "Default output directory:", self._settings.get("default_output_dir"), directory=True
        )

        # Hash rate
        hr = QSpinBox()
        hr.setRange(1, 2_147_483_647)
        hr.setValue(min(self._settings.get("hash_rate"), 2_147_483_647))
        hr_row = QHBoxLayout()
        hr_row.addWidget(hr)
        hr_row.addWidget(self._info_icon("Default hash rate (H/s) used for time estimates in Mask Builder and MaskGen."))
        hr_row.addStretch()
        hr_container = QWidget()
        hr_container.setLayout(hr_row)
        form.addRow("Default hash rate (H/s):", hr_container)
        self._edits["hash_rate"] = hr

        # Terminal (Linux)
        tl = QComboBox()
        tl.addItems(["auto", "gnome-terminal", "xfce4-terminal", "konsole", "xterm"])
        tl.setCurrentText(self._settings.get("terminal_linux"))
        tl_row = QHBoxLayout()
        tl_row.addWidget(tl)
        tl_row.addWidget(self._info_icon("Terminal emulator to spawn on Linux. 'auto' detects the first available."))
        tl_row.addStretch()
        tl_container = QWidget()
        tl_container.setLayout(tl_row)
        form.addRow("Terminal (Linux):", tl_container)
        self._edits["terminal_linux"] = tl

        # Terminal (Windows)
        tw = QComboBox()
        tw.addItems(["cmd", "powershell"])
        tw.setCurrentText(self._settings.get("terminal_windows"))
        tw_row = QHBoxLayout()
        tw_row.addWidget(tw)
        tw_row.addWidget(self._info_icon("Terminal to spawn on Windows."))
        tw_row.addStretch()
        tw_container = QWidget()
        tw_container.setLayout(tw_row)
        form.addRow("Terminal (Windows):", tw_container)
        self._edits["terminal_windows"] = tw

        # Theme
        th = QComboBox()
        th.addItems(["dark", "light"])
        th.setCurrentText(self._settings.get("theme"))
        form.addRow("Theme:", th)
        self._edits["theme"] = th

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _path_row(self, form: QFormLayout, label: str, value: str, directory: bool = False) -> QLineEdit:
        row = QHBoxLayout()
        line = QLineEdit(value)
        btn = QPushButton("Browse…")

        def browse() -> None:
            if directory:
                p = QFileDialog.getExistingDirectory(self, label, value)
            else:
                p, _ = QFileDialog.getOpenFileName(self, label, value)
            if p:
                line.setText(p)

        btn.clicked.connect(browse)
        row.addWidget(line, stretch=1)
        row.addWidget(btn)
        container = QLabel()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(line, stretch=1)
        container_layout.addWidget(btn)
        form.addRow(label, container)
        return line

    def _apply(self) -> None:
        for key, widget in self._edits.items():
            if isinstance(widget, QLineEdit):
                self._settings.set(key, widget.text())
            elif isinstance(widget, QSpinBox):
                self._settings.set(key, widget.value())
            elif isinstance(widget, QComboBox):
                self._settings.set(key, widget.currentText())
        self._settings.save()
        self.accept()
