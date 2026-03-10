"""Module 2: PCFG Guesser — wraps pcfg_guesser.py to generate password
guesses in probability order using a trained PCFG grammar model.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QRadioButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QPushButton,
)

from .base_module import BaseModule, ProcessRunner


class PCFGGuesserModule(BaseModule):
    MODULE_NAME = "PCFG Guesser"
    MODULE_DESCRIPTION = (
        "Generate password guesses in probability order using a trained "
        "PCFG grammar model. The most likely passwords come first. "
        "Supports session save/restore for long runs."
    )
    MODULE_CATEGORY = "Wordlist Generation"

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        self._pcfg_dir = self._find_pcfg_dir()
        self._rules_dir = self._pcfg_dir / "Rules" if self._pcfg_dir else None
        self._head_runner: ProcessRunner | None = None
        super().__init__(parent)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._refresh_rulesets()

    def build_input_section(self, layout: QVBoxLayout) -> None:
        # Workflow banner — explains PCFG Trainer dependency
        banner = QGroupBox("\u26a0 Requires Trained PCFG Ruleset")
        bl = QVBoxLayout(banner)
        info = QLabel(
            "This tool uses a trained PCFG grammar to generate password guesses "
            "in probability order. If no rulesets appear below, use the PCFG "
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
        rs_row.addWidget(self._info_icon("The trained PCFG ruleset to use."))
        self._ruleset = QComboBox()
        self._ruleset.addItems(self._list_rulesets())
        rs_row.addWidget(self._ruleset, stretch=1)
        refresh_btn = QPushButton("\u21bb")
        refresh_btn.setFixedWidth(30)
        refresh_btn.setToolTip("Reload available rulesets after training a new one.")
        refresh_btn.clicked.connect(self._refresh_rulesets)
        rs_row.addWidget(refresh_btn)
        layout.addLayout(rs_row)

        grp = QGroupBox("Generation Mode (-m)")
        ml = QVBoxLayout(grp)
        self._mode_group = QButtonGroup(self)
        self._mode_prob = QRadioButton("true_prob_order — strict probability order (best for cracking)")
        self._mode_random = QRadioButton("random_walk — random sampling")
        self._mode_honey = QRadioButton("honeywords — generate decoy passwords")
        self._mode_prob.setChecked(True)
        self._mode_group.addButton(self._mode_prob, 0)
        self._mode_group.addButton(self._mode_random, 1)
        self._mode_group.addButton(self._mode_honey, 2)
        for btn in [self._mode_prob, self._mode_random, self._mode_honey]:
            ml.addWidget(btn)
        layout.addWidget(grp)

    def build_params_section(self, layout: QVBoxLayout) -> None:
        self._limit = self.create_spinbox(
            layout, "Limit (-n):", 0, 999_999_999, 0,
            "Stop after N guesses. 0 = unlimited. Use a small number (100-1000) for previewing.",
        )
        self._skip_brute = self.create_checkbox(
            layout, "Skip brute-force (OMEN/Markov) guesses", False,
            "Disable OMEN/Markov brute-force guesses. Only structured PCFG guesses are produced.",
        )
        self._all_lower = self.create_checkbox(
            layout, "All lowercase", False,
            "Only generate lowercase candidates (no case variations).",
        )
        self._session = self.create_line_edit(
            layout, "Session name (-s):", "default_run",
            "Name for saving/restoring this session. Allows pausing and resuming.",
        )

        # Head preview
        preview_grp = QGroupBox("Preview (top 200 guesses)")
        pl = QVBoxLayout(preview_grp)
        head_btn = QPushButton("Preview Head (top 200)")
        head_btn.setToolTip("Run the guesser with --limit 200 to see the highest-probability candidates.")
        head_btn.clicked.connect(self._preview_head)
        pl.addWidget(head_btn)

        self._head_stats = QLabel("")
        self._head_stats.setStyleSheet("color: #a6adc8; font-size: 11px;")
        pl.addWidget(self._head_stats)

        from PyQt6.QtWidgets import QTextEdit
        self._head_preview = QTextEdit()
        self._head_preview.setReadOnly(True)
        self._head_preview.setPlaceholderText("Highest-probability guesses will appear here…")
        pl.addWidget(self._head_preview)
        layout.addWidget(preview_grp)

    def build_advanced_section(self, layout: QVBoxLayout) -> None:
        # ── Session management list ──
        layout.addWidget(QLabel("Saved sessions:"))
        self._session_tree = QTreeWidget()
        self._session_tree.setHeaderLabels(["Session", "Guesses", "Coverage", "Last Updated"])
        self._session_tree.setMaximumHeight(120)
        self._session_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._refresh_sessions()
        layout.addWidget(self._session_tree)

        s_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_sessions)
        resume_btn = QPushButton("Resume Selected")
        resume_btn.setToolTip("Load the selected session name into the Session field.")
        resume_btn.clicked.connect(self._resume_session)
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setToolTip("Delete the selected session save file.")
        delete_btn.clicked.connect(self._delete_session)
        s_row.addWidget(refresh_btn)
        s_row.addWidget(resume_btn)
        s_row.addWidget(delete_btn)
        s_row.addStretch()
        layout.addLayout(s_row)

    def build_output_section(self, layout: QVBoxLayout) -> None:
        self._output_file = self.create_file_browser(
            layout, "Output file:", "Save guesses to file.",
            save=True, file_filter="Text Files (*.txt);;All Files (*)",
        )
        self._output_file.setText(str(self._default_output_dir() / "pcfg_guesses.txt"))
        self._pipe_hashcat = self.create_checkbox(
            layout, "Pipe to Hashcat (stdin)", False,
            "When sending to Attack Launcher, set up as a piped stdin command "
            "instead of writing to a file first.",
        )
        row = QHBoxLayout()
        self.send_to_menu(row, ["demeuk \u2014 Wordlist Cleaner", "Hashcat Command Builder"])
        row.addStretch()
        layout.addLayout(row)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self._ruleset.currentText().strip():
            errors.append("Select a PCFG ruleset.")
        return errors

    def run_tool(self) -> None:
        cmd = self._build_cmd()
        if not cmd:
            return
        out = self._output_file.text().strip()
        if out:
            cmd += ["-o", out]
            self._output_path = out
        self._output_log.append(f"$ {' '.join(cmd)}\n")
        self._runner.run(cmd)

    def _build_cmd(self, limit_override=None, skip_override=None) -> list[str] | None:
        guesser = self._find_guesser()
        if not guesser:
            self._output_log.append(
                "Error: pcfg_guesser.py not found.\n"
                "Expected in: Scripts_to_use/pcfg_cracker-master/\n"
                "Configure paths in Settings (⚙ in the toolbar)."
            )
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return None

        python = self._find_python()
        cmd = [python, str(guesser)]

        ruleset = self._ruleset.currentText() if hasattr(self._ruleset, 'currentText') else "Default"
        cmd += ["-r", ruleset]

        mode_id = self._mode_group.checkedId()
        modes = {0: "true_prob_order", 1: "random_walk", 2: "honeywords"}
        cmd += ["-m", modes.get(mode_id, "true_prob_order")]

        limit = limit_override if limit_override is not None else self._limit.value()
        if limit > 0:
            cmd += ["-n", str(limit)]

        if skip_override is not None and skip_override > 0:
            cmd += ["--skip", str(skip_override)]

        if self._skip_brute.isChecked():
            cmd.append("--skip-brute")
        if self._all_lower.isChecked():
            cmd.append("--all-lower")

        session = self._session.text().strip() if hasattr(self._session, 'text') else ""
        if session:
            cmd += ["-s", session]

        return cmd

    @staticmethod
    def _is_guess_line(line: str) -> bool:
        """Return True if *line* is an actual password guess, not banner/status noise."""
        if not line or line.isspace():
            return False
        # ASCII-art banner characters
        if line.lstrip().startswith(('/', '\\', '|', '_', 'Version:', 'Loading',
                                     'Starting', 'Press ', 'Limit ', 'Exception',
                                     'Traceback', 'File ', 'Thread')):
            return False
        return True

    def _preview_head(self) -> None:
        self._head_preview.clear()
        self._head_stats.setText("Running…")
        self._head_lines: list[str] = []
        cmd = self._build_cmd(limit_override=200)
        if not cmd:
            return
        if self._head_runner:
            self._head_runner.cancel()
            self._head_runner.deleteLater()
        self._head_runner = ProcessRunner()
        def _on_head_line(line: str) -> None:
            if self._is_guess_line(line):
                self._head_preview.append(line)
                self._head_lines.append(line)
        self._head_runner.output_line.connect(_on_head_line)
        self._head_runner.finished.connect(lambda _: self._head_stats.setText(
            self._compute_stats(self._head_lines)
        ))
        self._head_runner.run(cmd)

    def _on_process_finished(self, exit_code: int) -> None:
        super()._on_process_finished(exit_code)
        if exit_code == 0 and self._output_path:
            try:
                p = Path(self._output_path)
                size = p.stat().st_size
                # Estimate line count from first 64 lines
                sample_bytes = 0
                sample_count = 0
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        sample_bytes += len(line)
                        sample_count += 1
                        if sample_count >= 64:
                            break
                if sample_count > 0 and sample_bytes < size:
                    avg = sample_bytes / sample_count
                    count = int(size / avg)
                    count_str = f"~{count:,}"
                else:
                    count_str = f"{sample_count:,}"
                for unit in ("B", "KB", "MB", "GB"):
                    if size < 1024:
                        sz = f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
                        break
                    size /= 1024
                else:
                    sz = f"{size:.1f} TB"
                self._output_log.append(f"Output: {count_str} lines, {sz}")
            except OSError:
                pass

    @staticmethod
    def _compute_stats(lines: list[str]) -> str:
        """Compute avg length + character composition from preview lines."""
        if not lines:
            return "No data"
        import re
        from collections import Counter
        lengths = [len(l) for l in lines]
        avg = sum(lengths) / len(lengths)
        has_lower = sum(1 for l in lines if re.search(r"[a-z]", l))
        has_upper = sum(1 for l in lines if re.search(r"[A-Z]", l))
        has_digit = sum(1 for l in lines if re.search(r"\d", l))
        has_special = sum(1 for l in lines if re.search(r"[^a-zA-Z0-9]", l))
        n = len(lines)
        return (
            f"Avg length: {avg:.1f}  |  "
            f"lower: {has_lower*100//n}%  upper: {has_upper*100//n}%  "
            f"digit: {has_digit*100//n}%  special: {has_special*100//n}%"
        )

    # ── Session management ──
    def _refresh_sessions(self) -> None:
        self._session_tree.clear()
        if not self._pcfg_dir:
            return
        import configparser
        # Look for .sav files in pcfg_dir (where pcfg_guesser.py saves them)
        for p in sorted(self._pcfg_dir.glob("*.sav")):
            name = p.stem
            guesses = "—"
            coverage = "—"
            last_updated = "—"
            try:
                cfg = configparser.ConfigParser()
                cfg.read(str(p), encoding="utf-8")
                if cfg.has_section("session_info"):
                    ng = cfg.get("session_info", "num_guesses", fallback="")
                    if ng:
                        guesses = f"{int(ng):,}"
                    pc = cfg.get("session_info", "probability_coverage", fallback="")
                    if pc:
                        coverage = f"{float(pc):.2%}"
                    lu = cfg.get("session_info", "last_updated", fallback="")
                    if lu:
                        last_updated = lu[:19].replace("T", " ")
            except Exception:
                pass
            item = QTreeWidgetItem([name, guesses, coverage, last_updated])
            item.setData(0, Qt.ItemDataRole.UserRole, str(p))
            self._session_tree.addTopLevelItem(item)
        # Also check Sessions/ directory for folder-based sessions
        sessions_dir = self._pcfg_dir / "Sessions"
        if sessions_dir.is_dir():
            for d in sorted(sessions_dir.iterdir()):
                if d.is_dir():
                    item = QTreeWidgetItem([d.name, "—", "—", "—"])
                    item.setData(0, Qt.ItemDataRole.UserRole, str(d))
                    self._session_tree.addTopLevelItem(item)

    def _resume_session(self) -> None:
        item = self._session_tree.currentItem()
        if item:
            self._session.setText(item.text(0))

    def _delete_session(self) -> None:
        item = self._session_tree.currentItem()
        if not item:
            return
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return
        p = Path(path)
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            import shutil
            shutil.rmtree(p, ignore_errors=True)
        self._refresh_sessions()

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

    def _find_guesser(self) -> Optional[Path]:
        if self._pcfg_dir:
            p = self._pcfg_dir / "pcfg_guesser.py"
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

    def get_pipe_command(self) -> str:
        """Return the guesser command for piping to hashcat."""
        cmd = self._build_cmd()
        if not cmd:
            return ""
        return " ".join(cmd)

    def _send_to(self, target: str) -> None:
        if target == "Hashcat Command Builder":
            pipe_cmd = self.get_pipe_command()
            if pipe_cmd:
                from .data_bus import data_bus
                data_bus.send(source=self.MODULE_NAME, target=target, path="pipe:" + pipe_cmd)
                return
        super()._send_to(target)

    def receive_from(self, path: str) -> None:
        pass  # Rulesets are selected from dropdown
