"""Module 3: Combinator — both standard (combinatorX wrapper) and permutation mode.

Combine 2-8 wordlists with custom separators.  Permutation mode uses
itertools.permutations natively.
"""

from __future__ import annotations

import itertools
import threading
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .base_module import BaseModule

# Built-in thematic wordlists
THEMATIC_LISTS = {
    "Digits (0-9)": [str(d) for d in range(10)],
    "Digits (00-99)": [f"{d:02d}" for d in range(100)],
    "Digits (000-999)": [f"{d:03d}" for d in range(1000)],
    "Common PINs": [
        "1234", "0000", "1111", "2222", "3333", "4444", "5555", "6666",
        "7777", "8888", "9999", "1212", "6969", "4321", "1122", "1001",
        "2580", "1010", "7890", "0987", "123456", "654321", "111111",
    ],
    "Special characters": list("!@#$%^&*()-_=+[]{};:'\",.<>?/\\|`~"),
    "Special combos (2-char)": ["!!", "!@", "@#", "#$", "$!", "!!!", "@@", "##", "$$"],
    "Years (1950-2030)": [str(y) for y in range(1950, 2031)],
    "Days & Months": (
        [f"{d:02d}" for d in range(1, 32)]
        + ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        + ["january", "february", "march", "april", "may", "june",
           "july", "august", "september", "october", "november", "december"]
    ),
    "Keyboard walks": [
        "qwerty", "asdf", "zxcv", "1234", "qwer1234", "1q2w3e4r",
        "asdfgh", "zxcvbn", "12345", "123456",
    ],
    "Common Names": [
        "james", "john", "robert", "michael", "david", "william", "richard",
        "joseph", "thomas", "charles", "mary", "patricia", "jennifer", "linda",
        "elizabeth", "barbara", "susan", "jessica", "sarah", "karen", "ashley",
        "daniel", "matthew", "anthony", "mark", "donald", "steven", "paul",
        "andrew", "joshua", "emma", "olivia", "sophia", "isabella", "mia",
        "charlotte", "amelia", "harper", "evelyn", "abigail", "charlie", "max",
        "alex", "sam", "chris", "jordan", "taylor", "morgan", "casey", "riley",
    ],
    "Seasons & Weather": [
        "spring", "summer", "autumn", "fall", "winter",
        "sunny", "rain", "snow", "storm", "thunder", "lightning",
        "Spring", "Summer", "Autumn", "Fall", "Winter",
    ],
    "Colors": [
        "red", "blue", "green", "yellow", "black", "white", "purple",
        "orange", "pink", "brown", "silver", "gold", "grey", "gray",
        "Red", "Blue", "Green", "Yellow", "Black", "White", "Purple",
    ],
    "Sports Teams": [
        "yankees", "lakers", "cowboys", "patriots", "eagles", "steelers",
        "packers", "bears", "celtics", "warriors", "bulls", "dodgers",
        "giants", "redsox", "tigers", "broncos", "niners", "ravens",
        "chiefs", "braves", "astros", "heat", "thunder", "rockets",
    ],
    "Pet Names": [
        "buddy", "max", "charlie", "bella", "lucy", "daisy", "molly",
        "lola", "sadie", "maggie", "rocky", "bailey", "duke", "bear",
        "tucker", "jack", "coco", "oliver", "harley", "shadow", "lucky",
        "ginger", "toby", "zeus", "bandit", "princess", "angel", "rex",
    ],
    "Leet-speak substitutions": [
        "@", "4", "3", "1", "0", "5", "7", "!", "$",
        "@1", "3r", "h4x", "p4ss", "l33t", "1337", "n00b", "r00t",
        "h4ck", "pr0", "z3r0", "0n3", "tw0", "thr33",
    ],
}


class WordlistSlot(QWidget):
    """One wordlist slot in the combinator."""

    def __init__(self, index: int, parent=None) -> None:
        super().__init__(parent)
        self.index = index
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        layout.addWidget(QLabel(f"Slot {index + 1}:"))

        self.source_combo = QComboBox()
        self.source_combo.addItem("Browse file…")
        self.source_combo.addItems(THEMATIC_LISTS.keys())
        self.source_combo.currentTextChanged.connect(self._on_source_changed)
        layout.addWidget(self.source_combo)
        layout.addWidget(BaseModule._info_icon("Select a built-in thematic list or browse for a file."))

        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("Select or type a file path…")
        layout.addWidget(self.file_path, stretch=1)

        self.browse_btn = QPushButton("Browse…")
        self.browse_btn.clicked.connect(self._browse)
        layout.addWidget(self.browse_btn)

        self.preview_btn = QPushButton("Peek")
        self.preview_btn.setMinimumWidth(50)
        self.preview_btn.setToolTip("Preview first 20 lines")
        self.preview_btn.setStatusTip("Preview first 20 lines of this slot")
        self.preview_btn.clicked.connect(self._show_preview)
        layout.addWidget(self.preview_btn)

    def _on_source_changed(self, text: str) -> None:
        is_file = text == "Browse file…"
        self.file_path.setVisible(is_file)
        self.browse_btn.setVisible(is_file)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, f"Slot {self.index + 1} wordlist", "", "All Files (*)")
        if path:
            self.file_path.setText(path)

    def _show_preview(self) -> None:
        """Show first 20 lines of this slot in a tooltip popup."""
        from PyQt6.QtWidgets import QToolTip
        from PyQt6.QtCore import QPoint
        head, total_hint = self._peek_head(20)
        if head:
            text = "\n".join(head)
            if total_hint and total_hint > len(head):
                text += f"\n… (~{total_hint:,} total)"
        else:
            text = "(empty)"
        QToolTip.showText(
            self.preview_btn.mapToGlobal(QPoint(0, self.preview_btn.height())),
            text, self.preview_btn,
        )

    def _peek_head(self, n: int = 20) -> tuple[list[str], int | None]:
        """Read only the first *n* lines.  Return (lines, estimated_total)."""
        source = self.source_combo.currentText()
        if source in THEMATIC_LISTS:
            words = THEMATIC_LISTS[source]
            return words[:n], len(words)
        fpath = self.file_path.text().strip()
        if fpath and Path(fpath).is_file():
            p = Path(fpath)
            head: list[str] = []
            bytes_read = 0
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        stripped = line.rstrip("\n\r")
                        if stripped:
                            head.append(stripped)
                            bytes_read += len(line)
                            if len(head) >= n:
                                break
            except OSError:
                return [], None
            # Estimate total lines from file size
            avg = bytes_read / len(head) if head else 1
            est_total = int(p.stat().st_size / avg)
            return head, est_total
        return [], None

    def has_words(self) -> bool:
        """Return True if this slot has at least one word (without loading the full file)."""
        source = self.source_combo.currentText()
        if source in THEMATIC_LISTS:
            return True
        fpath = self.file_path.text().strip()
        if fpath and Path(fpath).is_file():
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if line.strip():
                            return True
            except OSError:
                pass
        return False

    def get_words(self) -> list[str]:
        source = self.source_combo.currentText()
        if source in THEMATIC_LISTS:
            return THEMATIC_LISTS[source]
        fpath = self.file_path.text().strip()
        if fpath and Path(fpath).is_file():
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                return [line.rstrip("\n\r") for line in f if line.strip()]
        return []


class CombinatorModule(BaseModule):
    MODULE_NAME = "Combinator"
    MODULE_DESCRIPTION = (
        "Combine 2 to 8 wordlists together, concatenating one word from "
        "each list per candidate. Supports custom separators between words. "
        "Useful for building passphrase-style candidates."
    )
    MODULE_CATEGORY = "Wordlist Generation"

    _generation_done = pyqtSignal(list)

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        self._slots: list[WordlistSlot] = []
        self._sep_inputs: list[QLineEdit] = []
        super().__init__(parent)
        self._generation_done.connect(self._on_done)

    def build_input_section(self, layout: QVBoxLayout) -> None:
        # Slots container
        self._slots_container = QVBoxLayout()
        layout.addLayout(self._slots_container)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Slot")
        add_btn.setToolTip("Add another wordlist slot (max 8).")
        add_btn.clicked.connect(self._add_slot)
        rm_btn = QPushButton("− Remove Last")
        rm_btn.setToolTip("Remove the last wordlist slot (min 2).")
        rm_btn.clicked.connect(self._remove_slot)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(rm_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def build_params_section(self, layout: QVBoxLayout) -> None:
        # Separators
        sep_grp = QGroupBox("Separators")
        self._sep_layout = QVBoxLayout(sep_grp)
        self._sep_layout.addWidget(QLabel(
            "Define separator strings between adjacent slots. "
            "Leave empty for no separator."
        ))
        self._sep_container = QVBoxLayout()
        self._sep_layout.addLayout(self._sep_container)

        sr = QHBoxLayout()
        sr.addWidget(QLabel("Start separator:"))
        sr.addWidget(self._info_icon("Characters prepended before the first word."))
        self._sep_start = QLineEdit()
        sr.addWidget(self._sep_start)
        sr.addWidget(QLabel("End separator:"))
        sr.addWidget(self._info_icon("Characters appended after the last word."))
        self._sep_end = QLineEdit()
        sr.addWidget(self._sep_end)
        sr.addStretch()
        self._sep_layout.addLayout(sr)
        layout.addWidget(sep_grp)

        # Start with 2 slots (after _sep_container exists)
        for _ in range(2):
            self._add_slot()

        # Additional options
        self._max_len = self.create_spinbox(
            layout, "Max output length:", 1, 1000, 256,
            "Discard candidates longer than this. Useful to keep output manageable.",
        )
        self._skip = self.create_spinbox(
            layout, "Skip first N (-s):", 0, 999_999_999, 0,
            "Skip the first N combinations. For distributed processing or resuming.",
        )
        self._limit = self.create_spinbox(
            layout, "Limit (0=unlimited):", 0, 999999999, 0,
            "Stop after N combinations. 0 = unlimited.",
        )

        # Permutation mode toggle
        self._perm_mode = self.create_checkbox(
            layout, "Permutation mode (all orderings of input elements)",
            default=False,
            tooltip=(
                "Try all orderings of the input elements. Useful when you know "
                "which pieces make up a password but not their order. "
                "Warning: N elements produce N! orderings — 5 = 120, 6 = 720."
            ),
        )
        perm_row = QHBoxLayout()
        perm_row.addWidget(QLabel("Max permutation depth:"))
        perm_row.addWidget(self._info_icon("Maximum number of elements to permute to prevent combinatorial explosion."))
        self._perm_depth = QSpinBox()
        self._perm_depth.setRange(2, 10)
        self._perm_depth.setValue(5)
        perm_row.addWidget(self._perm_depth)
        perm_row.addStretch()
        layout.addLayout(perm_row)

        # Permutation paste box
        self._perm_input = QTextEdit()
        self._perm_input.setMaximumHeight(80)
        self._perm_input.setPlaceholderText("Elements for permutation (one per line)…")
        _pi_tip = QHBoxLayout()
        _pi_tip.addWidget(self._info_icon("Enter elements to permute, one per line."))
        _pi_tip.addStretch()
        layout.addLayout(_pi_tip)
        layout.addWidget(self._perm_input)

    def build_output_section(self, layout: QVBoxLayout) -> None:
        self._output_file = self.create_file_browser(
            layout, "Output file:", "Save combined candidates to file.",
            save=True, file_filter="Text Files (*.txt);;All Files (*)",
        )
        self._output_file.setText(str(self._default_output_dir() / "combined.txt"))

        # Preview section
        prev_btn = QPushButton("Preview (first 100 candidates)")
        prev_btn.setToolTip("Generate only the first 100 combinations and show them below.")
        prev_btn.clicked.connect(self._on_preview)
        layout.addWidget(prev_btn)

        self._preview_box = QTextEdit()
        self._preview_box.setReadOnly(True)
        self._preview_box.setMaximumHeight(160)
        self._preview_box.setStyleSheet("font-family: Consolas, 'Courier New', monospace; font-size: 11px;")
        self._preview_box.setPlaceholderText("Click 'Preview' to see the first 100 candidates\u2026")
        layout.addWidget(self._preview_box)

        send_row = QHBoxLayout()
        self.send_to_menu(send_row, ["Hashcat Command Builder", "PRINCE Processor"])
        send_row.addStretch()
        layout.addLayout(send_row)

    # ── Slot management ──────────────────────────────────────────
    def _add_slot(self) -> None:
        if len(self._slots) >= 8:
            return
        slot = WordlistSlot(len(self._slots))
        self._slots.append(slot)
        self._slots_container.addWidget(slot)
        self._rebuild_separators()

    def _remove_slot(self) -> None:
        if len(self._slots) <= 2:
            return
        slot = self._slots.pop()
        self._slots_container.removeWidget(slot)
        slot.deleteLater()
        self._rebuild_separators()

    def _rebuild_separators(self) -> None:
        # Clear existing separator inputs
        for inp in self._sep_inputs:
            self._sep_container.removeWidget(inp)
            inp.deleteLater()
        self._sep_inputs.clear()

        for i in range(len(self._slots) - 1):
            row_w = QWidget()
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addWidget(QLabel(f"Between slot {i + 1} and {i + 2}:"))
            rl.addWidget(BaseModule._info_icon(
                f"Characters inserted between words from slot {i + 1} and slot {i + 2}. "
                "Leave empty for no separator. Example: '-' produces 'word1-word2'."
            ))
            sep_le = QLineEdit()
            rl.addWidget(sep_le)
            self._sep_container.addWidget(row_w)
            self._sep_inputs.append(row_w)

    def _get_separator(self, index: int) -> str:
        """Get separator between slot index and index+1."""
        widget = self._sep_inputs[index] if index < len(self._sep_inputs) else None
        if widget:
            le = widget.findChild(QLineEdit)
            return le.text() if le else ""
        return ""

    # ── Validation ──────────────────────────────────────────────
    def validate(self) -> list[str]:
        errors: list[str] = []
        if self._perm_mode.isChecked():
            if not self._perm_input.toPlainText().strip():
                errors.append("Enter elements in the permutation text box.")
        else:
            populated = sum(1 for s in self._slots if s.has_words())
            if populated < 2:
                errors.append("Populate at least 2 wordlist slots.")
        return errors

    # ── Preview ───────────────────────────────────────────────────
    def _on_preview(self) -> None:
        """Generate first 100 candidates using only head samples from each slot."""
        if self._perm_mode.isChecked():
            text = self._perm_input.toPlainText().strip()
            if not text:
                self._preview_box.setPlainText("(enter permutation elements first)")
                return
            elements = [line.strip() for line in text.splitlines() if line.strip()]
            depth = min(self._perm_depth.value(), len(elements))
            max_len = self._max_len.value()
            results: list[str] = []
            for perm in itertools.permutations(elements, depth):
                candidate = "".join(perm)
                if len(candidate) <= max_len:
                    results.append(candidate)
                    if len(results) >= 100:
                        break
        else:
            # Use only first 50 words from each slot to keep it fast
            word_lists = [s._peek_head(50)[0] for s in self._slots]
            if not all(word_lists):
                self._preview_box.setPlainText("(populate at least 2 slots first)")
                return
            max_len = self._max_len.value()
            sep_start = self._sep_start.text()
            sep_end = self._sep_end.text()
            results = []
            for combo in itertools.product(*word_lists):
                parts: list[str] = []
                for i, word in enumerate(combo):
                    parts.append(word)
                    if i < len(combo) - 1:
                        sep = self._get_separator(i)
                        if sep:
                            parts.append(sep)
                candidate = sep_start + "".join(parts) + sep_end
                if len(candidate) <= max_len:
                    results.append(candidate)
                    if len(results) >= 100:
                        break

        if results:
            self._preview_box.setPlainText("\n".join(results))
        else:
            self._preview_box.setPlainText("(no candidates produced with current settings)")

    # ── Generation ───────────────────────────────────────────────
    def run_tool(self) -> None:
        thread = threading.Thread(target=self._generate, daemon=True)
        thread.start()

    def _generate(self) -> None:
        if self._perm_mode.isChecked():
            results = self._generate_permutations()
        else:
            results = self._generate_combinations()
        self._generation_done.emit(results)

    def _generate_combinations(self) -> list[str]:
        word_lists = [slot.get_words() for slot in self._slots]
        if not all(word_lists):
            return []

        max_len = self._max_len.value()
        skip = self._skip.value()
        limit = self._limit.value()
        sep_start = self._sep_start.text()
        sep_end = self._sep_end.text()

        results: list[str] = []
        count = 0
        skipped = 0

        for combo in itertools.product(*word_lists):
            if skipped < skip:
                skipped += 1
                continue
            parts = []
            for i, word in enumerate(combo):
                parts.append(word)
                if i < len(combo) - 1:
                    sep = self._get_separator(i)
                    if sep:
                        parts.append(sep)
            candidate = sep_start + "".join(parts) + sep_end
            if len(candidate) <= max_len:
                results.append(candidate)
                count += 1
                if limit > 0 and count >= limit:
                    break

        return results

    def _generate_permutations(self) -> list[str]:
        text = self._perm_input.toPlainText().strip()
        if not text:
            return []
        elements = [line.strip() for line in text.splitlines() if line.strip()]
        depth = min(self._perm_depth.value(), len(elements))
        max_len = self._max_len.value()
        limit = self._limit.value()

        results: list[str] = []
        count = 0
        for perm in itertools.permutations(elements, depth):
            candidate = "".join(perm)
            if len(candidate) <= max_len:
                results.append(candidate)
                count += 1
                if limit > 0 and count >= limit:
                    break
        return results

    def _on_done(self, results: list[str]) -> None:
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress.setVisible(False)

        self._output_log.clear()
        self._output_log.append(f"Generated {len(results):,} candidates.\n")
        preview = results[:1000]
        self._output_log.append("\n".join(preview))
        if len(results) > 1000:
            self._output_log.append(f"\n… and {len(results) - 1000:,} more.")

        out_path = self._output_file.text().strip()
        if out_path:
            self._save(out_path, results)

    def _save(self, path: str, data: list[str]) -> None:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(data) + "\n")
            self._output_path = path
            self._output_log.append(f"\n✓ Saved to {path}")
        except OSError as e:
            self._output_log.append(f"\n✗ Save failed: {e}")

    def get_output_path(self) -> Optional[str]:
        return self._output_path

    def receive_from(self, path: str) -> None:
        if self._slots:
            self._slots[0].file_path.setText(path)
            self._slots[0].source_combo.setCurrentText("Browse file…")
