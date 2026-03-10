"""Module 12: Mask Builder.

Visually build hashcat masks by clicking elements to add them to a
sequence.  Click to reorder, multi-character literal support.  Real-time
keyspace calculation and estimated crack time.  Mask list accumulator
with .hcmask export/import.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from itertools import islice, product

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
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

# Hashcat mask placeholder definitions
PLACEHOLDERS = {
    "?l": ("a-z", 26),
    "?u": ("A-Z", 26),
    "?d": ("0-9", 10),
    "?h": ("0-9 a-f", 16),
    "?H": ("0-9 A-F", 16),
    "?s": ("Special chars", 33),
    "?a": ("All printable ASCII", 95),
    "?b": ("All bytes 0x00-0xFF", 256),
    "?1": ("Custom charset 1", 0),
    "?2": ("Custom charset 2", 0),
    "?3": ("Custom charset 3", 0),
    "?4": ("Custom charset 4", 0),
    "?5": ("Custom charset 5", 0),
    "?6": ("Custom charset 6", 0),
    "?7": ("Custom charset 7", 0),
    "?8": ("Custom charset 8", 0),
}

# Catppuccin-inspired tint per token type
CHIP_COLORS = {
    "?l": "#1e4620",
    "?u": "#46201e",
    "?d": "#1e2046",
    "?h": "#1e3046",
    "?H": "#1e3046",
    "?s": "#46441e",
    "?a": "#2e2e3e",
    "?b": "#3e2e2e",
    "?1": "#1e3646",
    "?2": "#1e3646",
    "?3": "#1e3646",
    "?4": "#1e3646",
    "?5": "#1e3646",
    "?6": "#1e3646",
    "?7": "#1e3646",
    "?8": "#1e3646",
}
LITERAL_COLOR = "#2e3040"
INCOMPLETE_BORDER = "#f38ba8"


_CUSTOM_TOKENS = ("?1", "?2", "?3", "?4", "?5", "?6", "?7", "?8")


def _charset_size(placeholder: str, custom_charsets: dict[str, str]) -> int:
    """Return the effective character count for a placeholder."""
    if placeholder in PLACEHOLDERS:
        base = PLACEHOLDERS[placeholder][1]
        if placeholder in _CUSTOM_TOKENS:
            cs_key = placeholder[1]
            chars = custom_charsets.get(cs_key, "")
            return _count_effective_chars(chars)
        return base
    return 1


def _count_effective_chars(charset_str: str) -> int:
    """Count effective characters from a charset string that may include
    placeholders like ``?l?d``."""
    count = 0
    i = 0
    while i < len(charset_str):
        if i + 1 < len(charset_str) and charset_str[i] == "?":
            token = charset_str[i : i + 2]
            if token in PLACEHOLDERS:
                count += PLACEHOLDERS[token][1]
                i += 2
                continue
        count += 1
        i += 1
    return count


# ── MaskChip ─────────────────────────────────────────────────────


class MaskChip(QFrame):
    """A coloured tag representing one mask element in the sequence.

    *token* is either a placeholder like ``?l`` or a literal string such
    as ``hello``.  Literals can be multi-character — each character
    becomes one fixed mask position.
    """

    selected = pyqtSignal(object)
    removed = pyqtSignal(object)
    changed = pyqtSignal()

    def __init__(self, token: str, parent=None) -> None:
        super().__init__(parent)
        self._token = token
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

        self._apply_style()

    # -- helpers --------------------------------------------------
    def _display(self) -> str:
        if self._token.startswith("?"):
            return self._token
        return f'"{self._token}"' if self._token else '"\u2026"'

    def _bg(self) -> str:
        return CHIP_COLORS.get(self._token, LITERAL_COLOR)

    def _apply_style(self) -> None:
        bg = self._bg()
        bc = INCOMPLETE_BORDER if not self.is_complete() else (
            "#cba6f7" if self._is_selected else "#585b70"
        )
        bw = "2px" if self._is_selected or not self.is_complete() else "1px"
        self.setStyleSheet(
            f"MaskChip {{ background: {bg}; border: {bw} solid {bc}; "
            f"border-radius: 4px; }}"
        )

    # -- public API -----------------------------------------------
    def token(self) -> str:
        return self._token

    def set_token(self, token: str) -> None:
        self._token = token
        self._label.setText(self._display())
        self._update_warn()
        self._apply_style()
        self.changed.emit()

    def is_literal(self) -> bool:
        return not self._token.startswith("?")

    def is_complete(self, charsets: dict[str, str] | None = None) -> bool:
        """Return False if this chip needs user input that is missing."""
        if self.is_literal():
            return bool(self._token)
        if self._token in _CUSTOM_TOKENS:
            cs = charsets or {}
            return bool(cs.get(self._token[1], ""))
        return True

    def set_charsets(self, charsets: dict[str, str]) -> None:
        """Refresh warning badge when charsets change."""
        self._update_warn(charsets)
        self._apply_style()

    def _update_warn(self, charsets: dict[str, str] | None = None) -> None:
        if self.is_complete(charsets):
            self._warn_label.setText("")
            self._warn_label.setFixedWidth(0)
        else:
            self._warn_label.setText("!")
            self._warn_label.setFixedWidth(12)

    def set_selected(self, sel: bool) -> None:
        self._is_selected = sel
        self._apply_style()

    def mask_contribution(self) -> str:
        return self._token

    def keyspace_factor(self, custom_charsets: dict[str, str]) -> int:
        if self._token.startswith("?"):
            return _charset_size(self._token, custom_charsets)
        return 1

    def position_count(self) -> int:
        if self._token.startswith("?"):
            return 1
        return max(len(self._token), 1)

    # -- mouse ----------------------------------------------------
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self)
        super().mousePressEvent(event)


# ── Module ───────────────────────────────────────────────────────


class MaskBuilderModule(BaseModule):
    MODULE_NAME = "Mask Builder"
    MODULE_DESCRIPTION = (
        "Visually build hashcat masks by clicking elements to add them "
        "to a sequence. See real-time keyspace and estimated crack time. "
        "Build and export .hcmask files."
    )
    MODULE_CATEGORY = "Mask Tools"

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        self._chips: list[MaskChip] = []
        self._selected_chip: MaskChip | None = None
        self._mask_list: list[dict] = []
        super().__init__(parent)
        # No run action — hide execution controls
        self._run_btn.setVisible(False)
        self._save_as_run_btn.setVisible(False)
        self._stop_btn.setVisible(False)
        self._progress.setVisible(False)
        self._reset_btn.setVisible(False)

    # ── Sections ─────────────────────────────────────────────────

    def build_input_section(self, layout: QVBoxLayout) -> None:
        ref_grp = QGroupBox("Character Reference")
        rl = QVBoxLayout(ref_grp)
        for ph, (desc, count) in PLACEHOLDERS.items():
            if ph.startswith("?") and ph[1].isdigit():
                continue
            rl.addWidget(QLabel(f"  {ph}  \u2192  {desc} ({count} chars)"))
        layout.addWidget(ref_grp)

    def build_params_section(self, layout: QVBoxLayout) -> None:
        # Charset values stored as plain strings keyed by "1"-"8"
        self._charsets: dict[str, str] = {}

        # ── Palette ──
        pal_grp = QGroupBox("Click to Add")
        pl = QVBoxLayout(pal_grp)

        pal_row1 = QHBoxLayout()
        palette_items = [
            ("?l", "?l  a-z"),
            ("?u", "?u  A-Z"),
            ("?d", "?d  0-9"),
            ("?h", "?h  hex lc"),
            ("?H", "?H  hex UC"),
            ("?s", "?s  Special"),
            ("?a", "?a  All"),
            ("?b", "?b  Bytes"),
        ]
        for token, label in palette_items:
            btn = QPushButton(label)
            btn.setStyleSheet(
                f"QPushButton {{ background: {CHIP_COLORS.get(token, '#45475a')}; "
                f"border: 1px solid #585b70; border-radius: 3px; padding: 4px 8px; "
                f"font-family: monospace; font-weight: bold; }}"
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, t=token: self._add_chip(t))
            pal_row1.addWidget(btn)

        pal_row2 = QHBoxLayout()
        cs_btn = QPushButton("Custom Charset")
        cs_btn.setStyleSheet(
            f"QPushButton {{ background: {CHIP_COLORS.get('?1', '#45475a')}; "
            f"border: 1px solid #585b70; border-radius: 3px; padding: 4px 8px; "
            f"font-family: monospace; font-weight: bold; }}"
        )
        cs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cs_btn.clicked.connect(lambda: self._add_next_custom_chip())
        pal_row2.addWidget(cs_btn)

        lit_btn = QPushButton("Abc  Literal")
        lit_btn.setStyleSheet(
            f"QPushButton {{ background: {LITERAL_COLOR}; "
            f"border: 1px solid #585b70; border-radius: 3px; padding: 4px 8px; "
            f"font-family: monospace; font-weight: bold; }}"
        )
        lit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        lit_btn.clicked.connect(lambda: self._add_chip(""))
        pal_row2.addWidget(lit_btn)
        pal_row2.addStretch()

        pl.addLayout(pal_row1)
        pl.addLayout(pal_row2)
        layout.addWidget(pal_grp)

        # ── Chip lane ──
        lane_grp = QGroupBox("Mask Sequence")
        lane_l = QVBoxLayout(lane_grp)
        lane_hdr = QHBoxLayout()
        add_btn = QPushButton("Add to List")
        add_btn.setToolTip("Append the current mask to the accumulator list.")
        add_btn.clicked.connect(self._add_to_list)
        lane_hdr.addWidget(add_btn)
        lane_hdr.addStretch()
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_chips)
        lane_hdr.addWidget(clear_btn)
        lane_l.addLayout(lane_hdr)

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
        lane_l.addWidget(scroll)
        layout.addWidget(lane_grp)

        # ── Detail panel (shown when a chip is selected) ──
        self._detail_frame = QGroupBox("Selected Element")
        dl = QVBoxLayout(self._detail_frame)
        self._detail_desc = QLabel("")
        self._detail_desc.setWordWrap(True)
        dl.addWidget(self._detail_desc)

        edit_row = QHBoxLayout()
        self._detail_edit = QLineEdit()
        self._detail_edit.setPlaceholderText("Type literal text\u2026")
        self._detail_edit.textChanged.connect(self._on_detail_text_changed)
        edit_row.addWidget(self._detail_edit, stretch=1)

        _arrow_style = (
            "QToolButton { background: #45475a; border: 1px solid #585b70; "
            "border-radius: 3px; }"
        )

        self._move_left_btn = QToolButton()
        self._move_left_btn.setArrowType(Qt.ArrowType.LeftArrow)
        self._move_left_btn.setFixedSize(30, 24)
        self._move_left_btn.setStyleSheet(_arrow_style)
        self._move_left_btn.setToolTip("Move element left")
        self._move_left_btn.clicked.connect(self._move_selected_left)
        edit_row.addWidget(self._move_left_btn)

        self._move_right_btn = QToolButton()
        self._move_right_btn.setArrowType(Qt.ArrowType.RightArrow)
        self._move_right_btn.setFixedSize(30, 24)
        self._move_right_btn.setStyleSheet(_arrow_style)
        self._move_right_btn.setToolTip("Move element right")
        self._move_right_btn.clicked.connect(self._move_selected_right)
        edit_row.addWidget(self._move_right_btn)
        dl.addLayout(edit_row)

        # ── Inline custom charset editor (visible for ?1-?8 chips) ──
        self._charset_edit_row = QHBoxLayout()
        cs_label = QLabel("Charset:")
        self._charset_edit_row.addWidget(cs_label)
        self._charset_edit = QLineEdit()
        self._charset_edit.setPlaceholderText("e.g. aeiou0123 or ?l?d")
        self._charset_edit.textChanged.connect(self._on_charset_text_changed)
        self._charset_edit_row.addWidget(self._charset_edit, stretch=1)
        self._charset_import_btn = QPushButton("Import\u2026")
        self._charset_import_btn.setToolTip(
            "Import unique chars from Element Extractor output."
        )
        self._charset_import_btn.clicked.connect(
            lambda: self._import_charset_from_extractor(self._charset_edit)
        )
        self._charset_edit_row.addWidget(self._charset_import_btn)
        # Wrap in a widget so we can show/hide it
        self._charset_edit_widget = QWidget()
        self._charset_edit_widget.setLayout(self._charset_edit_row)
        self._charset_edit_widget.setVisible(False)
        dl.addWidget(self._charset_edit_widget)

        self._detail_warn = QLabel("")
        self._detail_warn.setStyleSheet("color: #f38ba8; font-size: 11px;")
        dl.addWidget(self._detail_warn)

        self._detail_frame.setVisible(False)
        layout.addWidget(self._detail_frame)

        # ── Live mask display ──
        self._mask_label = QLabel("Mask: (empty)")
        self._mask_label.setStyleSheet(
            "font-family: monospace; font-size: 14px; font-weight: bold; padding: 4px;"
        )
        layout.addWidget(self._mask_label)

        self._desc_label = QLabel("")
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet("padding: 4px;")
        layout.addWidget(self._desc_label)

        # ── Mask preview ──
        prev_grp = QGroupBox("Preview (first 10 candidates)")
        prev_l = QVBoxLayout(prev_grp)
        self._preview_label = QLabel("")
        self._preview_label.setStyleSheet(
            "font-family: monospace; font-size: 12px; padding: 4px;"
        )
        self._preview_label.setWordWrap(False)
        prev_l.addWidget(self._preview_label)
        layout.addWidget(prev_grp)

    def build_output_section(self, layout: QVBoxLayout) -> None:
        btn_row = QHBoxLayout()

        export_btn = QPushButton("Export as .hcmask")
        export_btn.setToolTip("Save the mask list as a .hcmask file.")
        export_btn.clicked.connect(self._export_hcmask)
        btn_row.addWidget(export_btn)

        import_btn = QPushButton("Import .hcmask")
        import_btn.setToolTip("Load an existing .hcmask file.")
        import_btn.clicked.connect(self._import_hcmask)
        btn_row.addWidget(import_btn)

        clear_btn = QPushButton("Clear List")
        clear_btn.clicked.connect(self._clear_list)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._list_table = QTableWidget(0, 4)
        self._list_table.setHorizontalHeaderLabels(
            ["Mask", "Description", "Keyspace", ""]
        )
        self._list_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._list_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._list_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Fixed
        )
        self._list_table.setColumnWidth(3, 160)
        self._list_table.setMaximumHeight(250)
        layout.addWidget(self._list_table)

        self._cumulative_label = QLabel("Cumulative: 0 masks, keyspace 0")
        layout.addWidget(self._cumulative_label)

    def run_tool(self) -> None:
        self._add_to_list()
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress.setVisible(False)

    # ── Chip management ──────────────────────────────────────────

    def _add_chip(self, token: str) -> None:
        chip = MaskChip(token)
        chip.selected.connect(self._on_chip_selected)
        chip.removed.connect(self._on_chip_removed)
        chip.changed.connect(self._update_mask_display)
        chip.set_charsets(self._charsets)
        self._chips.append(chip)
        # Insert before the trailing stretch
        self._lane_layout.insertWidget(self._lane_layout.count() - 1, chip)
        self._select_chip(chip)
        self._update_mask_display()

    def _add_next_custom_chip(self) -> None:
        """Add the next available custom charset (?1-?8)."""
        used = {c.token() for c in self._chips if c.token() in _CUSTOM_TOKENS}
        for n in range(1, 9):
            token = f"?{n}"
            if token not in used:
                self._add_chip(token)
                return
        # All 8 in use — add ?1 as duplicate
        self._add_chip("?1")

    def _on_chip_selected(self, chip: MaskChip) -> None:
        self._select_chip(chip)

    def _on_chip_removed(self, chip: MaskChip) -> None:
        if chip in self._chips:
            self._chips.remove(chip)
            self._lane_layout.removeWidget(chip)
            chip.deleteLater()
            if self._selected_chip is chip:
                self._selected_chip = None
                self._detail_frame.setVisible(False)
            self._update_mask_display()

    def _select_chip(self, chip: MaskChip) -> None:
        if self._selected_chip and self._selected_chip is not chip:
            self._selected_chip.set_selected(False)
        self._selected_chip = chip
        chip.set_selected(True)
        self._show_detail(chip)

    def _show_detail(self, chip: MaskChip) -> None:
        self._detail_frame.setVisible(True)
        token = chip.token()
        if token.startswith("?"):
            desc, count = PLACEHOLDERS.get(token, ("", 0))
            if token in _CUSTOM_TOKENS:
                cs_key = token[1]
                cs_text = self._charsets.get(cs_key, "")
                eff = _count_effective_chars(cs_text) if cs_text else 0
                self._detail_desc.setText(
                    f"<b>{token}</b> \u2014 {desc}<br>"
                    f"Currently {eff} effective characters."
                )
                # Show inline charset editor pre-filled with current value
                self._charset_edit_widget.setVisible(True)
                self._charset_edit.blockSignals(True)
                self._charset_edit.setText(cs_text)
                self._charset_edit.blockSignals(False)
            else:
                self._detail_desc.setText(
                    f"<b>{token}</b> \u2014 {desc} ({count} chars)"
                )
                self._charset_edit_widget.setVisible(False)
            self._detail_edit.setVisible(False)
            self._detail_warn.setText("")
        else:
            n = len(token)
            self._detail_desc.setText(
                f"<b>Literal</b> \u2014 \"{token}\" "
                f"({n} position{'s' if n != 1 else ''})<br>"
                f"Each character becomes one fixed mask position."
            )
            self._detail_edit.setVisible(True)
            self._detail_edit.blockSignals(True)
            self._detail_edit.setText(token)
            self._detail_edit.blockSignals(False)
            self._charset_edit_widget.setVisible(False)
            self._detail_warn.setText("")

    def _on_detail_text_changed(self, text: str) -> None:
        if not self._selected_chip or not self._selected_chip.is_literal():
            return
        if "?" in text:
            self._detail_warn.setText(
                "\u26a0 The '?' character cannot be used in literals \u2014 "
                "it is reserved for mask placeholders."
            )
            text = text.replace("?", "")
            self._detail_edit.blockSignals(True)
            self._detail_edit.setText(text)
            self._detail_edit.blockSignals(False)
        else:
            self._detail_warn.setText("")
        self._selected_chip.set_token(text)
        self._update_mask_display()

    def _on_charset_text_changed(self, text: str) -> None:
        """Store edited charset value and refresh display."""
        if not self._selected_chip:
            return
        token = self._selected_chip.token()
        if token not in _CUSTOM_TOKENS:
            return
        cs_key = token[1]
        self._charsets[cs_key] = text
        # Refresh warning badges on ALL custom chips that use this charset
        for c in self._chips:
            if c.token() in _CUSTOM_TOKENS:
                c.set_charsets(self._charsets)
        eff = _count_effective_chars(text) if text else 0
        desc, _ = PLACEHOLDERS.get(token, ("", 0))
        self._detail_desc.setText(
            f"<b>{token}</b> \u2014 {desc}<br>"
            f"Currently {eff} effective characters."
        )
        self._update_mask_display()

    def _move_selected_left(self) -> None:
        if not self._selected_chip:
            return
        idx = self._chips.index(self._selected_chip)
        if idx <= 0:
            return
        self._chips[idx], self._chips[idx - 1] = self._chips[idx - 1], self._chips[idx]
        self._rebuild_lane()
        self._update_mask_display()

    def _move_selected_right(self) -> None:
        if not self._selected_chip:
            return
        idx = self._chips.index(self._selected_chip)
        if idx >= len(self._chips) - 1:
            return
        self._chips[idx], self._chips[idx + 1] = self._chips[idx + 1], self._chips[idx]
        self._rebuild_lane()
        self._update_mask_display()

    def _rebuild_lane(self) -> None:
        for c in self._chips:
            self._lane_layout.removeWidget(c)
        for i, c in enumerate(self._chips):
            self._lane_layout.insertWidget(i, c)

    def _clear_chips(self) -> None:
        for c in self._chips.copy():
            self._lane_layout.removeWidget(c)
            c.deleteLater()
        self._chips.clear()
        self._selected_chip = None
        self._detail_frame.setVisible(False)
        self._update_mask_display()

    # ── Mask string / keyspace ───────────────────────────────────

    def _get_custom_charsets(self) -> dict[str, str]:
        return dict(self._charsets)

    def _get_mask_string(self) -> str:
        cs = self._get_custom_charsets()
        return "".join(
            c.mask_contribution() for c in self._chips if c.is_complete(cs)
        )

    def _get_keyspace(self) -> int:
        cs = self._get_custom_charsets()
        ks = 1
        for c in self._chips:
            if c.is_complete(cs):
                ks *= max(c.keyspace_factor(cs), 1)
        return ks

    def _update_mask_display(self) -> None:
        if not self._chips:
            self._mask_label.setText("Mask: (empty)")
            self._desc_label.setText("")
            self._preview_label.setText("")
            return

        mask = self._get_mask_string()
        self._mask_label.setText(f"Mask: {mask}")

        cs = self._get_custom_charsets()
        parts: list[str] = []
        pos = 1
        for chip in self._chips:
            if not chip.is_complete(cs):
                continue
            token = chip.token()
            n = chip.position_count()
            if token.startswith("?"):
                desc, count = PLACEHOLDERS.get(token, ("?", 0))
                if token in _CUSTOM_TOKENS:
                    count = _charset_size(token, cs)
                parts.append(f"Position {pos}: {token} ({desc}, {count} chars)")
            else:
                if n == 1:
                    parts.append(f"Position {pos}: literal '{token}'")
                else:
                    parts.append(
                        f"Positions {pos}\u2013{pos + n - 1}: "
                        f"literal \"{token}\" (1 each)"
                    )
            pos += n

        keyspace = self._get_keyspace()
        desc = "\n".join(parts)
        desc += f"\n\nKeyspace: {keyspace:,}"
        self._desc_label.setText(desc)

        # ── Preview first 10 candidates ──
        self._preview_label.setText(self._generate_preview(cs, 10))

    # ── Preview generation ───────────────────────────────────────

    _EXPAND = {
        "?l": "abcdefghijklmnopqrstuvwxyz",
        "?u": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "?d": "0123456789",
        "?h": "0123456789abcdef",
        "?H": "0123456789ABCDEF",
        "?s": " !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~",
        "?a": (
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789"
            " !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
        ),
    }

    def _generate_preview(
        self, cs: dict[str, str], limit: int = 10
    ) -> str:
        """Return the first *limit* candidate strings for the current mask."""
        position_chars: list[str] = []
        for chip in self._chips:
            if not chip.is_complete(cs):
                continue
            token = chip.token()
            if token.startswith("?"):
                if token in _CUSTOM_TOKENS:
                    raw = cs.get(token[1], "")
                    chars = self._expand_charset_string(raw)
                elif token == "?b":
                    # ?b is 256 bytes — skip preview for masks containing ?b
                    return "(preview unavailable for ?b)"
                else:
                    chars = self._EXPAND.get(token, token)
                if not chars:
                    return "(define custom charset to see preview)"
                position_chars.append(chars)
            else:
                # Literal — each character is a fixed position
                for ch in (token if token else " "):
                    position_chars.append(ch)
        if not position_chars:
            return ""
        lines = list(
            islice(
                ("".join(combo) for combo in product(*position_chars)),
                limit,
            )
        )
        return "\n".join(lines)

    def _expand_charset_string(self, raw: str) -> str:
        """Expand a charset definition like ``?l?d`` to its characters."""
        out: list[str] = []
        i = 0
        while i < len(raw):
            if i + 1 < len(raw) and raw[i] == "?":
                token = raw[i : i + 2]
                expanded = self._EXPAND.get(token)
                if expanded:
                    out.append(expanded)
                    i += 2
                    continue
            out.append(raw[i])
            i += 1
        return "".join(out)

    # ── List management ──────────────────────────────────────────

    def _add_to_list(self) -> None:
        mask = self._get_mask_string()
        if not mask:
            return
        keyspace = self._get_keyspace()
        self._mask_list.append({"mask": mask, "keyspace": keyspace})
        self._refresh_table()

    def _refresh_table(self) -> None:
        self._list_table.setRowCount(0)
        total_ks = 0
        for idx, entry in enumerate(self._mask_list):
            row = self._list_table.rowCount()
            self._list_table.insertRow(row)
            self._list_table.setItem(row, 0, QTableWidgetItem(entry["mask"]))
            self._list_table.setItem(row, 1, QTableWidgetItem(""))
            self._list_table.setItem(
                row, 2, QTableWidgetItem(f"{entry['keyspace']:,}")
            )

            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(2, 0, 2, 0)
            al.setSpacing(2)
            _tbl_btn_style = (
                "QPushButton { font-size: 11px; padding: 1px 3px; }"
            )
            for sym, tip, cb in (
                ("Up", "Move up", lambda c, i=idx: self._move_entry(i, -1)),
                ("Dn", "Move down", lambda c, i=idx: self._move_entry(i, 1)),
                ("Edit", "Load into builder", lambda c, i=idx: self._edit_entry(i)),
                ("Del", "Remove", lambda c, i=idx: self._delete_entry(i)),
            ):
                b = QPushButton(sym)
                b.setFixedWidth(32)
                b.setStyleSheet(_tbl_btn_style)
                b.setToolTip(tip)
                b.clicked.connect(cb)
                al.addWidget(b)
            self._list_table.setCellWidget(row, 3, actions)
            total_ks += entry["keyspace"]

        self._cumulative_label.setText(
            f"Cumulative: {len(self._mask_list)} masks, "
            f"keyspace {total_ks:,}"
        )

    def _delete_entry(self, index: int) -> None:
        if 0 <= index < len(self._mask_list):
            self._mask_list.pop(index)
            self._refresh_table()

    def _edit_entry(self, index: int) -> None:
        if 0 <= index < len(self._mask_list):
            self._load_mask_to_builder(self._mask_list[index]["mask"])

    def _move_entry(self, index: int, direction: int) -> None:
        j = index + direction
        if 0 <= j < len(self._mask_list):
            self._mask_list[index], self._mask_list[j] = (
                self._mask_list[j],
                self._mask_list[index],
            )
            self._refresh_table()

    def _load_mask_to_builder(self, mask: str) -> None:
        """Parse a mask string and create chips."""
        self._clear_chips()
        for token in self._tokenize_mask(mask):
            self._add_chip(token)

    @staticmethod
    def _tokenize_mask(mask: str) -> list[str]:
        """Split a mask string into tokens, grouping consecutive literal
        characters into one token."""
        tokens: list[str] = []
        literal_buf = ""
        i = 0
        while i < len(mask):
            if i + 1 < len(mask) and mask[i] == "?":
                candidate = mask[i : i + 2]
                if candidate in PLACEHOLDERS:
                    if literal_buf:
                        tokens.append(literal_buf)
                        literal_buf = ""
                    tokens.append(candidate)
                    i += 2
                    continue
            literal_buf += mask[i]
            i += 1
        if literal_buf:
            tokens.append(literal_buf)
        return tokens

    def _clear_list(self) -> None:
        self._mask_list.clear()
        self._refresh_table()

    # ── Import / Export ──────────────────────────────────────────

    def _export_hcmask(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export .hcmask", str(self._default_output_dir()),
            "Hashcat Mask Files (*.hcmask);;All Files (*)",
        )
        if not path:
            return
        try:
            cs = self._get_custom_charsets()
            with open(path, "w", encoding="utf-8") as f:
                for entry in self._mask_list:
                    cs_parts = [
                        cs.get(n, "")
                        for n in ("1", "2", "3", "4", "5", "6", "7", "8")
                    ]
                    while cs_parts and not cs_parts[-1]:
                        cs_parts.pop()
                    if cs_parts:
                        line = ",".join(cs_parts) + "," + entry["mask"]
                    else:
                        line = entry["mask"]
                    f.write(line + "\n")
            self._output_path = path
            self._output_log.append(
                f"\u2713 Exported {len(self._mask_list)} masks to {path}"
            )
        except OSError as e:
            self._output_log.append(f"\u2717 Export failed: {e}")

    def _import_hcmask(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import .hcmask", "",
            "Hashcat Mask Files (*.hcmask);;All Files (*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(",")
                    mask = parts[-1] if parts else line
                    ks = self._calc_mask_keyspace(mask)
                    self._mask_list.append(
                        {"mask": mask, "keyspace": ks}
                    )
            self._refresh_table()
            self._output_log.append(f"\u2713 Imported masks from {path}")
        except OSError as e:
            self._output_log.append(f"\u2717 Import failed: {e}")

    def _calc_mask_keyspace(self, mask: str) -> int:
        cs = self._get_custom_charsets()
        ks = 1
        i = 0
        while i < len(mask):
            if i + 1 < len(mask) and mask[i] == "?":
                token = mask[i : i + 2]
                ks *= _charset_size(token, cs)
                i += 2
            else:
                i += 1
        return ks

    def _import_charset_from_extractor(self, target_edit: QLineEdit) -> None:
        """Import unique characters from Element Extractor output."""
        from ..app.main_window import MainWindow
        from ..app.tool_registry import TOOLS

        main = self.window()
        if not isinstance(main, MainWindow):
            return
        for mid, widget in main._loaded_modules.items():
            tool = next((t for t in TOOLS if t.module_id == mid), None)
            if tool and tool.name == "Element Extractor":
                path = (
                    widget.get_output_path()
                    if hasattr(widget, "get_output_path")
                    else None
                )
                if path and Path(path).is_file():
                    try:
                        with open(
                            path, "r", encoding="utf-8", errors="replace"
                        ) as f:
                            chars = set()
                            for fline in f:
                                chars.update(fline.strip())
                        unique = "".join(
                            sorted(c for c in chars if c.isprintable())
                        )
                        target_edit.setText(unique)
                        return
                    except OSError:
                        pass
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            "No Output",
            "Element Extractor has not produced output yet.\n"
            "Run Element Extractor first, then try again.",
        )

    def get_output_path(self) -> Optional[str]:
        return self._output_path

    def receive_from(self, path: str) -> None:
        """Receive an .hcmask file from another module."""
        if path and Path(path).is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        parts = line.split(",")
                        mask = parts[-1] if parts else line
                        ks = self._calc_mask_keyspace(mask)
                        self._mask_list.append(
                            {"mask": mask, "keyspace": ks}
                        )
                self._refresh_table()
                self._output_log.append(f"Received masks from {path}")
            except OSError as e:
                self._output_log.append(f"Failed to load masks: {e}")
