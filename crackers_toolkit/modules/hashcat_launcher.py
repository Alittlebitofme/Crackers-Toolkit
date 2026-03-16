"""Module 18: Hashcat Command Builder & Launcher.

Visually construct a hashcat attack command, then launch it in a native
terminal window.  Supports all attack modes: dictionary, mask, combinator,
hybrid.  Receives wordlists, rules, and masks from other tools.

Key design: the GUI does NOT embed a terminal.  It builds the full
command line, displays a live preview, and spawns a *native* OS terminal
so the user has full access to hashcat keyboard controls
(s=status, p=pause, r=resume, q=quit, c=checkpoint).
"""

from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .base_module import BaseModule


# ---------------------------------------------------------------------------
# Searchable combo (hash-mode selector)
# ---------------------------------------------------------------------------
class _SearchableCombo(QComboBox):
    """A QComboBox that is editable + filters items by typed text."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer().setCompletionMode(
            self.completer().CompletionMode.PopupCompletion
        )


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------
class HashcatLauncherModule(BaseModule):
    MODULE_NAME = "Hashcat Command Builder"
    MODULE_DESCRIPTION = (
        "Visually construct a hashcat attack command, then launch it "
        "in a native terminal window.  Supports all attack modes: "
        "dictionary, mask, combinator, hybrid."
    )
    MODULE_CATEGORY = "Attack Launcher"

    _ATTACK_MODES = [
        ("0", "Dictionary", "Straight wordlist attack. Try every word, optionally applying mangling rules."),
        ("1", "Combinator", "Concatenate one word from each of two wordlists."),
        ("3", "Brute-Force / Mask", "Generate candidates from a mask pattern (e.g., ?u?l?l?l?d?d)."),
        ("6", "Hybrid: Wordlist + Mask", "Append mask-generated suffixes to each word in a wordlist."),
        ("7", "Hybrid: Mask + Wordlist", "Prepend mask-generated prefixes to each word in a wordlist."),
        ("9", "Association", "Wordlist attack using per-hash hint words."),
    ]

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._hash_modes: list[dict] = []
        self._load_hash_modes()
        self._m0_rule_rows: list[QLineEdit] = []
        self._m3_charset_rows: list[tuple[int, QLineEdit]] = []  # (num, line_edit)
        super().__init__(parent)
        # This module uses "Launch in Terminal" — hide BaseModule controls
        self._run_btn.setVisible(False)
        self._save_as_run_btn.setVisible(False)
        self._stop_btn.setVisible(False)
        self._progress.setVisible(False)
        self._reset_btn.setVisible(False)
        self._connect_preview_signals()

    def _toggle_container(self, container: QWidget, visible: bool) -> None:
        """Show/hide a container."""
        container.setVisible(visible)

    def _connect_preview_signals(self) -> None:
        """Wire every input widget's change signal to live-update the preview."""
        up = self._update_preview
        # Input section
        self._hash_file.textChanged.connect(up)
        self._single_hash.textChanged.connect(up)
        self._hash_mode_combo.currentIndexChanged.connect(up)
        # Attack mode (already triggers _on_mode_changed which calls _update_preview)
        # Mode 0
        self._m0_wordlist.textChanged.connect(up)
        self._m0_rulefile.textChanged.connect(up)
        self._m0_inline_j.textChanged.connect(up)
        self._m0_inline_k.textChanged.connect(up)
        # Mode 1
        self._m1_left.textChanged.connect(up)
        self._m1_right.textChanged.connect(up)
        self._m1_rule_left.textChanged.connect(up)
        self._m1_rule_right.textChanged.connect(up)
        # Mode 3
        self._m3_mask.textChanged.connect(up)
        self._m3_maskfile.textChanged.connect(up)
        self._m3_cs1.textChanged.connect(up)
        # Dynamic charsets 2-4 connect themselves in _add_charset_row()
        self._m3_increment.stateChanged.connect(up)
        self._m3_inc_min.valueChanged.connect(up)
        self._m3_inc_max.valueChanged.connect(up)
        # Mode 6
        self._m6_wordlist.textChanged.connect(up)
        self._m6_mask.textChanged.connect(up)
        self._m6_increment.stateChanged.connect(up)
        self._m6_inc_min.valueChanged.connect(up)
        self._m6_inc_max.valueChanged.connect(up)
        self._m6_inline_j.textChanged.connect(up)
        self._m6_inline_k.textChanged.connect(up)
        # Mode 7
        self._m7_mask.textChanged.connect(up)
        self._m7_wordlist.textChanged.connect(up)
        self._m7_increment.stateChanged.connect(up)
        self._m7_inc_min.valueChanged.connect(up)
        self._m7_inc_max.valueChanged.connect(up)
        self._m7_inline_j.textChanged.connect(up)
        self._m7_inline_k.textChanged.connect(up)
        # Mode 9
        self._m9_wordlist.textChanged.connect(up)
        # Optimization (in params section)
        self._optimized.stateChanged.connect(up)
        self._slow_candidates.stateChanged.connect(up)
        # _workload connects via _on_workload_changed which calls _update_preview
        # Advanced options
        self._force.stateChanged.connect(up)
        self._outfile.textChanged.connect(up)
        self._outformat.currentIndexChanged.connect(up)
        self._potfile_disable.stateChanged.connect(up)
        self._session.textChanged.connect(up)
        self._status.stateChanged.connect(up)
        self._status_timer.valueChanged.connect(up)

    # ------------------------------------------------------------------
    # Hash mode JSON
    # ------------------------------------------------------------------
    def _load_hash_modes(self) -> None:
        candidates = [
            Path(__file__).resolve().parent.parent / "resources" / "hashcat_modes.json",
        ]
        if self._base_dir:
            candidates.append(
                Path(self._base_dir) / "crackers_toolkit" / "resources" / "hashcat_modes.json"
            )
        for p in candidates:
            if p.is_file():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._hash_modes = data.get("modes", [])
                except (json.JSONDecodeError, OSError):
                    pass
                break

    # ------------------------------------------------------------------
    # Input section
    # ------------------------------------------------------------------
    def build_input_section(self, layout: QVBoxLayout) -> None:
        # --- Session restore ---
        restore_row = QHBoxLayout()
        restore_row.addWidget(QLabel("Restore session:"))
        restore_row.addWidget(self._info_icon(
            "Resume a previously interrupted hashcat session. "
            "'Restore Default' resumes the unnamed default session. "
            "'Restore Named' resumes a specific --session name."
        ))
        self._restore_default_btn = QPushButton("Restore Default Session")
        self._restore_default_btn.setToolTip(
            "Run 'hashcat --restore' to resume the last unnamed session."
        )
        self._restore_default_btn.clicked.connect(self._restore_default_session)
        restore_row.addWidget(self._restore_default_btn)

        self._restore_name = QLineEdit()
        self._restore_name.setPlaceholderText("Session name…")
        restore_row.addWidget(self._restore_name, 1)

        self._restore_named_btn = QPushButton("Restore Named")
        self._restore_named_btn.setToolTip(
            "Run 'hashcat --session <name> --restore' to resume a named session."
        )
        self._restore_named_btn.clicked.connect(self._restore_named_session)
        restore_row.addWidget(self._restore_named_btn)
        layout.addLayout(restore_row)

        # --- Hash config ---
        self._hash_file = self.create_file_browser(
            layout, "Hash file:",
            "File containing the hashes to crack. One hash per line (or hash:salt depending on format).",
            receive_type="hash",
        )
        self._single_hash = self.create_line_edit(
            layout, "Single hash:", "",
            "Paste a single hash directly instead of using a file.",
        )

        # Searchable hash-mode combo
        row = QHBoxLayout()
        lbl = QLabel("Hash mode (-m):")
        row.addWidget(lbl)
        row.addWidget(self._info_icon("Hashcat mode number. E.g. 0 = MD5, 1000 = NTLM."))
        self._hash_mode_combo = _SearchableCombo()
        for m in self._hash_modes:
            self._hash_mode_combo.addItem(f"{m['id']} - {m['name']}")
        self._hash_mode_combo.setCurrentIndex(0)
        row.addWidget(lbl)
        row.addWidget(self._hash_mode_combo, stretch=1)
        layout.addLayout(row)

    # ------------------------------------------------------------------
    # Parameters – attack mode + stacked per-mode panels
    # ------------------------------------------------------------------
    def build_params_section(self, layout: QVBoxLayout) -> None:
        # Attack mode selector
        row = QHBoxLayout()
        lbl = QLabel("Attack mode (-a):")
        self._attack_combo = QComboBox()
        for code, name, tip in self._ATTACK_MODES:
            self._attack_combo.addItem(f"{code} – {name}")
            self._attack_combo.setItemData(
                self._attack_combo.count() - 1, tip, Qt.ItemDataRole.ToolTipRole
            )
        self._attack_combo.currentIndexChanged.connect(self._on_mode_changed)
        row.addWidget(lbl)
        row.addWidget(self._attack_combo, stretch=1)
        layout.addLayout(row)

        # Mode panels container – simple visibility toggling (no QStackedWidget)
        self._mode_panels: list[QWidget] = []

        self._build_mode0_panel()   # Dictionary
        self._build_mode1_panel()   # Combinator
        self._build_mode3_panel()   # Mask
        self._build_mode6_panel()   # Hybrid WL+Mask
        self._build_mode7_panel()   # Hybrid Mask+WL
        self._build_mode9_panel()   # Association

        for panel in self._mode_panels:
            layout.addWidget(panel)

        # Show only the first panel
        for i, panel in enumerate(self._mode_panels):
            panel.setVisible(i == 0)

        # --- Optimization cluster (below mode panels) ---
        opt_label = QLabel("Optimization:")
        opt_label.setStyleSheet("font-weight: bold; margin-top: 6px;")
        layout.addWidget(opt_label)

        self._optimized = self.create_checkbox(
            layout, "-O  Optimized kernels", False,
            "Use optimized GPU kernels. Faster but limits max password length to 32.",
        )
        self._slow_candidates = self.create_checkbox(
            layout, "-S  Slow candidates", False,
            "Enable slow-candidate mode. Useful for slow hash types (e.g. bcrypt). "
            "Generates candidates on the CPU side to reduce GPU idle time.",
        )

        # Workload slider (1-4)
        w_row = QHBoxLayout()
        w_row.addWidget(QLabel("Workload profile (-w):"))
        w_row.addWidget(self._info_icon("1=Low (desktop usable), 2=Default, 3=High (some lag), 4=Nightmare."))
        self._workload = QSlider(Qt.Orientation.Horizontal)
        self._workload.setRange(1, 4)
        self._workload.setValue(2)
        self._workload.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._workload.setTickInterval(1)
        w_row.addWidget(self._workload)
        self._workload_label = QLabel("2")
        self._workload_label.setFixedWidth(16)
        w_row.addWidget(self._workload_label)
        layout.addLayout(w_row)
        self._workload_warning = QLabel(
            "\u26a0 Ensure your GPU / system has sufficient cooling for Nightmare workload!"
        )
        self._workload_warning.setStyleSheet("color: #f38ba8; font-weight: bold;")
        self._workload_warning.setVisible(False)
        layout.addWidget(self._workload_warning)
        self._workload.valueChanged.connect(self._on_workload_changed)

    # --- Per-mode sub-panels ---

    def _build_mode0_panel(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        self._m0_wordlist = self.create_file_browser(
            lay, "Wordlist:",
            "Wordlist file for dictionary attack.",
            file_filter="Wordlists (*.txt *.dict *.lst);;All Files (*)",
            receive_type="wordlist",
        )
        # First rule file row
        self._m0_rulefile = self.create_file_browser(
            lay, "Rule file (-r):",
            "Optional rule file to mangle each word.",
            file_filter="Rule Files (*.rule *.txt);;All Files (*)",
            receive_type="rule",
        )
        # Container for extra stacked rule files
        self._m0_extra_rules_layout = QVBoxLayout()
        self._m0_extra_rules_layout.setContentsMargins(0, 0, 0, 0)
        self._m0_extra_rules_layout.setSpacing(4)
        lay.addLayout(self._m0_extra_rules_layout)

        add_rule_btn = QPushButton("+ Add Rule File")
        add_rule_btn.setToolTip(
            "Stack additional rule files. Hashcat applies rule stacking "
            "(combinatorial product of all rule files)."
        )
        add_rule_btn.clicked.connect(self._add_rule_file_row)
        lay.addWidget(add_rule_btn)

        # Inline rules for dictionary mode (hidden until enabled)
        self._m0_inline_check = QCheckBox("Enable inline rules (-j / -k)")
        self._m0_inline_check.setToolTip("Show inline rule fields for left and right words.")
        lay.addWidget(self._m0_inline_check)
        self._m0_inline_container = QWidget()
        m0_jl = QVBoxLayout(self._m0_inline_container)
        m0_jl.setContentsMargins(0, 0, 0, 0)
        self._m0_inline_j = self.create_line_edit(
            m0_jl, "Left rule (-j):", "",
            "Rule applied to each word from the wordlist. E.g. 'c' to capitalize.",
        )
        self._m0_inline_k = self.create_line_edit(
            m0_jl, "Right rule (-k):", "",
            "Second inline rule applied to each word.",
        )
        self._m0_inline_container.setVisible(False)
        self._m0_inline_check.toggled.connect(lambda c: self._toggle_container(self._m0_inline_container, c))
        self._m0_inline_check.toggled.connect(lambda: self._update_preview())
        lay.addWidget(self._m0_inline_container)

        self._mode_panels.append(w)

    def _add_rule_file_row(self) -> None:
        """Add an extra rule-file browser row to A0 mode."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        le = QLineEdit()
        le.setPlaceholderText("Additional rule file…")
        le.textChanged.connect(lambda: self._update_preview())
        browse = QPushButton("Browse")
        remove = QPushButton("✕")
        remove.setFixedWidth(28)

        def _browse() -> None:
            from PyQt6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getOpenFileName(
                None, "Select Rule File", "",
                "Rule Files (*.rule *.txt);;All Files (*)",
            )
            if path:
                le.setText(path)

        browse.clicked.connect(_browse)
        remove.clicked.connect(lambda: self._remove_rule_file_row(row, le))
        row.addWidget(QLabel("Rule file (-r):"))
        row.addWidget(le, 1)
        row.addWidget(browse)
        row.addWidget(remove)
        self._m0_extra_rules_layout.addLayout(row)
        self._m0_rule_rows.append(le)

    def _remove_rule_file_row(self, layout: QHBoxLayout, le: QLineEdit) -> None:
        """Remove a stacked rule-file row."""
        self._m0_rule_rows.remove(le)
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._m0_extra_rules_layout.removeItem(layout)
        self._update_preview()

    def _build_mode1_panel(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        self._m1_left = self.create_file_browser(
            lay, "Left wordlist:",
            "Left wordlist for combinator attack.",
            file_filter="Wordlists (*.txt *.dict *.lst);;All Files (*)",
            receive_type="wordlist",
        )
        self._m1_right = self.create_file_browser(
            lay, "Right wordlist:",
            "Right wordlist for combinator attack.",
            file_filter="Wordlists (*.txt *.dict *.lst);;All Files (*)",
            receive_type="wordlist",
        )
        # Inline rules (hidden until enabled)
        self._m1_inline_check = QCheckBox("Enable inline rules (-j / -k)")
        self._m1_inline_check.setToolTip("Show inline rule fields for left and right words.")
        lay.addWidget(self._m1_inline_check)
        self._m1_inline_container = QWidget()
        m1_jl = QVBoxLayout(self._m1_inline_container)
        m1_jl.setContentsMargins(0, 0, 0, 0)
        self._m1_rule_left = self.create_line_edit(m1_jl, "Left rule (-j):", "", "Inline rule applied to left words.")
        self._m1_rule_right = self.create_line_edit(m1_jl, "Right rule (-k):", "", "Inline rule applied to right words.")
        self._m1_inline_container.setVisible(False)
        self._m1_inline_check.toggled.connect(lambda c: self._toggle_container(self._m1_inline_container, c))
        self._m1_inline_check.toggled.connect(lambda: self._update_preview())
        lay.addWidget(self._m1_inline_container)
        self._mode_panels.append(w)

    def _build_mode3_panel(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        self._m3_mask = self.create_line_edit(
            lay, "Mask:", "?a?a?a?a?a?a",
            "Mask pattern. Charsets: ?l=lower, ?u=upper, ?d=digit, ?s=special, ?a=all, ?b=binary.",
        )
        self._m3_maskfile = self.create_file_browser(
            lay, "Mask file (.hcmask):",
            "A .hcmask file with one mask per line.",
            file_filter="Mask Files (*.hcmask);;All Files (*)",
            receive_type="mask",
        )
        # First custom charset (always visible)
        self._m3_cs1 = self.create_line_edit(
            lay, "Custom charset 1 (-1):", "",
            "Custom charset for ?1. E.g. ?l?d or abcdef.",
        )
        # Container for dynamically added charsets 2-4
        self._m3_extra_cs_layout = QVBoxLayout()
        self._m3_extra_cs_layout.setContentsMargins(0, 0, 0, 0)
        self._m3_extra_cs_layout.setSpacing(4)
        lay.addLayout(self._m3_extra_cs_layout)

        self._m3_add_cs_btn = QPushButton("+ Add Custom Charset")
        self._m3_add_cs_btn.setToolTip(
            "Add another custom charset definition (-2 through -4). "
            "Hashcat supports up to 4 custom charsets."
        )
        self._m3_add_cs_btn.clicked.connect(self._add_charset_row)
        lay.addWidget(self._m3_add_cs_btn)

        # Increment option (mask-relevant) — min/max hidden until enabled
        self._m3_increment = self.create_checkbox(
            lay, "--increment", False,
            "Try shorter masks first, incrementing up to the full mask length.",
        )
        self._m3_inc_container = QWidget()
        m3_il = QHBoxLayout(self._m3_inc_container)
        m3_il.setContentsMargins(0, 0, 0, 0)
        m3_il.addWidget(QLabel("Increment min:"))
        self._m3_inc_min = QSpinBox()
        self._m3_inc_min.setRange(0, 64)
        self._m3_inc_min.setValue(1)
        m3_il.addWidget(self._m3_inc_min)
        m3_il.addWidget(QLabel("Max:"))
        self._m3_inc_max = QSpinBox()
        self._m3_inc_max.setRange(0, 64)
        self._m3_inc_max.setValue(8)
        m3_il.addWidget(self._m3_inc_max)
        m3_il.addStretch()
        self._m3_inc_container.setVisible(False)
        self._m3_increment.toggled.connect(lambda c: self._toggle_container(self._m3_inc_container, c))
        lay.addWidget(self._m3_inc_container)

        self._mode_panels.append(w)

    def _next_charset_num(self) -> int | None:
        """Return the next available charset number (2-4), or None if all used."""
        used = {num for num, _ in self._m3_charset_rows}
        for n in range(2, 5):
            if n not in used:
                return n
        return None

    def _add_charset_row(self) -> None:
        """Add a removable custom charset row (2-4)."""
        num = self._next_charset_num()
        if num is None:
            return  # all 4 slots used
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(f"Custom charset {num} (-{num}):")
        le = QLineEdit()
        le.setPlaceholderText(f"Charset for ?{num}…")
        le.textChanged.connect(self._update_preview)
        remove = QPushButton("✕")
        remove.setFixedWidth(28)
        remove.setToolTip(f"Remove custom charset {num}")
        remove.clicked.connect(lambda: self._remove_charset_row(num, row, le))
        row.addWidget(lbl)
        row.addWidget(le, 1)
        row.addWidget(remove)
        self._m3_extra_cs_layout.addLayout(row)
        self._m3_charset_rows.append((num, le))
        # Hide button when all 4 are defined
        if self._next_charset_num() is None:
            self._m3_add_cs_btn.setVisible(False)
        self._update_preview()

    def _remove_charset_row(self, num: int, layout: QHBoxLayout, le: QLineEdit) -> None:
        """Remove a dynamic charset row."""
        self._m3_charset_rows = [(n, e) for n, e in self._m3_charset_rows if n != num]
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._m3_extra_cs_layout.removeItem(layout)
        self._m3_add_cs_btn.setVisible(True)
        self._update_preview()

    def _build_mode6_panel(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        self._m6_wordlist = self.create_file_browser(
            lay, "Wordlist:",
            "Wordlist base for hybrid attack.",
            file_filter="Wordlists (*.txt *.dict *.lst);;All Files (*)",
            receive_type="wordlist",
        )
        self._m6_mask = self.create_line_edit(lay, "Mask:", "?d?d?d", "Mask to append after each word.")
        self._m6_increment = self.create_checkbox(
            lay, "--increment", False,
            "Try shorter masks first, incrementing up to the full mask length.",
        )
        self._m6_inc_container = QWidget()
        m6_il = QHBoxLayout(self._m6_inc_container)
        m6_il.setContentsMargins(0, 0, 0, 0)
        m6_il.addWidget(QLabel("Increment min:"))
        self._m6_inc_min = QSpinBox()
        self._m6_inc_min.setRange(0, 64)
        self._m6_inc_min.setValue(1)
        m6_il.addWidget(self._m6_inc_min)
        m6_il.addWidget(QLabel("Max:"))
        self._m6_inc_max = QSpinBox()
        self._m6_inc_max.setRange(0, 64)
        self._m6_inc_max.setValue(8)
        m6_il.addWidget(self._m6_inc_max)
        m6_il.addStretch()
        self._m6_inc_container.setVisible(False)
        self._m6_increment.toggled.connect(lambda c: self._toggle_container(self._m6_inc_container, c))
        lay.addWidget(self._m6_inc_container)
        # Inline rules (hidden until enabled)
        self._m6_inline_check = QCheckBox("Enable inline rules (-j / -k)")
        self._m6_inline_check.setToolTip("Show inline rule fields for left and right words.")
        lay.addWidget(self._m6_inline_check)
        self._m6_inline_container = QWidget()
        m6_jl = QVBoxLayout(self._m6_inline_container)
        m6_jl.setContentsMargins(0, 0, 0, 0)
        self._m6_inline_j = self.create_line_edit(
            m6_jl, "Left rule (-j):", "",
            "Rule applied to each word from the wordlist.",
        )
        self._m6_inline_k = self.create_line_edit(
            m6_jl, "Right rule (-k):", "",
            "Rule applied to each mask-generated candidate.",
        )
        self._m6_inline_container.setVisible(False)
        self._m6_inline_check.toggled.connect(lambda c: self._toggle_container(self._m6_inline_container, c))
        self._m6_inline_check.toggled.connect(lambda: self._update_preview())
        lay.addWidget(self._m6_inline_container)
        self._mode_panels.append(w)

    def _build_mode7_panel(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        self._m7_mask = self.create_line_edit(lay, "Mask:", "?d?d?d", "Mask to prepend before each word.")
        self._m7_wordlist = self.create_file_browser(
            lay, "Wordlist:",
            "Wordlist base for hybrid attack.",
            file_filter="Wordlists (*.txt *.dict *.lst);;All Files (*)",
            receive_type="wordlist",
        )
        self._m7_increment = self.create_checkbox(
            lay, "--increment", False,
            "Try shorter masks first, incrementing up to the full mask length.",
        )
        self._m7_inc_container = QWidget()
        m7_il = QHBoxLayout(self._m7_inc_container)
        m7_il.setContentsMargins(0, 0, 0, 0)
        m7_il.addWidget(QLabel("Increment min:"))
        self._m7_inc_min = QSpinBox()
        self._m7_inc_min.setRange(0, 64)
        self._m7_inc_min.setValue(1)
        m7_il.addWidget(self._m7_inc_min)
        m7_il.addWidget(QLabel("Max:"))
        self._m7_inc_max = QSpinBox()
        self._m7_inc_max.setRange(0, 64)
        self._m7_inc_max.setValue(8)
        m7_il.addWidget(self._m7_inc_max)
        m7_il.addStretch()
        self._m7_inc_container.setVisible(False)
        self._m7_increment.toggled.connect(lambda c: self._toggle_container(self._m7_inc_container, c))
        lay.addWidget(self._m7_inc_container)
        # Inline rules (hidden until enabled)
        self._m7_inline_check = QCheckBox("Enable inline rules (-j / -k)")
        self._m7_inline_check.setToolTip("Show inline rule fields for left and right words.")
        lay.addWidget(self._m7_inline_check)
        self._m7_inline_container = QWidget()
        m7_jl = QVBoxLayout(self._m7_inline_container)
        m7_jl.setContentsMargins(0, 0, 0, 0)
        self._m7_inline_j = self.create_line_edit(
            m7_jl, "Left rule (-j):", "",
            "Rule applied to each mask-generated candidate.",
        )
        self._m7_inline_k = self.create_line_edit(
            m7_jl, "Right rule (-k):", "",
            "Rule applied to each word from the wordlist.",
        )
        self._m7_inline_container.setVisible(False)
        self._m7_inline_check.toggled.connect(lambda c: self._toggle_container(self._m7_inline_container, c))
        self._m7_inline_check.toggled.connect(lambda: self._update_preview())
        lay.addWidget(self._m7_inline_container)
        self._mode_panels.append(w)

    def _build_mode9_panel(self) -> None:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        self._m9_wordlist = self.create_file_browser(
            lay, "Wordlist:",
            "Association wordlist (one hint per hash).",
            file_filter="Wordlists (*.txt *.dict *.lst);;All Files (*)",
            receive_type="wordlist",
        )
        self._mode_panels.append(w)

    def _on_mode_changed(self, idx: int) -> None:
        for i, panel in enumerate(self._mode_panels):
            panel.setVisible(i == idx)
        self._update_preview()

    # ------------------------------------------------------------------
    # Advanced options
    # ------------------------------------------------------------------
    def build_advanced_section(self, layout: QVBoxLayout) -> None:
        self._force = self.create_checkbox(
            layout, "--force", False,
            "Ignore warnings. Use when hashcat complains but you know you want to proceed.",
        )
        self._outfile = self.create_file_browser(
            layout, "Output file (-o):",
            "File to write cracked hash:password pairs to. Leave empty to use the potfile (default).",
            save=True,
        )
        self._outformat = self.create_combo(
            layout, "Output format (--outfile-format):",
            ["1 – hash:plain", "2 – plain", "3 – hex:plain", "5 – hash:plain:hex"],
            "Output line format for cracked hashes.",
        )
        self._potfile_disable = self.create_checkbox(
            layout, "--potfile-disable", False,
            "Don't use the potfile. By default hashcat skips already-cracked hashes.",
        )
        self._session = self.create_line_edit(
            layout, "Session name (--session):", "",
            "Session name. Allows pausing with 'c' key and restoring with --restore.",
        )
        self._status = self.create_checkbox(
            layout, "--status", False,
            "Auto-display status at regular intervals.",
        )
        self._status_timer = self.create_spinbox(
            layout, "Status timer (s):", 1, 3600, 10,
            "Seconds between auto-status updates.",
        )

    # ------------------------------------------------------------------
    # Output section – preview + launch
    # ------------------------------------------------------------------
    def build_output_section(self, layout: QVBoxLayout) -> None:
        layout.addWidget(QLabel("Command preview:"))
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setMaximumHeight(80)
        self._preview.setStyleSheet("font-family: Consolas, 'DejaVu Sans Mono', 'Courier New', monospace;")
        layout.addWidget(self._preview)

        row = QHBoxLayout()
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.setToolTip("Copy the full command to the system clipboard.")
        copy_btn.clicked.connect(self._copy_command)
        row.addWidget(copy_btn)

        self._edit_toggle = QPushButton("Edit Manually")
        self._edit_toggle.setCheckable(True)
        self._edit_toggle.setToolTip("Switch to editable mode to hand-modify the command.")
        self._edit_toggle.toggled.connect(self._toggle_edit)
        row.addWidget(self._edit_toggle)

        refresh_btn = QPushButton("Refresh Preview")
        refresh_btn.setToolTip("Rebuild the command from the current GUI settings.")
        refresh_btn.clicked.connect(self._update_preview)
        row.addWidget(refresh_btn)
        row.addStretch()
        layout.addLayout(row)

        # Launch button
        launch_btn = QPushButton("Launch in Terminal")
        launch_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        launch_btn.setToolTip(
            "Spawn a native OS terminal running the hashcat command. "
            "Use hashcat keyboard controls: s=status, p=pause, r=resume, q=quit."
        )
        launch_btn.clicked.connect(self._launch)
        layout.addWidget(launch_btn)

        # Initial preview
        self._update_preview()

    # ------------------------------------------------------------------
    # Build the command (core logic)
    # ------------------------------------------------------------------
    def _build_command(self) -> str:
        """Construct the full hashcat command string from the GUI state."""
        hc = self._hashcat_path()
        parts: list[str] = [hc]

        # Attack mode
        mode_idx = self._attack_combo.currentIndex()
        mode_code = self._ATTACK_MODES[mode_idx][0]
        parts += ["-a", mode_code]

        # Hash mode
        hm_text = self._hash_mode_combo.currentText()
        hm_id = hm_text.split(" - ")[0].strip() if " - " in hm_text else hm_text.strip()
        parts += ["-m", hm_id]

        # Hash target
        hf = self._hash_file.text().strip()
        sh = self._single_hash.text().strip()
        hash_target = hf if hf else (f'"{sh}"' if sh else "<hash_file>")

        # Optimization flags (from params section)
        if self._force.isChecked():
            parts.append("--force")
        if self._optimized.isChecked():
            parts.append("-O")
        if self._slow_candidates.isChecked():
            parts.append("-S")
        parts += ["-w", str(self._workload.value())]

        outfile = self._outfile.text().strip()
        if outfile:
            parts += ["-o", outfile]

        fmt = self._outformat.currentText().split(" ")[0]
        if fmt != "1":
            parts += ["--outfile-format", fmt]

        if self._potfile_disable.isChecked():
            parts.append("--potfile-disable")

        session = self._session.text().strip()
        if session:
            parts += ["--session", session]

        if self._status.isChecked():
            parts.append("--status")
            parts += ["--status-timer", str(self._status_timer.value())]

        # Per-mode inputs
        if mode_code == "0":
            parts.append(hash_target)
            wl = self._m0_wordlist.text().strip()
            parts.append(wl if wl else "<wordlist>")
            rf = self._m0_rulefile.text().strip()
            if rf:
                parts += ["-r", rf]
            for extra in self._m0_rule_rows:
                ef = extra.text().strip()
                if ef:
                    parts += ["-r", ef]
            j = self._m0_inline_j.text().strip()
            if j:
                parts += ["-j", j]
            k = self._m0_inline_k.text().strip()
            if k:
                parts += ["-k", k]

        elif mode_code == "1":
            jl = self._m1_rule_left.text().strip()
            if jl:
                parts += ["-j", jl]
            kr = self._m1_rule_right.text().strip()
            if kr:
                parts += ["-k", kr]
            parts.append(hash_target)
            parts.append(self._m1_left.text().strip() or "<left_wordlist>")
            parts.append(self._m1_right.text().strip() or "<right_wordlist>")

        elif mode_code == "3":
            if self._m3_increment.isChecked():
                parts.append("--increment")
                parts += ["--increment-min", str(self._m3_inc_min.value())]
                parts += ["--increment-max", str(self._m3_inc_max.value())]
            v1 = self._m3_cs1.text().strip()
            if v1:
                parts += ["-1", v1]
            for num, le in self._m3_charset_rows:
                v = le.text().strip()
                if v:
                    parts += [f"-{num}", v]
            parts.append(hash_target)
            mf = self._m3_maskfile.text().strip()
            mask = self._m3_mask.text().strip()
            parts.append(mf if mf else (mask if mask else "<mask>"))

        elif mode_code == "6":
            if self._m6_increment.isChecked():
                parts.append("--increment")
                parts += ["--increment-min", str(self._m6_inc_min.value())]
                parts += ["--increment-max", str(self._m6_inc_max.value())]
            j6 = self._m6_inline_j.text().strip()
            if j6:
                parts += ["-j", j6]
            k6 = self._m6_inline_k.text().strip()
            if k6:
                parts += ["-k", k6]
            parts.append(hash_target)
            parts.append(self._m6_wordlist.text().strip() or "<wordlist>")
            parts.append(self._m6_mask.text().strip() or "<mask>")

        elif mode_code == "7":
            if self._m7_increment.isChecked():
                parts.append("--increment")
                parts += ["--increment-min", str(self._m7_inc_min.value())]
                parts += ["--increment-max", str(self._m7_inc_max.value())]
            j7 = self._m7_inline_j.text().strip()
            if j7:
                parts += ["-j", j7]
            k7 = self._m7_inline_k.text().strip()
            if k7:
                parts += ["-k", k7]
            parts.append(hash_target)
            parts.append(self._m7_mask.text().strip() or "<mask>")
            parts.append(self._m7_wordlist.text().strip() or "<wordlist>")

        elif mode_code == "9":
            parts.append(hash_target)
            parts.append(self._m9_wordlist.text().strip() or "<wordlist>")

        cmd = " ".join(parts)

        return cmd

    # ------------------------------------------------------------------
    # Preview / clipboard
    # ------------------------------------------------------------------
    def _update_preview(self) -> None:
        if not self._edit_toggle.isChecked():
            self._preview.setPlainText(self._build_command())

    def _copy_command(self) -> None:
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self._preview.toPlainText())

    def _toggle_edit(self, editable: bool) -> None:
        self._preview.setReadOnly(not editable)
        if editable:
            self._edit_toggle.setText("Lock (rebuild)")
            self._preview.setStyleSheet(
                "font-family: Consolas, 'DejaVu Sans Mono', 'Courier New', monospace; "
                "border: 1px solid #cba6f7;"
            )
            self._preview.setFocus()
        else:
            self._edit_toggle.setText("Edit Manually")
            self._preview.setStyleSheet(
                "font-family: Consolas, 'DejaVu Sans Mono', 'Courier New', monospace;"
            )
            self._update_preview()  # rebuild from GUI state

    # ------------------------------------------------------------------
    # Workload warning
    # ------------------------------------------------------------------
    def _on_workload_changed(self, value: int) -> None:
        self._workload_label.setText(str(value))
        self._workload_warning.setVisible(value == 4)
        self._update_preview()

    # ------------------------------------------------------------------
    # Session restore
    # ------------------------------------------------------------------
    def _restore_default_session(self) -> None:
        """Launch 'hashcat --restore' in a terminal."""
        hc = self._hashcat_path()
        cmd = f"{hc} --restore"
        try:
            self._spawn_terminal(cmd)
            self._output_log.append("Restoring default hashcat session…")
        except Exception as exc:
            self._output_log.append(f"ERROR launching restore: {exc}")

    def _restore_named_session(self) -> None:
        """Launch 'hashcat --session <name> --restore' in a terminal."""
        name = self._restore_name.text().strip()
        if not name:
            QMessageBox.warning(self, "No Session Name", "Enter a session name to restore.")
            return
        hc = self._hashcat_path()
        cmd = f"{hc} --session {name} --restore"
        try:
            self._spawn_terminal(cmd)
            self._output_log.append(f"Restoring session '{name}'…")
        except Exception as exc:
            self._output_log.append(f"ERROR launching restore: {exc}")

    # ------------------------------------------------------------------
    # Launch
    # ------------------------------------------------------------------
    def _launch(self) -> None:
        cmd = self._preview.toPlainText().strip()
        if not cmd:
            QMessageBox.warning(self, "Empty Command", "Build a command first.")
            return

        try:
            self._spawn_terminal(cmd)
            self._output_log.append(
                "Hashcat launched in external terminal.\n"
                "Use hashcat keyboard controls: s=status, p=pause, "
                "r=resume, q=quit, c=checkpoint."
            )
        except Exception as exc:
            self._output_log.append(f"ERROR launching terminal: {exc}")

    def _spawn_terminal(self, cmd: str) -> None:
        """Open a native OS terminal running *cmd*."""
        # Determine hashcat's directory so OpenCL/ etc. are found
        hc = self._hashcat_path()
        hc_dir = str(Path(hc).parent) if hc != "hashcat" else None

        if platform.system() == "Windows":
            term = "cmd"
            if self._settings:
                term = self._settings.get("terminal_windows") or "cmd"
            if term == "powershell":
                subprocess.Popen(
                    f'powershell -NoExit -Command "{cmd}"',
                    cwd=hc_dir,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:
                subprocess.Popen(
                    f'cmd /k {cmd}',
                    cwd=hc_dir,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
        else:
            if self._settings:
                prefix = self._settings.get_terminal_command()
            else:
                import shutil
                for t in ("gnome-terminal", "xfce4-terminal", "konsole", "xterm"):
                    if shutil.which(t):
                        prefix = [t, "-e"] if t == "konsole" else [t, "--"]
                        break
                else:
                    prefix = ["xterm", "-e"]
            # Wrap in bash so pipes / complex commands work
            subprocess.Popen(
                prefix + ["bash", "-c", f'{cmd}; read -p "Press Enter to close"'],
                cwd=hc_dir,
            )

    # ------------------------------------------------------------------
    # Hashcat path helper
    # ------------------------------------------------------------------
    def _hashcat_path(self) -> str:
        if self._settings:
            p = self._settings.get("hashcat_path")
            if p:
                return p
        # Guess from base_dir
        if self._base_dir:
            for name in ("hashcat.exe", "hashcat.bin", "hashcat"):
                candidates = list(Path(self._base_dir).glob(f"hashcat-*/{name}"))
                if candidates:
                    return str(candidates[0])
        return "hashcat"

    def validate(self) -> list[str]:
        """Check required fields before launch."""
        errors: list[str] = []
        hf = self._hash_file.text().strip()
        sh = self._single_hash.text().strip()
        if not hf and not sh:
            errors.append("Provide a hash file or single hash.")
        if hf and not Path(hf).is_file():
            errors.append(f"Hash file not found: {hf}")

        idx = self._attack_combo.currentIndex()
        mode = self._ATTACK_MODES[idx][0]
        if mode == "0":
            wl = self._m0_wordlist.text().strip()
            if wl and not Path(wl).is_file():
                errors.append(f"Wordlist not found: {wl}")
        elif mode == "1":
            for label, edit in [("Left wordlist", self._m1_left), ("Right wordlist", self._m1_right)]:
                p = edit.text().strip()
                if p and not Path(p).is_file():
                    errors.append(f"{label} not found: {p}")
        return errors

    # ------------------------------------------------------------------
    # run_tool() – required by BaseModule but we use Launch instead
    # ------------------------------------------------------------------
    def run_tool(self) -> None:
        """Override: Hashcat is launched via the Launch button, not Run."""
        self._output_log.append("Use the 'Launch in Terminal' button to start hashcat.")

    # ------------------------------------------------------------------
    # Data bus integration
    # ------------------------------------------------------------------
    def receive_from(self, path: str) -> None:
        """Auto-populate wordlist/rule/mask/hash input for the current mode."""
        # Detect hash files (from Hash Extractor or manually)
        lp = path.lower()
        if ("hash_extractor" in lp or "extracted_hash" in lp
                or lp.endswith(".hash")):
            self._hash_file.setText(path)
            # Auto-set hash mode from sidecar metadata if present
            meta = Path(path + ".meta")
            if meta.is_file():
                try:
                    import json as _json
                    info = _json.loads(meta.read_text(encoding="utf-8"))
                    mode_id = str(info.get("hashcat_mode", ""))
                    if mode_id:
                        for i in range(self._hash_mode_combo.count()):
                            if self._hash_mode_combo.itemText(i).startswith(mode_id + " "):
                                self._hash_mode_combo.setCurrentIndex(i)
                                break
                except Exception:
                    pass
            self._update_preview()
            return

        idx = self._attack_combo.currentIndex()
        mode = self._ATTACK_MODES[idx][0]
        if mode == "0":
            self._m0_wordlist.setText(path)
        elif mode == "1":
            if not self._m1_left.text().strip():
                self._m1_left.setText(path)
            else:
                self._m1_right.setText(path)
        elif mode == "3":
            self._m3_maskfile.setText(path)
        elif mode == "6":
            self._m6_wordlist.setText(path)
        elif mode == "7":
            self._m7_wordlist.setText(path)
        elif mode == "9":
            self._m9_wordlist.setText(path)
        self._update_preview()
