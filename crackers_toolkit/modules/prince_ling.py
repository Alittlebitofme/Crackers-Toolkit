"""Module 4: PRINCE-LING — wraps prince_ling.py to generate wordlists
optimized for PRINCE attacks using a trained PCFG model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from .base_module import BaseModule


class PrinceLingModule(BaseModule):
    MODULE_NAME = "PRINCE-LING"
    MODULE_DESCRIPTION = (
        "Generate wordlists optimized for PRINCE attacks using a trained "
        "PCFG model. Outputs individual words (not full passwords) in "
        "probability order — the best input for PRINCE processor."
    )
    MODULE_CATEGORY = "Wordlist Generation"

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        self._pcfg_dir = self._find_pcfg_dir()
        self._rules_dir = self._pcfg_dir / "Rules" if self._pcfg_dir else None
        super().__init__(parent)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._refresh_rulesets()

    def build_input_section(self, layout: QVBoxLayout) -> None:
        # Workflow banner — explains PCFG Trainer dependency
        banner = QGroupBox("\u26a0 Requires Trained PCFG Ruleset")
        bl = QVBoxLayout(banner)
        info = QLabel(
            "This tool generates wordlists optimised for PRINCE attacks using a "
            "trained PCFG grammar. If no rulesets appear below, use the PCFG "
            "Trainer to create one from a plaintext password list."
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
        rs_row.addWidget(self._info_icon("PCFG ruleset to use for word generation."))
        self._ruleset = QComboBox()
        self._ruleset.addItems(self._list_rulesets())
        rs_row.addWidget(self._ruleset, stretch=1)
        refresh_btn = QPushButton("\u21bb")
        refresh_btn.setFixedWidth(30)
        refresh_btn.setToolTip("Reload available rulesets after training a new one.")
        refresh_btn.clicked.connect(self._refresh_rulesets)
        rs_row.addWidget(refresh_btn)
        layout.addLayout(rs_row)

    def build_params_section(self, layout: QVBoxLayout) -> None:
        self._max_size = self.create_spinbox(
            layout, "Max words (-s):", 0, 999_999_999, 0,
            "Maximum number of words to generate. 0 = all.",
        )
        self._all_lower = self.create_checkbox(
            layout, "All lowercase", False,
            "Generate only lowercase words.",
        )

    def build_output_section(self, layout: QVBoxLayout) -> None:
        self._output_file = self.create_file_browser(
            layout, "Output file (-o):", "Where to save the generated wordlist.",
            save=True, file_filter="Text Files (*.txt);;All Files (*)",
        )
        self._output_file.setText(str(self._default_output_dir() / "prince_ling_words.txt"))
        row = QHBoxLayout()
        self.send_to_menu(row, ["PRINCE Processor", "Hashcat Command Builder"])
        row.addStretch()
        layout.addLayout(row)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self._ruleset.currentText().strip():
            errors.append("Select a PCFG ruleset.")
        return errors

    def run_tool(self) -> None:
        script = self._find_script()
        if not script:
            self._output_log.append(
                "Error: prince_ling.py not found.\n"
                "Expected in: Scripts_to_use/pcfg_cracker-master/lib_guesser/\n"
                "Configure paths in Settings (⚙ in the toolbar)."
            )
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        python = self._find_python()
        cmd = [python, str(script)]

        ruleset = self._ruleset.currentText() if hasattr(self._ruleset, 'currentText') else "Default"
        cmd += ["-r", ruleset]

        max_s = self._max_size.value()
        if max_s > 0:
            cmd += ["-s", str(max_s)]

        if self._all_lower.isChecked():
            cmd.append("--all-lower")

        out = self._output_file.text().strip()
        if out:
            cmd += ["-o", out]
            self._output_path = out

        self._output_log.append(f"$ {' '.join(cmd)}\n")
        self._runner.run(cmd, cwd=self._pcfg_dir)

    def _list_rulesets(self) -> list[str]:
        if self._rules_dir and self._rules_dir.is_dir():
            return [d.name for d in self._rules_dir.iterdir() if d.is_dir()] or ["Default"]
        return ["Default"]

    def _open_trainer(self) -> None:
        """Navigate to the PCFG Trainer module."""
        from crackers_toolkit.app.data_bus import data_bus
        data_bus.navigate_to_tool.emit("PCFG Trainer")

    def _refresh_rulesets(self) -> None:
        """Reload available rulesets from disk."""
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

    def _find_script(self) -> Optional[Path]:
        if self._pcfg_dir:
            p = self._pcfg_dir / "prince_ling.py"
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
        return self._output_path

    def receive_from(self, path: str) -> None:
        pass
