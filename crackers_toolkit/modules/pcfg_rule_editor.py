"""Module 17: PCFG Rule Editor GUI.

Edit a trained PCFG ruleset to match a specific password policy.
Wraps ``Scripts_to_use/pcfg_cracker-master/edit_rules.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from PyQt6.QtGui import QColor

from .base_module import BaseModule, ProcessRunner


class PCFGRuleEditorModule(BaseModule):
    MODULE_NAME = "PCFG Rule Editor"
    MODULE_DESCRIPTION = (
        "Edit a trained PCFG ruleset to match a specific password policy. "
        "Filter base structures by length, required character types, and "
        "custom regex patterns."
    )
    MODULE_CATEGORY = "Rule Tools"

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._pcfg_dir = self._find_pcfg_dir()
        self._rules_dir = self._pcfg_dir / "Rules" if self._pcfg_dir else None
        self._preview_runner = ProcessRunner()
        self._preview_runner.output_line.connect(self._on_preview_line)
        self._preview_runner.finished.connect(self._on_preview_finished)
        self._preview_runner.error.connect(self._on_process_error)
        super().__init__(parent)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._refresh_rulesets()

    # ------------------------------------------------------------------
    # Build sections
    # ------------------------------------------------------------------
    def build_input_section(self, layout: QVBoxLayout) -> None:
        # Workflow banner — explains PCFG Trainer dependency
        banner = QGroupBox("\u26a0 Requires Trained PCFG Ruleset")
        bl = QVBoxLayout(banner)
        info = QLabel(
            "This tool edits a trained PCFG ruleset to match a specific password "
            "policy. If no rulesets appear below, use the PCFG Trainer to create "
            "one from a plaintext password list."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #f9e2af; font-size: 11px;")
        bl.addWidget(info)
        trainer_btn = QPushButton("Open PCFG Trainer \u2192")
        trainer_btn.setToolTip("Navigate to PCFG Trainer to create or manage rulesets.")
        trainer_btn.clicked.connect(self._open_trainer)
        bl.addWidget(trainer_btn)
        banner.setStyleSheet(
            "QGroupBox { border-color: #f9e2af; } "
            "QGroupBox::title { color: #f9e2af; }"
        )
        layout.addWidget(banner)

        # Ruleset selector with refresh
        rs_row = QHBoxLayout()
        rs_row.addWidget(QLabel("Ruleset (-r):"))
        rs_row.addWidget(self._info_icon("The PCFG ruleset to edit."))
        self._ruleset = QComboBox()
        self._ruleset.addItems(self._list_rulesets())
        rs_row.addWidget(self._ruleset, stretch=1)
        refresh_btn = QPushButton("\u21bb")
        refresh_btn.setFixedWidth(30)
        refresh_btn.setToolTip("Reload available rulesets after training a new one.")
        refresh_btn.clicked.connect(self._refresh_rulesets)
        rs_row.addWidget(refresh_btn)
        layout.addLayout(rs_row)

        self._create_copy = self.create_checkbox(
            layout, "Create copy (--copy)", False,
            "Create a copy of the ruleset before editing, leaving the original intact.",
        )

    def build_params_section(self, layout: QVBoxLayout) -> None:
        self._min_len = self.create_spinbox(
            layout, "Min length:", 0, 128, 0,
            "Minimum total password length for kept base structures.",
        )
        self._max_len = self.create_spinbox(
            layout, "Max length:", 0, 128, 0,
            "Maximum total password length. 0 = no limit.",
        )

        # Terminal type checkboxes
        layout.addWidget(QLabel("Terminal types to keep:"))
        self._terminals: dict[str, object] = {}
        terminal_types = [
            ("A", "Alpha (letters)"),
            ("D", "Digits"),
            ("Y", "Year"),
            ("O", "Special characters"),
            ("K", "Keyboard walk"),
            ("X", "Context-specific"),
        ]
        for code, desc in terminal_types:
            self._terminals[code] = self.create_checkbox(
                layout, f"{code} — {desc}", True,
                f"Keep terminal type {code} ({desc}). Uncheck to remove.",
            )

        self._regex_filter = self.create_line_edit(
            layout, "Regex filter:", "",
            "Comma-separated regexes. ALL must match for a structure to be kept.",
        )

    def build_output_section(self, layout: QVBoxLayout) -> None:
        btn_row = QHBoxLayout()
        preview_btn = QPushButton("Preview")
        preview_btn.setToolTip("Show structures that would be kept vs. removed.")
        preview_btn.clicked.connect(self._on_preview)
        btn_row.addWidget(preview_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Kept vs. Removed comparison table
        self._preview_table = QTableWidget(0, 3)
        self._preview_table.setHorizontalHeaderLabels(["Structure", "Status", "Probability"])
        self._preview_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._preview_table.setMaximumHeight(250)
        self._preview_table.setVisible(False)
        layout.addWidget(self._preview_table)

        self._preview_summary = QLabel("")
        layout.addWidget(self._preview_summary)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        import re as _re
        errors: list[str] = []
        if not self._ruleset.currentText().strip():
            errors.append("Select a PCFG ruleset to edit.")
        regex = self._regex_filter.text().strip()
        if regex:
            for pat in regex.split(","):
                pat = pat.strip()
                if pat:
                    try:
                        _re.compile(pat)
                    except _re.error as e:
                        errors.append(f"Invalid regex pattern '{pat}': {e}")
        return errors

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def run_tool(self) -> None:
        script = self._find_edit_rules()
        if not script:
            self._output_log.append(
                "Error: edit_rules.py not found.\n"
                "Expected in: Scripts_to_use/pcfg_cracker-master/\n"
                "Configure paths in Settings (⚙ in the toolbar)."
            )
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        cmd = self._build_cmd(script, preview=False)
        self._output_log.append(f"$ {' '.join(cmd)}\n")
        self._runner.run(cmd, cwd=self._pcfg_dir)

    def _on_preview(self) -> None:
        script = self._find_edit_rules()
        if not script:
            self._output_log.append(
                "Error: edit_rules.py not found.\n"
                "Expected in: Scripts_to_use/pcfg_cracker-master/\n"
                "Configure paths in Settings (⚙ in the toolbar)."
            )
            return
        cmd = self._build_cmd(script, preview=True)
        self._output_log.clear()
        self._output_log.append(f"[Preview] $ {' '.join(cmd)}\n")
        self._preview_table.setRowCount(0)
        self._preview_table.setVisible(True)
        self._preview_kept = 0
        self._preview_removed = 0
        self._preview_runner.run(cmd, cwd=self._pcfg_dir)

    def _build_cmd(self, script: Path, preview: bool = False) -> list[str]:
        python = self._find_python()
        cmd = [python, str(script)]

        ruleset = self._ruleset.currentText()
        cmd += ["-r", ruleset]

        if self._create_copy.isChecked():
            cmd.append("--copy")

        min_l = self._min_len.value()
        if min_l > 0:
            cmd += ["--min-length", str(min_l)]

        max_l = self._max_len.value()
        if max_l > 0:
            cmd += ["--max-length", str(max_l)]

        # Terminal types: only pass the flag if some are unchecked
        kept = [code for code, cb in self._terminals.items() if cb.isChecked()]
        if len(kept) < len(self._terminals):
            cmd += ["--terminal-types", "".join(kept)]

        regex = self._regex_filter.text().strip()
        if regex:
            cmd += ["--regex", regex]

        if preview:
            cmd.append("--preview")

        return cmd

    def _on_preview_line(self, line: str) -> None:
        self._output_log.append(line)
        # Parse preview output: expect lines like "KEPT: L4D2 (0.035)" or "REMOVED: ..."
        text = line.strip()
        if not text:
            return

        is_kept = text.upper().startswith("KEPT")
        is_removed = text.upper().startswith("REMOV")
        if not is_kept and not is_removed:
            # Fallback: treat as kept if it contains structure-like patterns
            return

        status = "Kept" if is_kept else "Removed"
        color = QColor("#a6e3a1") if is_kept else QColor("#f38ba8")  # green / red
        # Extract structure name and probability
        parts = text.split(":", 1)
        detail = parts[1].strip() if len(parts) > 1 else text
        prob = ""
        if "(" in detail and ")" in detail:
            idx = detail.rfind("(")
            prob = detail[idx + 1 : detail.rfind(")")]
            detail = detail[:idx].strip()

        row = self._preview_table.rowCount()
        self._preview_table.insertRow(row)
        for col, val in enumerate([detail, status, prob]):
            item = QTableWidgetItem(val)
            item.setForeground(color)
            self._preview_table.setItem(row, col, item)

        if is_kept:
            self._preview_kept += 1
        else:
            self._preview_removed += 1

    def _on_preview_finished(self, exit_code: int) -> None:
        if exit_code == 0:
            self._output_log.append("\n✓ Preview complete.")
        else:
            self._output_log.append(f"\n✗ Preview exited with code {exit_code}.")
        self._preview_summary.setText(
            f"Kept: {self._preview_kept}  |  Removed: {self._preview_removed}"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _list_rulesets(self) -> list[str]:
        if self._rules_dir and self._rules_dir.is_dir():
            return [d.name for d in self._rules_dir.iterdir() if d.is_dir()] or ["Default"]
        return ["Default"]

    def _refresh_rulesets(self) -> None:
        current = self._ruleset.currentText()
        self._ruleset.clear()
        self._ruleset.addItems(self._list_rulesets())
        idx = self._ruleset.findText(current)
        if idx >= 0:
            self._ruleset.setCurrentIndex(idx)

    def _open_trainer(self) -> None:
        """Navigate to the PCFG Trainer module."""
        from crackers_toolkit.app.data_bus import data_bus
        data_bus.navigate_to_tool.emit("PCFG Trainer")

    def _find_pcfg_dir(self) -> Optional[Path]:
        if self._base_dir:
            d = Path(self._base_dir) / "Scripts_to_use" / "pcfg_cracker-master"
            nested = d / "pcfg_cracker-master"
            if nested.is_dir():
                return nested
            if d.is_dir():
                return d
        return None

    def _find_edit_rules(self) -> Optional[Path]:
        if self._pcfg_dir:
            p = self._pcfg_dir / "edit_rules.py"
            if p.is_file():
                return p
        return None

    def _find_python(self) -> str:
        if self._settings:
            p = self._settings.get("python_path")
            if p:
                return p
        return "python"

    def get_output_path(self) -> Optional[str]:
        if self._rules_dir:
            return str(self._rules_dir / self._ruleset.currentText())
        return None

    def receive_from(self, path: str) -> None:
        pass
