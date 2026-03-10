"""Module 5: Element Extractor.

Decompose passwords into structural building blocks: alpha words, digit
runs, special character sequences, years, etc.
"""

from __future__ import annotations

import re
import threading
from collections import Counter
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from .base_module import BaseModule

LEET_MAP = {
    "@": "a", "4": "a", "8": "b", "(": "c", "3": "e",
    "6": "g", "#": "h", "1": "i", "!": "i", "0": "o",
    "5": "s", "$": "s", "7": "t", "+": "t", "2": "z",
}

# Common keyboard walk sequences for detection
_KEYBOARD_PATTERNS = {
    "qwerty", "qwert", "asdf", "asdfg", "asdfgh", "zxcv", "zxcvb",
    "zxcvbn", "qwer", "1234", "12345", "123456", "1q2w3e", "1q2w3e4r",
    "qwer1234", "2580", "1qaz", "2wsx", "3edc", "4rfv", "1qaz2wsx",
    "qazwsx", "zaq1", "xsw2", "cde3", "asdfjkl", "poiuy", "lkjhg",
    "mnbvc", "0987", "09876", "987654", "7890",
}


def _detect_keyboard_patterns(password: str) -> list[tuple[str, str]]:
    """Detect keyboard walk subsequences within a password."""
    results: list[tuple[str, str]] = []
    pw_lower = password.lower()
    for pat in sorted(_KEYBOARD_PATTERNS, key=len, reverse=True):
        if pat in pw_lower:
            results.append((pat, "keyboard_pattern"))
    return results


def _detect_capitalization_pattern(password: str) -> list[tuple[str, str]]:
    """Classify the capitalization pattern of a password."""
    if not any(c.isalpha() for c in password):
        return []
    alpha = "".join(c for c in password if c.isalpha())
    if alpha.islower():
        pat = "all-lower"
    elif alpha.isupper():
        pat = "ALL-CAPS"
    elif alpha[0].isupper() and alpha[1:].islower():
        pat = "First-upper"
    elif alpha[0].islower() and alpha[-1].isupper():
        pat = "last-upper"
    elif re.match(r'^[a-z]+[A-Z][a-z]+', alpha):
        pat = "camelCase"
    elif all(c.isupper() for c in alpha if alpha.index(c) % 2 == 0):
        pat = "aLtErNaTiNg"
    else:
        pat = "mixed-case"
    return [(pat, "capitalization")]


def _decompose(password: str, rules: dict[str, bool]) -> list[tuple[str, str]]:
    """Tokenize a single password into (element, type) pairs."""
    tokens: list[tuple[str, str]] = []
    i = 0
    while i < len(password):
        ch = password[i]
        if ch.isdigit():
            j = i
            while j < len(password) and password[j].isdigit():
                j += 1
            run = password[i:j]
            # Year detection
            if rules.get("year_detection") and len(run) == 4:
                yr = int(run)
                if 1900 <= yr <= 2099:
                    tokens.append((run, "year"))
                    i = j
                    continue
            if rules.get("isolated_digits"):
                for d in run:
                    tokens.append((d, "digit"))
            else:
                tokens.append((run, "digit"))
            i = j
        elif ch.isalpha():
            j = i
            while j < len(password) and password[j].isalpha():
                j += 1
            run = password[i:j]
            if rules.get("alpha_case_split"):
                # Split at lowercase→uppercase transitions
                parts = re.findall(r"[A-Z]?[a-z]*|[A-Z]+(?=[A-Z][a-z]|\b)", run)
                parts = [p for p in parts if p]
                for p in parts:
                    val = p.lower() if rules.get("alpha_lower") else p
                    tokens.append((val, "alpha"))
            else:
                val = run.lower() if rules.get("alpha_lower") else run
                tokens.append((val, "alpha"))
            i = j
        else:
            # Special characters
            j = i
            while j < len(password) and not password[j].isalnum():
                j += 1
            run = password[i:j]
            if rules.get("isolated_specials"):
                for s in run:
                    tokens.append((s, "special"))
            else:
                tokens.append((run, "special"))
            i = j
    return tokens


def _leet_decode(tokens: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Add leet-decoded variants for tokens that contain leet chars."""
    extra: list[tuple[str, str]] = []
    for elem, typ in tokens:
        decoded = "".join(LEET_MAP.get(c, c) for c in elem.lower())
        if decoded != elem.lower() and decoded.isalpha():
            extra.append((decoded, "alpha"))
    return extra


class ElementExtractorModule(BaseModule):
    MODULE_NAME = "Element Extractor"
    MODULE_DESCRIPTION = (
        "Decompose passwords from a wordlist into their structural "
        "building blocks: words, digit runs, special character sequences, "
        "years, etc. The extracted elements make excellent input for "
        "PRINCE or combinator attacks."
    )
    MODULE_CATEGORY = "Wordlist Generation"

    _extraction_done = pyqtSignal(object)  # Counter

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        self._elements: Counter = Counter()
        super().__init__(parent)
        self._extraction_done.connect(self._on_extraction_done)

    def build_input_section(self, layout: QVBoxLayout) -> None:
        self._input_file = self.create_file_browser(
            layout, "Wordlist file:",
            "One or more wordlists to decompose.",
            file_filter="Text Files (*.txt);;All Files (*)",
        )
        layout.addWidget(QLabel("— or paste passwords below —"))
        self._paste_box = QTextEdit()
        self._paste_box.setMaximumHeight(100)
        self._paste_box.setPlaceholderText("Paste passwords here, one per line…")
        layout.addWidget(self._paste_box)

    def build_params_section(self, layout: QVBoxLayout) -> None:
        lbl = QLabel("Decomposition rules:")
        lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl)

        self._rules: dict[str, QCheckBox] = {}
        rules_def = [
            ("contiguous_digits", "Contiguous digits", True,
             "Extract runs of consecutive digits as single tokens."),
            ("contiguous_specials", "Contiguous specials", True,
             "Extract runs of consecutive special characters as tokens."),
            ("isolated_digits", "Isolated digits", False,
             "Split digit runs into individual digits."),
            ("isolated_specials", "Isolated specials", False,
             "Split special runs into individual characters."),
            ("alpha_case_split", "Alpha words (case-split)", True,
             "Split alphabetic sequences at lowercase→uppercase transitions."),
            ("alpha_no_split", "Alpha words (no split)", False,
             "Keep alphabetic sequences whole."),
            ("alpha_lower", "Full alpha-lower", False,
             "Extract alphabetic segments and lowercase them."),
            ("year_detection", "Year detection (1900-2099)", True,
             "Recognize 4-digit sequences resembling years as a 'year' element type."),
            ("leet_decode", "Leet-speak decode", False,
             "Attempt to reverse leet-speak substitutions (@→a, 3→e, 0→o, etc.)."),
            ("keyboard_patterns", "Keyboard patterns", False,
             "Detect common keyboard walk sequences (qwerty, asdf, 1q2w3e, etc.) within passwords."),
            ("capitalization_patterns", "Capitalization patterns", False,
             "Classify the capitalization style of each password (all-lower, ALL-CAPS, First-upper, camelCase, etc.)."),
        ]
        for key, label, default, tip in rules_def:
            _er = QHBoxLayout()
            cb = QCheckBox(label)
            cb.setChecked(default)
            _er.addWidget(cb)
            _er.addWidget(self._info_icon(tip))
            _er.addStretch()
            layout.addLayout(_er)
            self._rules[key] = cb

        # Decomposition preview
        layout.addWidget(QLabel(""))
        preview_grp = QGroupBox("Decomposition Preview")
        pl = QVBoxLayout(preview_grp)
        pr = QHBoxLayout()
        self._preview_input = QLineEdit()
        self._preview_input.setPlaceholderText("Enter a single password to preview…")
        self._preview_input.textChanged.connect(self._update_preview)
        pr.addWidget(self._preview_input, stretch=1)
        pl.addLayout(pr)
        self._preview_output = QLabel("")
        self._preview_output.setWordWrap(True)
        self._preview_output.setStyleSheet("font-family: monospace; padding: 4px;")
        pl.addWidget(self._preview_output)
        layout.addWidget(preview_grp)

    def build_output_section(self, layout: QVBoxLayout) -> None:
        self._output_file = self.create_file_browser(
            layout, "Output file:", "Save extracted elements as a plain text file.",
            save=True, file_filter="Text Files (*.txt);;All Files (*)",
        )
        self._output_file.setText(str(self._default_output_dir() / "extracted_elements.txt"))
        self._dedup_cb = QCheckBox("Deduplicate (show unique elements only)")
        self._dedup_cb.setChecked(True)
        layout.addWidget(self._dedup_cb)

        send_row = QHBoxLayout()
        self.send_to_menu(send_row, ["PRINCE Processor", "Combinator", "Mask Builder"])
        send_row.addStretch()
        layout.addLayout(send_row)

        # Results table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Element", "Type", "Frequency", ""])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(3, 40)
        self._table.setSortingEnabled(True)
        self._table.setMaximumHeight(300)
        layout.addWidget(self._table)

    def _get_active_rules(self) -> dict[str, bool]:
        return {key: cb.isChecked() for key, cb in self._rules.items()}

    def _update_preview(self, text: str) -> None:
        if not text:
            self._preview_output.setText("")
            return
        rules = self._get_active_rules()
        tokens = _decompose(text, rules)
        if rules.get("leet_decode"):
            tokens.extend(_leet_decode(tokens))
        if rules.get("keyboard_patterns"):
            tokens.extend(_detect_keyboard_patterns(text))
        if rules.get("capitalization_patterns"):
            tokens.extend(_detect_capitalization_pattern(text))
        display = " ".join(f"[{elem}]" for elem, _ in tokens)
        typed = " ".join(f"[{elem}:{typ}]" for elem, typ in tokens)
        self._preview_output.setText(f"{display}\n{typed}")

    def validate(self) -> list[str]:
        errors: list[str] = []
        fpath = self._input_file.text().strip()
        pasted = self._paste_box.toPlainText().strip()
        if not fpath and not pasted:
            errors.append("Provide an input file or paste passwords.")
        if fpath and not Path(fpath).is_file():
            errors.append(f"Input file not found: {fpath}")
        return errors

    def run_tool(self) -> None:
        # Read GUI state on the main thread before spawning worker
        self._extract_rules = self._get_active_rules()
        self._extract_fpath = self._input_file.text().strip()
        self._extract_pasted = self._paste_box.toPlainText().strip()
        thread = threading.Thread(target=self._extract, daemon=True)
        thread.start()

    def _extract(self) -> None:
        rules = self._extract_rules
        counter: Counter = Counter()
        type_map: dict[str, str] = {}

        passwords: list[str] = []
        # From file
        fpath = self._extract_fpath
        if fpath and Path(fpath).is_file():
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                passwords.extend(line.rstrip("\n\r") for line in f)
        # From paste box
        pasted = self._extract_pasted
        if pasted:
            passwords.extend(pasted.splitlines())

        for pw in passwords:
            if not pw:
                continue
            tokens = _decompose(pw, rules)
            if rules.get("leet_decode"):
                tokens.extend(_leet_decode(tokens))
            if rules.get("keyboard_patterns"):
                tokens.extend(_detect_keyboard_patterns(pw))
            if rules.get("capitalization_patterns"):
                tokens.extend(_detect_capitalization_pattern(pw))
            for elem, typ in tokens:
                counter[elem] += 1
                type_map[elem] = typ

        # Bundle type_map with counter
        self._type_map = type_map
        self._extraction_done.emit(counter)

    def _on_extraction_done(self, counter: Counter) -> None:
        self._elements = counter
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress.setVisible(False)

        # Populate table
        self._table.setRowCount(0)
        self._table.setSortingEnabled(False)
        for elem, count in counter.most_common():
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(elem))
            self._table.setItem(row, 1, QTableWidgetItem(self._type_map.get(elem, "")))
            freq_item = QTableWidgetItem()
            freq_item.setData(Qt.ItemDataRole.DisplayRole, count)
            self._table.setItem(row, 2, freq_item)
            extract_btn = QPushButton("📋")
            extract_btn.setFixedWidth(32)
            extract_btn.setToolTip(f"Copy '{elem}' to clipboard")
            extract_btn.clicked.connect(lambda checked, e=elem: self._copy_element(e))
            self._table.setCellWidget(row, 3, extract_btn)
        self._table.setSortingEnabled(True)

        self._output_log.clear()
        self._output_log.append(f"Extracted {len(counter):,} unique elements from {sum(counter.values()):,} tokens.")

        # Auto-save
        out_path = self._output_file.text().strip()
        if out_path:
            self._save_elements(out_path)

    def _save_elements(self, path: str) -> None:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                for elem, _ in self._elements.most_common():
                    f.write(elem + "\n")
            self._output_path = path
            self._output_log.append(f"✓ Saved to {path}")
        except OSError as e:
            self._output_log.append(f"✗ Save failed: {e}")

    def _copy_element(self, element: str) -> None:
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(element)
            self._output_log.append(f"Copied to clipboard: {element}")

    def get_output_path(self) -> Optional[str]:
        return self._output_path

    def receive_from(self, path: str) -> None:
        self._input_file.setText(path)
