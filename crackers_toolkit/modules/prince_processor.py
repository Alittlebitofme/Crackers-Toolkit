"""Module 1: PRINCE Processor — wraps the compiled pp binary to generate
password candidates by chaining words from a wordlist in probability order.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from .base_module import BaseModule, CollapsibleSection, ProcessRunner


class PrinceProcessorModule(BaseModule):
    MODULE_NAME = "PRINCE Processor"
    MODULE_DESCRIPTION = (
        "Generate password candidates by chaining words from a wordlist "
        "in probability order. Combines 1-8 words per candidate, "
        "prioritizing the most likely combinations first."
    )
    MODULE_CATEGORY = "Wordlist Generation"

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        self._candidate_count = 0
        super().__init__(parent)

    def build_input_section(self, layout: QVBoxLayout) -> None:
        self._wordlist = self.create_file_browser(
            layout, "Wordlist:", "File browser to select one input wordlist file.",
            file_filter="Text Files (*.txt);;All Files (*)",
        )
        self._file_info = QLabel("")
        self._file_info.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self._file_info)
        self._wordlist.textChanged.connect(self._on_wordlist_changed)

    def build_params_section(self, layout: QVBoxLayout) -> None:
        self._pw_min = self.create_spinbox(
            layout, "--pw-min (min length):", 1, 256, 1,
            "Minimum length of generated passwords. Candidates shorter than this are discarded. Typical: 6-8.",
        )
        self._pw_max = self.create_spinbox(
            layout, "--pw-max (max length):", 1, 256, 16,
            "Maximum length of generated passwords. Candidates longer than this are discarded. Typical: 12-20.",
        )
        self._elem_min = self.create_spinbox(
            layout, "--elem-cnt-min:", 1, 8, 1,
            "Minimum number of words chained per candidate. Set to 2 to force at least two words combined.",
        )
        self._elem_max = self.create_spinbox(
            layout, "--elem-cnt-max:", 1, 8, 8,
            "Maximum words chained per candidate. Higher = more combinations but slower. Typical: 3-4.",
        )
        self._wl_max = self.create_spinbox(
            layout, "--wl-max:", 1, 10_000_000, 10_000_000,
            "Maximum words to read from the wordlist. Words beyond this limit are ignored.",
        )
        self._dupe_disable = self.create_checkbox(
            layout, "--dupe-check-disable", False,
            "Disable duplicate checking. Faster but may output duplicate candidates.",
        )
        self._case_permute = self.create_checkbox(
            layout, "--case-permute", False,
            "Also generate variants with first letter of each word toggled upper/lower. Doubles or more the output.",
        )

    def build_advanced_section(self, layout: QVBoxLayout) -> None:
        self._skip = self.create_spinbox(
            layout, "--skip:", 0, 999_999_999, 0,
            "Skip the first N candidates. For distributed/resumed processing.",
        )
        self._limit = self.create_spinbox(
            layout, "--limit:", 0, 999_999_999, 0,
            "Stop after N candidates. 0 = unlimited.",
        )
        self._keyspace = self.create_checkbox(
            layout, "--keyspace (calculate only)", False,
            "Only calculate and display total number of possible candidates, don't generate them.",
        )
        self._save_file = self.create_file_browser(
            layout, "Session save file:", "Save session state to this file for later restore.",
            save=True, file_filter="Session Files (*.session);;All Files (*)",
        )
        self._restore_file = self.create_file_browser(
            layout, "Session restore file:", "Restore a previously saved session.",
            file_filter="Session Files (*.session);;All Files (*)",
        )

    def build_output_section(self, layout: QVBoxLayout) -> None:
        self._output_file = self.create_file_browser(
            layout, "Output file:", "Save generated candidates to this file.",
            save=True, file_filter="Text Files (*.txt);;All Files (*)",
        )
        self._output_file.setText(str(self._default_output_dir() / "prince_candidates.txt"))

        # ── Preview first 1000 lines ──
        prev_btn = QPushButton("Preview (first 1 000 candidates)")
        prev_btn.setToolTip("Run PRINCE with --limit 1000 and show the output here.")
        prev_btn.clicked.connect(self._on_preview)
        layout.addWidget(prev_btn)

        self._preview_box = QPlainTextEdit()
        self._preview_box.setReadOnly(True)
        self._preview_box.setMaximumHeight(180)
        self._preview_box.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 11px;")
        self._preview_box.setPlaceholderText("Click 'Preview' to see the first 1 000 candidates…")
        layout.addWidget(self._preview_box)

        row = QHBoxLayout()
        self.send_to_menu(row, ["demeuk \u2014 Wordlist Cleaner", "Combinator", "Hashcat Command Builder"])
        row.addStretch()
        layout.addLayout(row)

        # ── Help panel (collapsible) ──
        help_section = CollapsibleSection("How PRINCE works", self)
        help_text = QLabel(
            "<b>PRINCE</b> (PRobability INfinite Chained Elements) generates password "
            "candidates by chaining one or more words from the input wordlist.<br><br>"
            "<b>How it works:</b><br>"
            "1. Words are sorted by probability (frequency in the wordlist).<br>"
            "2. PRINCE builds candidates by combining 1 to <i>elem-cnt-max</i> words.<br>"
            "3. Candidates are emitted in <i>probability order</i> — the most likely "
            "passwords come first, making the attack efficient.<br><br>"
            "<b>Example:</b> Given wordlist <code>[pass, 123, word]</code> with "
            "<code>elem-cnt-max=2</code>:<br>"
            "<code>pass → 123 → word → pass123 → password → 123pass → …</code><br><br>"
            "<b>Tip:</b> Use a small, curated wordlist (e.g. 1 000 words from "
            "demeuk + Element Extractor) rather than a giant one. PRINCE's output "
            "grows combinatorially with wordlist size."
        )
        help_text.setWordWrap(True)
        help_text.setTextFormat(Qt.TextFormat.RichText)
        help_section.content_layout().addWidget(help_text)
        layout.addWidget(help_section)

    def _on_wordlist_changed(self, path: str) -> None:
        p = Path(path)
        if p.is_file():
            size = p.stat().st_size
            try:
                # Estimate line count from first 64 lines instead of reading entire file
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
                    est = int(size / avg)
                    self._file_info.setText(f"~{est:,} lines, {size:,} bytes")
                else:
                    self._file_info.setText(f"{sample_count:,} lines, {size:,} bytes")
            except OSError:
                self._file_info.setText(f"{size:,} bytes")
        else:
            self._file_info.setText("")

    # ── Preview (first 1 000 lines) ──────────────────────────────
    def _on_preview(self) -> None:
        """Run PRINCE with --limit 1000 and capture output into preview box (non-blocking)."""
        wl = self._wordlist.text().strip()
        pp = self._find_pp_binary()
        if not wl or not pp:
            self._preview_box.setPlainText("Select a wordlist and ensure PRINCE binary is available.")
            return

        cmd = [
            str(pp),
            "--pw-min", str(self._pw_min.value()),
            "--pw-max", str(self._pw_max.value()),
            "--elem-cnt-min", str(self._elem_min.value()),
            "--elem-cnt-max", str(self._elem_max.value()),
            "--limit", "1000",
            wl,
        ]
        self._preview_box.setPlainText("Running preview…")
        self._preview_runner = ProcessRunner()
        self._preview_lines: list[str] = []
        self._preview_runner.output_line.connect(self._on_preview_line)
        self._preview_runner.finished.connect(self._on_preview_finished)
        self._preview_runner.error.connect(
            lambda msg: self._preview_box.setPlainText(f"Error: {msg}")
        )
        self._preview_runner.run(cmd)

    def _on_preview_line(self, line: str) -> None:
        self._preview_lines.append(line)

    def _on_preview_finished(self, exit_code: int) -> None:
        text = "\n".join(self._preview_lines) if self._preview_lines else "(no output)"
        self._preview_box.setPlainText(text)

    def validate(self) -> list[str]:
        errors: list[str] = []
        wl = self._wordlist.text().strip()
        if not wl:
            errors.append("Select an input wordlist file.")
        elif not Path(wl).is_file():
            errors.append(f"Wordlist not found: {wl}")
        return errors

    def run_tool(self) -> None:
        wl_path = self._wordlist.text().strip()
        if not wl_path:
            self._output_log.append("Error: No wordlist selected.")
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        pp_path = self._find_pp_binary()
        if not pp_path:
            self._output_log.append(
                "Error: PRINCE processor binary (pp64/pp) not found.\n"
                "Expected in: Scripts_to_use/princeprocessor-master/\n"
                "Configure a custom path in Settings (⚙ in the toolbar)."
            )
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        cmd = [str(pp_path)]
        cmd += ["--pw-min", str(self._pw_min.value())]
        cmd += ["--pw-max", str(self._pw_max.value())]
        cmd += ["--elem-cnt-min", str(self._elem_min.value())]
        cmd += ["--elem-cnt-max", str(self._elem_max.value())]
        cmd += ["--wl-max", str(self._wl_max.value())]

        if self._dupe_disable.isChecked():
            cmd.append("--dupe-check-disable")
        if self._case_permute.isChecked():
            cmd.append("--case-permute")
        if self._keyspace.isChecked():
            cmd.append("--keyspace")

        skip_val = self._skip.value()
        if skip_val > 0:
            cmd += ["--skip", str(skip_val)]
        limit_val = self._limit.value()
        if limit_val > 0:
            cmd += ["--limit", str(limit_val)]

        save = self._save_file.text().strip()
        if save:
            cmd += ["--save-file", save]
        restore = self._restore_file.text().strip()
        if restore:
            cmd += ["--restore-file", restore]

        out_path = self._output_file.text().strip()
        if out_path:
            cmd += ["-o", out_path]
            self._output_path = out_path

        cmd.append(wl_path)

        self._candidate_count = 0
        self._output_log.append(f"$ {' '.join(cmd)}\n")
        self._runner.run(cmd)

    def _on_process_output(self, line: str) -> None:
        self._candidate_count += 1
        if self._candidate_count <= 1000:
            self._output_log.append(line)
        elif self._candidate_count % 10000 == 0:
            self._output_log.append(f"[{self._candidate_count:,} candidates generated…]")

    def _on_process_finished(self, exit_code: int) -> None:
        super()._on_process_finished(exit_code)
        self._output_log.append(f"\nTotal candidates: {self._candidate_count:,}")
        if exit_code == 0 and self._output_path:
            try:
                size = Path(self._output_path).stat().st_size
                self._output_log.append(f"Output file size: {self._fmt_size(size)}")
            except OSError:
                pass

    @staticmethod
    def _fmt_size(n: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
            n /= 1024
        return f"{n:.1f} TB"

    def _find_pp_binary(self) -> Optional[Path]:
        candidates = []
        if self._settings:
            custom = self._settings.get("prince_path")
            if custom:
                candidates.append(Path(custom))
        if self._base_dir:
            base = Path(self._base_dir)
            pp_dirs = [
                base / "Scripts_to_use" / "princeprocessor-master" / "princeprocessor-master" / "src",
                base / "Scripts_to_use" / "princeprocessor-master" / "princeprocessor-master",
                base / "Scripts_to_use" / "princeprocessor-master",
            ]
            for d in pp_dirs:
                for name in ("pp64.exe", "pp.exe", "pp64.bin", "pp.bin", "pp"):
                    candidates.append(d / name)
        _src_ext = {".c", ".h", ".py", ".txt", ".md"}
        for c in candidates:
            if c.is_file() and c.suffix.lower() not in _src_ext:
                return c
        return None

    def get_output_path(self) -> Optional[str]:
        return self._output_path

    def get_pipe_command(self) -> str:
        """Return the pp command for piping to hashcat."""
        pp_path = self._find_pp_binary()
        if not pp_path:
            return ""
        parts = [str(pp_path)]
        parts += ["--pw-min", str(self._pw_min.value())]
        parts += ["--pw-max", str(self._pw_max.value())]
        parts += ["--elem-cnt-min", str(self._elem_min.value())]
        parts += ["--elem-cnt-max", str(self._elem_max.value())]
        parts += ["--wl-max", str(self._wl_max.value())]
        if self._dupe_disable.isChecked():
            parts.append("--dupe-check-disable")
        if self._case_permute.isChecked():
            parts.append("--case-permute")
        wl_path = self._wordlist.text().strip()
        if wl_path:
            parts.append(wl_path)
        return " ".join(parts)

    def _send_to(self, target: str) -> None:
        if target == "Hashcat Command Builder":
            pipe_cmd = self.get_pipe_command()
            if pipe_cmd:
                from .data_bus import data_bus
                data_bus.send(source=self.MODULE_NAME, target=target, path="pipe:" + pipe_cmd)
                return
        super()._send_to(target)

    def receive_from(self, path: str) -> None:
        self._wordlist.setText(path)
