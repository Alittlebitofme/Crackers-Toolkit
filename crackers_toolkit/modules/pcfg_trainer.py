"""Module 9: PCFG Trainer GUI.

Train a probabilistic grammar model from a plaintext password list.
Wraps ``Scripts_to_use/pcfg_cracker-master/trainer.py``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
)
from PyQt6.QtCore import Qt

from .base_module import BaseModule


class PCFGTrainerModule(BaseModule):
    MODULE_NAME = "PCFG Trainer"
    MODULE_DESCRIPTION = (
        "Train a probabilistic grammar model from a plaintext password list. "
        "The model learns password structures and their probabilities — "
        "used by PCFG Guesser and PRINCE-LING."
    )
    MODULE_CATEGORY = "Wordlist Analysis"

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._pcfg_dir = self._find_pcfg_dir()
        self._rules_dir = self._pcfg_dir / "Rules" if self._pcfg_dir else None
        super().__init__(parent)

    # ------------------------------------------------------------------
    # Build sections
    # ------------------------------------------------------------------
    def build_input_section(self, layout: QVBoxLayout) -> None:
        self._training_file = self.create_file_browser(
            layout, "Training password list:",
            "Plaintext file of real passwords, one per line.",
            file_filter="Text Files (*.txt);;All Files (*)",
        )
        # File metadata display
        self._file_meta = QLabel("")
        self._file_meta.setWordWrap(True)
        self._file_meta.setStyleSheet("color: #a6adc8; font-size: 11px;")
        layout.addWidget(self._file_meta)

        from PyQt6.QtWidgets import QTextEdit
        self._file_preview = QTextEdit()
        self._file_preview.setReadOnly(True)
        self._file_preview.setMaximumHeight(100)
        self._file_preview.setPlaceholderText("First 10 lines will appear here…")
        self._file_preview.setVisible(False)
        layout.addWidget(self._file_preview)

        self._training_file.textChanged.connect(self._on_file_selected)

    def build_params_section(self, layout: QVBoxLayout) -> None:
        self._ruleset_name = self.create_line_edit(
            layout, "Ruleset name (-r):", "Default",
            "Name for the trained ruleset. Stored under Rules/<name>/.",
        )
        self._encoding = self.create_combo(
            layout, "Encoding (-e):",
            ["Auto", "utf-8", "latin-1", "cp1252", "iso-8859-1", "ascii"],
            "Character encoding of the training file.",
        )

        # Coverage slider 0.0 → 1.0
        cov_row = QHBoxLayout()
        cov_lbl = QLabel("Coverage (-c):")
        cov_row.addWidget(cov_lbl)
        cov_row.addWidget(self._info_icon(
            "Balance between structured guesses (1.0) and Markov brute-force (0.0). Default 0.6."
        ))
        self._coverage_slider = QSlider(Qt.Orientation.Horizontal)
        self._coverage_slider.setRange(0, 100)
        self._coverage_slider.setValue(60)
        self._coverage_val = QLabel("0.60")
        self._coverage_slider.valueChanged.connect(
            lambda v: self._coverage_val.setText(f"{v / 100:.2f}")
        )
        cov_row.addWidget(cov_lbl)
        cov_row.addWidget(self._coverage_slider, stretch=1)
        cov_row.addWidget(self._coverage_val)
        layout.addLayout(cov_row)

        self._ngram_depth = self.create_spinbox(
            layout, "N-gram depth (-n):", 2, 5, 4,
            "Markov chain order. Higher = more patterns but needs more data.",
        )
        self._alphabet_size = self.create_spinbox(
            layout, "Alphabet size (-a):", 10, 1000, 100,
            "Number of most-frequent characters for Markov model.",
        )

    def build_advanced_section(self, layout: QVBoxLayout) -> None:
        self._save_sensitive = self.create_checkbox(
            layout, "Save sensitive data", False,
            "Save emails and URLs found in training data. Contains PII.",
        )
        self._multiword_file = self.create_file_browser(
            layout, "Multiword file (-m):", "Optional file for compound-word detection.",
            file_filter="Text Files (*.txt);;All Files (*)",
        )
        self._prefix_count = self.create_checkbox(
            layout, "Prefix count mode", False,
            "Input has 'uniq -c' style count prefixes.",
        )

    def build_output_section(self, layout: QVBoxLayout) -> None:
        # Ruleset browser
        self._ruleset_list_label = QLabel("Existing rulesets:")
        layout.addWidget(self._ruleset_list_label)

        from PyQt6.QtWidgets import QListWidget, QTreeWidget, QTreeWidgetItem, QHeaderView
        self._ruleset_tree = QTreeWidget()
        self._ruleset_tree.setHeaderLabels(["Ruleset", "Created", "Files", "Size"])
        self._ruleset_tree.setMaximumHeight(160)
        self._ruleset_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._refresh_rulesets()
        layout.addWidget(self._ruleset_tree)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_rulesets)
        btn_row.addWidget(refresh_btn)

        copy_btn = QPushButton("Copy")
        copy_btn.setToolTip("Duplicate the selected ruleset under a new name.")
        copy_btn.clicked.connect(self._copy_ruleset)
        btn_row.addWidget(copy_btn)

        edit_btn = QPushButton("Edit →")
        edit_btn.setToolTip("Open the selected ruleset in PCFG Rule Editor for filtering.")
        edit_btn.clicked.connect(self._edit_ruleset)
        btn_row.addWidget(edit_btn)

        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._delete_ruleset)
        btn_row.addWidget(del_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # File metadata
    # ------------------------------------------------------------------
    def _on_file_selected(self, path: str) -> None:
        """Display line count, encoding, and first 10 sample lines."""
        p = Path(path)
        if not p.is_file():
            self._file_meta.setText("")
            self._file_preview.setVisible(False)
            return

        # Detect encoding
        encoding = "utf-8"
        try:
            import chardet
            with open(p, "rb") as f:
                raw = f.read(8192)
            det = chardet.detect(raw)
            if det and det.get("encoding"):
                encoding = det["encoding"]
        except ImportError:
            pass

        # Read first 10 lines and estimate total from file size
        sample: list[str] = []
        bytes_read = 0
        try:
            with open(p, "r", encoding=encoding, errors="replace") as f:
                for line in f:
                    sample.append(line.rstrip("\n\r"))
                    bytes_read += len(line)
                    if len(sample) >= 10:
                        break
        except OSError:
            self._file_meta.setText("Error reading file.")
            self._file_preview.setVisible(False)
            return

        size = p.stat().st_size
        size_str = f"{size:,} bytes" if size < 1_048_576 else f"{size / 1_048_576:.1f} MB"
        avg = bytes_read / len(sample) if sample else 1
        est_lines = int(size / avg)
        self._file_meta.setText(
            f"Lines: ~{est_lines:,}  |  Size: {size_str}  |  Encoding: {encoding}"
        )
        self._file_preview.setPlainText("\n".join(sample))
        self._file_preview.setVisible(True)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        errors: list[str] = []
        inp = self._training_file.text().strip()
        if not inp:
            errors.append("Select a training password file.")
        elif not Path(inp).is_file():
            errors.append(f"Training file not found: {inp}")
        name = self._ruleset_name.text().strip()
        if not name:
            errors.append("Enter a ruleset name.")
        return errors

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def run_tool(self) -> None:
        trainer = self._find_trainer()
        if not trainer:
            self._output_log.append(
                "Error: trainer.py not found.\n"
                "Expected in: Scripts_to_use/pcfg_cracker-master/\n"
                "Configure paths in Settings (⚙ in the toolbar)."
            )
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        inp = self._training_file.text().strip()
        if not inp:
            self._output_log.append("Error: no training file selected.")
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        python = self._find_python()
        cmd = [python, str(trainer)]

        ruleset = self._ruleset_name.text().strip() or "Default"
        cmd += ["-r", ruleset]

        cmd += ["-t", inp]

        enc = self._encoding.currentText()
        if enc == "Auto":
            enc = "utf-8"
        cmd += ["-e", enc]

        cov = self._coverage_slider.value() / 100.0
        cmd += ["-c", f"{cov:.2f}"]

        cmd += ["-n", str(self._ngram_depth.value())]
        cmd += ["-a", str(self._alphabet_size.value())]

        if self._save_sensitive.isChecked():
            cmd.append("--save-sensitive")

        mw = self._multiword_file.text().strip()
        if mw:
            cmd += ["-m", mw]

        if self._prefix_count.isChecked():
            cmd.append("--prefix-count")

        self._output_log.append(f"$ {' '.join(cmd)}\n")
        self._runner.run(cmd, cwd=self._pcfg_dir)

    def _on_process_finished(self, exit_code: int) -> None:
        super()._on_process_finished(exit_code)
        if exit_code == 0:
            self._refresh_rulesets()

    # ------------------------------------------------------------------
    # Ruleset browser helpers
    # ------------------------------------------------------------------
    def _refresh_rulesets(self) -> None:
        self._ruleset_tree.clear()
        if self._rules_dir and self._rules_dir.is_dir():
            from PyQt6.QtWidgets import QTreeWidgetItem
            import datetime
            for d in sorted(self._rules_dir.iterdir()):
                if d.is_dir():
                    # Gather metadata
                    mtime = datetime.datetime.fromtimestamp(d.stat().st_mtime)
                    created_str = mtime.strftime("%Y-%m-%d %H:%M")
                    file_count = sum(1 for f in d.rglob("*") if f.is_file())
                    total_bytes = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
                    if total_bytes < 1024:
                        size_str = f"{total_bytes} B"
                    elif total_bytes < 1024 * 1024:
                        size_str = f"{total_bytes / 1024:.1f} KB"
                    else:
                        size_str = f"{total_bytes / (1024 * 1024):.1f} MB"
                    item = QTreeWidgetItem([d.name, created_str, str(file_count), size_str])
                    self._ruleset_tree.addTopLevelItem(item)

    def _copy_ruleset(self) -> None:
        item = self._ruleset_tree.currentItem()
        if not item or not self._rules_dir:
            return
        name = item.text(0)
        from PyQt6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self, "Copy Ruleset", "New ruleset name:", text=f"{name}_copy"
        )
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()
        src = self._rules_dir / name
        dst = self._rules_dir / new_name
        if dst.exists():
            QMessageBox.warning(self, "Error", f"Ruleset '{new_name}' already exists.")
            return
        import shutil
        shutil.copytree(src, dst)
        self._refresh_rulesets()
        self._output_log.append(f"Copied ruleset '{name}' → '{new_name}'")

    def _edit_ruleset(self) -> None:
        item = self._ruleset_tree.currentItem()
        if not item or not self._rules_dir:
            return
        name = item.text(0)
        ruleset_path = str(self._rules_dir / name)
        from app.data_bus import DataBus
        DataBus.instance().send("PCFG Rule Editor", {"ruleset_path": ruleset_path})

    def _delete_ruleset(self) -> None:
        item = self._ruleset_tree.currentItem()
        if not item:
            return
        name = item.text(0)
        reply = QMessageBox.question(
            self, "Delete Ruleset",
            f"Delete ruleset '{name}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes and self._rules_dir:
            import shutil
            target = self._rules_dir / name
            if target.is_dir():
                shutil.rmtree(target)
                self._refresh_rulesets()
                self._output_log.append(f"Deleted ruleset: {name}")

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    def _find_pcfg_dir(self) -> Optional[Path]:
        if self._base_dir:
            d = Path(self._base_dir) / "Scripts_to_use" / "pcfg_cracker-master"
            # Handle both flat and nested (double) extraction layouts
            nested = d / "pcfg_cracker-master"
            if nested.is_dir():
                return nested
            if d.is_dir():
                return d
        return None

    def _find_trainer(self) -> Optional[Path]:
        if self._pcfg_dir:
            p = self._pcfg_dir / "trainer.py"
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
            name = self._ruleset_name.text().strip() or "Default"
            return str(self._rules_dir / name)
        return None

    def receive_from(self, path: str) -> None:
        self._training_file.setText(path)
