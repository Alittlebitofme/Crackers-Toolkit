"""Module 7: Date & Number Pattern Generator.

Generate systematic date-formatted strings and number patterns that
people commonly use in passwords: birthdays, anniversaries, years, PINs.
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
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from .base_module import BaseModule

# Month name tables by language
MONTH_NAMES = {
    "English": {
        "abbr": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "full": ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"],
    },
    "German": {
        "abbr": ["Jan", "Feb", "Mrz", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
        "full": ["Januar", "Februar", "März", "April", "Mai", "Juni",
                 "Juli", "August", "September", "Oktober", "November", "Dezember"],
    },
    "French": {
        "abbr": ["jan", "fév", "mar", "avr", "mai", "jun", "jul", "aoû", "sep", "oct", "nov", "déc"],
        "full": ["janvier", "février", "mars", "avril", "mai", "juin",
                 "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    },
    "Spanish": {
        "abbr": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
        "full": ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    },
    "Dutch": {
        "abbr": ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"],
        "full": ["januari", "februari", "maart", "april", "mei", "juni",
                 "juli", "augustus", "september", "oktober", "november", "december"],
    },
    "Danish": {
        "abbr": ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"],
        "full": ["januar", "februar", "marts", "april", "maj", "juni",
                 "juli", "august", "september", "oktober", "november", "december"],
    },
}

# Curated list of most common PINs
COMMON_PINS = [
    "1234", "0000", "1111", "2222", "3333", "4444", "5555", "6666", "7777", "8888", "9999",
    "1212", "6969", "4321", "1122", "1001", "2580", "1010", "7890", "0987", "2468", "1357",
    "9876", "5678", "0852", "1313", "2525", "8520", "1590", "7531",
    "123456", "654321", "111111", "000000", "121212", "696969", "112233",
    "123123", "159753", "147258", "789456", "321654", "999999", "666666",
]


def _days_in_month(month: int, year: int) -> int:
    if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
    if month in (4, 6, 9, 11):
        return 30
    # February
    if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        return 29
    return 28


class DateNumberModule(BaseModule):
    MODULE_NAME = "Date & Number Patterns"
    MODULE_DESCRIPTION = (
        "Generate systematic date-formatted strings and number patterns "
        "that people commonly use in passwords: birthdays, anniversaries, "
        "years, PINs. Covers multiple date formats and configurable year ranges."
    )
    MODULE_CATEGORY = "Wordlist Generation"

    _generation_done = pyqtSignal(list)

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        self._generated: list[str] = []
        self._date_set: set[str] = set()
        self._number_set: set[str] = set()
        super().__init__(parent)
        self._generation_done.connect(self._on_generation_done)

    # ── Input section ────────────────────────────────────────────
    def build_input_section(self, layout: QVBoxLayout) -> None:
        note = QLabel("This tool generates patterns from configuration — no file input needed.")
        note.setStyleSheet("color: #888;")
        layout.addWidget(note)

    # ── Parameters section ───────────────────────────────────────
    def build_params_section(self, layout: QVBoxLayout) -> None:
        # Date parameters
        date_grp = QGroupBox("Date Patterns")
        dl = QVBoxLayout(date_grp)

        # Year range
        yr_row = QHBoxLayout()
        yr_row.addWidget(QLabel("Year range:"))
        yr_row.addWidget(self._info_icon("Start year for date generation. Covers typical birth years."))
        self._year_from = QSpinBox()
        self._year_from.setRange(1900, 2100)
        self._year_from.setValue(1950)
        yr_row.addWidget(self._year_from)
        yr_row.addWidget(QLabel("to"))
        yr_row.addWidget(self._info_icon("End year for date generation."))
        self._year_to = QSpinBox()
        self._year_to.setRange(1900, 2100)
        self._year_to.setValue(2030)
        yr_row.addWidget(self._year_to)
        yr_row.addStretch()
        dl.addLayout(yr_row)

        # Date formats
        fmt_lbl = QLabel("Date formats to generate:")
        fmt_lbl.setStyleSheet("font-weight: bold; margin-top: 6px;")
        dl.addWidget(fmt_lbl)

        self._date_formats: dict[str, QCheckBox] = {}
        formats = [
            ("DDMMYYYY", "25121990", "Day-Month-Year, no separator. Common in Europe."),
            ("DD/MM/YYYY", "25/12/1990", "Day/Month/Year with slash."),
            ("DD-MM-YYYY", "25-12-1990", "Day-Month-Year with dash."),
            ("DD.MM.YYYY", "25.12.1990", "Day-Month-Year with dot. Common in Germany."),
            ("MMDDYYYY", "12251990", "Month-Day-Year, no separator. Common in US."),
            ("MM/DD/YYYY", "12/25/1990", "Month/Day/Year with slash."),
            ("YYYYMMDD", "19901225", "ISO-style Year-Month-Day."),
            ("YYYY-MM-DD", "1990-12-25", "ISO format with dashes."),
            ("DDMM", "2512", "Day-Month short (no year)."),
            ("MMDD", "1225", "Month-Day short (no year)."),
            ("DDMMYY", "251290", "Day-Month-2-digit-Year."),
            ("MMDDYY", "122590", "Month-Day-2-digit-Year."),
            ("MM-DD-YY", "12-25-90", "Month-Day-2-digit-Year with dashes."),
            ("MonYYYY", "Dec1990", "Abbreviated month + year."),
            ("MonthYYYY", "December1990", "Full month + year."),
            ("YYYY", "1990", "Year only."),
            ("YY", "90", "Two-digit year only."),
        ]
        for fmt, example, tip in formats:
            row = QHBoxLayout()
            cb = QCheckBox(f"{fmt}  (e.g. {example})")
            cb.setChecked(True)
            row.addWidget(cb)
            row.addWidget(self._info_icon(tip))
            row.addStretch()
            dl.addLayout(row)
            self._date_formats[fmt] = cb

        # Month names
        _r = QHBoxLayout()
        self._include_month_names = QCheckBox("Include month names (Jan, January, etc.)")
        self._include_month_names.setChecked(True)
        _r.addWidget(self._include_month_names)
        _r.addWidget(self._info_icon("Also generate dates with month names in addition to numeric."))
        _r.addStretch()
        dl.addLayout(_r)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Month name language:"))
        self._month_lang = QComboBox()
        self._month_lang.addItems(list(MONTH_NAMES.keys()))
        lang_row.addWidget(self._month_lang)
        lang_row.addWidget(self._info_icon("Language for month names."))
        lang_row.addStretch()
        dl.addLayout(lang_row)

        layout.addWidget(date_grp)

        # Number parameters
        num_grp = QGroupBox("Number Patterns")
        nl = QVBoxLayout(num_grp)

        _r2 = QHBoxLayout()
        self._digit_sequences = QCheckBox("Digit sequences (123, 1234, 12345, etc.)")
        self._digit_sequences.setChecked(True)
        _r2.addWidget(self._digit_sequences)
        _r2.addWidget(self._info_icon("Generate sequential digit runs, ascending and descending."))
        _r2.addStretch()
        nl.addLayout(_r2)

        _r3 = QHBoxLayout()
        self._repeated_digits = QCheckBox("Repeated digits (111, 0000, 9999, etc.)")
        self._repeated_digits.setChecked(True)
        _r3.addWidget(self._repeated_digits)
        _r3.addWidget(self._info_icon("Generate repeated-digit strings."))
        _r3.addStretch()
        nl.addLayout(_r3)

        min_row = QHBoxLayout()
        min_row.addWidget(QLabel("Min digits:"))
        min_row.addWidget(self._info_icon("Minimum length of generated number patterns."))
        self._min_digits = QSpinBox()
        self._min_digits.setRange(1, 20)
        self._min_digits.setValue(2)
        min_row.addWidget(self._min_digits)
        min_row.addWidget(QLabel("Max digits:"))
        min_row.addWidget(self._info_icon("Maximum length of generated number patterns."))
        self._max_digits = QSpinBox()
        self._max_digits.setRange(1, 20)
        self._max_digits.setValue(8)
        min_row.addWidget(self._max_digits)
        min_row.addStretch()
        nl.addLayout(min_row)

        _r4 = QHBoxLayout()
        self._common_pins = QCheckBox("Include curated common PINs (1234, 0000, 1111, etc.)")
        self._common_pins.setChecked(True)
        _r4.addWidget(self._common_pins)
        _r4.addWidget(self._info_icon("Include a curated list of the most common PINs."))
        _r4.addStretch()
        nl.addLayout(_r4)

        # Systematic PIN generation
        pin_lbl = QLabel("Systematic PIN generation:")
        pin_lbl.setStyleSheet("font-weight: bold; margin-top: 4px;")
        nl.addWidget(pin_lbl)
        _r5 = QHBoxLayout()
        self._pin_4 = QCheckBox("4-digit PINs (0000-9999)")
        self._pin_4.setChecked(False)
        _r5.addWidget(self._pin_4)
        _r5.addWidget(self._info_icon("Generate all 10,000 possible 4-digit PINs."))
        _r5.addStretch()
        nl.addLayout(_r5)
        _r6 = QHBoxLayout()
        self._pin_6 = QCheckBox("6-digit PINs (000000-999999)")
        self._pin_6.setChecked(False)
        _r6.addWidget(self._pin_6)
        _r6.addWidget(self._info_icon("Generate all 1,000,000 possible 6-digit PINs. Warning: large output."))
        _r6.addStretch()
        nl.addLayout(_r6)
        _r7 = QHBoxLayout()
        self._pin_8 = QCheckBox("8-digit PINs (00000000-99999999)")
        self._pin_8.setChecked(False)
        _r7.addWidget(self._pin_8)
        _r7.addWidget(self._info_icon("Generate all 100,000,000 possible 8-digit PINs. Warning: very large output."))
        _r7.addStretch()
        nl.addLayout(_r7)

        layout.addWidget(num_grp)

        # Phone patterns
        phone_grp = QGroupBox("Phone Number Patterns")
        phl = QVBoxLayout(phone_grp)
        _r8 = QHBoxLayout()
        self._phone_enabled = QCheckBox("Generate phone number patterns")
        self._phone_enabled.setChecked(False)
        _r8.addWidget(self._phone_enabled)
        _r8.addWidget(self._info_icon("Generate common phone number formats. Useful for passwords based on phone numbers."))
        _r8.addStretch()
        phl.addLayout(_r8)

        self._phone_area_codes = QLineEdit("212,310,415,305,702,312,617,206")
        _ac_row = QHBoxLayout()
        _ac_row.addWidget(QLabel("Area codes (comma-separated):"))
        _ac_row.addWidget(self._info_icon("Comma-separated US area codes to use. Leave empty for all 3-digit codes."))
        _ac_row.addWidget(self._phone_area_codes, stretch=1)
        phl.addLayout(_ac_row)

        self._phone_formats: dict[str, QCheckBox] = {}
        phone_fmts = [
            ("XXXXXXXXXX", "10 digits, no separator (e.g. 2125551234)"),
            ("XXX-XXX-XXXX", "Dashed (e.g. 212-555-1234)"),
            ("(XXX) XXX-XXXX", "Parenthesized area code (e.g. (212) 555-1234)"),
            ("XXX.XXX.XXXX", "Dotted (e.g. 212.555.1234)"),
            ("XXXXXXX", "7 digits, no area code (e.g. 5551234)"),
        ]
        for fmt, tip in phone_fmts:
            _pr = QHBoxLayout()
            cb = QCheckBox(fmt)
            cb.setChecked(True)
            _pr.addWidget(cb)
            _pr.addWidget(self._info_icon(tip))
            _pr.addStretch()
            phl.addLayout(_pr)
            self._phone_formats[fmt] = cb

        layout.addWidget(phone_grp)

        # Custom templates
        tmpl_grp = QGroupBox("Custom Templates")
        tl = QVBoxLayout(tmpl_grp)
        tl.addWidget(QLabel(
            "Enter custom templates using placeholders: {YYYY}, {YY}, {MM}, {DD}, {PIN4}, {PIN6}, {DIGIT}.\n"
            "One template per line. Example: {YYYY}{MM}{DD}"
        ))
        self._custom_templates = QTextEdit()
        self._custom_templates.setMaximumHeight(80)
        self._custom_templates.setPlaceholderText("{YYYY}_{DD}{MM}\n{PIN4}@{YYYY}")
        _tmpl_tip = QHBoxLayout()
        _tmpl_tip.addWidget(self._info_icon(
            "Custom pattern templates using placeholders. "
            "{YYYY}=4-digit year, {YY}=2-digit year, {MM}=month, {DD}=day, "
            "{PIN4}=4-digit PIN, {PIN6}=6-digit PIN, {DIGIT}=single digit 0-9."
        ))
        _tmpl_tip.addStretch()
        tl.addLayout(_tmpl_tip)
        tl.addWidget(self._custom_templates)
        layout.addWidget(tmpl_grp)

    # ── Output section ───────────────────────────────────────────
    def build_output_section(self, layout: QVBoxLayout) -> None:
        self._output_file = self.create_file_browser(
            layout, "Output file:", "Where to save generated patterns.", save=True,
            file_filter="Text Files (*.txt);;All Files (*)",
        )
        self._output_file.setText(str(self._default_output_dir() / "date_number_patterns.txt"))

        # Preview mode toggle
        view_row = QHBoxLayout()
        self._view_all = QRadioButton("All")
        self._view_all.setChecked(True)
        self._view_dates = QRadioButton("Dates only")
        self._view_numbers = QRadioButton("Numbers only")
        self._view_all.toggled.connect(self._apply_view_filter)
        self._view_dates.toggled.connect(self._apply_view_filter)
        self._view_numbers.toggled.connect(self._apply_view_filter)
        view_row.addWidget(QLabel("Preview filter:"))
        view_row.addWidget(self._view_all)
        view_row.addWidget(self._view_dates)
        view_row.addWidget(self._view_numbers)
        view_row.addStretch()
        layout.addLayout(view_row)

        # Send-to buttons
        send_row = QHBoxLayout()
        self.send_to_menu(send_row, ["Combinator", "PRINCE Processor", "Hashcat Command Builder"])
        send_row.addStretch()
        layout.addLayout(send_row)

    # ── Generation logic ─────────────────────────────────────────
    def run_tool(self) -> None:
        thread = threading.Thread(target=self._generate, daemon=True)
        thread.start()

    def _generate(self) -> None:
        results: list[str] = []
        date_patterns = self._get_date_patterns()
        number_patterns = self._get_number_patterns()
        # Tag patterns for filtering
        self._date_set: set[str] = set(date_patterns)
        self._number_set: set[str] = set(number_patterns)
        results.extend(date_patterns)
        results.extend(number_patterns)
        # Deduplicate preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for p in results:
            if p not in seen:
                seen.add(p)
                deduped.append(p)
        self._generation_done.emit(deduped)

    def _get_date_patterns(self) -> list[str]:
        patterns: list[str] = []
        y_from = self._year_from.value()
        y_to = self._year_to.value()
        enabled = {fmt for fmt, cb in self._date_formats.items() if cb.isChecked()}
        use_names = self._include_month_names.isChecked()
        lang = self._month_lang.currentText()
        names = MONTH_NAMES.get(lang, MONTH_NAMES["English"])

        for year in range(y_from, y_to + 1):
            yy = f"{year % 100:02d}"
            yyyy = f"{year:04d}"

            # Year-only formats (outside month loop to avoid duplication)
            if "YYYY" in enabled:
                patterns.append(yyyy)
            if "YY" in enabled:
                patterns.append(yy)

            for month in range(1, 13):
                mm = f"{month:02d}"
                mon_abbr = names["abbr"][month - 1]
                mon_full = names["full"][month - 1]
                max_day = _days_in_month(month, year)

                # Month-year formats (no day iteration)
                if "MonYYYY" in enabled and use_names:
                    patterns.append(f"{mon_abbr}{yyyy}")
                if "MonthYYYY" in enabled and use_names:
                    patterns.append(f"{mon_full}{yyyy}")

                for day in range(1, max_day + 1):
                    dd = f"{day:02d}"

                    if "DDMMYYYY" in enabled:
                        patterns.append(f"{dd}{mm}{yyyy}")
                    if "DD/MM/YYYY" in enabled:
                        patterns.append(f"{dd}/{mm}/{yyyy}")
                    if "DD-MM-YYYY" in enabled:
                        patterns.append(f"{dd}-{mm}-{yyyy}")
                    if "DD.MM.YYYY" in enabled:
                        patterns.append(f"{dd}.{mm}.{yyyy}")
                    if "MMDDYYYY" in enabled:
                        patterns.append(f"{mm}{dd}{yyyy}")
                    if "MM/DD/YYYY" in enabled:
                        patterns.append(f"{mm}/{dd}/{yyyy}")
                    if "YYYYMMDD" in enabled:
                        patterns.append(f"{yyyy}{mm}{dd}")
                    if "YYYY-MM-DD" in enabled:
                        patterns.append(f"{yyyy}-{mm}-{dd}")
                    if "DDMM" in enabled:
                        patterns.append(f"{dd}{mm}")
                    if "MMDD" in enabled:
                        patterns.append(f"{mm}{dd}")
                    if "DDMMYY" in enabled:
                        patterns.append(f"{dd}{mm}{yy}")
                    if "MMDDYY" in enabled:
                        patterns.append(f"{mm}{dd}{yy}")
                    if "MM-DD-YY" in enabled:
                        patterns.append(f"{mm}-{dd}-{yy}")

        return patterns

    def _get_number_patterns(self) -> list[str]:
        patterns: list[str] = []
        min_d = self._min_digits.value()
        max_d = self._max_digits.value()

        if self._digit_sequences.isChecked():
            # Ascending sequences starting from each digit
            for length in range(min_d, max_d + 1):
                for start in range(10):
                    seq = "".join(str((start + i) % 10) for i in range(length))
                    patterns.append(seq)
                # Descending
                for start in range(10):
                    seq = "".join(str((start - i) % 10) for i in range(length))
                    patterns.append(seq)

        if self._repeated_digits.isChecked():
            for length in range(min_d, max_d + 1):
                for digit in range(10):
                    patterns.append(str(digit) * length)

        if self._common_pins.isChecked():
            for pin in COMMON_PINS:
                if min_d <= len(pin) <= max_d:
                    patterns.append(pin)

        # Systematic PIN generation
        if self._pin_4.isChecked():
            patterns.extend(f"{n:04d}" for n in range(10000))
        if self._pin_6.isChecked():
            patterns.extend(f"{n:06d}" for n in range(1000000))
        if self._pin_8.isChecked():
            patterns.extend(f"{n:08d}" for n in range(100000000))

        # Phone patterns
        if self._phone_enabled.isChecked():
            patterns.extend(self._get_phone_patterns())

        # Custom templates
        templates_text = self._custom_templates.toPlainText().strip()
        if templates_text:
            patterns.extend(self._expand_templates(templates_text))

        return patterns

    def _get_phone_patterns(self) -> list[str]:
        """Generate phone number patterns with configured area codes and formats."""
        patterns: list[str] = []
        area_text = self._phone_area_codes.text().strip()
        if area_text:
            area_codes = [a.strip() for a in area_text.split(",") if a.strip().isdigit()]
        else:
            area_codes = [f"{a:03d}" for a in range(200, 1000)]  # broad range
        enabled_fmts = [fmt for fmt, cb in self._phone_formats.items() if cb.isChecked()]
        # Use a sample of exchange+subscriber combos to keep output manageable
        exchanges = ["555"]  # default safe exchange; user can adjust area codes
        subscribers = [f"{s:04d}" for s in range(0, 10000, 1000)]  # 0000, 1000, ..., 9000
        for ac in area_codes[:50]:  # Cap to avoid huge output
            for ex in exchanges:
                for sub in subscribers:
                    full = ac + ex + sub
                    for fmt in enabled_fmts:
                        if fmt == "XXXXXXXXXX":
                            patterns.append(full)
                        elif fmt == "XXX-XXX-XXXX":
                            patterns.append(f"{ac}-{ex}-{sub}")
                        elif fmt == "(XXX) XXX-XXXX":
                            patterns.append(f"({ac}) {ex}-{sub}")
                        elif fmt == "XXX.XXX.XXXX":
                            patterns.append(f"{ac}.{ex}.{sub}")
                        elif fmt == "XXXXXXX":
                            patterns.append(ex + sub)
        return patterns

    def _expand_templates(self, templates_text: str) -> list[str]:
        """Expand custom templates with placeholder substitution."""
        import random
        patterns: list[str] = []
        y_from = self._year_from.value()
        y_to = self._year_to.value()
        for tmpl in templates_text.splitlines():
            tmpl = tmpl.strip()
            if not tmpl:
                continue
            # Generate a sample expansion for each year/month/day combo
            for year in range(y_from, y_to + 1):
                base = tmpl.replace("{YYYY}", f"{year:04d}").replace("{YY}", f"{year % 100:02d}")
                if "{MM}" in base or "{DD}" in base:
                    for month in range(1, 13):
                        m_str = f"{month:02d}"
                        mb = base.replace("{MM}", m_str)
                        if "{DD}" in mb:
                            for day in range(1, _days_in_month(month, year) + 1):
                                d_str = f"{day:02d}"
                                db = mb.replace("{DD}", d_str)
                                # PIN/DIGIT sub
                                db = self._sub_pin_digit(db)
                                if db:
                                    patterns.append(db)
                        else:
                            mb = self._sub_pin_digit(mb)
                            if mb:
                                patterns.append(mb)
                else:
                    base = self._sub_pin_digit(base)
                    if base:
                        patterns.append(base)
                if len(patterns) > 500_000:
                    break
        return patterns

    @staticmethod
    def _sub_pin_digit(s: str) -> str:
        """Replace {PIN4}, {PIN6}, {DIGIT} placeholders with a representative sample."""
        if "{PIN4}" in s:
            s = s.replace("{PIN4}", "1234")
        if "{PIN6}" in s:
            s = s.replace("{PIN6}", "123456")
        if "{DIGIT}" in s:
            s = s.replace("{DIGIT}", "0")
        return s

    def _on_generation_done(self, results: list[str]) -> None:
        self._generated = results
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress.setVisible(False)

        self._show_filtered_preview()

        # Auto-save if output path specified
        out_path = self._output_file.text().strip()
        if out_path:
            self._save_to_file(out_path, results)

    def _apply_view_filter(self) -> None:
        """Re-display the preview based on the selected radio filter."""
        if self._generated:
            self._show_filtered_preview()

    def _show_filtered_preview(self) -> None:
        """Show generated patterns filtered by the radio selection."""
        results = self._generated
        if self._view_dates.isChecked():
            results = [p for p in results if p in self._date_set]
        elif self._view_numbers.isChecked():
            results = [p for p in results if p in self._number_set]

        self._output_log.clear()
        self._output_log.append(f"Showing {len(results):,} of {len(self._generated):,} patterns.\n")
        preview = results[:1000]
        self._output_log.append("\n".join(preview))
        if len(results) > 1000:
            self._output_log.append(f"\n… and {len(results) - 1000:,} more.")

        # Auto-save if output path specified
        out_path = self._output_file.text().strip()
        if out_path:
            self._save_to_file(out_path, results)

    def _save_to_file(self, path: str, data: list[str]) -> None:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(data))
                f.write("\n")
            self._output_path = path
            self._output_log.append(f"\n✓ Saved to {path}")
        except OSError as e:
            self._output_log.append(f"\n✗ Save failed: {e}")

    def get_output_path(self) -> Optional[str]:
        return self._output_path
