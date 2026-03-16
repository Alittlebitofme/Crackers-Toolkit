"""Module 11: StatsGen GUI (PACK).

Analyze a password list to discover statistical patterns: length
distributions, character set usage, mask frequency. Wraps the ported
pack_ports/statsgen.py.

Rich output: parses CLI text into tabbed views with bar charts
(Length Distribution, Character Sets, Simple Masks, Advanced Masks,
Complexity).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .base_module import BaseModule


# ── Charset names supported by pack_ports/statsgen.py ─────────────────
_CHARSET_OPTIONS = [
    "loweralpha",
    "upperalpha",
    "numeric",
    "special",
    "mixedalpha",
    "loweralphanum",
    "upperalphanum",
    "mixedalphanum",
    "loweralphaspecial",
    "upperalphaspecial",
    "specialnum",
    "mixedalphaspecial",
    "loweralphaspecialnum",
    "upperalphaspecialnum",
    "all",
]


class StatsGenModule(BaseModule):
    MODULE_NAME = "StatsGen (PACK)"
    MODULE_DESCRIPTION = (
        "Analyze a password list to discover statistical patterns: "
        "length distributions, character set usage, mask frequency, "
        "and complexity ranges. Essential input for the Mask Generator."
    )
    MODULE_CATEGORY = "Wordlist Analysis"

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        super().__init__(parent)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def build_input_section(self, layout: QVBoxLayout) -> None:
        self._input_file = self.create_file_browser(
            layout,
            "Password file:",
            "Plaintext password file to analyze, one per line.",
            file_filter="Text Files (*.txt);;All Files (*)",
        )

    # ------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------
    def build_params_section(self, layout: QVBoxLayout) -> None:
        self._min_length = self.create_spinbox(
            layout, "Min length:", 0, 999, 0,
            "Only analyze passwords of at least this length. 0 = no filter.",
        )
        self._max_length = self.create_spinbox(
            layout, "Max length:", 0, 999, 0,
            "Only analyze passwords up to this length. 0 = no filter.",
        )
        self._hiderare = self.create_checkbox(
            layout, "Hide rare (< 1%)", False,
            "Suppress statistics covering less than 1% of the sample.",
        )

        # ── Charset filter multi-select ──
        grp = QGroupBox("Charset filter (leave all unchecked = no filter)")
        grid = QGridLayout()
        self._charset_checks: dict[str, QCheckBox] = {}
        for idx, name in enumerate(_CHARSET_OPTIONS):
            _cr = QHBoxLayout()
            cb = QCheckBox(name)
            _cr.addWidget(cb)
            _cr.addWidget(self._info_icon(f"Include only passwords matching the '{name}' charset."))
            _cr.addStretch()
            self._charset_checks[name] = cb
            grid.addLayout(_cr, idx // 3, idx % 3)
        grp.setLayout(grid)
        layout.addWidget(grp)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    def build_output_section(self, layout: QVBoxLayout) -> None:
        self._output_csv = self.create_file_browser(
            layout, "Output CSV (-o):",
            "Save mask statistics to CSV for use in MaskGen.",
            save=True, file_filter="CSV Files (*.csv);;All Files (*)",
        )
        self._output_csv.setText(str(self._default_output_dir() / "statsgen_output.csv"))

        # ── Tabbed results view ──
        self._tabs = QTabWidget()
        self._tab_length = self._make_stat_table(["Length", "%", "Count"])
        self._tab_charset = self._make_stat_table(["Character Set", "%", "Count"])
        self._tab_simple = self._make_stat_table(["Simple Mask", "%", "Count"])
        self._tab_advanced = self._make_stat_table(["Advanced Mask", "%", "Count"])
        self._tab_complexity = QTextEdit()
        self._tab_complexity.setReadOnly(True)
        self._tab_raw = QTextEdit()
        self._tab_raw.setReadOnly(True)
        self._tab_raw.setStyleSheet("font-family: Consolas, 'DejaVu Sans Mono', 'Courier New', monospace;")

        self._tabs.addTab(self._tab_length, "Length Distribution")
        self._tabs.addTab(self._tab_charset, "Character Sets")
        self._tabs.addTab(self._tab_simple, "Simple Masks")
        self._tabs.addTab(self._tab_advanced, "Advanced Masks")
        self._tabs.addTab(self._tab_complexity, "Complexity")
        self._tabs.addTab(self._tab_raw, "Raw Output")
        layout.addWidget(self._tabs, stretch=1)

        row = QHBoxLayout()
        self.send_to_menu(row, ["MaskGen (PACK)", "Hashcat Command Builder"])
        row.addStretch()
        layout.addLayout(row)

    # ------------------------------------------------------------------
    # Helpers: table builder
    # ------------------------------------------------------------------
    @staticmethod
    def _make_stat_table(headers: list[str]) -> QTableWidget:
        tbl = QTableWidget(0, len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        return tbl

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        errors: list[str] = []
        inp = self._input_file.text().strip()
        if not inp:
            errors.append("Select a password file to analyze.")
        elif not Path(inp).is_file():
            errors.append(f"Password file not found: {inp}")
        return errors

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    def run_tool(self) -> None:
        script = self._find_statsgen()
        if not script:
            self._output_log.append(
                "Error: statsgen.py port not found.\n"
                "Expected in: crackers_toolkit/pack_ports/\n"
                "Verify the application installation is complete."
            )
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        inp = self._input_file.text().strip()
        if not inp:
            self._output_log.append("Error: no password file selected.")
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        python = self._find_python()
        cmd = [python, str(script)]

        min_l = self._min_length.value()
        if min_l > 0:
            cmd += ["--minlength", str(min_l)]

        max_l = self._max_length.value()
        if max_l > 0:
            cmd += ["--maxlength", str(max_l)]

        if self._hiderare.isChecked():
            cmd.append("--hiderare")

        # Charset filter
        selected = [n for n, cb in self._charset_checks.items() if cb.isChecked()]
        if selected:
            cmd += ["--charset", ",".join(selected)]

        out = self._output_csv.text().strip()
        if out:
            cmd += ["-o", out]
            self._output_path = out

        cmd.append(inp)

        # Clear previous results
        self._tab_raw.clear()
        for tbl in (self._tab_length, self._tab_charset, self._tab_simple, self._tab_advanced):
            tbl.setRowCount(0)
        self._tab_complexity.clear()

        # Accumulate all stdout, then parse on finish
        self._stdout_buf: list[str] = []
        self._runner.output_line.disconnect()
        self._runner.output_line.connect(self._collect_output)
        self._runner.finished.disconnect()
        self._runner.finished.connect(self._on_finished)

        self._output_log.append(f"$ {' '.join(cmd)}\n")
        self._runner.run(cmd)

    def _collect_output(self, text: str) -> None:
        """Buffer stdout lines and show in raw tab."""
        self._tab_raw.append(text)
        self._stdout_buf.append(text)

    def _on_finished(self, exit_code: int) -> None:
        """Parse accumulated output into tabs."""
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress.setVisible(False)
        # Reconnect default signals
        try:
            self._runner.output_line.disconnect(self._collect_output)
            self._runner.finished.disconnect(self._on_finished)
        except TypeError:
            pass
        self._runner.output_line.connect(self._on_process_output)
        self._runner.finished.connect(self._on_process_finished)

        full = "\n".join(self._stdout_buf)
        self._parse_output(full)
        self._output_log.append(f"\nStatsGen finished (exit code {exit_code}).")

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------
    _STAT_RE = re.compile(
        r"\[\+\]\s+(.+?):\s+(\d+)%\s+\((\d+)\)"
    )

    def _parse_output(self, text: str) -> None:
        """Parse statsgen stdout sections into the tab tables."""
        section = ""
        complexity_lines: list[str] = []

        for line in text.splitlines():
            stripped = line.strip()
            # Detect section headers
            if "[*] Length:" in stripped:
                section = "length"
                continue
            if "[*] Character-set:" in stripped:
                section = "charset"
                continue
            if "[*] Simple Masks:" in stripped:
                section = "simple"
                continue
            if "[*] Advanced Masks:" in stripped:
                section = "advanced"
                continue
            if "[*] Password complexity:" in stripped:
                section = "complexity"
                continue
            # Skip unrelated headers
            if stripped.startswith("[*]") and ":" in stripped:
                section = ""
                continue

            m = self._STAT_RE.search(stripped)
            if m:
                label, pct, count = m.group(1).strip(), int(m.group(2)), int(m.group(3))
                if section == "length":
                    self._add_stat_row(self._tab_length, label, pct, count)
                elif section == "charset":
                    self._add_stat_row(self._tab_charset, label, pct, count)
                elif section == "simple":
                    self._add_stat_row(self._tab_simple, label, pct, count)
                elif section == "advanced":
                    self._add_stat_row(self._tab_advanced, label, pct, count)
            elif section == "complexity":
                complexity_lines.append(stripped)

        if complexity_lines:
            self._tab_complexity.setPlainText("\n".join(complexity_lines))

    def _add_stat_row(self, table: QTableWidget, label: str, pct: int, count: int) -> None:
        """Append a row with a visual bar in the % column."""
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(label))

        # Use a QProgressBar as % visualization
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(pct)
        bar.setFormat(f"{pct}%")
        bar.setTextVisible(True)
        table.setCellWidget(row, 1, bar)

        count_item = QTableWidgetItem(f"{count:,}")
        count_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        table.setItem(row, 2, count_item)

    # ------------------------------------------------------------------
    # Locate script + python
    # ------------------------------------------------------------------
    def _find_statsgen(self) -> Optional[Path]:
        if self._base_dir:
            p = Path(self._base_dir) / "crackers_toolkit" / "pack_ports" / "statsgen.py"
            if p.is_file():
                return p
        p = Path(__file__).resolve().parent.parent / "pack_ports" / "statsgen.py"
        if p.is_file():
            return p
        return None

    def _find_python(self) -> str:
        if self._settings:
            p = self._settings.get("python_path")
            if p:
                return p
        return sys.executable

    def get_output_path(self) -> Optional[str]:
        return self._output_path

    def receive_from(self, path: str) -> None:
        self._input_file.setText(path)
