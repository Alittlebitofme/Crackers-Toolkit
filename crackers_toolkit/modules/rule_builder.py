"""Module 15: Rule Builder.

Visually construct hashcat mangling rules by clicking functions from a
categorised palette.  Each rule appears as a chip in the chain.  Click
a chip to edit its parameters and see a real-time preview.  Export as
.rule files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .base_module import BaseModule

# Hashcat rule function reference
# (symbol_template, name, category, description, example_input, example_output, param_count)
RULE_FUNCTIONS = [
    # Case rules
    ("l", "Lowercase all", "Case", "Convert entire word to lowercase.", "PassWord", "password", 0),
    ("u", "Uppercase all", "Case", "Convert entire word to uppercase.", "PassWord", "PASSWORD", 0),
    ("c", "Capitalize", "Case", "Capitalize first letter, lowercase the rest.", "passWORD", "Password", 0),
    ("C", "Invert capitalize", "Case", "Lowercase first letter, uppercase the rest.", "passWORD", "pASSWORD", 0),
    ("t", "Toggle all", "Case", "Toggle case of every character.", "PassWord", "pASSwORD", 0),
    ("TN", "Toggle at pos N", "Case", "Toggle case of character at position N.", "password", "pAssword (N=1)", 1),
    # Append / Prepend
    ("$X", "Append char", "Append/Prepend", "Append character X to end of word.", "pass", "pass1 (X=1)", 1),
    ("^X", "Prepend char", "Append/Prepend", "Prepend character X to beginning.", "pass", "1pass (X=1)", 1),
    # Positional
    ("DN", "Delete at N", "Positional", "Delete character at position N.", "password", "pssword (N=1)", 1),
    ("[", "Truncate left", "Positional", "Delete the first character.", "password", "assword", 0),
    ("]", "Truncate right", "Positional", "Delete the last character.", "password", "passwor", 0),
    ("iNX", "Insert at N", "Positional", "Insert character X at position N.", "password", "pa!ssword (N=2,X=!)", 2),
    ("oNX", "Overwrite at N", "Positional", "Overwrite char at position N with X.", "password", "p!ssword (N=1,X=!)", 2),
    ("xNM", "Extract substr", "Positional", "Extract substring starting at N, length M.", "password", "assw (N=1,M=4)", 2),
    ("ONM", "Omit range", "Positional", "Delete M characters starting at position N.", "password", "psword (N=1,M=2)", 2),
    ("'N", "Truncate at N", "Positional", "Truncate word at position N.", "password", "pass (N=4)", 1),
    # Rotation / Reflection
    ("r", "Reverse", "Rotation", "Reverse the word.", "password", "drowssap", 0),
    ("{", "Rotate left", "Rotation", "Rotate word left (first char goes to end).", "password", "asswordp", 0),
    ("}", "Rotate right", "Rotation", "Rotate word right (last char goes to front).", "password", "dpasswor", 0),
    ("f", "Reflect", "Rotation", "Append reversed copy (reflect).", "pass", "passssap", 0),
    ("d", "Duplicate", "Rotation", "Duplicate the entire word.", "pass", "passpass", 0),
    ("pN", "Duplicate N times", "Rotation", "Concatenate word N times.", "pass", "passpasspass (N=2)", 1),
    ("q", "Duplicate chars", "Rotation", "Duplicate every character.", "password", "ppaasssswwoorrdd", 0),
    ("zN", "Dup first N", "Rotation", "Duplicate first character N times.", "password", "pppassword (N=2)", 1),
    ("ZN", "Dup last N", "Rotation", "Duplicate last character N times.", "password", "passworddd (N=2)", 1),
    ("yN", "Dup block front", "Rotation", "Duplicate first N characters.", "password", "papassword (N=2)", 1),
    ("YN", "Dup block back", "Rotation", "Duplicate last N characters.", "password", "passwordrd (N=2)", 1),
    # Swap
    ("k", "Swap front", "Swap", "Swap the first two characters.", "password", "apssword", 0),
    ("K", "Swap back", "Swap", "Swap the last two characters.", "password", "passwodr", 0),
    ("*NM", "Swap @ N,M", "Swap", "Swap characters at positions N and M.", "password", "psasword (N=1,M=3)", 2),
    # Substitution
    ("sXY", "Replace X\u2192Y", "Substitution", "Replace all occurrences of X with Y.", "password", "p@ssword (X=a,Y=@)", 2),
    ("@X", "Purge char", "Substitution", "Remove all occurrences of character X.", "password", "pssword (X=a)", 1),
    # Rejection
    (">N", "Reject < len N", "Rejection", "Reject word if length is less than N.", "pass", "rejected (N=6)", 1),
    ("<N", "Reject > len N", "Rejection", "Reject word if length is greater than N.", "password123", "rejected (N=8)", 1),
    ("!X", "Reject no X", "Rejection", "Reject word if it does not contain char X.", "password", "rejected (X=1)", 1),
    ("/X", "Reject has X", "Rejection", "Reject word if it contains char X.", "password", "rejected (X=a)", 1),
    # Memory
    ("M", "Memorize", "Memory", "Save current word in memory buffer.", "password", "(memorized)", 0),
    ("4", "Append memory", "Memory", "Append memorized word to current.", "pass", "passpassword", 0),
    ("6", "Prepend memory", "Memory", "Prepend memorized word to current.", "pass", "passwordpass", 0),
    ("XNMI", "Extract memory", "Memory", "Insert M chars from memory pos N into current at I.", "pass+wordMem", "pass+Mewordm (N=0,M=2,I=5)", 3),
]

ADVANCED_RULE_FUNCTIONS = [
    # Title case
    ("E", "Title case", "Title Case", "Lower-case all, then capitalize first letter and after spaces.", "p@ssW0rd w0rld", "P@ssw0rd W0rld", 0),
    ("eX", "Title w/sep", "Title Case", "Title-case using custom separator X instead of space.", "p@ss-w0rd", "P@ss-W0rd (X=-)", 1),
    # Bitwise / ASCII
    ("+N", "ASCII incr", "Bitwise/ASCII", "Increment character at position N by 1 ASCII value.", "password", "pbtssword (N=1)", 1),
    ("-N", "ASCII decr", "Bitwise/ASCII", "Decrement character at position N by 1 ASCII value.", "password", "p`ssword (N=1)", 1),
    (".N", "Replace N+1", "Bitwise/ASCII", "Replace character at N with the character at N+1.", "password", "psssword (N=1)", 1),
    (",N", "Replace N\u22121", "Bitwise/ASCII", "Replace character at N with the character at N\u22121.", "password", "ppssword (N=1)", 1),
    ("LN", "Bitwise left", "Bitwise/ASCII", "Bitwise shift left character at position N.", "p@ssW0rd", "p\u0080ssW0rd (N=1)", 1),
    ("RN", "Bitwise right", "Bitwise/ASCII", "Bitwise shift right character at position N.", "p@ssW0rd", "p sW0rd (N=1)", 1),
    # Advanced Rejection
    ("_N", "Reject \u2260 len N", "Adv. Rejection", "Reject word if length is not equal to N.", "pass", "rejected (N=6)", 1),
    ("(X", "Reject \u2260 first X", "Adv. Rejection", "Reject word if it does not start with char X.", "password", "rejected (X=a)", 1),
    (")X", "Reject \u2260 last X", "Adv. Rejection", "Reject word if it does not end with char X.", "password", "rejected (X=a)", 1),
    ("=NX", "Reject \u2260 at N", "Adv. Rejection", "Reject word if character at position N is not X.", "password", "rejected (N=1,X=b)", 2),
    ("%NX", "Reject < N of X", "Adv. Rejection", "Reject word if char X appears less than N times.", "password", "rejected (N=2,X=s)", 2),
    ("Q", "Reject mem match", "Adv. Rejection", "Reject word if it matches the memorized word.", "password", "rejected", 0),
    # Utility
    (":", "Nothing", "Utility", "Do nothing (passthrough). Useful in multi-rule stacking.", "password", "password", 0),
]

# Category colours for chips
CATEGORY_COLORS = {
    "Case": "#1e2046",
    "Append/Prepend": "#1e4620",
    "Positional": "#46441e",
    "Rotation": "#2e2046",
    "Swap": "#1e3040",
    "Substitution": "#46301e",
    "Rejection": "#46201e",
    "Memory": "#1e3646",
    "Title Case": "#1e2046",
    "Bitwise/ASCII": "#2e3040",
    "Adv. Rejection": "#46201e",
    "Utility": "#2e3040",
}
DEFAULT_CAT_COLOR = "#2e3040"
INCOMPLETE_BORDER = "#f38ba8"


# ── RuleChip ─────────────────────────────────────────────────────


class RuleChip(QFrame):
    """A coloured tag representing one rule function in the chain."""

    selected = pyqtSignal(object)
    removed = pyqtSignal(object)
    changed = pyqtSignal()

    def __init__(self, func_def: tuple, parent=None) -> None:
        super().__init__(parent)
        self._func = func_def
        self._params: list[str] = [""] * func_def[6]
        self._is_selected = False

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(30)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 4, 2)
        layout.setSpacing(4)

        self._warn_label = QLabel("")
        self._warn_label.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #f38ba8; "
            "background: transparent; border: none; padding: 0;"
        )
        self._warn_label.setFixedWidth(0)
        layout.addWidget(self._warn_label)

        self._label = QLabel(self._display())
        self._label.setStyleSheet(
            "font-family: monospace; font-weight: bold; font-size: 12px; "
            "background: transparent; border: none;"
        )
        layout.addWidget(self._label)

        rm = QPushButton("\u00d7")
        rm.setFixedSize(18, 18)
        rm.setStyleSheet(
            "border: none; background: transparent; color: #f38ba8; "
            "font-weight: bold; font-size: 13px; padding: 0;"
        )
        rm.setCursor(Qt.CursorShape.PointingHandCursor)
        rm.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(rm)

        self._update_warn()
        self._apply_style()

    def _display(self) -> str:
        return self.get_rule_string()

    def _cat_color(self) -> str:
        return CATEGORY_COLORS.get(self._func[2], DEFAULT_CAT_COLOR)

    def _apply_style(self) -> None:
        bg = self._cat_color()
        bc = INCOMPLETE_BORDER if not self.is_complete() else (
            "#cba6f7" if self._is_selected else "#585b70"
        )
        bw = "2px" if self._is_selected or not self.is_complete() else "1px"
        self.setStyleSheet(
            f"RuleChip {{ background: {bg}; border: {bw} solid {bc}; "
            f"border-radius: 4px; }}"
        )

    # -- public API -----------------------------------------------
    def func(self) -> tuple:
        return self._func

    def set_selected(self, sel: bool) -> None:
        self._is_selected = sel
        self._apply_style()

    def is_complete(self) -> bool:
        """Return False if any required parameter is still empty."""
        if self._func[6] == 0:
            return True
        return all(p for p in self._params)

    def _update_warn(self) -> None:
        if self.is_complete():
            self._warn_label.setText("")
            self._warn_label.setFixedWidth(0)
        else:
            self._warn_label.setText("!")
            self._warn_label.setFixedWidth(12)

    def set_param(self, index: int, value: str) -> None:
        if 0 <= index < len(self._params):
            self._params[index] = value
            self._label.setText(self._display())
            self._update_warn()
            self._apply_style()
            self.changed.emit()

    def get_params(self) -> list[str]:
        return list(self._params)

    def get_rule_string(self) -> str:
        template = self._func[0]
        if self._func[6] == 0:
            return template
        parts = list(template)
        param_idx = 0
        result: list[str] = []
        for ch in parts:
            if ch in ("N", "X", "Y", "M", "I") and param_idx < len(self._params):
                val = self._params[param_idx]
                result.append(val if val else "0")
                param_idx += 1
            else:
                result.append(ch)
        return "".join(result)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self)
        super().mousePressEvent(event)


# ── Module ───────────────────────────────────────────────────────


class RuleBuilderModule(BaseModule):
    MODULE_NAME = "Rule Builder"
    MODULE_DESCRIPTION = (
        "Visually construct hashcat mangling rules. Click rule functions "
        "from the palette to build a chain. See real-time preview and "
        "description. Export as .rule files."
    )
    MODULE_CATEGORY = "Rule Tools"

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        self._chips: list[RuleChip] = []
        self._selected_chip: RuleChip | None = None
        self._rule_list: list[dict] = []
        super().__init__(parent)
        # No run action — hide execution controls
        self._run_btn.setVisible(False)
        self._save_as_run_btn.setVisible(False)
        self._stop_btn.setVisible(False)
        self._progress.setVisible(False)
        self._reset_btn.setVisible(False)

    # ── Sections ─────────────────────────────────────────────────

    def build_input_section(self, layout: QVBoxLayout) -> None:
        pal_grp = QGroupBox("Rule Functions \u2014 Click to Add")
        pl = QVBoxLayout(pal_grp)

        adv_cats = {f[2] for f in ADVANCED_RULE_FUNCTIONS}
        all_funcs = RULE_FUNCTIONS + ADVANCED_RULE_FUNCTIONS

        # Group functions by category
        cats: dict[str, list[tuple]] = {}
        for func in all_funcs:
            cats.setdefault(func[2], []).append(func)

        self._adv_rule_rows: list[QWidget] = []

        for cat_name, funcs in cats.items():
            is_adv = cat_name in adv_cats
            row_w = QWidget()
            cat_row = QHBoxLayout(row_w)
            cat_row.setContentsMargins(0, 0, 0, 0)
            cat_lbl = QLabel(f"<b>{cat_name}:</b>")
            cat_lbl.setFixedWidth(110)
            cat_row.addWidget(cat_lbl)

            color = CATEGORY_COLORS.get(cat_name, DEFAULT_CAT_COLOR)
            for func in funcs:
                btn = QPushButton(f"{func[0]}  {func[1]}")
                btn.setToolTip(
                    f"{func[3]}\nExample: '{func[4]}' \u2192 '{func[5]}'"
                )
                btn.setStyleSheet(
                    f"QPushButton {{ background: {color}; "
                    f"border: 1px solid #585b70; border-radius: 3px; "
                    f"padding: 3px 6px; font-size: 11px; "
                    f"font-family: monospace; }}"
                )
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(
                    lambda checked, f=func: self._add_chip(f)
                )
                cat_row.addWidget(btn)
            cat_row.addStretch()
            pl.addWidget(row_w)
            if is_adv:
                row_w.setVisible(False)
                self._adv_rule_rows.append(row_w)

        adv_cb = QCheckBox("Show Advanced Rules")
        adv_cb.toggled.connect(self._toggle_advanced_rules)
        pl.addWidget(adv_cb)

        layout.addWidget(pal_grp)

    def build_params_section(self, layout: QVBoxLayout) -> None:
        # ── Chip lane ──
        chain_grp = QGroupBox("Rule Chain")
        cl = QVBoxLayout(chain_grp)
        hdr = QHBoxLayout()
        add_btn = QPushButton("Add to List")
        add_btn.setToolTip("Append the current rule chain as a single rule line.")
        add_btn.clicked.connect(self._add_to_list)
        hdr.addWidget(add_btn)
        hdr.addStretch()
        clear_btn = QPushButton("Clear Chain")
        clear_btn.clicked.connect(self._clear_chain)
        hdr.addWidget(clear_btn)
        cl.addLayout(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedHeight(50)
        self._lane_widget = QWidget()
        self._lane_layout = QHBoxLayout(self._lane_widget)
        self._lane_layout.setContentsMargins(4, 4, 4, 4)
        self._lane_layout.setSpacing(6)
        self._lane_layout.addStretch()
        scroll.setWidget(self._lane_widget)
        cl.addWidget(scroll)
        layout.addWidget(chain_grp)

        # ── Detail panel ──
        self._detail_frame = QGroupBox("Selected Rule")
        dl = QVBoxLayout(self._detail_frame)
        self._detail_desc = QLabel("")
        self._detail_desc.setWordWrap(True)
        dl.addWidget(self._detail_desc)

        param_row = QHBoxLayout()
        self._param_widgets: list[tuple[QLabel, QLineEdit]] = []
        for i in range(3):
            lbl = QLabel("")
            lbl.setVisible(False)
            le = QLineEdit()
            le.setFixedWidth(40)
            le.setMaxLength(1)
            le.setVisible(False)
            le.textChanged.connect(
                lambda text, idx=i: self._on_param_changed(idx, text)
            )
            param_row.addWidget(lbl)
            param_row.addWidget(le)
            self._param_widgets.append((lbl, le))

        _arrow_style = (
            "QToolButton { background: #45475a; border: 1px solid #585b70; "
            "border-radius: 3px; }"
        )

        self._move_left_btn = QToolButton()
        self._move_left_btn.setArrowType(Qt.ArrowType.LeftArrow)
        self._move_left_btn.setFixedSize(30, 24)
        self._move_left_btn.setStyleSheet(_arrow_style)
        self._move_left_btn.setToolTip("Move rule left in chain")
        self._move_left_btn.clicked.connect(self._move_selected_left)
        param_row.addWidget(self._move_left_btn)

        self._move_right_btn = QToolButton()
        self._move_right_btn.setArrowType(Qt.ArrowType.RightArrow)
        self._move_right_btn.setFixedSize(30, 24)
        self._move_right_btn.setStyleSheet(_arrow_style)
        self._move_right_btn.setToolTip("Move rule right in chain")
        self._move_right_btn.clicked.connect(self._move_selected_right)
        param_row.addWidget(self._move_right_btn)
        param_row.addStretch()
        dl.addLayout(param_row)

        self._detail_frame.setVisible(False)
        layout.addWidget(self._detail_frame)

        # ── Live display ──
        self._rule_string_label = QLabel("Rule: (empty)")
        self._rule_string_label.setStyleSheet(
            "font-family: monospace; font-size: 14px; font-weight: bold; "
            "padding: 4px;"
        )
        layout.addWidget(self._rule_string_label)

        self._desc_text = QLabel("")
        self._desc_text.setWordWrap(True)
        self._desc_text.setStyleSheet("padding: 4px;")
        layout.addWidget(self._desc_text)

        # ── Preview ──
        preview_grp = QGroupBox("Real-Time Preview")
        pvl = QVBoxLayout(preview_grp)
        pr = QHBoxLayout()
        pr.addWidget(QLabel("Sample word:"))
        pr.addWidget(
            self._info_icon("Enter a word to see the chain applied in real-time.")
        )
        self._sample_word = QLineEdit("Password")
        self._sample_word.textChanged.connect(self._update_preview)
        pr.addWidget(self._sample_word, stretch=1)
        pvl.addLayout(pr)

        self._preview_result = QLabel("")
        self._preview_result.setStyleSheet(
            "font-family: monospace; font-size: 14px; padding: 4px;"
        )
        pvl.addWidget(self._preview_result)
        layout.addWidget(preview_grp)

    def build_output_section(self, layout: QVBoxLayout) -> None:
        btn_row = QHBoxLayout()

        export_btn = QPushButton("Export as .rule")
        export_btn.setToolTip("Save the rule list as a hashcat .rule file.")
        export_btn.clicked.connect(self._export_rule)
        btn_row.addWidget(export_btn)

        import_btn = QPushButton("Import .rule")
        import_btn.setToolTip("Load an existing .rule file.")
        import_btn.clicked.connect(self._import_rule)
        btn_row.addWidget(import_btn)

        clear_btn = QPushButton("Clear List")
        clear_btn.clicked.connect(self._clear_rule_list)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._rule_table = QTableWidget(0, 3)
        self._rule_table.setHorizontalHeaderLabels(
            ["Rule (hashcat notation)", "Description", ""]
        )
        self._rule_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._rule_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Fixed
        )
        self._rule_table.setColumnWidth(2, 160)
        self._rule_table.setMaximumHeight(200)
        layout.addWidget(self._rule_table)

        self._net_effect_label = QLabel("")
        self._net_effect_label.setWordWrap(True)
        self._net_effect_label.setStyleSheet(
            "font-family: monospace; padding: 2px; color: #a6e3a1;"
        )
        layout.addWidget(self._net_effect_label)

    def run_tool(self) -> None:
        self._add_to_list()
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress.setVisible(False)

    # ── Chip management ──────────────────────────────────────────

    def _add_chip(self, func: tuple) -> None:
        chip = RuleChip(func)
        chip.selected.connect(self._on_chip_selected)
        chip.removed.connect(self._on_chip_removed)
        chip.changed.connect(self._update_preview)
        self._chips.append(chip)
        self._lane_layout.insertWidget(self._lane_layout.count() - 1, chip)
        self._select_chip(chip)
        self._update_preview()

    def _on_chip_selected(self, chip: RuleChip) -> None:
        self._select_chip(chip)

    def _on_chip_removed(self, chip: RuleChip) -> None:
        if chip in self._chips:
            self._chips.remove(chip)
            self._lane_layout.removeWidget(chip)
            chip.deleteLater()
            if self._selected_chip is chip:
                self._selected_chip = None
                self._detail_frame.setVisible(False)
            self._update_preview()

    def _select_chip(self, chip: RuleChip) -> None:
        if self._selected_chip and self._selected_chip is not chip:
            self._selected_chip.set_selected(False)
        self._selected_chip = chip
        chip.set_selected(True)
        self._show_detail(chip)

    def _show_detail(self, chip: RuleChip) -> None:
        func = chip.func()
        template, name, cat, desc, ex_in, ex_out, param_count = func

        self._detail_desc.setText(
            f"<b>{template}</b> \u2014 {name}<br>"
            f"{desc}<br>"
            f"Example: '{ex_in}' \u2192 '{ex_out}'"
        )

        # Extract meaningful param labels from the template
        param_labels = self._param_labels(template)
        params = chip.get_params()

        for i, (lbl, le) in enumerate(self._param_widgets):
            if i < param_count:
                lbl.setText(param_labels[i] + ":" if i < len(param_labels) else "?:")
                lbl.setVisible(True)
                le.setVisible(True)
                le.blockSignals(True)
                le.setText(params[i])
                le.blockSignals(False)
            else:
                lbl.setVisible(False)
                le.setVisible(False)

        self._detail_frame.setVisible(True)

    @staticmethod
    def _param_labels(template: str) -> list[str]:
        """Extract human-readable parameter labels from a rule template."""
        labels: list[str] = []
        for ch in template[1:]:  # skip command char
            if ch == "N":
                labels.append("N")
            elif ch == "X":
                labels.append("X")
            elif ch == "Y":
                labels.append("Y")
            elif ch == "M":
                labels.append("M")
            elif ch == "I":
                labels.append("I")
        return labels

    def _on_param_changed(self, index: int, text: str) -> None:
        if self._selected_chip:
            self._selected_chip.set_param(index, text)
            self._update_preview()

    def _move_selected_left(self) -> None:
        if not self._selected_chip:
            return
        idx = self._chips.index(self._selected_chip)
        if idx <= 0:
            return
        self._chips[idx], self._chips[idx - 1] = (
            self._chips[idx - 1],
            self._chips[idx],
        )
        self._rebuild_lane()
        self._update_preview()

    def _move_selected_right(self) -> None:
        if not self._selected_chip:
            return
        idx = self._chips.index(self._selected_chip)
        if idx >= len(self._chips) - 1:
            return
        self._chips[idx], self._chips[idx + 1] = (
            self._chips[idx + 1],
            self._chips[idx],
        )
        self._rebuild_lane()
        self._update_preview()

    def _rebuild_lane(self) -> None:
        for c in self._chips:
            self._lane_layout.removeWidget(c)
        for i, c in enumerate(self._chips):
            self._lane_layout.insertWidget(i, c)

    def _clear_chain(self) -> None:
        for c in self._chips.copy():
            self._lane_layout.removeWidget(c)
            c.deleteLater()
        self._chips.clear()
        self._selected_chip = None
        self._detail_frame.setVisible(False)
        self._update_preview()

    def _toggle_advanced_rules(self, checked: bool) -> None:
        for w in self._adv_rule_rows:
            w.setVisible(checked)

    # ── Preview / description ────────────────────────────────────

    def _get_rule_string(self) -> str:
        return " ".join(
            chip.get_rule_string() for chip in self._chips if chip.is_complete()
        )

    def _update_preview(self) -> None:
        rule_str = self._get_rule_string()
        self._rule_string_label.setText(
            f"Rule: {rule_str}" if rule_str else "Rule: (empty)"
        )

        descs: list[str] = []
        for i, chip in enumerate(self._chips, 1):
            if chip.is_complete():
                descs.append(f"{i}. {chip.func()[3]}")
        self._desc_text.setText("\n".join(descs) if descs else "")

        word = self._sample_word.text()
        result = self._apply_rules_locally(word)
        self._preview_result.setText(
            f"'{word}' \u2192 '{result}'" if word else ""
        )

    def _apply_rules_locally(self, word: str) -> str:
        """Simplified local rule application for preview."""
        memory = ""
        for chip in self._chips:
            if not chip.is_complete():
                continue
            rule = chip.get_rule_string()
            if not rule:
                continue
            cmd = rule[0]
            if cmd == "l":
                word = word.lower()
            elif cmd == "u":
                word = word.upper()
            elif cmd == "c":
                word = word.capitalize()
            elif cmd == "C":
                word = word[0].lower() + word[1:].upper() if word else word
            elif cmd == "t":
                word = word.swapcase()
            elif cmd == "T" and len(rule) > 1:
                n = int(rule[1]) if rule[1].isdigit() else 0
                if n < len(word):
                    word = word[:n] + word[n].swapcase() + word[n + 1:]
            elif cmd == "$" and len(rule) > 1:
                word += rule[1]
            elif cmd == "^" and len(rule) > 1:
                word = rule[1] + word
            elif cmd == "D" and len(rule) > 1:
                n = int(rule[1]) if rule[1].isdigit() else 0
                if n < len(word):
                    word = word[:n] + word[n + 1:]
            elif cmd == "r":
                word = word[::-1]
            elif cmd == "{":
                word = word[1:] + word[0] if word else word
            elif cmd == "}":
                word = word[-1] + word[:-1] if word else word
            elif cmd == "f":
                word = word + word[::-1]
            elif cmd == "d":
                word = word + word
            elif cmd == "s" and len(rule) >= 3:
                word = word.replace(rule[1], rule[2])
            elif cmd == "@" and len(rule) > 1:
                word = word.replace(rule[1], "")
            elif cmd == "i" and len(rule) >= 3:
                n = int(rule[1]) if rule[1].isdigit() else 0
                if n <= len(word):
                    word = word[:n] + rule[2] + word[n:]
            elif cmd == "o" and len(rule) >= 3:
                n = int(rule[1]) if rule[1].isdigit() else 0
                if n < len(word):
                    word = word[:n] + rule[2] + word[n + 1:]
            elif cmd == "x" and len(rule) >= 3:
                n = int(rule[1]) if rule[1].isdigit() else 0
                m = int(rule[2]) if rule[2].isdigit() else 0
                word = word[n : n + m]
            elif cmd == "'" and len(rule) > 1:
                n = int(rule[1]) if rule[1].isdigit() else 0
                word = word[:n]
            elif cmd == "p" and len(rule) > 1:
                n = int(rule[1]) if rule[1].isdigit() else 0
                word = word * (n + 1)
            elif cmd == "M":
                memory = word
            elif cmd == "4":
                word = word + memory
            elif cmd == "6":
                word = memory + word
            elif cmd == "X" and len(rule) >= 4:
                n = int(rule[1]) if rule[1].isdigit() else 0
                m = int(rule[2]) if rule[2].isdigit() else 0
                ii = int(rule[3]) if rule[3].isdigit() else 0
                excerpt = memory[n : n + m]
                if ii <= len(word):
                    word = word[:ii] + excerpt + word[ii:]
            # -- New standard rules --
            elif cmd == "[":
                word = word[1:] if word else word
            elif cmd == "]":
                word = word[:-1] if word else word
            elif cmd == "O" and len(rule) >= 3:
                n = int(rule[1]) if rule[1].isdigit() else 0
                m = int(rule[2]) if rule[2].isdigit() else 0
                word = word[:n] + word[n + m:]
            elif cmd == "q":
                word = "".join(c * 2 for c in word)
            elif cmd == "z" and len(rule) > 1:
                n = int(rule[1]) if rule[1].isdigit() else 0
                if word:
                    word = word[0] * n + word
            elif cmd == "Z" and len(rule) > 1:
                n = int(rule[1]) if rule[1].isdigit() else 0
                if word:
                    word = word + word[-1] * n
            elif cmd == "y" and len(rule) > 1:
                n = int(rule[1]) if rule[1].isdigit() else 0
                word = word[:n] + word
            elif cmd == "Y" and len(rule) > 1:
                n = int(rule[1]) if rule[1].isdigit() else 0
                if n <= len(word):
                    word = word + word[-n:]
            elif cmd == "k":
                if len(word) >= 2:
                    word = word[1] + word[0] + word[2:]
            elif cmd == "K":
                if len(word) >= 2:
                    word = word[:-2] + word[-1] + word[-2]
            elif cmd == "*" and len(rule) >= 3:
                n = int(rule[1]) if rule[1].isdigit() else 0
                m = int(rule[2]) if rule[2].isdigit() else 0
                if n < len(word) and m < len(word):
                    lst = list(word)
                    lst[n], lst[m] = lst[m], lst[n]
                    word = "".join(lst)
            # -- Advanced rules --
            elif cmd == "E":
                word = " ".join(w.capitalize() for w in word.lower().split(" "))
            elif cmd == "e" and len(rule) > 1:
                sep = rule[1]
                word = sep.join(w.capitalize() for w in word.lower().split(sep))
            elif cmd == "+" and len(rule) > 1:
                n = int(rule[1]) if rule[1].isdigit() else 0
                if n < len(word):
                    word = word[:n] + chr((ord(word[n]) + 1) & 0xFF) + word[n + 1:]
            elif cmd == "-" and len(rule) > 1:
                n = int(rule[1]) if rule[1].isdigit() else 0
                if n < len(word):
                    word = word[:n] + chr((ord(word[n]) - 1) & 0xFF) + word[n + 1:]
            elif cmd == "." and len(rule) > 1:
                n = int(rule[1]) if rule[1].isdigit() else 0
                if n < len(word) - 1:
                    word = word[:n] + word[n + 1] + word[n + 1:]
            elif cmd == "," and len(rule) > 1:
                n = int(rule[1]) if rule[1].isdigit() else 0
                if 0 < n < len(word):
                    word = word[:n] + word[n - 1] + word[n + 1:]
            elif cmd == "L" and len(rule) > 1:
                n = int(rule[1]) if rule[1].isdigit() else 0
                if n < len(word):
                    word = word[:n] + chr((ord(word[n]) << 1) & 0xFF) + word[n + 1:]
            elif cmd == "R" and len(rule) > 1:
                n = int(rule[1]) if rule[1].isdigit() else 0
                if n < len(word):
                    word = word[:n] + chr(ord(word[n]) >> 1) + word[n + 1:]
        return word

    # ── Rule list management ─────────────────────────────────────

    def _add_to_list(self) -> None:
        rule_str = self._get_rule_string()
        if not rule_str:
            return
        descs = [chip.func()[3] for chip in self._chips if chip.is_complete()]
        self._rule_list.append({"rule": rule_str, "desc": "; ".join(descs)})
        self._refresh_rule_table()

    def _refresh_rule_table(self) -> None:
        self._rule_table.setRowCount(0)
        for idx, entry in enumerate(self._rule_list):
            row = self._rule_table.rowCount()
            self._rule_table.insertRow(row)
            self._rule_table.setItem(row, 0, QTableWidgetItem(entry["rule"]))
            self._rule_table.setItem(row, 1, QTableWidgetItem(entry["desc"]))

            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(2, 0, 2, 0)
            al.setSpacing(2)
            _tbl_btn_style = (
                "QPushButton { font-size: 11px; padding: 1px 3px; }"
            )
            for sym, tip, cb in (
                ("Up", "Move up", lambda c, i=idx: self._move_rule_entry(i, -1)),
                ("Dn", "Move down", lambda c, i=idx: self._move_rule_entry(i, 1)),
                ("Edit", "Load into chain", lambda c, i=idx: self._edit_rule_entry(i)),
                ("Del", "Remove", lambda c, i=idx: self._delete_rule_entry(i)),
            ):
                b = QPushButton(sym)
                b.setFixedWidth(32)
                b.setStyleSheet(_tbl_btn_style)
                b.setToolTip(tip)
                b.clicked.connect(cb)
                al.addWidget(b)
            self._rule_table.setCellWidget(row, 2, actions)

        self._update_net_effect()

    def _delete_rule_entry(self, index: int) -> None:
        if 0 <= index < len(self._rule_list):
            self._rule_list.pop(index)
            self._refresh_rule_table()

    def _move_rule_entry(self, index: int, direction: int) -> None:
        j = index + direction
        if 0 <= j < len(self._rule_list):
            self._rule_list[index], self._rule_list[j] = (
                self._rule_list[j],
                self._rule_list[index],
            )
            self._refresh_rule_table()

    def _edit_rule_entry(self, index: int) -> None:
        if 0 <= index < len(self._rule_list):
            self._load_rule_to_chain(self._rule_list[index]["rule"])

    def _load_rule_to_chain(self, rule_str: str) -> None:
        """Parse a rule string and recreate chips in the chain."""
        self._clear_chain()
        for token in rule_str.split():
            if not token:
                continue
            func = self._match_rule_func(token)
            if func:
                chip = RuleChip(func)
                # Set params: chars after the command char
                for i, ch in enumerate(token[1:]):
                    chip.set_param(i, ch)
                chip.selected.connect(self._on_chip_selected)
                chip.removed.connect(self._on_chip_removed)
                chip.changed.connect(self._update_preview)
                self._chips.append(chip)
                self._lane_layout.insertWidget(
                    self._lane_layout.count() - 1, chip
                )
        self._update_preview()

    @staticmethod
    def _match_rule_func(token: str) -> tuple | None:
        """Find the RULE_FUNCTIONS entry matching a rule token."""
        cmd = token[0]
        param_len = len(token) - 1
        _all = RULE_FUNCTIONS + ADVANCED_RULE_FUNCTIONS
        for func in _all:
            if func[0][0] == cmd and func[6] == param_len:
                return func
        # Fallback: match by first char only
        for func in _all:
            if func[0][0] == cmd:
                return func
        return None

    def _update_net_effect(self) -> None:
        word = self._sample_word.text() or "password"
        if not self._rule_list:
            self._net_effect_label.setText("")
            return
        previews: list[str] = []
        for entry in self._rule_list[:8]:
            result = self._apply_single_rule_locally(word, entry["rule"])
            previews.append(f"  {entry['rule']}  \u2192  {result}")
        text = (
            f"Net effect on '{word}' ({len(self._rule_list)} rules):\n"
            + "\n".join(previews)
        )
        if len(self._rule_list) > 8:
            text += f"\n  \u2026 and {len(self._rule_list) - 8} more"
        self._net_effect_label.setText(text)

    def _apply_single_rule_locally(self, word: str, rule_str: str) -> str:
        """Apply a full rule string (space-separated commands) to a word."""
        memory = ""
        for part in rule_str.split():
            if not part:
                continue
            cmd = part[0]
            if cmd == "l":
                word = word.lower()
            elif cmd == "u":
                word = word.upper()
            elif cmd == "c":
                word = word.capitalize()
            elif cmd == "C":
                word = word[0].lower() + word[1:].upper() if word else word
            elif cmd == "t":
                word = word.swapcase()
            elif cmd == "T" and len(part) > 1:
                n = int(part[1]) if part[1].isdigit() else 0
                if n < len(word):
                    word = word[:n] + word[n].swapcase() + word[n + 1:]
            elif cmd == "$" and len(part) > 1:
                word += part[1]
            elif cmd == "^" and len(part) > 1:
                word = part[1] + word
            elif cmd == "D" and len(part) > 1:
                n = int(part[1]) if part[1].isdigit() else 0
                if n < len(word):
                    word = word[:n] + word[n + 1:]
            elif cmd == "r":
                word = word[::-1]
            elif cmd == "{":
                word = word[1:] + word[0] if word else word
            elif cmd == "}":
                word = word[-1] + word[:-1] if word else word
            elif cmd == "f":
                word = word + word[::-1]
            elif cmd == "d":
                word = word + word
            elif cmd == "s" and len(part) >= 3:
                word = word.replace(part[1], part[2])
            elif cmd == "@" and len(part) > 1:
                word = word.replace(part[1], "")
            elif cmd == "i" and len(part) >= 3:
                n = int(part[1]) if part[1].isdigit() else 0
                if n <= len(word):
                    word = word[:n] + part[2] + word[n:]
            elif cmd == "o" and len(part) >= 3:
                n = int(part[1]) if part[1].isdigit() else 0
                if n < len(word):
                    word = word[:n] + part[2] + word[n + 1:]
            elif cmd == "x" and len(part) >= 3:
                n = int(part[1]) if part[1].isdigit() else 0
                m = int(part[2]) if part[2].isdigit() else 0
                word = word[n : n + m]
            elif cmd == "'" and len(part) > 1:
                n = int(part[1]) if part[1].isdigit() else 0
                word = word[:n]
            elif cmd == "p" and len(part) > 1:
                n = int(part[1]) if part[1].isdigit() else 0
                word = word * (n + 1)
            elif cmd == "M":
                memory = word
            elif cmd == "4":
                word = word + memory
            elif cmd == "6":
                word = memory + word
            elif cmd == "X" and len(part) >= 4:
                n = int(part[1]) if part[1].isdigit() else 0
                m = int(part[2]) if part[2].isdigit() else 0
                ii = int(part[3]) if part[3].isdigit() else 0
                excerpt = memory[n : n + m]
                if ii <= len(word):
                    word = word[:ii] + excerpt + word[ii:]
            # -- New standard rules --
            elif cmd == "[":
                word = word[1:] if word else word
            elif cmd == "]":
                word = word[:-1] if word else word
            elif cmd == "O" and len(part) >= 3:
                n = int(part[1]) if part[1].isdigit() else 0
                m = int(part[2]) if part[2].isdigit() else 0
                word = word[:n] + word[n + m:]
            elif cmd == "q":
                word = "".join(c * 2 for c in word)
            elif cmd == "z" and len(part) > 1:
                n = int(part[1]) if part[1].isdigit() else 0
                if word:
                    word = word[0] * n + word
            elif cmd == "Z" and len(part) > 1:
                n = int(part[1]) if part[1].isdigit() else 0
                if word:
                    word = word + word[-1] * n
            elif cmd == "y" and len(part) > 1:
                n = int(part[1]) if part[1].isdigit() else 0
                word = word[:n] + word
            elif cmd == "Y" and len(part) > 1:
                n = int(part[1]) if part[1].isdigit() else 0
                if n <= len(word):
                    word = word + word[-n:]
            elif cmd == "k":
                if len(word) >= 2:
                    word = word[1] + word[0] + word[2:]
            elif cmd == "K":
                if len(word) >= 2:
                    word = word[:-2] + word[-1] + word[-2]
            elif cmd == "*" and len(part) >= 3:
                n = int(part[1]) if part[1].isdigit() else 0
                m = int(part[2]) if part[2].isdigit() else 0
                if n < len(word) and m < len(word):
                    lst = list(word)
                    lst[n], lst[m] = lst[m], lst[n]
                    word = "".join(lst)
            # -- Advanced rules --
            elif cmd == "E":
                word = " ".join(w.capitalize() for w in word.lower().split(" "))
            elif cmd == "e" and len(part) > 1:
                sep = part[1]
                word = sep.join(w.capitalize() for w in word.lower().split(sep))
            elif cmd == "+" and len(part) > 1:
                n = int(part[1]) if part[1].isdigit() else 0
                if n < len(word):
                    word = word[:n] + chr((ord(word[n]) + 1) & 0xFF) + word[n + 1:]
            elif cmd == "-" and len(part) > 1:
                n = int(part[1]) if part[1].isdigit() else 0
                if n < len(word):
                    word = word[:n] + chr((ord(word[n]) - 1) & 0xFF) + word[n + 1:]
            elif cmd == "." and len(part) > 1:
                n = int(part[1]) if part[1].isdigit() else 0
                if n < len(word) - 1:
                    word = word[:n] + word[n + 1] + word[n + 1:]
            elif cmd == "," and len(part) > 1:
                n = int(part[1]) if part[1].isdigit() else 0
                if 0 < n < len(word):
                    word = word[:n] + word[n - 1] + word[n + 1:]
            elif cmd == "L" and len(part) > 1:
                n = int(part[1]) if part[1].isdigit() else 0
                if n < len(word):
                    word = word[:n] + chr((ord(word[n]) << 1) & 0xFF) + word[n + 1:]
            elif cmd == "R" and len(part) > 1:
                n = int(part[1]) if part[1].isdigit() else 0
                if n < len(word):
                    word = word[:n] + chr(ord(word[n]) >> 1) + word[n + 1:]
        return word

    def _clear_rule_list(self) -> None:
        self._rule_list.clear()
        self._refresh_rule_table()

    # ── Import / Export ──────────────────────────────────────────

    def _export_rule(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export .rule", str(self._default_output_dir()),
            "Hashcat Rule Files (*.rule);;All Files (*)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                for entry in self._rule_list:
                    f.write(entry["rule"] + "\n")
            self._output_path = path
            self._output_log.append(
                f"\u2713 Exported {len(self._rule_list)} rules to {path}"
            )
        except OSError as e:
            self._output_log.append(f"\u2717 Export failed: {e}")

    def _import_rule(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import .rule", "",
            "Hashcat Rule Files (*.rule);;All Files (*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.rstrip("\n\r")
                    if line and not line.startswith("#"):
                        self._rule_list.append(
                            {"rule": line, "desc": "(imported)"}
                        )
            self._refresh_rule_table()
            self._output_log.append(f"\u2713 Imported rules from {path}")
        except OSError as e:
            self._output_log.append(f"\u2717 Import failed: {e}")

    def get_output_path(self) -> Optional[str]:
        return self._output_path
