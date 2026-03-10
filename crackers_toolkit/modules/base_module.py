"""Abstract base class that all tool modules inherit from.

Provides the consistent layout: input section (top), parameters (middle with
collapsible Advanced Options), and output/action buttons (bottom).  Also
supplies subprocess execution helpers with non-blocking I/O, progress
indicators, and cancel support.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
from abc import abstractmethod
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


# ---------------------------------------------------------------------------
# Event filter that blocks wheel events on combo boxes, spin boxes, and
# sliders so the parent scroll area scrolls instead of changing the value.
# ---------------------------------------------------------------------------
class _NoScrollWheelFilter(QObject):
    """Installed on combo boxes, spin boxes, and sliders to block wheel events."""

    def eventFilter(self, obj: QObject, event) -> bool:  # noqa: N802
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.Wheel:
            event.ignore()
            return True
        return super().eventFilter(obj, event)


class ProcessRunner(QObject):
    """Runs a subprocess on a background thread and emits signals."""

    output_line = pyqtSignal(str)
    finished = pyqtSignal(int)  # exit code
    error = pyqtSignal(str)
    # Logging signals: (command_string,) and (command_string, exit_code, runtime_secs)
    started = pyqtSignal(str)
    completed = pyqtSignal(str, int, float)

    def __init__(self) -> None:
        super().__init__()
        self._process: Optional[subprocess.Popen] = None
        self._cancelled = False
        self._start_time: float = 0.0
        self._last_cmd: str = ""

    def run(self, cmd: list[str], cwd: Optional[Path] = None, timeout: float = 0) -> None:
        self._cancelled = False
        self._timeout = timeout
        self._last_cmd = " ".join(cmd)
        self._start_time = time.monotonic()
        self.started.emit(self._last_cmd)
        thread = threading.Thread(target=self._execute, args=(cmd, cwd), daemon=True)
        thread.start()

    def _execute(self, cmd: list[str], cwd: Optional[Path]) -> None:
        timer: Optional[threading.Timer] = None
        try:
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(cwd) if cwd else None,
                bufsize=1,
            )
            if self._timeout > 0:
                timer = threading.Timer(self._timeout, self._on_timeout)
                timer.daemon = True
                timer.start()
            for line in iter(self._process.stdout.readline, ""):
                if self._cancelled:
                    break
                self.output_line.emit(line.rstrip("\n"))
            self._process.stdout.close()
            rc = self._process.wait()
            if timer:
                timer.cancel()
            elapsed = time.monotonic() - self._start_time
            self.completed.emit(self._last_cmd, rc, elapsed)
            self.finished.emit(rc)
        except FileNotFoundError:
            if timer:
                timer.cancel()
            self.error.emit(f"Executable not found: {cmd[0]}")
            elapsed = time.monotonic() - self._start_time
            self.completed.emit(self._last_cmd, -1, elapsed)
            self.finished.emit(-1)
        except Exception as exc:
            if timer:
                timer.cancel()
            self.error.emit(str(exc))
            elapsed = time.monotonic() - self._start_time
            self.completed.emit(self._last_cmd, -1, elapsed)
            self.finished.emit(-1)

    def _on_timeout(self) -> None:
        self._cancelled = True
        if self._process and self._process.poll() is None:
            self._process.terminate()
        elapsed = time.monotonic() - self._start_time
        self.error.emit(f"Process timed out after {elapsed:.0f}s")

    def cancel(self) -> None:
        self._cancelled = True
        if self._process and self._process.poll() is None:
            self._process.terminate()


class CollapsibleSection(QWidget):
    """A widget that can be expanded / collapsed by clicking its header."""

    def __init__(self, title: str = "Advanced Options", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._toggle_btn = QPushButton(f"▶ {title}")
        self._toggle_btn.setStyleSheet("text-align: left; font-weight: bold; border: none; padding: 4px;")
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.toggled.connect(self._on_toggle)
        self._layout.addWidget(self._toggle_btn)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(12, 0, 0, 0)
        self._content.setVisible(False)
        self._layout.addWidget(self._content)

        self._title = title

    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def _on_toggle(self, checked: bool) -> None:
        self._content.setVisible(checked)
        arrow = "▼" if checked else "▶"
        self._toggle_btn.setText(f"{arrow} {self._title}")


class BaseModule(QWidget):
    """Abstract base for every tool module in the application.

    Subclasses implement ``build_input_section``, ``build_params_section``,
    ``build_output_section``, and the ``run_tool`` action.
    """

    # Emitted when the module produces an output file that can be sent elsewhere
    output_ready = pyqtSignal(str)  # path to output file

    MODULE_NAME: str = "Unnamed Module"
    MODULE_DESCRIPTION: str = ""
    MODULE_CATEGORY: str = ""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._runner = ProcessRunner()
        self._runner.output_line.connect(self._on_process_output)
        self._runner.finished.connect(self._on_process_finished)
        self._runner.error.connect(self._on_process_error)

        self._last_dirs: dict[str, str] = {}
        self._save_line_edit: QLineEdit | None = None
        self._save_file_filter: str = "All Files (*)"
        self._build_ui()
        self._snapshot_defaults()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._wheel_filter = _NoScrollWheelFilter(self)
        inner = QWidget()
        self._main_layout = QVBoxLayout(inner)

        # Header
        header = QLabel(self.MODULE_NAME)
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 4px;")
        self._main_layout.addWidget(header)
        if self.MODULE_DESCRIPTION:
            desc = QLabel(self.MODULE_DESCRIPTION)
            desc.setWordWrap(True)
            desc.setStyleSheet("color: gray; margin-bottom: 8px;")
            self._main_layout.addWidget(desc)

        # Sections built by subclasses
        input_grp = QGroupBox("Input")
        input_layout = QVBoxLayout(input_grp)
        self.build_input_section(input_layout)
        self._main_layout.addWidget(input_grp)

        params_grp = QGroupBox("Parameters")
        params_layout = QVBoxLayout(params_grp)
        self.build_params_section(params_layout)
        self._main_layout.addWidget(params_grp)

        # Advanced options (collapsible) — hidden when empty
        self._advanced = CollapsibleSection("Advanced Options")
        self.build_advanced_section(self._advanced.content_layout())
        if self._advanced.content_layout().count() > 0:
            self._main_layout.addWidget(self._advanced)
        else:
            self._advanced.setVisible(False)

        # Output section
        output_grp = QGroupBox("Output")
        output_layout = QVBoxLayout(output_grp)
        self.build_output_section(output_layout)
        self._main_layout.addWidget(output_grp)

        # Execution controls
        exec_layout = QHBoxLayout()
        self._run_btn = QPushButton("Run")
        self._run_btn.setToolTip("Run and save to the current output file.")
        self._run_btn.clicked.connect(self._on_run_clicked)
        self._save_as_run_btn = QPushButton("Save as\u2026 + Run")
        self._save_as_run_btn.setToolTip("Choose a new output file, then run.")
        self._save_as_run_btn.clicked.connect(self._on_run_save_as_clicked)
        if self._save_line_edit is None:
            self._save_as_run_btn.setVisible(False)
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        self._reset_btn = QPushButton("Reset to Defaults")
        self._reset_btn.setToolTip("Reset all fields in this module to their initial values.")
        self._reset_btn.clicked.connect(self._reset_to_defaults)
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate
        self._progress.setVisible(False)
        exec_layout.addWidget(self._run_btn)
        exec_layout.addWidget(self._save_as_run_btn)
        exec_layout.addWidget(self._stop_btn)
        exec_layout.addWidget(self._reset_btn)
        exec_layout.addWidget(self._progress, stretch=1)
        self._main_layout.addLayout(exec_layout)

        # Keep save-as button in sync with run button's enabled state so
        # subclass code that sets _run_btn.setEnabled() works automatically.
        _orig_run_setEnabled = self._run_btn.setEnabled

        def _synced_setEnabled(enabled: bool) -> None:
            _orig_run_setEnabled(enabled)
            self._save_as_run_btn.setEnabled(enabled)

        self._run_btn.setEnabled = _synced_setEnabled

        # Log / preview area
        self._output_log = QTextEdit()
        self._output_log.setReadOnly(True)
        self._output_log.setMaximumHeight(200)
        self._main_layout.addWidget(self._output_log)

        self._main_layout.addStretch()
        # Install wheel-block filter on all scrollable input widgets
        from PyQt6.QtWidgets import QAbstractSpinBox, QAbstractSlider
        for child in inner.findChildren(QWidget):
            if isinstance(child, (QComboBox, QAbstractSpinBox, QAbstractSlider)):
                child.installEventFilter(self._wheel_filter)
        scroll.setWidget(inner)
        root.addWidget(scroll)

    # ------------------------------------------------------------------
    # Methods subclasses override
    # ------------------------------------------------------------------
    @abstractmethod
    def build_input_section(self, layout: QVBoxLayout) -> None:
        """Populate the Input group box."""

    @abstractmethod
    def build_params_section(self, layout: QVBoxLayout) -> None:
        """Populate the Parameters group box."""

    def build_advanced_section(self, layout: QVBoxLayout) -> None:
        """Override to add advanced options. Default: empty."""

    @abstractmethod
    def build_output_section(self, layout: QVBoxLayout) -> None:
        """Populate the Output group box."""

    @abstractmethod
    def run_tool(self) -> None:
        """Called when the user clicks Run. Start the tool."""

    def get_output_path(self) -> Optional[str]:
        """Return the last output file path, if any."""
        return None

    def validate(self) -> list[str]:
        """Return a list of validation error messages (empty = OK).

        Override in subclasses to check required fields before run_tool().
        """
        return []

    # ------------------------------------------------------------------
    # Slot helpers
    # ------------------------------------------------------------------
    def _on_run_clicked(self) -> None:
        errors = self.validate()
        if errors:
            QMessageBox.warning(
                self, "Validation Error",
                "Please fix the following before running:\n\n• " + "\n• ".join(errors),
            )
            return
        self._output_log.clear()
        self._run_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._progress.setVisible(True)
        self.run_tool()

    def _on_run_save_as_clicked(self) -> None:
        """Open a Save dialog, update the output path, then run."""
        if not self._save_line_edit:
            return
        current = self._save_line_edit.text().strip()
        start_dir = str(Path(current).parent) if current else str(self._default_output_dir())
        path, _ = QFileDialog.getSaveFileName(
            self, "Save output as\u2026", start_dir, self._save_file_filter,
        )
        if not path:
            return
        self._save_line_edit.setText(path)
        self._on_run_clicked()

    def _on_stop_clicked(self) -> None:
        self._runner.cancel()
        self._stop_btn.setEnabled(False)

    def _on_process_output(self, line: str) -> None:
        self._output_log.append(line)

    def _on_process_finished(self, exit_code: int) -> None:
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress.setVisible(False)
        if exit_code == 0:
            self._output_log.append("\n✓ Process finished successfully.")
            hint = self._get_what_next_hint()
            if hint:
                self._output_log.append(f"\n👉 What next? {hint}")
        else:
            self._output_log.append(f"\n✗ Process exited with code {exit_code}.")

    def _get_what_next_hint(self) -> str:
        """Return a contextual suggestion for what the user should do next."""
        from ..app.tool_registry import TOOLS
        my_tool = next((t for t in TOOLS if t.name == self.MODULE_NAME), None)
        if not my_tool or not my_tool.produces_output_types:
            return ""
        suggestions: list[str] = []
        if "wordlist" in my_tool.produces_output_types:
            suggestions.append('Use "Send to…" to clean with demeuk or launch an attack with Hashcat.')
        elif "mask" in my_tool.produces_output_types:
            suggestions.append('Use "Send to…" to launch a mask attack in Hashcat Command Builder.')
        elif "rule" in my_tool.produces_output_types:
            suggestions.append('Use "Send to…" to apply these rules in Hashcat Command Builder.')
        elif "csv" in my_tool.produces_output_types:
            suggestions.append('Use "Send to…" to generate optimized masks with MaskGen.')
        elif "ruleset" in my_tool.produces_output_types:
            suggestions.append('Use the trained ruleset in PCFG Guesser to generate password candidates.')
        return " ".join(suggestions) if suggestions else ""

    def _on_process_error(self, msg: str) -> None:
        self._output_log.append(f"ERROR: {msg}")

    # ------------------------------------------------------------------
    # Reset to defaults
    # ------------------------------------------------------------------
    def _snapshot_defaults(self) -> None:
        """Record the initial state of all editable child widgets."""
        self._defaults: list[tuple] = []
        # Skip the output log and preview boxes (read-only QTextEdits)
        skip = {id(self._output_log)}
        for w in self.findChildren(QSpinBox):
            self._defaults.append(("spin", w, w.value()))
        for w in self.findChildren(QCheckBox):
            self._defaults.append(("check", w, w.isChecked()))
        for w in self.findChildren(QRadioButton):
            self._defaults.append(("radio", w, w.isChecked()))
        for w in self.findChildren(QComboBox):
            self._defaults.append(("combo", w, w.currentIndex()))
        for w in self.findChildren(QLineEdit):
            self._defaults.append(("line", w, w.text()))
        for w in self.findChildren(QTextEdit):
            if id(w) not in skip and not w.isReadOnly():
                self._defaults.append(("text", w, w.toPlainText()))

    def _reset_to_defaults(self) -> None:
        """Restore all editable widgets to their initial values."""
        for kind, widget, value in self._defaults:
            if kind == "spin":
                widget.setValue(value)
            elif kind == "check":
                widget.setChecked(value)
            elif kind == "radio":
                widget.setChecked(value)
            elif kind == "combo":
                widget.setCurrentIndex(value)
            elif kind == "line":
                widget.setText(value)
            elif kind == "text":
                widget.setPlainText(value)
        self._output_log.clear()

    # ------------------------------------------------------------------
    # Default output directory
    # ------------------------------------------------------------------
    def _default_output_dir(self) -> Path:
        """Return the default output folder for this module, creating it if needed.

        Layout: ``<base_dir>/output/<slug>_output/``
        """
        slug = re.sub(r"[^a-z0-9]+", "_", self.MODULE_NAME.lower()).strip("_")
        base = getattr(self, "_base_dir", None)
        if base:
            root = Path(base) / "output" / f"{slug}_output"
        else:
            root = Path.cwd() / "output" / f"{slug}_output"
        root.mkdir(parents=True, exist_ok=True)
        return root

    # ------------------------------------------------------------------
    # Convenience helpers for subclasses
    # ------------------------------------------------------------------
    @staticmethod
    def _info_icon(tooltip: str) -> QLabel:
        """Return a small ⓘ label that shows *tooltip* on hover."""
        icon = QLabel("ⓘ")
        icon.setToolTip(tooltip)
        icon.setFixedWidth(16)
        icon.setStyleSheet(
            "color: #89b4fa; font-weight: bold; font-size: 13px; "
            "qproperty-alignment: AlignCenter; cursor: pointer;"
        )
        icon.setCursor(Qt.CursorShape.WhatsThisCursor)
        return icon

    def create_file_browser(
        self,
        layout,
        label: str,
        tooltip: str = "",
        save: bool = False,
        directory: bool = False,
        file_filter: str = "All Files (*)",
        key: str = "",
        receive_type: str = "",
    ) -> QLineEdit:
        """Add a file browser row (label + line-edit + browse button).

        If *receive_type* is set (e.g. ``"wordlist"``), a "Receive from…"
        dropdown button is appended to the same row.
        """
        row = QHBoxLayout()
        lbl = QLabel(label)
        line = QLineEdit()
        btn = QPushButton("Browse…")
        browse_key = key or label

        def browse() -> None:
            start = self._last_dirs.get(browse_key, "")
            if directory:
                path = QFileDialog.getExistingDirectory(self, f"Select {label}", start)
            elif save:
                path, _ = QFileDialog.getSaveFileName(self, f"Save {label}", start, file_filter)
            else:
                path, _ = QFileDialog.getOpenFileName(self, f"Open {label}", start, file_filter)
            if path:
                line.setText(path)
                self._last_dirs[browse_key] = str(Path(path).parent)
                # Warn if file is very large (>1 GB)
                if not save and not directory:
                    try:
                        size = Path(path).stat().st_size
                        if size > 1_073_741_824:
                            gb = size / 1_073_741_824
                            QMessageBox.warning(
                                self, "Large File",
                                f"This file is {gb:.1f} GB. Processing may be slow "
                                f"and use significant memory.",
                            )
                    except OSError:
                        pass

        btn.clicked.connect(browse)
        if save:
            self._save_line_edit = line
            self._save_file_filter = file_filter
        row.addWidget(lbl)
        if tooltip:
            row.addWidget(self._info_icon(tooltip))
        row.addWidget(line, stretch=1)
        row.addWidget(btn)

        # Bookmark quick-access button
        bookmark_dirs = self._get_bookmark_dirs()
        if bookmark_dirs:
            from PyQt6.QtWidgets import QMenu
            bm_btn = QPushButton("★")
            bm_btn.setFixedWidth(28)
            bm_btn.setToolTip("Quick-access bookmarks to toolkit directories")
            bm_menu = QMenu(self)
            for bm_label, bm_path in bookmark_dirs:
                action = bm_menu.addAction(bm_label)
                action.triggered.connect(
                    lambda checked, p=bm_path, k=browse_key: self._bookmark_navigate(p, k, line, save, file_filter)
                )
            bm_btn.setMenu(bm_menu)
            row.addWidget(bm_btn)

        if receive_type:
            self.receive_from_menu(row, line, receive_type)
        layout.addLayout(row)
        return line

    def _get_bookmark_dirs(self) -> list[tuple[str, str]]:
        """Return list of (label, path) bookmark entries for toolkit directories."""
        bookmarks: list[tuple[str, str]] = []
        base = Path(__file__).resolve().parent.parent.parent  # project root
        candidates = [
            ("Scripts_to_use/", base / "Scripts_to_use"),
            ("hashcat rules/", base / "hashcat-7.1.2" / "rules"),
            ("hashcat masks/", base / "hashcat-7.1.2" / "masks"),
            ("hashcat charsets/", base / "hashcat-7.1.2" / "charsets"),
            ("hashcat layouts/", base / "hashcat-7.1.2" / "layouts"),
            ("PCFG Rules/", base / "Scripts_to_use" / "pcfg_cracker-master" / "pcfg_cracker-master" / "Rules"),
            ("PCFG Rules/", base / "Scripts_to_use" / "pcfg_cracker-master" / "Rules"),
        ]
        for label, p in candidates:
            if p.is_dir():
                if label not in {b[0] for b in bookmarks}:
                    bookmarks.append((label, str(p)))
        return bookmarks

    def _bookmark_navigate(self, dir_path: str, browse_key: str, line_edit: QLineEdit,
                           save: bool, file_filter: str) -> None:
        """Open a file dialog starting in the bookmarked directory."""
        if save:
            path, _ = QFileDialog.getSaveFileName(self, "Save file", dir_path, file_filter)
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Open file", dir_path, file_filter)
        if path:
            line_edit.setText(path)
            self._last_dirs[browse_key] = str(Path(path).parent)

    def create_spinbox(
        self,
        layout,
        label: str,
        minimum: int = 0,
        maximum: int = 999999999,
        default: int = 0,
        tooltip: str = "",
    ) -> QSpinBox:
        row = QHBoxLayout()
        lbl = QLabel(label)
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(default)
        row.addWidget(lbl)
        if tooltip:
            row.addWidget(self._info_icon(tooltip))
        row.addWidget(spin)
        row.addStretch()
        layout.addLayout(row)
        return spin

    def create_checkbox(self, layout, label: str, default: bool = False, tooltip: str = "") -> QCheckBox:
        if tooltip:
            row = QHBoxLayout()
            cb = QCheckBox(label)
            cb.setChecked(default)
            row.addWidget(cb)
            row.addWidget(self._info_icon(tooltip))
            row.addStretch()
            layout.addLayout(row)
        else:
            cb = QCheckBox(label)
            cb.setChecked(default)
            layout.addWidget(cb)
        return cb

    def create_combo(self, layout, label: str, items: list[str], tooltip: str = "") -> QComboBox:
        row = QHBoxLayout()
        lbl = QLabel(label)
        combo = QComboBox()
        combo.addItems(items)
        row.addWidget(lbl)
        if tooltip:
            row.addWidget(self._info_icon(tooltip))
        row.addWidget(combo)
        row.addStretch()
        layout.addLayout(row)
        return combo

    def create_line_edit(self, layout, label: str, default: str = "", tooltip: str = "") -> QLineEdit:
        row = QHBoxLayout()
        lbl = QLabel(label)
        line = QLineEdit(default)
        row.addWidget(lbl)
        if tooltip:
            row.addWidget(self._info_icon(tooltip))
        row.addWidget(line, stretch=1)
        layout.addLayout(row)
        return line

    def send_to_menu(self, layout, targets: list[str]) -> QPushButton:
        """Create a 'Send to…' button with dynamic target population.

        *targets* provides preferred/pinned targets shown first. Additional
        compatible targets are appended dynamically from the tool registry.
        """
        btn = QPushButton("Send to…")
        btn.setToolTip("Send this output to another tool's input.")
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        self._send_to_preferred = targets  # kept for dynamic menu

        def _populate() -> None:
            menu.clear()
            seen = set()
            # Preferred targets first
            for t in targets:
                action = menu.addAction(t)
                action.triggered.connect(lambda checked, tgt=t: self._send_to(tgt))
                seen.add(t)
            # Dynamic: find compatible targets from registry
            from ..app.tool_registry import TOOLS
            my_tool = next((t for t in TOOLS if t.name == self.MODULE_NAME), None)
            if my_tool:
                for out_type in my_tool.produces_output_types:
                    from ..app.tool_registry import get_compatible_targets
                    for name in get_compatible_targets(out_type):
                        if name not in seen and name != self.MODULE_NAME:
                            action = menu.addAction(name)
                            action.triggered.connect(lambda checked, tgt=name: self._send_to(tgt))
                            seen.add(name)
            if not seen:
                a = menu.addAction("(no targets available)")
                a.setEnabled(False)

        menu.aboutToShow.connect(_populate)
        btn.setMenu(menu)
        layout.addWidget(btn)
        return btn

    def _send_to(self, target: str) -> None:
        from crackers_toolkit.app.data_bus import data_bus
        output = self.get_output_path()
        if output:
            data_bus.send(source=self.MODULE_NAME, target=target, path=output)
        else:
            QMessageBox.warning(self, "No Output", "Run the tool first to produce output.")

    def receive_from(self, path: str) -> None:
        """Called by the data bus when another module sends data here."""

    def receive_from_menu(
        self,
        layout,
        line_edit: QLineEdit,
        output_type: str,
        label: str = "Receive from…",
    ) -> QPushButton:
        """Create a 'Receive from…' button that populates *line_edit* from another module."""
        from PyQt6.QtWidgets import QMenu
        from crackers_toolkit.app.data_bus import data_bus

        btn = QPushButton(label)
        btn.setToolTip(f"Populate this field with output from another tool ({output_type}).")
        menu = QMenu(self)

        # Dynamically populate with registered targets that produce this type
        def _about_to_show() -> None:
            menu.clear()
            from ..app.tool_registry import get_compatible_targets
            # get_compatible_targets returns tools that *accept* an output_type,
            # but here we want tools that *produce* it.  Walk the registry.
            from ..app.tool_registry import TOOLS
            producers = [
                t.name for t in TOOLS
                if output_type in t.produces_output_types and t.module_class
            ]
            if not producers:
                action = menu.addAction("(no sources available)")
                action.setEnabled(False)
            else:
                for name in producers:
                    action = menu.addAction(name)
                    action.triggered.connect(
                        lambda checked, n=name: self._receive_request(n, line_edit)
                    )

        menu.aboutToShow.connect(_about_to_show)
        btn.setMenu(menu)
        layout.addWidget(btn)
        return btn

    def _receive_request(self, source_name: str, target_edit: QLineEdit) -> None:
        """Ask the named module for its last output and fill target_edit."""
        from ..app.main_window import MainWindow
        from ..app.tool_registry import TOOLS
        # Find the module widget if loaded
        main = self.window()
        if isinstance(main, MainWindow):
            for mid, widget in main._loaded_modules.items():
                tool = next((t for t in TOOLS if t.module_id == mid), None)
                if tool and tool.name == source_name:
                    path = widget.get_output_path() if hasattr(widget, "get_output_path") else None
                    if path:
                        target_edit.setText(path)
                        return
        QMessageBox.information(
            self, "No Output",
            f"{source_name} has not produced output yet.\n"
            f"Open and run {source_name} first, then try again.",
        )
