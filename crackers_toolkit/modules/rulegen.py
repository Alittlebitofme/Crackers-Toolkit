"""Module 16: RuleGen GUI (PACK).

Reverse-engineer hashcat rules from cracked passwords.
Wraps the ported pack_ports/rulegen.py.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from .base_module import BaseModule


class RuleGenModule(BaseModule):
    MODULE_NAME = "RuleGen (PACK)"
    MODULE_DESCRIPTION = (
        "Reverse-engineer hashcat rules from cracked passwords. "
        "Discovers base words and transformation rules. "
        "Great for finding real-world mangling patterns."
    )
    MODULE_CATEGORY = "Rule Tools"

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        super().__init__(parent)

    def build_input_section(self, layout: QVBoxLayout) -> None:
        self._input_file = self.create_file_browser(
            layout, "Cracked password file:",
            "File of cracked passwords, one per line.",
            file_filter="Text Files (*.txt);;All Files (*)",
        )
        layout.addWidget(QLabel("— or paste a single password —"))
        self._single_password = self.create_line_edit(
            layout, "Single password (--password):", "",
            "Analyze a single password instead of a file.",
        )

    def build_params_section(self, layout: QVBoxLayout) -> None:
        self._basename = self.create_line_edit(
            layout, "Output basename (-b):", "analysis",
            "Prefix for output files: <name>.word, <name>.rule, <name>-sorted.*",
        )
        self._custom_wordlist = self.create_file_browser(
            layout, "Custom wordlist (-w):",
            "Use a custom dictionary file alongside the system dictionary.",
            file_filter="Text Files (*.txt *.dict);;All Files (*)",
        )

        # Dictionary provider
        layout.addWidget(QLabel("Dictionary provider:"))
        _dp_row = QHBoxLayout()
        self._provider_combo = QComboBox()
        self._provider_combo.addItems(["aspell", "myspell", "aspell,myspell", "hunspell"])
        self._provider_combo.setCurrentText("aspell,myspell")
        _dp_row.addWidget(self._provider_combo)
        _dp_row.addWidget(self._info_icon("Enchant spell-check provider ordering."))
        _dp_row.addStretch()
        layout.addLayout(_dp_row)

        # Language
        layout.addWidget(QLabel("Language:"))
        _ln_row = QHBoxLayout()
        self._language_combo = QComboBox()
        self._language_combo.addItems(["en", "de", "fr", "es", "it", "pt", "nl", "ru", "pl", "sv"])
        self._language_combo.setCurrentText("en")
        self._language_combo.setEditable(True)
        _ln_row.addWidget(self._language_combo)
        _ln_row.addWidget(self._info_icon("Enchant dictionary language code."))
        _ln_row.addStretch()
        layout.addLayout(_ln_row)

    def build_advanced_section(self, layout: QVBoxLayout) -> None:
        self._more_words = self.create_checkbox(
            layout, "More words (--morewords)", False,
            "Consider suboptimal source word candidates (slower).",
        )
        self._simple_words = self.create_checkbox(
            layout, "Simple words (--simplewords)", False,
            "Prefer simpler, shorter source words.",
        )
        self._more_rules = self.create_checkbox(
            layout, "More rules (--morerules)", False,
            "Generate more possible rule variants (slower).",
        )
        self._simple_rules = self.create_checkbox(
            layout, "Simple rules (--simplerules)", False,
            "Prefer simpler insert/delete/replace rules only.",
        )
        self._brute_rules = self.create_checkbox(
            layout, "Brute rules (--bruterules)", False,
            "Bruteforce reversal and rotation rules (slow).",
        )
        self._hashcat_validate = self.create_checkbox(
            layout, "Validate with hashcat (--hashcat)", False,
            "Validate discovered rules using hashcat --stdout. Requires hashcat binary path in Settings.",
        )
        self._threads = self.create_spinbox(
            layout, "Threads:", 1, 64, 4,
            "Parallel processing threads.",
        )

    def build_output_section(self, layout: QVBoxLayout) -> None:
        # Results table: Words & Rules with frequency
        layout.addWidget(QLabel("Discovered words \u0026 rules:"))
        self._results_table = QTableWidget(0, 3)
        self._results_table.setHorizontalHeaderLabels(["Type", "Value", "Frequency"])
        self._results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._results_table.setMaximumHeight(200)
        self._results_table.setSortingEnabled(True)
        self._results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._results_table)

        btn_row = QHBoxLayout()
        export_words_btn = QPushButton("Export Words…")
        export_words_btn.setToolTip("Save discovered source words as a wordlist file.")
        export_words_btn.clicked.connect(self._export_words)
        btn_row.addWidget(export_words_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        row = QHBoxLayout()
        self.send_to_menu(row, ["Rule Builder", "Hashcat Command Builder"])
        row.addStretch()
        layout.addLayout(row)

    def validate(self) -> list[str]:
        errors: list[str] = []
        fpath = self._input_file.text().strip()
        single = self._single_password.text().strip()
        if not fpath and not single:
            errors.append("Provide a password file or single password.")
        if fpath and not Path(fpath).is_file():
            errors.append(f"Password file not found: {fpath}")
        return errors

    def run_tool(self) -> None:
        script = self._find_rulegen()
        if not script:
            self._output_log.append(
                "Error: rulegen.py port not found.\n"
                "Expected in: crackers_toolkit/pack_ports/\n"
                "Verify the application installation is complete."
            )
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        python = self._find_python()
        cmd = [python, str(script)]

        basename = self._basename.text().strip() or "analysis"
        cmd += ["-b", basename]

        wl = self._custom_wordlist.text().strip()
        if wl:
            cmd += ["-w", wl]

        cmd += ["--providers", self._provider_combo.currentText()]
        cmd += ["--language", self._language_combo.currentText()]

        if self._more_words.isChecked():
            cmd.append("--morewords")
        if self._simple_words.isChecked():
            cmd.append("--simplewords")
        if self._more_rules.isChecked():
            cmd.append("--morerules")
        if self._simple_rules.isChecked():
            cmd.append("--simplerules")
        if self._brute_rules.isChecked():
            cmd.append("--bruterules")

        if self._hashcat_validate.isChecked():
            hashcat_path = None
            if self._settings:
                hashcat_path = self._settings.get("hashcat_path")
            if hashcat_path:
                cmd += ["--hashcat", hashcat_path]
            else:
                cmd.append("--hashcat")

        cmd += ["--threads", str(self._threads.value())]

        single = self._single_password.text().strip()
        inp = self._input_file.text().strip()

        if single:
            cmd.append("--password")
            cmd.append(single)
        elif inp:
            cmd.append(inp)
        else:
            self._output_log.append("Error: no password file or single password provided.")
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        self._output_path = f"{basename}.rule"
        self._output_log.append(f"$ {' '.join(cmd)}\n")
        self._results_table.setRowCount(0)
        self._runner.run(cmd)

    def _on_process_finished(self, exit_code: int) -> None:
        super()._on_process_finished(exit_code)
        if exit_code == 0:
            self._populate_results_table()

    def _populate_results_table(self) -> None:
        """Parse .word and .rule output files to populate the results table."""
        basename = self._basename.text().strip() or "analysis"
        self._results_table.setSortingEnabled(False)
        # Read words file
        word_file = Path(basename + ".word")
        if word_file.is_file():
            freq: dict[str, int] = {}
            for line in word_file.read_text(encoding="utf-8", errors="replace").splitlines():
                w = line.strip()
                if w:
                    freq[w] = freq.get(w, 0) + 1
            for word, count in sorted(freq.items(), key=lambda x: -x[1]):
                r = self._results_table.rowCount()
                self._results_table.insertRow(r)
                self._results_table.setItem(r, 0, QTableWidgetItem("word"))
                self._results_table.setItem(r, 1, QTableWidgetItem(word))
                freq_item = QTableWidgetItem()
                freq_item.setData(0x0002, count)
                self._results_table.setItem(r, 2, freq_item)
        # Read rules file
        rule_file = Path(basename + ".rule")
        if rule_file.is_file():
            freq_r: dict[str, int] = {}
            for line in rule_file.read_text(encoding="utf-8", errors="replace").splitlines():
                rl = line.strip()
                if rl:
                    freq_r[rl] = freq_r.get(rl, 0) + 1
            for rule, count in sorted(freq_r.items(), key=lambda x: -x[1]):
                r = self._results_table.rowCount()
                self._results_table.insertRow(r)
                self._results_table.setItem(r, 0, QTableWidgetItem("rule"))
                self._results_table.setItem(r, 1, QTableWidgetItem(rule))
                freq_item = QTableWidgetItem()
                freq_item.setData(0x0002, count)
                self._results_table.setItem(r, 2, freq_item)
        self._results_table.setSortingEnabled(True)

    def _export_words(self) -> None:
        """Export discovered words from the results table as a wordlist."""
        words = []
        for r in range(self._results_table.rowCount()):
            type_item = self._results_table.item(r, 0)
            val_item = self._results_table.item(r, 1)
            if type_item and type_item.text() == "word" and val_item:
                words.append(val_item.text())
        if not words:
            self._output_log.append("No words to export. Run RuleGen first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Words", str(self._default_output_dir()), "Wordlists (*.txt *.dict);;All Files (*)"
        )
        if path:
            Path(path).write_text("\n".join(words) + "\n", encoding="utf-8")
            self._output_log.append(f"Exported {len(words)} words to {path}")

    def _find_rulegen(self) -> Optional[Path]:
        p = Path(__file__).resolve().parent.parent / "pack_ports" / "rulegen.py"
        if p.is_file():
            return p
        if self._base_dir:
            p = Path(self._base_dir) / "crackers_toolkit" / "pack_ports" / "rulegen.py"
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
