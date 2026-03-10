"""Module 14: PolicyGen GUI (PACK).

Generate hashcat masks that comply with (or violate) a specific password
policy.  Wraps the ported pack_ports/policygen.py.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .base_module import BaseModule


class PolicyGenModule(BaseModule):
    MODULE_NAME = "PolicyGen (PACK)"
    MODULE_DESCRIPTION = (
        "Generate hashcat masks that comply with (or violate) a specific "
        "password policy. Useful for targeted attacks against known policies."
    )
    MODULE_CATEGORY = "Mask Tools"

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        super().__init__(parent)

    def build_input_section(self, layout: QVBoxLayout) -> None:
        layout.addWidget(QLabel(
            "Define a password policy below. PolicyGen generates all "
            "hashcat masks matching (or violating) that policy."
        ))

    def build_params_section(self, layout: QVBoxLayout) -> None:
        self._min_length = self.create_spinbox(
            layout, "Min length:", 1, 64, 8,
            "Minimum password length required by the policy.",
        )
        self._max_length = self.create_spinbox(
            layout, "Max length:", 1, 64, 8,
            "Maximum password length.",
        )

        # Digit constraints
        self._min_digit = self.create_spinbox(layout, "Min digits:", 0, 64, 0)
        self._max_digit = self.create_spinbox(layout, "Max digits:", 0, 64, 0,
            "0 = unlimited")

        # Lowercase
        self._min_lower = self.create_spinbox(layout, "Min lowercase:", 0, 64, 0)
        self._max_lower = self.create_spinbox(layout, "Max lowercase:", 0, 64, 0)

        # Uppercase
        self._min_upper = self.create_spinbox(layout, "Min uppercase:", 0, 64, 0)
        self._max_upper = self.create_spinbox(layout, "Max uppercase:", 0, 64, 0)

        # Special
        self._min_special = self.create_spinbox(layout, "Min special:", 0, 64, 0)
        self._max_special = self.create_spinbox(layout, "Max special:", 0, 64, 0)

        self._noncompliant = self.create_checkbox(
            layout, "Non-compliant mode", False,
            "Generate masks that VIOLATE the policy instead of complying.",
        )
        self._pps = self.create_spinbox(
            layout, "Passwords/sec:", 1, 2_000_000_000, 1_000_000_000,
            "Hash rate for time estimation.",
        )
        self._showmasks = self.create_checkbox(
            layout, "Show masks in output", False,
            "Display individual masks in the log.",
        )

    def build_output_section(self, layout: QVBoxLayout) -> None:
        self._output_file = self.create_file_browser(
            layout, "Export as .hcmask:",
            "Save generated masks as a hashcat mask file.",
            save=True, file_filter="Hashcat Masks (*.hcmask);;All Files (*)",
        )
        self._output_file.setText(str(self._default_output_dir() / "policy_masks.hcmask"))

        # Summary labels
        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet("color: #a6adc8; font-size: 11px;")
        layout.addWidget(self._summary_label)

        # ── Mask table (displayed when showmasks is on) ──
        self._mask_table = QTableWidget(0, 3)
        self._mask_table.setHorizontalHeaderLabels(["Mask", "Keyspace", "Est. Time"])
        self._mask_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._mask_table.setMaximumHeight(200)
        self._mask_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._mask_table.setVisible(False)
        layout.addWidget(self._mask_table)

        row = QHBoxLayout()
        self.send_to_menu(row, ["Mask Builder", "Hashcat Command Builder"])
        row.addStretch()
        layout.addLayout(row)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self._min_length.value() > self._max_length.value():
            errors.append("Min length must be ≤ max length.")
        return errors

    def run_tool(self) -> None:
        script = self._find_policygen()
        if not script:
            self._output_log.append(
                "Error: policygen.py port not found.\n"
                "Expected in: crackers_toolkit/pack_ports/\n"
                "Verify the application installation is complete."
            )
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        python = self._find_python()
        cmd = [python, str(script)]

        cmd += ["--minlength", str(self._min_length.value())]
        cmd += ["--maxlength", str(self._max_length.value())]

        for flag, spin in [
            ("--mindigit", self._min_digit),
            ("--maxdigit", self._max_digit),
            ("--minlower", self._min_lower),
            ("--maxlower", self._max_lower),
            ("--minupper", self._min_upper),
            ("--maxupper", self._max_upper),
            ("--minspecial", self._min_special),
            ("--maxspecial", self._max_special),
        ]:
            v = spin.value()
            if v > 0:
                cmd += [flag, str(v)]

        if self._noncompliant.isChecked():
            cmd.append("--noncompliant")

        cmd += ["--pps", str(self._pps.value())]

        if self._showmasks.isChecked():
            cmd.append("--showmasks")

        out = self._output_file.text().strip()
        if out:
            cmd += ["-o", out]
            self._output_path = out

        self._output_log.append(f"$ {' '.join(cmd)}\n")
        self._pg_mask_count = 0
        self._pg_total_ks = 0
        self._summary_label.setText("")
        self._mask_table.setRowCount(0)
        self._mask_table.setVisible(self._showmasks.isChecked())
        self._runner.run(cmd)

    def _on_process_output(self, line: str) -> None:
        super()._on_process_output(line)
        import re
        # Parse summary lines like: [*] Generated 256 masks / total keyspace: 123456789
        m = re.search(r"Generated\s+(\d+)\s+masks", line)
        if m:
            self._pg_mask_count = int(m.group(1))
        m2 = re.search(r"keyspace:\s*(\d+)", line)
        if m2:
            self._pg_total_ks = int(m2.group(1))
        # Update summary
        if self._pg_mask_count > 0:
            pps = max(self._pps.value(), 1)
            est_secs = self._pg_total_ks / pps if self._pg_total_ks else 0
            if est_secs < 3600:
                time_str = f"{est_secs:.0f}s"
            elif est_secs < 86400:
                time_str = f"{est_secs / 3600:.1f}h"
            else:
                time_str = f"{est_secs / 86400:.1f}d"
            self._summary_label.setText(
                f"{self._pg_mask_count} masks • keyspace: {self._pg_total_ks:,} • est. time: {time_str}"
            )

        # Parse per-mask lines: [+] ?u?l?l?l?l?d?d?d [keyspace: 2088270645]
        m3 = re.search(r"\[\+\]\s+(\S+)\s+\[keyspace:\s*(\d+)\]", line)
        if m3 and self._showmasks.isChecked():
            mask_str = m3.group(1)
            ks = int(m3.group(2))
            pps = max(self._pps.value(), 1)
            est = ks / pps
            if est < 60:
                t_str = f"{est:.0f}s"
            elif est < 3600:
                t_str = f"{est / 60:.1f}m"
            elif est < 86400:
                t_str = f"{est / 3600:.1f}h"
            else:
                t_str = f"{est / 86400:.1f}d"
            row = self._mask_table.rowCount()
            self._mask_table.insertRow(row)
            self._mask_table.setItem(row, 0, QTableWidgetItem(mask_str))
            ks_item = QTableWidgetItem()
            ks_item.setData(0x0002, ks)
            self._mask_table.setItem(row, 1, ks_item)
            self._mask_table.setItem(row, 2, QTableWidgetItem(t_str))

    def _find_policygen(self) -> Optional[Path]:
        p = Path(__file__).resolve().parent.parent / "pack_ports" / "policygen.py"
        if p.is_file():
            return p
        if self._base_dir:
            p = Path(self._base_dir) / "crackers_toolkit" / "pack_ports" / "policygen.py"
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
        pass
