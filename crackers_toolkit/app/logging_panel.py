"""Application log viewer panel.

All subprocess calls are logged with full commands, timestamp, exit code,
and runtime.  The log panel is accessible via "View Log" in the menu bar.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


@dataclass
class LogEntry:
    timestamp: str
    command: str
    exit_code: int | None = None
    runtime_seconds: float | None = None
    message: str = ""


class LoggingPanel(QWidget):
    """Scrollable panel that shows logged subprocess calls."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._entries: list[LogEntry] = []
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear)
        export_btn = QPushButton("Export Log")
        export_btn.setToolTip("Save the full log to a .log file.")
        export_btn.clicked.connect(self._export_log)
        toolbar.addStretch()
        toolbar.addWidget(export_btn)
        toolbar.addWidget(clear_btn)
        layout.addLayout(toolbar)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setStyleSheet("font-family: 'Consolas', 'DejaVu Sans Mono', 'Courier New', monospace; font-size: 12px;")
        layout.addWidget(self._text)

    def log_command(self, command: str) -> int:
        """Log a command invocation and return the entry index."""
        entry = LogEntry(
            timestamp=datetime.datetime.now().isoformat(timespec="seconds"),
            command=command,
        )
        self._entries.append(entry)
        self._text.append(f"[{entry.timestamp}] RUN: {command}")
        return len(self._entries) - 1

    def log_finish(self, index: int, exit_code: int, runtime: float) -> None:
        if 0 <= index < len(self._entries):
            e = self._entries[index]
            e.exit_code = exit_code
            e.runtime_seconds = runtime
            self._text.append(
                f"[{e.timestamp}] DONE (exit={exit_code}, {runtime:.1f}s): {e.command}"
            )

    def log_message(self, message: str) -> None:
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        self._entries.append(LogEntry(timestamp=ts, command="", message=message))
        self._text.append(f"[{ts}] {message}")

    def clear(self) -> None:
        self._entries.clear()
        self._text.clear()

    def _export_log(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Log", "crackers_toolkit.log",
            "Log Files (*.log *.txt);;All Files (*)",
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self._text.toPlainText())
            except OSError:
                pass
