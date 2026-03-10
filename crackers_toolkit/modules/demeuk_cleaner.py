"""Module 8: demeuk — Wordlist Cleaner.

Wraps the external ``demeuk.py`` script to clean, filter, fix encoding,
deduplicate, and transform raw wordlists.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .base_module import BaseModule, CollapsibleSection


class DemeukModule(BaseModule):
    MODULE_NAME = "demeuk — Wordlist Cleaner"
    MODULE_DESCRIPTION = (
        "Clean, filter, fix encoding, deduplicate, and transform raw "
        "wordlists. Handles mojibake, HTML artifacts, control characters, "
        "hash lines, email addresses, and more."
    )
    MODULE_CATEGORY = "Wordlist Cleaning"

    # ── Preset definitions ───────────────────────────────────────
    PRESETS = {
        "Leak cleanup": [
            "chk_control", "mod_mojibake", "mod_encoding_fix", "mod_fix_newlines",
        ],
        "Leak full cleanup": [
            "chk_control", "mod_mojibake", "mod_encoding_fix", "mod_fix_newlines",
            "mod_decode_hex", "mod_decode_html", "chk_hash", "chk_mac",
            "chk_uuid", "chk_email", "chk_replacement", "chk_empty",
        ],
        "Google N-gram": [
            "mod_strip_pos_tags",
        ],
    }

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        self._checks: dict[str, object] = {}
        self._modifies: dict[str, object] = {}
        self._adds: dict[str, object] = {}
        super().__init__(parent)

    # ------------------------------------------------------------------
    # Build sections
    # ------------------------------------------------------------------
    def build_input_section(self, layout: QVBoxLayout) -> None:
        self._input_file = self.create_file_browser(
            layout, "Input file(s) (-i):",
            "One or more raw wordlist files to clean.",
            file_filter="Text Files (*.txt);;All Files (*)",
        )
        self._input_encoding = self.create_combo(
            layout, "Input encoding:", ["Auto", "utf-8", "latin-1", "cp1252", "iso-8859-1", "ascii"],
            "Character encoding of input. 'Auto' uses chardet.",
        )

    def build_params_section(self, layout: QVBoxLayout) -> None:
        # ── Separator / Cutting options ──────────────────────────
        cut_section = CollapsibleSection("Separator / Cutting Options")
        cl = cut_section.content_layout()
        self._enable_cut = self.create_checkbox(cl, "Enable cut (-c)", False,
            "Split lines on a delimiter; keep only the password portion.")
        self._delimiter = self.create_line_edit(cl, "Delimiter (-d):", ":",
            "Character to split on. Default ':'.")
        self._cut_before = self.create_checkbox(cl, "Keep before delimiter", False,
            "Keep the part BEFORE the delimiter instead of after.")
        self._cut_fields = self.create_line_edit(cl, "Cut fields (-f):", "",
            "Specific fields to keep (like cut -f). E.g. '2'.")
        layout.addWidget(cut_section)

        # ── Check modules (drop lines) ──────────────────────────
        chk_section = CollapsibleSection("Check Modules (Drop Lines)")
        cl = chk_section.content_layout()
        checks = [
            ("chk_min_len",        "Min length",                      "Drop lines shorter than the specified minimum length."),
            ("chk_max_len",        "Max length",                      "Drop lines longer than the specified maximum length."),
            ("chk_case",           "Check case (no letters → drop)",  "Drop lines that contain no alphabetic letters at all (pure digits/symbols)."),
            ("chk_control",        "Check control chars",             "Drop lines containing ASCII control characters (0x00-0x1F except \\n, \\r, \\t)."),
            ("chk_email",          "Check email",                     "Drop lines that look like email addresses (contain @ with domain pattern)."),
            ("chk_hash",           "Check hash strings",              "Drop lines that match common hash formats (MD5, SHA1, SHA256, bcrypt, etc.)."),
            ("chk_mac",            "Check MAC address",               "Drop lines that match MAC address format (XX:XX:XX:XX:XX:XX)."),
            ("chk_uuid",           "Check UUID",                      "Drop lines matching UUID format (8-4-4-4-12 hex)."),
            ("chk_non_ascii",      "Check non-ASCII",                 "Drop lines containing any characters outside the ASCII range (> 0x7F)."),
            ("chk_replacement",    "Check replacement char (U+FFFD)", "Drop lines containing the Unicode replacement character (U+FFFD), indicating encoding errors."),
            ("chk_starts_with",    "Check starts with…",              "Drop lines that start with the specified string."),
            ("chk_ends_with",      "Check ends with…",                "Drop lines that end with the specified string."),
            ("chk_contains",       "Check contains…",                 "Drop lines that contain the specified substring anywhere."),
            ("chk_regex",          "Check regex…",                    "Drop lines matching the specified Python regular expression."),
            ("chk_empty",          "Check empty lines",               "Drop blank or whitespace-only lines."),
        ]
        for key, label, tip in checks:
            self._checks[key] = self.create_checkbox(cl, label, False, tip)

        self._chk_min_len_val = self.create_spinbox(cl, "Min length value:", 0, 999, 0)
        self._chk_max_len_val = self.create_spinbox(cl, "Max length value:", 0, 999, 64)
        self._chk_starts_with_val = self.create_line_edit(cl, "Starts with string:", "")
        self._chk_ends_with_val = self.create_line_edit(cl, "Ends with string:", "")
        self._chk_contains_val = self.create_line_edit(cl, "Contains string:", "")
        self._chk_regex_val = self.create_line_edit(cl, "Regex pattern:", "")

        # Extra digit / uppercase / special character checks
        self._chk_min_digits = self.create_spinbox(cl, "Min digits:", 0, 999, 0,
            "Drop lines with fewer than N digits.")
        self._chk_max_digits = self.create_spinbox(cl, "Max digits:", 0, 999, 0,
            "Drop lines with more than N digits. 0 = no limit.")
        self._chk_min_upper = self.create_spinbox(cl, "Min uppercase:", 0, 999, 0,
            "Drop lines with fewer than N uppercase letters.")
        self._chk_max_upper = self.create_spinbox(cl, "Max uppercase:", 0, 999, 0,
            "Drop lines with more than N uppercase letters. 0 = no limit.")
        self._chk_min_special = self.create_spinbox(cl, "Min special chars:", 0, 999, 0,
            "Drop lines with fewer than N special characters.")
        self._chk_max_special = self.create_spinbox(cl, "Max special chars:", 0, 999, 0,
            "Drop lines with more than N special characters. 0 = no limit.")
        layout.addWidget(chk_section)

        # ── Modify modules (transform lines) ─────────────────────
        mod_section = CollapsibleSection("Modify Modules (Transform Lines)")
        ml = mod_section.content_layout()
        modifies = [
            ("mod_decode_hex",       "Decode $HEX[]",                     "Convert $HEX[...] encoded strings back to their original text."),
            ("mod_decode_html",      "Decode HTML entities",              "Convert numeric HTML entities (&#xx;) back to characters."),
            ("mod_decode_html_named","Decode HTML named entities",        "Convert named HTML entities (&amp; &lt; etc.) back to characters."),
            ("mod_lowercase",        "Lowercase all",                     "Convert every character to lowercase. Destructive — loses case info."),
            ("mod_titlecase",        "Title case",                        "Capitalize the first letter of each word, lowercase the rest."),
            ("mod_fix_umlauts",      "Fix umlauts",                       "Repair broken umlaut sequences (e.g. \\xc3\\xa4 → ä)."),
            ("mod_mojibake",         "Fix mojibake",                      "Attempt to repair double-encoded or mis-encoded UTF-8 text (ftfy)."),
            ("mod_encoding_fix",     "Auto-fix encoding",                 "Detect and fix character encoding issues automatically (chardet + ftfy)."),
            ("mod_fix_tabs",         "Fix tabs → spaces",                 "Replace tab characters with a single space."),
            ("mod_fix_newlines",     "Fix newlines",                      "Normalize \\r\\n and \\r to \\n; strip trailing whitespace on each line."),
            ("mod_trim",             "Trim whitespace",                   "Strip leading and trailing whitespace from each line."),
            ("mod_replace_non_ascii","Replace non-ASCII → ASCII",         "Replace non-ASCII characters with their closest ASCII equivalent."),
            ("mod_transliterate",    "Transliterate (other scripts → Latin)", "Convert Cyrillic, Greek, CJK, etc. to Latin approximations via unidecode."),
            ("mod_unicode_norm",     "Unicode normalize (NFC)",           "Apply Unicode NFC normalization (precomposed forms: é instead of e + ́)."),
            ("mod_homoglyph_ascii",  "Homoglyph → ASCII",                "Replace Unicode look-alikes (Cyrillic а, fullwidth Ａ) with ASCII equivalents."),
            ("mod_strip_emoji",      "Strip emoji",                       "Remove all emoji characters from lines entirely."),
            ("mod_emoji_text",       "Emoji to text",                     "Convert emoji to their CLDR short names (e.g. 😀 → grinning_face)."),
            ("mod_strip_pos_tags",   "Strip universal POS tags",          "Remove _NOUN, _VERB, etc. tags appended by Google N-gram datasets."),
        ]
        for key, label, tip in modifies:
            self._modifies[key] = self.create_checkbox(ml, label, False, tip)
        layout.addWidget(mod_section)

        # ── Add modules (keep original + variant) ────────────────
        add_section = CollapsibleSection("Add Modules (Keep Original + Add Variant)")
        al = add_section.content_layout()
        adds = [
            ("add_lowercase",          "Add lowercase copy",          "Keep original line and add a lowercased copy."),
            ("add_first_upper",        "Add first-upper variant",     "Keep original and add a variant with the first letter capitalized."),
            ("add_titlecase",          "Add title-case variant",      "Keep original and add a Title Case variant."),
            ("add_no_punct",           "Add without punctuation",     "Keep original and add a variant with all punctuation removed."),
            ("add_split",              "Add split (compound words)",  "Keep original and add individual parts of compound words split by camelCase/separators."),
            ("add_umlaut_variants",    "Add umlaut variants",         "Keep original and add variants with ä→ae, ö→oe, etc. substitutions."),
            ("add_ligature_variants",  "Add Latin ligature variants", "Keep original and add variants expanding Latin ligatures (æ→ae, œ→oe, ß→ss)."),
            ("add_homoglyph_variants", "Add homoglyph variants",     "Keep original and add variants with Unicode look-alikes replaced by ASCII."),
        ]
        for key, label, tip in adds:
            self._adds[key] = self.create_checkbox(al, label, False, tip)
        layout.addWidget(add_section)

        # ── Presets ──────────────────────────────────────────────
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Presets:"))
        for name in self.PRESETS:
            btn = __import__("PyQt6.QtWidgets", fromlist=["QPushButton"]).QPushButton(name)
            btn.setToolTip(f"Apply preset: {name}")
            btn.clicked.connect(lambda checked, n=name: self._apply_preset(n))
            preset_row.addWidget(btn)
        preset_row.addStretch()
        layout.addLayout(preset_row)

    def build_advanced_section(self, layout: QVBoxLayout) -> None:
        self._output_encoding = self.create_combo(
            layout, "Output encoding:", ["utf-8", "latin-1", "cp1252", "ascii"],
            "Character encoding for output. Default UTF-8.",
        )
        self._threads = self.create_spinbox(layout, "Threads (-j):", 0, 64, 0,
            "Number of processing threads. 0 = all CPU cores.")
        self._limit = self.create_spinbox(layout, "Limit (-n):", 0, 999_999_999, 0,
            "Process only the first N lines. 0 = all.")
        self._log_file = self.create_file_browser(
            layout, "Log file (-l):", "Log dropped/modified lines for review.",
            save=True, file_filter="Text Files (*.txt *.log);;All Files (*)",
        )

    def build_output_section(self, layout: QVBoxLayout) -> None:
        self._output_file = self.create_file_browser(
            layout, "Output file (-o):", "Where to write cleaned output.",
            save=True, file_filter="Text Files (*.txt);;All Files (*)",
        )
        self._output_file.setText(str(self._default_output_dir() / "cleaned.txt"))

        # Before / After comparison table for dry run
        self._compare_table = QTableWidget(0, 3)
        self._compare_table.setHorizontalHeaderLabels(["#", "Original", "Cleaned"])
        self._compare_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._compare_table.setMaximumHeight(180)
        self._compare_table.setVisible(False)
        layout.addWidget(self._compare_table)

        btn_row = QHBoxLayout()
        from PyQt6.QtWidgets import QPushButton
        self._dry_run_btn = QPushButton("Dry Run (preview first 100 lines)")
        self._dry_run_btn.setToolTip("Process first 100 lines and show before/after comparison.")
        self._dry_run_btn.clicked.connect(self._on_dry_run)
        btn_row.addWidget(self._dry_run_btn)
        self.send_to_menu(btn_row, [
            "PCFG Trainer", "PRINCE Processor", "Combinator",
            "PCFG Guesser", "StatsGen (PACK)", "Hashcat Command Builder",
        ])
        btn_row.addStretch()
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        import re as _re
        errors: list[str] = []
        inp = self._input_file.text().strip()
        if not inp:
            errors.append("Select an input wordlist file.")
        elif not Path(inp).is_file():
            errors.append(f"Input file not found: {inp}")
        out = self._output_file.text().strip()
        if not out:
            errors.append("Specify an output file path.")
        # Validate regex pattern if enabled
        if self._checks.get("chk_regex") and self._checks["chk_regex"].isChecked():
            pattern = self._chk_regex_val.text().strip()
            if pattern:
                try:
                    _re.compile(pattern)
                except _re.error as e:
                    errors.append(f"Invalid regex pattern: {e}")
        return errors

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def run_tool(self) -> None:
        script = self._find_demeuk()
        if not script:
            self._output_log.append(
                "Error: demeuk.py not found.\n"
                "Expected in: Scripts_to_use/demeuk-master/\n"
                "Configure paths in Settings (⚙ in the toolbar)."
            )
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)
            return

        cmd = self._build_cmd(script)
        self._output_log.append(f"$ {' '.join(cmd)}\n")
        self._runner.run(cmd, cwd=script.parent)

    def _on_dry_run(self) -> None:
        script = self._find_demeuk()
        if not script:
            self._output_log.append(
                "Error: demeuk.py not found.\n"
                "Expected in: Scripts_to_use/demeuk-master/\n"
                "Configure paths in Settings (⚙ in the toolbar)."
            )
            return

        inp = self._input_file.text().strip()
        if not inp:
            self._output_log.append("Error: no input file selected.")
            return

        # Read first 100 original lines for comparison
        self._dry_originals: list[str] = []
        try:
            with open(inp, "r", encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f):
                    if i >= 100:
                        break
                    self._dry_originals.append(line.rstrip("\n\r"))
        except OSError:
            self._dry_originals = []

        self._dry_cleaned: list[str] = []
        self._compare_table.setRowCount(0)
        self._compare_table.setVisible(True)

        cmd = self._build_cmd(script, dry_run=True)
        self._output_log.clear()
        self._output_log.append(f"[Dry Run] $ {' '.join(cmd)}\n")

        # Connect a one-shot collector
        self._runner.output_line.disconnect(self._on_process_output)
        self._runner.finished.disconnect(self._on_process_finished)
        self._runner.output_line.connect(self._on_dry_line)
        self._runner.finished.connect(self._on_dry_finished)
        self._runner.run(cmd, cwd=script.parent)

    def _on_dry_line(self, line: str) -> None:
        self._dry_cleaned.append(line.rstrip("\n\r"))
        self._output_log.append(line)

    def _on_dry_finished(self, exit_code: int) -> None:
        # Reconnect default handlers
        self._runner.output_line.disconnect(self._on_dry_line)
        self._runner.finished.disconnect(self._on_dry_finished)
        self._runner.output_line.connect(self._on_process_output)
        self._runner.finished.connect(self._on_process_finished)

        # Populate comparison table
        max_rows = max(len(self._dry_originals), len(self._dry_cleaned))
        self._compare_table.setRowCount(max_rows)
        for i in range(max_rows):
            self._compare_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            orig = self._dry_originals[i] if i < len(self._dry_originals) else ""
            cleaned = self._dry_cleaned[i] if i < len(self._dry_cleaned) else "(removed)"
            self._compare_table.setItem(i, 1, QTableWidgetItem(orig))
            self._compare_table.setItem(i, 2, QTableWidgetItem(cleaned))

        dropped = len(self._dry_originals) - len(self._dry_cleaned)
        modified = sum(
            1 for i in range(min(len(self._dry_originals), len(self._dry_cleaned)))
            if self._dry_originals[i] != self._dry_cleaned[i]
        )
        self._output_log.append(
            f"\n✓ Dry run complete. {len(self._dry_cleaned)} lines kept, "
            f"{max(0, dropped)} dropped, {modified} modified."
        )

        # Per-reason breakdown of dropped lines
        if dropped > 0:
            cleaned_set = set(self._dry_cleaned)
            dropped_lines = [
                l for l in self._dry_originals if l not in cleaned_set
            ]
            reasons = self._classify_drops(dropped_lines)
            if reasons:
                self._output_log.append("\nDrop reasons:")
                for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
                    self._output_log.append(f"  {reason}: {count}")

        super()._on_process_finished(exit_code)

    def _classify_drops(self, lines: list[str]) -> dict[str, int]:
        """Heuristically classify why lines were dropped based on enabled checks."""
        import re as _re
        reasons: dict[str, int] = {}
        for line in lines:
            matched = False
            if self._checks.get("chk_empty") and self._checks["chk_empty"].isChecked():
                if not line.strip():
                    reasons["Empty line"] = reasons.get("Empty line", 0) + 1
                    continue
            if self._checks.get("chk_min_len") and self._checks["chk_min_len"].isChecked():
                if len(line) < self._chk_min_len_val.value():
                    reasons["Too short"] = reasons.get("Too short", 0) + 1
                    matched = True
            if self._checks.get("chk_max_len") and self._checks["chk_max_len"].isChecked():
                if len(line) > self._chk_max_len_val.value():
                    reasons["Too long"] = reasons.get("Too long", 0) + 1
                    matched = True
            if self._checks.get("chk_control") and self._checks["chk_control"].isChecked():
                if _re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", line):
                    reasons["Control chars"] = reasons.get("Control chars", 0) + 1
                    matched = True
            if self._checks.get("chk_non_ascii") and self._checks["chk_non_ascii"].isChecked():
                if any(ord(c) > 127 for c in line):
                    reasons["Non-ASCII"] = reasons.get("Non-ASCII", 0) + 1
                    matched = True
            if self._checks.get("chk_email") and self._checks["chk_email"].isChecked():
                if "@" in line and "." in line:
                    reasons["Email pattern"] = reasons.get("Email pattern", 0) + 1
                    matched = True
            if self._checks.get("chk_hash") and self._checks["chk_hash"].isChecked():
                if _re.fullmatch(r"[0-9a-fA-F]{32,128}", line.strip()):
                    reasons["Hash pattern"] = reasons.get("Hash pattern", 0) + 1
                    matched = True
            if self._checks.get("chk_regex") and self._checks["chk_regex"].isChecked():
                pat = self._chk_regex_val.text().strip()
                if pat:
                    try:
                        if _re.search(pat, line):
                            reasons["Regex match"] = reasons.get("Regex match", 0) + 1
                            matched = True
                    except _re.error:
                        pass
            if not matched:
                reasons["Other"] = reasons.get("Other", 0) + 1
        return reasons

    def _build_cmd(self, script: Path, dry_run: bool = False) -> list[str]:
        python = self._find_python()
        cmd = [python, str(script)]

        inp = self._input_file.text().strip()
        if inp:
            cmd += ["-i", inp]

        out = self._output_file.text().strip()
        if out and not dry_run:
            cmd += ["-o", out]
            self._output_path = out

        enc_in = self._input_encoding.currentText()
        if enc_in != "Auto":
            cmd += ["--input-encoding", enc_in]

        enc_out = self._output_encoding.currentText()
        if enc_out != "utf-8":
            cmd += ["--output-encoding", enc_out]

        log = self._log_file.text().strip()
        if log:
            cmd += ["-l", log]

        threads = self._threads.value()
        if threads > 0:
            cmd += ["-j", str(threads)]

        limit_val = self._limit.value()
        if dry_run:
            cmd += ["-n", "100"]
        elif limit_val > 0:
            cmd += ["-n", str(limit_val)]

        # Cutting options
        if self._enable_cut.isChecked():
            cmd.append("-c")
            delim = self._delimiter.text()
            if delim and delim != ":":
                cmd += ["-d", delim]
            if self._cut_before.isChecked():
                cmd.append("--cut-before")
            fields = self._cut_fields.text().strip()
            if fields:
                cmd += ["-f", fields]

        # Check modules
        flag_map_checks = {
            "chk_min_len":     "--check-min-length",
            "chk_max_len":     "--check-max-length",
            "chk_case":        "--check-case",
            "chk_control":     "--check-controlchars",
            "chk_email":       "--check-email",
            "chk_hash":        "--check-hash",
            "chk_mac":         "--check-mac",
            "chk_uuid":        "--check-uuid",
            "chk_non_ascii":   "--check-non-ascii",
            "chk_replacement": "--check-replacement-character",
            "chk_starts_with": "--check-starts-with",
            "chk_ends_with":   "--check-ends-with",
            "chk_contains":    "--check-contains",
            "chk_regex":       "--check-regex",
            "chk_empty":       "--check-empty",
        }
        for key, flag in flag_map_checks.items():
            if key in self._checks and self._checks[key].isChecked():
                cmd.append(flag)

        # Value args for checks
        if self._checks.get("chk_min_len") and self._checks["chk_min_len"].isChecked():
            cmd.append(str(self._chk_min_len_val.value()))
        if self._checks.get("chk_max_len") and self._checks["chk_max_len"].isChecked():
            cmd.append(str(self._chk_max_len_val.value()))
        if self._checks.get("chk_starts_with") and self._checks["chk_starts_with"].isChecked():
            v = self._chk_starts_with_val.text().strip()
            if v:
                cmd.append(v)
        if self._checks.get("chk_ends_with") and self._checks["chk_ends_with"].isChecked():
            v = self._chk_ends_with_val.text().strip()
            if v:
                cmd.append(v)
        if self._checks.get("chk_contains") and self._checks["chk_contains"].isChecked():
            v = self._chk_contains_val.text().strip()
            if v:
                cmd.append(v)
        if self._checks.get("chk_regex") and self._checks["chk_regex"].isChecked():
            v = self._chk_regex_val.text().strip()
            if v:
                cmd.append(v)

        # Extra digit/uppercase/special checks
        if self._chk_min_digits.value() > 0:
            cmd += ["--check-min-digits", str(self._chk_min_digits.value())]
        if self._chk_max_digits.value() > 0:
            cmd += ["--check-max-digits", str(self._chk_max_digits.value())]
        if self._chk_min_upper.value() > 0:
            cmd += ["--check-min-upper", str(self._chk_min_upper.value())]
        if self._chk_max_upper.value() > 0:
            cmd += ["--check-max-upper", str(self._chk_max_upper.value())]
        if self._chk_min_special.value() > 0:
            cmd += ["--check-min-special", str(self._chk_min_special.value())]
        if self._chk_max_special.value() > 0:
            cmd += ["--check-max-special", str(self._chk_max_special.value())]

        # Modify modules
        flag_map_mods = {
            "mod_decode_hex":        "--decode-hex",
            "mod_decode_html":       "--decode-html",
            "mod_decode_html_named": "--decode-html-named",
            "mod_lowercase":         "--lowercase",
            "mod_titlecase":         "--titlecase",
            "mod_fix_umlauts":       "--fix-umlauts",
            "mod_mojibake":          "--fix-mojibake",
            "mod_encoding_fix":      "--auto-fix-encoding",
            "mod_fix_tabs":          "--fix-tabs",
            "mod_fix_newlines":      "--fix-newlines",
            "mod_trim":              "--trim",
            "mod_replace_non_ascii": "--replace-non-ascii",
            "mod_transliterate":     "--transliterate",
            "mod_unicode_norm":      "--unicode-normalize",
            "mod_homoglyph_ascii":   "--homoglyph-to-ascii",
            "mod_strip_emoji":       "--strip-emoji",
            "mod_emoji_text":        "--emoji-to-text",
            "mod_strip_pos_tags":    "--strip-pos-tags",
        }
        for key, flag in flag_map_mods.items():
            if key in self._modifies and self._modifies[key].isChecked():
                cmd.append(flag)

        # Add modules
        flag_map_adds = {
            "add_lowercase":          "--add-lowercase",
            "add_first_upper":        "--add-first-upper",
            "add_titlecase":          "--add-titlecase",
            "add_no_punct":           "--add-without-punctuation",
            "add_split":              "--add-split",
            "add_umlaut_variants":    "--add-umlaut-variants",
            "add_ligature_variants":  "--add-ligature-variants",
            "add_homoglyph_variants": "--add-homoglyph-variants",
        }
        for key, flag in flag_map_adds.items():
            if key in self._adds and self._adds[key].isChecked():
                cmd.append(flag)

        return cmd

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------
    def _apply_preset(self, name: str) -> None:
        # Uncheck everything first
        for cb in list(self._checks.values()) + list(self._modifies.values()) + list(self._adds.values()):
            cb.setChecked(False)
        # Enable the preset flags
        keys = self.PRESETS.get(name, [])
        for key in keys:
            for d in (self._checks, self._modifies, self._adds):
                if key in d:
                    d[key].setChecked(True)
        self._output_log.append(f"Applied preset: {name}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _find_demeuk(self) -> Optional[Path]:
        if self._base_dir:
            p = Path(self._base_dir) / "Scripts_to_use" / "demeuk-master" / "demeuk-master" / "bin" / "demeuk.py"
            if p.is_file():
                return p
            # alternate flat layout
            p2 = Path(self._base_dir) / "Scripts_to_use" / "demeuk-master" / "bin" / "demeuk.py"
            if p2.is_file():
                return p2
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
        self._input_file.setText(path)
