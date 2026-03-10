"""Module 10: Password Scorer GUI.

Score passwords against a trained PCFG model. Wraps
``Scripts_to_use/pcfg_cracker-master/password_scorer.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from .base_module import BaseModule, ProcessRunner


class PasswordScorerModule(BaseModule):
    MODULE_NAME = "Password Scorer"
    MODULE_DESCRIPTION = (
        "Score passwords against a trained PCFG model to see how probable "
        "each one is. Classifies entries as passwords, emails, websites, "
        "or other."
    )
    MODULE_CATEGORY = "Wordlist Analysis"

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._pcfg_dir = self._find_pcfg_dir()
        self._rules_dir = self._pcfg_dir / "Rules" if self._pcfg_dir else None
        self._result_rows: list[list[str]] = []
        super().__init__(parent)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._refresh_rulesets()

    # ------------------------------------------------------------------
    # Build sections
    # ------------------------------------------------------------------
    def build_input_section(self, layout: QVBoxLayout) -> None:
        self._input_file = self.create_file_browser(
            layout, "Password file:",
            "File of passwords to score, one per line.",
            file_filter="Text Files (*.txt);;All Files (*)",
        )
        layout.addWidget(QLabel("— or paste passwords below —"))
        self._paste_box = QTextEdit()
        self._paste_box.setPlaceholderText("One password per line…")
        self._paste_box.setMaximumHeight(100)
        layout.addWidget(self._paste_box)

    def build_params_section(self, layout: QVBoxLayout) -> None:
        rs_row = QHBoxLayout()
        rs_row.addWidget(QLabel("Ruleset (-r):"))
        rs_row.addWidget(self._info_icon("PCFG ruleset to score against."))
        self._ruleset = QComboBox()
        self._ruleset.addItems(self._list_rulesets())
        rs_row.addWidget(self._ruleset, stretch=1)
        refresh_btn = QPushButton("\u21bb")
        refresh_btn.setFixedWidth(30)
        refresh_btn.setToolTip("Reload available rulesets after training a new one.")
        refresh_btn.clicked.connect(self._refresh_rulesets)
        rs_row.addWidget(refresh_btn)
        layout.addLayout(rs_row)

        self._prob_cutoff = self.create_line_edit(
            layout, "Probability cutoff (-l):", "0",
            "Minimum probability to classify as 'password'. 0 = classify everything.",
        )
        self._max_omen = self.create_spinbox(
            layout, "Max OMEN level (-m):", 0, 20, 9,
            "Maximum Markov/OMEN level. Higher = slower but more complete.",
        )

    def build_output_section(self, layout: QVBoxLayout) -> None:
        # Classification filter checkboxes
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Show:"))
        self._class_filters: dict[str, QCheckBox] = {}
        for cls in ("Password", "Email", "Website", "Other"):
            cb = QCheckBox(cls)
            cb.setChecked(True)
            cb.stateChanged.connect(self._apply_filters)
            self._class_filters[cls.lower()] = cb
            filter_row.addWidget(cb)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self._result_table = QTableWidget(0, 4)
        self._result_table.setHorizontalHeaderLabels(
            ["Password", "Classification", "PCFG Probability", "OMEN Level"]
        )
        self._result_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._result_table.setSortingEnabled(True)
        self._result_table.setMaximumHeight(250)
        layout.addWidget(self._result_table)

        btn_row = QHBoxLayout()
        from PyQt6.QtWidgets import QPushButton
        export_btn = QPushButton("Export Results…")
        export_btn.clicked.connect(self._export_results)
        btn_row.addWidget(export_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        errors: list[str] = []
        fpath = self._input_file.text().strip()
        pasted = self._paste_box.toPlainText().strip()
        if not fpath and not pasted:
            errors.append("Provide a password file or paste passwords.")
        if fpath and not Path(fpath).is_file():
            errors.append(f"Password file not found: {fpath}")
        if not self._ruleset.currentText().strip():
            errors.append("Select a PCFG ruleset.")
        return errors

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def run_tool(self) -> None:
        scorer = self._find_scorer()
        if not scorer:
            self._output_log.append(
                "Error: password_scorer.py not found.\n"
                "Expected in: Scripts_to_use/pcfg_cracker-master/\n"
                "Configure paths in Settings (⚙ in the toolbar)."
            )
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        # If paste box has content, write to temp file
        paste = self._paste_box.toPlainText().strip()
        inp = self._input_file.text().strip()
        if paste and not inp:
            import tempfile
            tmp = Path(tempfile.mktemp(suffix=".txt"))
            tmp.write_text(paste, encoding="utf-8")
            inp = str(tmp)
        if not inp:
            self._output_log.append("Error: no passwords provided.")
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        python = self._find_python()
        cmd = [python, str(scorer)]

        ruleset = self._ruleset.currentText()
        cmd += ["-r", ruleset]

        cutoff = self._prob_cutoff.text().strip()
        if cutoff and cutoff != "0":
            cmd += ["-l", cutoff]

        cmd += ["-m", str(self._max_omen.value())]
        cmd.append(inp)

        self._result_rows.clear()
        self._result_table.setRowCount(0)
        self._output_log.append(f"$ {' '.join(cmd)}\n")
        self._runner.run(cmd, cwd=self._pcfg_dir)

    def _on_process_output(self, line: str) -> None:
        super()._on_process_output(line)
        # Try to parse tab-separated output into table
        parts = line.split("\t")
        if len(parts) >= 2:
            self._result_table.setSortingEnabled(False)
            row_idx = self._result_table.rowCount()
            self._result_table.insertRow(row_idx)
            for col, val in enumerate(parts[:4]):
                item = QTableWidgetItem(val)
                # Color-code probability column (col 2)
                if col == 2:
                    try:
                        prob = float(val)
                        if prob >= 1e-6:
                            item.setBackground(QColor("#40f38ba8"))  # red-ish — weak
                        elif prob >= 1e-10:
                            item.setBackground(QColor("#40fab387"))  # peach — medium
                        else:
                            item.setBackground(QColor("#40a6e3a1"))  # green — strong
                    except ValueError:
                        pass
                self._result_table.setItem(row_idx, col, item)
            self._result_rows.append(parts[:4])
            self._result_table.setSortingEnabled(True)
            self._apply_filters()

    def _apply_filters(self) -> None:
        """Show/hide rows based on classification filter checkboxes."""
        visible_classes = {
            cls for cls, cb in self._class_filters.items() if cb.isChecked()
        }
        for row in range(self._result_table.rowCount()):
            item = self._result_table.item(row, 1)
            classification = item.text().strip().lower() if item else ""
            visible = any(v in classification for v in visible_classes) if classification else ("other" in visible_classes)
            self._result_table.setRowHidden(row, not visible)

    def _export_results(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", str(self._default_output_dir()), "CSV Files (*.csv);;Text Files (*.txt)",
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Password\tClassification\tPCFG Probability\tOMEN Level\n")
                for row in self._result_rows:
                    f.write("\t".join(row) + "\n")
            self._output_log.append(f"Exported to {path}")

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

    def _find_pcfg_dir(self) -> Optional[Path]:
        if self._base_dir:
            d = Path(self._base_dir) / "Scripts_to_use" / "pcfg_cracker-master"
            nested = d / "pcfg_cracker-master"
            if nested.is_dir():
                return nested
            if d.is_dir():
                return d
        return None

    def _find_scorer(self) -> Optional[Path]:
        if self._pcfg_dir:
            p = self._pcfg_dir / "password_scorer.py"
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
        return None

    def receive_from(self, path: str) -> None:
        self._input_file.setText(path)
