"""Main application window with sidebar navigation and content area."""

from __future__ import annotations

import importlib
import os
import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .data_bus import data_bus
from .dependency_checker import DependencyDialog, run_checks
from .logging_panel import LoggingPanel
from .settings import Settings, SettingsDialog
from .sidebar import Sidebar
from .tool_registry import TOOLS, get_tool_by_id, get_tool_by_name


class MainWindow(QMainWindow):
    """Top-level window: sidebar (left) + stacked content area (right)."""

    def __init__(self, base_dir: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Cracker's Toolkit")
        self.setMinimumSize(1100, 700)

        # Inherit app-level icon so title bar + taskbar show the logo
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app and not app.windowIcon().isNull():
            self.setWindowIcon(app.windowIcon())

        self._settings = Settings(base_dir)
        self._base_dir = base_dir
        self._loaded_modules: dict[int, QWidget] = {}

        self._build_menu()
        self._build_central()

        # Wire data bus navigation and lazy-loading
        data_bus.navigate_to_tool.connect(self._navigate_to_tool_by_name)
        data_bus._ensure_loaded = self._ensure_tool_loaded

        self._apply_theme()

        # First-run dependency check
        if not self._settings.get("dependency_check_done"):
            self._run_dependency_check(first_run=True)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------
    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction("Settings…", self._open_settings)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        view_menu = menubar.addMenu("&View")
        view_menu.addAction("View Log", self._show_log)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("What should I use?", self._show_guide)
        help_menu.addAction("Check Dependencies…", self._run_dependency_check)
        help_menu.addAction("About", self._show_about)

    # ------------------------------------------------------------------
    # Central widget
    # ------------------------------------------------------------------
    def _build_central(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sidebar
        self._sidebar = Sidebar()
        self._sidebar.tool_selected.connect(self._on_tool_selected)
        splitter.addWidget(self._sidebar)

        # Content area (stacked widget)
        self._stack = QStackedWidget()

        # Default welcome page
        welcome = self._build_welcome()
        self._stack.addWidget(welcome)

        # Log panel (hidden — shown via menu)
        self._log_panel = LoggingPanel()
        self._stack.addWidget(self._log_panel)

        splitter.addWidget(self._stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 800])

        layout.addWidget(splitter)

    def _build_welcome(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Cracker's Toolkit")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(
            "Select a category from the sidebar, then choose a tool.\n"
            "Use the search bar to find tools by keyword."
        )
        subtitle.setStyleSheet("color: #888; font-size: 14px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        return w

    # ------------------------------------------------------------------
    # Tool loading
    # ------------------------------------------------------------------
    def _on_tool_selected(self, module_id: int) -> None:
        if module_id in self._loaded_modules:
            self._stack.setCurrentWidget(self._loaded_modules[module_id])
            return

        tool = get_tool_by_id(module_id)
        if not tool or not tool.module_class:
            QMessageBox.information(self, "Not Available", "This module is not implemented yet.")
            return

        try:
            module_path, class_name = tool.module_class.rsplit(".", 1)
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            widget = cls(settings=self._settings, base_dir=self._base_dir)

            # Register with data bus
            if hasattr(widget, "receive_from"):
                data_bus.register(tool.name, widget.receive_from)

            # Wire subprocess logging
            if hasattr(widget, "_runner"):
                runner = widget._runner
                runner.started.connect(
                    lambda cmd: self._log_panel.log_command(cmd)
                )
                runner.completed.connect(
                    lambda cmd, rc, secs: self._log_panel.log_finish(
                        self._find_log_index(cmd), rc, secs
                    )
                )

            self._stack.addWidget(widget)
            self._loaded_modules[module_id] = widget
            self._stack.setCurrentWidget(widget)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Module Load Error",
                f"Failed to load {tool.name}:\n{exc}",
            )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _navigate_to_tool_by_name(self, tool_name: str) -> None:
        """Switch the UI to the named tool (called by data bus after send)."""
        tool = get_tool_by_name(tool_name)
        if tool:
            self._on_tool_selected(tool.module_id)
            self.statusBar().showMessage(f"✓ Data sent to {tool_name}", 3000)

    def _ensure_tool_loaded(self, tool_name: str) -> None:
        """Lazy-load a module by name so the data bus can deliver to it."""
        tool = get_tool_by_name(tool_name)
        if tool and tool.module_id not in self._loaded_modules:
            self._on_tool_selected(tool.module_id)

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._settings, self)
        if dlg.exec():
            self._apply_theme()

    def _show_log(self) -> None:
        self._stack.setCurrentWidget(self._log_panel)

    def _find_log_index(self, cmd: str) -> int:
        """Find the most recent log entry matching *cmd*."""
        for i in range(len(self._log_panel._entries) - 1, -1, -1):
            if self._log_panel._entries[i].command == cmd:
                return i
        return -1

    def _show_guide(self) -> None:
        if not hasattr(self, "_guide_widget"):
            from .help_guide import HelpGuideWidget
            self._guide_widget = HelpGuideWidget(
                navigate_callback=self._on_tool_selected, parent=self
            )
            self._stack.addWidget(self._guide_widget)
        self._stack.setCurrentWidget(self._guide_widget)

    def _run_dependency_check(self, first_run: bool = False) -> None:
        """Run the dependency checker and show a status dialog."""
        base = self._base_dir or Path(".")
        while True:
            results = run_checks(base, self._settings)
            dlg = DependencyDialog(results, self)
            code = dlg.exec()
            if code == 2:          # Re-check requested
                continue
            if first_run:
                self._settings.set("dependency_check_done", True)
                self._settings.save()
            break

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About Cracker's Toolkit",
            "Cracker's Toolkit GUI v0.1.0\n\n"
            "A unified interface for password cracking tools.\n"
            "For authorized security testing, CTF competitions,\n"
            "and password security research.",
        )

    def _apply_theme(self) -> None:
        theme = self._settings.get("theme")
        if theme == "dark":
            # Generate a checkmark SVG for checkbox indicators
            _svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
                    '<path d="M3.5 8.5l3 3 6-7" stroke="#1e1e2e" stroke-width="2.2"'
                    ' fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')
            _ck_path = os.path.join(tempfile.gettempdir(), "ct_checkmark.svg")
            if not os.path.exists(_ck_path):
                with open(_ck_path, "w", encoding="utf-8") as _f:
                    _f.write(_svg)
            _ck_url = _ck_path.replace("\\", "/")

            # Generate a filled-circle SVG for radio button indicators
            _radio_svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
                          '<circle cx="8" cy="8" r="4" fill="#89b4fa"/></svg>')
            _rd_path = os.path.join(tempfile.gettempdir(), "ct_radiodot.svg")
            if not os.path.exists(_rd_path):
                with open(_rd_path, "w", encoding="utf-8") as _f:
                    _f.write(_radio_svg)
            _rd_url = _rd_path.replace("\\", "/")

            # Generate arrow SVGs for spinbox buttons
            _up_svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8">'
                       '<polygon points="4,1 7,7 1,7" fill="#cdd6f4"/></svg>')
            _up_path = os.path.join(tempfile.gettempdir(), "ct_spin_up.svg")
            with open(_up_path, "w", encoding="utf-8") as _f:
                _f.write(_up_svg)
            _up_url = _up_path.replace("\\", "/")

            _dn_svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8">'
                       '<polygon points="1,1 7,1 4,7" fill="#cdd6f4"/></svg>')
            _dn_path = os.path.join(tempfile.gettempdir(), "ct_spin_dn.svg")
            with open(_dn_path, "w", encoding="utf-8") as _f:
                _f.write(_dn_svg)
            _dn_url = _dn_path.replace("\\", "/")

            _checked_css = (
                "QCheckBox::indicator:checked {"
                f"  background-color: #89b4fa; border-color: #89b4fa; image: url({_ck_url});"
                "}"
                "QCheckBox::indicator:checked:hover {"
                f"  background-color: #74c7ec; border-color: #74c7ec; image: url({_ck_url});"
                "}"
                "QRadioButton::indicator:checked {"
                f"  border-color: #89b4fa; background-color: #313244; image: url({_rd_url});"
                "}"
                "QRadioButton::indicator:checked:hover {"
                f"  border-color: #74c7ec; image: url({_rd_url});"
                "}"
            )
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #1e1e2e;
                    color: #cdd6f4;
                }
                QGroupBox {
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    margin-top: 8px;
                    padding-top: 12px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 8px;
                    padding: 0 4px;
                }
                QLineEdit, QTextEdit, QSpinBox, QComboBox {
                    background-color: #313244;
                    border: 1px solid #45475a;
                    border-radius: 3px;
                    padding: 4px;
                    color: #cdd6f4;
                }
                QSpinBox, QDoubleSpinBox {
                    padding-right: 18px;
                }
                QSpinBox::up-button, QDoubleSpinBox::up-button {
                    subcontrol-origin: border;
                    subcontrol-position: top right;
                    width: 18px;
                    border-left: 1px solid #45475a;
                    border-bottom: 1px solid #45475a;
                    border-top-right-radius: 3px;
                    background-color: #45475a;
                }
                QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
                    background-color: #585b70;
                }
                QSpinBox::down-button, QDoubleSpinBox::down-button {
                    subcontrol-origin: border;
                    subcontrol-position: bottom right;
                    width: 18px;
                    border-left: 1px solid #45475a;
                    border-top: 1px solid #45475a;
                    border-bottom-right-radius: 3px;
                    background-color: #45475a;
                }
                QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
                    background-color: #585b70;
                }
                QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
                    image: url(""" + _up_url + """);
                    width: 8px;
                    height: 8px;
                }
                QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                    image: url(""" + _dn_url + """);
                    width: 8px;
                    height: 8px;
                }
                QPushButton {
                    background-color: #45475a;
                    border: 1px solid #585b70;
                    border-radius: 3px;
                    padding: 6px 14px;
                    color: #cdd6f4;
                }
                QPushButton:hover {
                    background-color: #585b70;
                }
                QPushButton:pressed {
                    background-color: #6c7086;
                }
                QPushButton:disabled {
                    background-color: #313244;
                    color: #6c7086;
                }
                QScrollArea {
                    border: none;
                }
                QProgressBar {
                    border: 1px solid #45475a;
                    border-radius: 3px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #89b4fa;
                }
                QCheckBox {
                    spacing: 6px;
                    color: #cdd6f4;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 2px solid #7f849c;
                    border-radius: 3px;
                    background-color: #313244;
                }
                QCheckBox::indicator:hover {
                    border-color: #89b4fa;
                }
                QRadioButton {
                    spacing: 6px;
                    color: #cdd6f4;
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                    border: 2px solid #7f849c;
                    border-radius: 9px;
                    background-color: #313244;
                }
                QRadioButton::indicator:hover {
                    border-color: #89b4fa;
                }
                QRadioButton::indicator:checked {
                    border-color: #89b4fa;
                    background-color: #313244;
                }
                QRadioButton::indicator:checked:hover {
                    border-color: #74c7ec;
                }
                QSplitter::handle {
                    background-color: #45475a;
                }
                QMenuBar {
                    background-color: #181825;
                    color: #cdd6f4;
                }
                QMenuBar::item:selected {
                    background-color: #45475a;
                }
                QMenu {
                    background-color: #313244;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                }
                QMenu::item:selected {
                    background-color: #45475a;
                }
            """ + _checked_css)
        else:
            self.setStyleSheet("")
