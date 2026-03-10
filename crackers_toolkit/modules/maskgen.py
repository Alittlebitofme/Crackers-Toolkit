"""Module 13: MaskGen GUI (PACK).

Generate an optimized set of hashcat masks from password statistics.
Wraps the ported pack_ports/maskgen.py.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .base_module import BaseModule


class _CoverageGraphWidget(QWidget):
    """Lightweight line chart showing cumulative coverage % vs mask count."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[float] = []  # cumulative % values per mask
        self.setMinimumHeight(80)
        self.setMaximumHeight(120)

    def add_point(self, cumulative_pct: float) -> None:
        self._data.append(cumulative_pct)
        self.update()

    def clear_data(self) -> None:
        self._data.clear()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        margin = 4
        plot = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)

        # Background
        painter.fillRect(self.rect(), QColor("#1e1e2e"))

        # Grid lines at 25% / 50% / 75%
        painter.setPen(QPen(QColor("#45475a"), 1, Qt.PenStyle.DotLine))
        for pct in (25, 50, 75):
            y = plot.bottom() - (pct / 100) * plot.height()
            painter.drawLine(int(plot.left()), int(y), int(plot.right()), int(y))

        # Line
        painter.setPen(QPen(QColor("#89b4fa"), 2))
        n = len(self._data)
        for i in range(1, n):
            x0 = plot.left() + ((i - 1) / max(n - 1, 1)) * plot.width()
            y0 = plot.bottom() - (self._data[i - 1] / 100) * plot.height()
            x1 = plot.left() + (i / max(n - 1, 1)) * plot.width()
            y1 = plot.bottom() - (self._data[i] / 100) * plot.height()
            painter.drawLine(int(x0), int(y0), int(x1), int(y1))

        # Label last value
        if self._data:
            painter.setPen(QColor("#cdd6f4"))
            painter.drawText(
                int(plot.right() - 60), int(plot.top()),
                60, 16, Qt.AlignmentFlag.AlignRight,
                f"{self._data[-1]:.1f}%",
            )
        painter.end()


class MaskGenModule(BaseModule):
    MODULE_NAME = "MaskGen (PACK)"
    MODULE_DESCRIPTION = (
        "Generate an optimized set of hashcat masks from password statistics. "
        "Ranks masks by efficiency and builds time-budgeted mask files."
    )
    MODULE_CATEGORY = "Mask Tools"

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        super().__init__(parent)

    def build_input_section(self, layout: QVBoxLayout) -> None:
        # Workflow banner — explains StatsGen dependency
        banner = QGroupBox("\u26a0 Requires StatsGen Output")
        bl = QVBoxLayout(banner)
        info = QLabel(
            "MaskGen needs a CSV statistics file produced by StatsGen (PACK). "
            "Run StatsGen on a plaintext password list first, then load the "
            "resulting CSV here or send it directly from StatsGen."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #f9e2af; font-size: 11px;")
        bl.addWidget(info)
        statsgen_btn = QPushButton("Open StatsGen \u2192")
        statsgen_btn.setToolTip("Navigate to StatsGen (PACK) to generate password statistics.")
        statsgen_btn.clicked.connect(self._open_statsgen)
        bl.addWidget(statsgen_btn)
        banner.setStyleSheet(
            "QGroupBox { border-color: #f9e2af; } "
            "QGroupBox::title { color: #f9e2af; }"
        )
        layout.addWidget(banner)

        self._input_csv = self.create_file_browser(
            layout, "StatsGen CSV file:",
            "CSV output from StatsGen, or receive directly from StatsGen.",
            file_filter="CSV Files (*.csv);;All Files (*)",
        )

    def build_params_section(self, layout: QVBoxLayout) -> None:
        self._target_time = self.create_spinbox(
            layout, "Target time (-t) seconds:", 0, 999_999_999, 0,
            "Time budget in seconds. 0 = no limit. 86400 = 24 hours.",
        )
        self._pps = self.create_spinbox(
            layout, "Passwords/sec (--pps):", 1, 2_000_000_000, 1_000_000_000,
            "Estimated hash rate. Check hashcat benchmark.",
        )

        # Sort by
        layout.addWidget(QLabel("Sort by:"))
        self._sort_group = QButtonGroup(self)
        sort_row = QHBoxLayout()
        for label, key in [("optindex (recommended)", "optindex"), ("occurrence", "occurrence"), ("complexity", "complexity")]:
            rb = QRadioButton(label)
            rb.setProperty("sort_key", key)
            self._sort_group.addButton(rb)
            sort_row.addWidget(rb)
            if key == "optindex":
                rb.setChecked(True)
        layout.addLayout(sort_row)

        self._showmasks = self.create_checkbox(
            layout, "Show mask details", False,
            "Display per-mask statistics in the output.",
        )

    def build_advanced_section(self, layout: QVBoxLayout) -> None:
        self._min_length = self.create_spinbox(layout, "Min length:", 0, 99, 0)
        self._max_length = self.create_spinbox(layout, "Max length:", 0, 99, 0)
        self._min_occurrence = self.create_spinbox(layout, "Min occurrence:", 0, 999_999_999, 0)
        self._max_occurrence = self.create_spinbox(layout, "Max occurrence:", 0, 999_999_999, 0)

    def build_output_section(self, layout: QVBoxLayout) -> None:
        self._output_file = self.create_file_browser(
            layout, "Export as .hcmask:",
            "Save generated masks as a hashcat mask file.",
            save=True, file_filter="Hashcat Masks (*.hcmask);;All Files (*)",
        )
        self._output_file.setText(str(self._default_output_dir() / "generated.hcmask"))

        # ── Cumulative coverage display ──
        cov_row = QHBoxLayout()
        cov_row.addWidget(QLabel("Coverage:"))
        self._coverage_bar = QProgressBar()
        self._coverage_bar.setRange(0, 100)
        self._coverage_bar.setValue(0)
        self._coverage_bar.setFormat("%v%")
        self._coverage_bar.setTextVisible(True)
        cov_row.addWidget(self._coverage_bar, stretch=1)
        self._coverage_label = QLabel("0 masks → 0%")
        cov_row.addWidget(self._coverage_label)
        layout.addLayout(cov_row)

        # ── Cumulative coverage graph ──
        self._coverage_graph = _CoverageGraphWidget()
        layout.addWidget(self._coverage_graph)

        # ── Mask results table ──
        self._mask_table = QTableWidget(0, 5)
        self._mask_table.setHorizontalHeaderLabels(["Mask", "Occurrence", "Keyspace", "Est. Time", "Cumulative %"])
        self._mask_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._mask_table.setMaximumHeight(200)
        self._mask_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._mask_table)

        # Add to Mask Builder button
        add_mb_btn = QPushButton("Add Selected to Mask Builder")
        add_mb_btn.setToolTip("Send the selected mask rows to the Mask Builder via the data bus.")
        add_mb_btn.clicked.connect(self._send_selected_to_mask_builder)
        layout.addWidget(add_mb_btn)

        row = QHBoxLayout()
        self.send_to_menu(row, ["Mask Builder", "Hashcat Command Builder"])
        row.addStretch()
        layout.addLayout(row)

    def validate(self) -> list[str]:
        errors: list[str] = []
        inp = self._input_csv.text().strip()
        if not inp:
            errors.append("Select a StatsGen CSV file.")
        elif not Path(inp).is_file():
            errors.append(f"CSV file not found: {inp}")
        return errors

    def run_tool(self) -> None:
        script = self._find_maskgen()
        if not script:
            self._output_log.append(
                "Error: maskgen.py port not found.\n"
                "Expected in: crackers_toolkit/pack_ports/\n"
                "Verify the application installation is complete."
            )
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        inp = self._input_csv.text().strip()
        if not inp:
            self._output_log.append("Error: no StatsGen CSV file selected.")
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        python = self._find_python()
        cmd = [python, str(script)]

        tt = self._target_time.value()
        if tt > 0:
            cmd += ["-t", str(tt)]

        cmd += ["--pps", str(self._pps.value())]

        checked = self._sort_group.checkedButton()
        if checked:
            key = checked.property("sort_key")
            cmd.append(f"--{key}")

        if self._showmasks.isChecked():
            cmd.append("--showmasks")

        ml = self._min_length.value()
        if ml > 0:
            cmd += ["--minlength", str(ml)]
        xl = self._max_length.value()
        if xl > 0:
            cmd += ["--maxlength", str(xl)]
        mo = self._min_occurrence.value()
        if mo > 0:
            cmd += ["--minoccurrence", str(mo)]
        xo = self._max_occurrence.value()
        if xo > 0:
            cmd += ["--maxoccurrence", str(xo)]

        out = self._output_file.text().strip()
        if out:
            cmd += ["-o", out]
            self._output_path = out

        cmd.append(inp)

        self._output_log.append(f"$ {' '.join(cmd)}\n")
        self._mask_count = 0
        self._last_coverage = 0.0
        self._coverage_bar.setValue(0)
        self._coverage_label.setText("0 masks → 0%")
        self._mask_table.setRowCount(0)
        self._coverage_graph.clear_data()
        self._runner.run(cmd)

    def _on_process_output(self, line: str) -> None:
        """Parse maskgen output for coverage information and populate table."""
        super()._on_process_output(line)
        import re
        # Look for coverage lines like: [*] ... 12 most efficient masks (99.50% ...)
        m = re.search(r"(\d+)\s+most efficient masks?\s+\((\d+(?:\.\d+)?)%", line)
        if m:
            self._mask_count = int(m.group(1))
            self._last_coverage = float(m.group(2))
            self._coverage_bar.setValue(min(int(self._last_coverage), 100))
            self._coverage_label.setText(
                f"{self._mask_count} masks → {self._last_coverage:.1f}%"
            )
        # Also look for per-mask lines with cumulative %
        m2 = re.search(r"\[\+\].*?(\d+(?:\.\d+)?)%\s+cumulative", line)
        if m2:
            cum = float(m2.group(1))
            self._coverage_bar.setValue(min(int(cum), 100))
            self._coverage_label.setText(f"cumulative: {cum:.1f}%")

        # Parse per-mask detail lines: [+] ?l?l?l?l?l?l [occ: 1234] [keyspace: 308915776] [42.50% cumulative]
        m3 = re.search(
            r"\[\+\]\s+(\S+)\s+\[occ:\s*(\d+)\]\s+\[keyspace:\s*(\d+)\]\s+\[(\d+(?:\.\d+)?)%\s+cumulative\]",
            line,
        )
        if m3:
            row = self._mask_table.rowCount()
            self._mask_table.insertRow(row)
            self._mask_table.setItem(row, 0, QTableWidgetItem(m3.group(1)))
            occ_item = QTableWidgetItem()
            occ_item.setData(0x0002, int(m3.group(2)))  # DisplayRole
            self._mask_table.setItem(row, 1, occ_item)
            ks_item = QTableWidgetItem()
            keyspace = int(m3.group(3))
            ks_item.setData(0x0002, keyspace)
            self._mask_table.setItem(row, 2, ks_item)
            # Est. Time = keyspace / PPS
            pps = max(self._pps.value(), 1)
            est_secs = keyspace / pps
            if est_secs < 60:
                t_str = f"{est_secs:.0f}s"
            elif est_secs < 3600:
                t_str = f"{est_secs / 60:.1f}m"
            elif est_secs < 86400:
                t_str = f"{est_secs / 3600:.1f}h"
            else:
                t_str = f"{est_secs / 86400:.1f}d"
            self._mask_table.setItem(row, 3, QTableWidgetItem(t_str))
            self._mask_table.setItem(row, 4, QTableWidgetItem(f"{m3.group(4)}%"))
            self._coverage_graph.add_point(float(m3.group(4)))

    def _find_maskgen(self) -> Optional[Path]:
        p = Path(__file__).resolve().parent.parent / "pack_ports" / "maskgen.py"
        if p.is_file():
            return p
        if self._base_dir:
            p = Path(self._base_dir) / "crackers_toolkit" / "pack_ports" / "maskgen.py"
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
        self._input_csv.setText(path)

    def _open_statsgen(self) -> None:
        """Navigate to the StatsGen module."""
        from crackers_toolkit.app.data_bus import data_bus
        data_bus.navigate_to_tool.emit("StatsGen (PACK)")

    def _send_selected_to_mask_builder(self) -> None:
        """Write selected masks to a temp .hcmask file and send to Mask Builder."""
        rows = self._mask_table.selectionModel().selectedRows()
        if not rows:
            self._output_log.append("Select one or more mask rows first.")
            return
        masks = []
        for idx in rows:
            item = self._mask_table.item(idx.row(), 0)
            if item:
                masks.append(item.text())
        if not masks:
            return
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".hcmask"))
        tmp.write_text("\n".join(masks) + "\n", encoding="utf-8")
        self._output_path = str(tmp)
        self._output_log.append(f"Prepared {len(masks)} mask(s) for Mask Builder.")
