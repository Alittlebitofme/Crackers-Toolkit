"""Module 21: Simple Cleaner.

A lightweight wordlist cleaner that sorts, deduplicates, filters by length,
and reports password frequency.  Operates entirely in Python — no external
tools required.
"""

from __future__ import annotations

import threading
from collections import Counter
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from .base_module import BaseModule


class SimpleCleanerModule(BaseModule):
    MODULE_NAME = "Simple Cleaner"
    MODULE_DESCRIPTION = (
        "Quick wordlist cleanup: deduplicate, sort, and filter passwords by "
        "length.  Shows a frequency report so you can see which passwords "
        "appeared the most (likely candidates).  No external tools needed."
    )
    MODULE_CATEGORY = "Wordlist Cleaning"

    _work_done = pyqtSignal(dict)  # results payload

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        super().__init__(parent)
        self._work_done.connect(self._on_work_done)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def build_input_section(self, layout: QVBoxLayout) -> None:
        self._input_file = self.create_file_browser(
            layout,
            "Input wordlist:",
            "Plain-text file with one password per line.",
            file_filter="Text Files (*.txt);;All Files (*)",
            receive_type="wordlist",
        )

    def build_params_section(self, layout: QVBoxLayout) -> None:
        self._deduplicate = self.create_checkbox(
            layout, "Remove duplicates (deduplicate)",
            default=True,
            tooltip="Remove duplicate lines, keeping only unique entries.",
        )
        self._sort_alpha = self.create_checkbox(
            layout, "Sort alphabetically",
            default=False,
            tooltip="Sort output lines in alphabetical order.",
        )
        self._sort_freq = self.create_checkbox(
            layout, "Sort by frequency (most common first)",
            default=True,
            tooltip=(
                "Sort passwords by how often they appear (most frequent first). "
                "The frequency count is written next to each password in the "
                "frequency report output."
            ),
        )
        self._write_freq_report = self.create_checkbox(
            layout, "Write frequency report file",
            default=True,
            tooltip=(
                "Save a separate report file where each line shows the count "
                "and the password, e.g. '  1423 password123'.  Sorted from "
                "most common to least common."
            ),
        )

        # Length filter
        len_label = QLabel("Password length filter:")
        len_label.setStyleSheet("font-weight: bold; margin-top: 6px;")
        layout.addWidget(len_label)
        self._filter_length = self.create_checkbox(
            layout, "Only include passwords within length range",
            default=False,
            tooltip="Discard passwords shorter than Min or longer than Max.",
        )
        row = QHBoxLayout()
        self._min_len = self.create_spinbox(
            layout, "Min length:", 0, 1000, 1,
            "Minimum password length to keep (inclusive).",
        )
        self._max_len = self.create_spinbox(
            layout, "Max length:", 0, 1000, 64,
            "Maximum password length to keep (inclusive).",
        )

    def build_output_section(self, layout: QVBoxLayout) -> None:
        self._output_file = self.create_file_browser(
            layout, "Output file:",
            "Cleaned wordlist (one password per line).",
            save=True, file_filter="Text Files (*.txt);;All Files (*)",
        )
        self._output_file.setText(
            str(self._default_output_dir() / "cleaned.txt")
        )

        self._freq_output_file = self.create_file_browser(
            layout, "Frequency report file:",
            "Frequency report showing how many times each password appeared.",
            save=True, file_filter="Text Files (*.txt);;All Files (*)",
        )
        self._freq_output_file.setText(
            str(self._default_output_dir() / "frequency_report.txt")
        )

        send_row = QHBoxLayout()
        self.send_to_menu(
            send_row,
            ["Hashcat Command Builder", "PRINCE Processor", "Combinator"],
        )
        send_row.addStretch()
        layout.addLayout(send_row)

    def build_advanced_section(self, layout: QVBoxLayout) -> None:
        self._strip_whitespace = self.create_checkbox(
            layout, "Strip leading/trailing whitespace",
            default=True,
            tooltip="Remove spaces and tabs from the start and end of each line.",
        )
        self._skip_blank = self.create_checkbox(
            layout, "Skip blank lines",
            default=True,
            tooltip="Discard empty lines or lines that become empty after stripping.",
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        errors: list[str] = []
        inp = self._input_file.text().strip()
        if not inp:
            errors.append("Input wordlist is required.")
        elif not Path(inp).is_file():
            errors.append(f"Input file not found: {inp}")
        if not self._output_file.text().strip():
            errors.append("Output file path is required.")
        if self._filter_length.isChecked():
            if self._min_len.value() > self._max_len.value():
                errors.append("Min length cannot exceed Max length.")
        return errors

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    def run_tool(self) -> None:
        thread = threading.Thread(target=self._process, daemon=True)
        thread.start()

    def _process(self) -> None:
        """Heavy work on a background thread — emits _work_done when complete."""
        try:
            inp = Path(self._input_file.text().strip())
            do_dedup = self._deduplicate.isChecked()
            do_sort_alpha = self._sort_alpha.isChecked()
            do_sort_freq = self._sort_freq.isChecked()
            do_freq_report = self._write_freq_report.isChecked()
            do_length_filter = self._filter_length.isChecked()
            min_len = self._min_len.value()
            max_len = self._max_len.value()
            do_strip = self._strip_whitespace.isChecked()
            do_skip_blank = self._skip_blank.isChecked()

            counter: Counter[str] = Counter()
            total_lines = 0

            with open(inp, "r", encoding="utf-8", errors="replace") as f:
                for raw_line in f:
                    total_lines += 1
                    line = raw_line.rstrip("\n\r")
                    if do_strip:
                        line = line.strip()
                    if do_skip_blank and not line:
                        continue
                    if do_length_filter and not (min_len <= len(line) <= max_len):
                        continue
                    counter[line] += 1

            # Build the output list based on requested sorting
            if do_sort_freq:
                # Most common first
                ordered = [pw for pw, _cnt in counter.most_common()]
            elif do_sort_alpha:
                ordered = sorted(counter.keys())
            else:
                # Preserve first-seen order (Counter keeps insertion order)
                ordered = list(counter.keys())

            if not do_dedup:
                # Expand back to full repetitions in the chosen order
                expanded: list[str] = []
                for pw in ordered:
                    expanded.extend([pw] * counter[pw])
                final_lines = expanded
            else:
                final_lines = ordered

            # Write cleaned output
            out_path = Path(self._output_file.text().strip())
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                for line in final_lines:
                    f.write(line + "\n")

            # Write frequency report
            freq_path_str = self._freq_output_file.text().strip()
            freq_written = False
            if do_freq_report and freq_path_str:
                freq_path = Path(freq_path_str)
                freq_path.parent.mkdir(parents=True, exist_ok=True)
                max_digits = len(str(counter.most_common(1)[0][1])) if counter else 1
                with open(freq_path, "w", encoding="utf-8", newline="\n") as f:
                    for pw, cnt in counter.most_common():
                        f.write(f"{cnt:>{max_digits}}  {pw}\n")
                freq_written = True

            self._work_done.emit({
                "total_lines": total_lines,
                "unique": len(counter),
                "output_lines": len(final_lines),
                "output_path": str(out_path),
                "freq_path": str(freq_path) if freq_written else "",
                "top10": counter.most_common(10),
                "error": "",
            })

        except Exception as exc:
            self._work_done.emit({"error": str(exc)})

    def _on_work_done(self, result: dict) -> None:
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress.setVisible(False)

        if result.get("error"):
            self._output_log.append(f"ERROR: {result['error']}")
            return

        total = result["total_lines"]
        unique = result["unique"]
        output_lines = result["output_lines"]
        removed = total - output_lines

        self._output_log.clear()
        self._output_log.append(f"Input:   {total:,} lines")
        self._output_log.append(f"Unique:  {unique:,} passwords")
        self._output_log.append(f"Output:  {output_lines:,} lines")
        if removed:
            self._output_log.append(f"Removed: {removed:,} lines ({removed/total*100:.1f}%)")
        self._output_log.append(f"\n\u2713 Saved to {result['output_path']}")

        if result.get("freq_path"):
            self._output_log.append(f"\u2713 Frequency report: {result['freq_path']}")

        # Top 10 most common passwords
        top10 = result.get("top10", [])
        if top10:
            self._output_log.append("\n\u2501\u2501 Top 10 most common passwords \u2501\u2501")
            for rank, (pw, cnt) in enumerate(top10, 1):
                self._output_log.append(f"  {rank:>2}. {pw:<30s}  ({cnt:,}x)")

        self._output_path = result["output_path"]
        hint = self._get_what_next_hint()
        if hint:
            self._output_log.append(f"\n\U0001f449 What next? {hint}")

    # ------------------------------------------------------------------
    # Output / receive
    # ------------------------------------------------------------------
    def get_output_path(self) -> Optional[str]:
        return self._output_path

    def receive_from(self, path: str) -> None:
        self._input_file.setText(path)
