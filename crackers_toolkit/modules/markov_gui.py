"""Module 20: Markov Chain / .hcstat2 GUI.

Load, visualize, and train hashcat Markov chain statistics (.hcstat2
files) for smarter brute-force candidate ordering.  Also configure
``--markov-hcstat2`` and ``--markov-threshold`` for the Hashcat
Command Builder.
"""

from __future__ import annotations

import array
import lzma
import struct
import threading
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .base_module import BaseModule

# =====================================================================
# .hcstat2 binary format constants
# =====================================================================

_HCSTAT2_VERSION = 0x6863737461740002          # "hcstat\x00\x02"
_CHARSIZ = 256
_PW_MAX = 256
_ROOT_CNT = _PW_MAX * _CHARSIZ                 # 65,536
_MARKOV_CNT = _PW_MAX * _CHARSIZ * _CHARSIZ    # 16,777,216
_HEADER_SZ = 16                                 # version (8) + zero (8)
_RAW_SIZE = _HEADER_SZ + _ROOT_CNT * 8 + _MARKOV_CNT * 8   # 134,742,032

# LZMA2 property byte used by hashcat (dict_size = 64 MB)
_LZMA2_PROPS = 0x1C
_LZMA2_DICT = (2 | (_LZMA2_PROPS & 1)) << (_LZMA2_PROPS // 2 + 11)  # 67,108,864


# =====================================================================
# .hcstat2 parser / writer
# =====================================================================

class HcStat2:
    """Read, write, and train hashcat .hcstat2 Markov chain files.

    The decompressed format (134 MB) is:
        u64  version        (big-endian)
        u64  zero           (big-endian)
        u64  root[256][256] (big-endian)  -- root character counts
        u64  markov[256][256][256] (BE)   -- transition counts
    """

    def __init__(self) -> None:
        self.root: array.array = array.array("Q", bytes(_ROOT_CNT * 8))
        self._raw: bytes = b""  # keep decompressed blob for on-demand markov access

    # ----- Loading -----
    def load(self, path: str | Path) -> None:
        compressed = Path(path).read_bytes()
        dec = lzma.LZMADecompressor(
            format=lzma.FORMAT_RAW,
            filters=[{"id": lzma.FILTER_LZMA2, "dict_size": _LZMA2_DICT}],
        )
        raw = dec.decompress(compressed)
        if len(raw) != _RAW_SIZE:
            raise ValueError(
                f"Unexpected decompressed size: {len(raw)} (expected {_RAW_SIZE})"
            )
        ver = struct.unpack_from(">Q", raw, 0)[0]
        if ver != _HCSTAT2_VERSION:
            raise ValueError(f"Bad hcstat2 version: 0x{ver:016x}")
        zer = struct.unpack_from(">Q", raw, 8)[0]
        if zer != 0:
            raise ValueError(f"Bad hcstat2 reserved field: {zer}")

        self.root = array.array("Q")
        self.root.frombytes(raw[_HEADER_SZ : _HEADER_SZ + _ROOT_CNT * 8])
        if __import__("sys").byteorder == "little":
            self.root.byteswap()
        self._raw = raw

    # ----- On-demand markov access -----
    def get_root_stats(self, position: int) -> list[tuple[int, int]]:
        """Return sorted [(count, char_code), ...] for root at *position*."""
        base = position * _CHARSIZ
        pairs = [(self.root[base + c], c) for c in range(_CHARSIZ)]
        pairs.sort(reverse=True)
        return pairs

    def get_transition_stats(
        self, position: int, prev_char: int
    ) -> list[tuple[int, int]]:
        """Return sorted [(count, char_code), ...] for markov at pos+prev."""
        if not self._raw:
            return []
        offset = _HEADER_SZ + _ROOT_CNT * 8
        idx = (position * _CHARSIZ * _CHARSIZ + prev_char * _CHARSIZ) * 8
        start = offset + idx
        chunk = self._raw[start : start + _CHARSIZ * 8]
        buf = array.array("Q")
        buf.frombytes(chunk)
        if __import__("sys").byteorder == "little":
            buf.byteswap()
        pairs = [(buf[c], c) for c in range(_CHARSIZ)]
        pairs.sort(reverse=True)
        return pairs

    def max_useful_position(self) -> int:
        """Return the highest position with non-zero root data."""
        for pos in range(_PW_MAX - 1, -1, -1):
            base = pos * _CHARSIZ
            if any(self.root[base + c] for c in range(_CHARSIZ)):
                return pos
        return 0

    # ----- Training -----
    def train(
        self,
        path: str | Path,
        min_len: int = 1,
        max_len: int = 256,
        *,
        progress_cb=None,
    ) -> int:
        """Train from a password file.  Returns total passwords processed."""
        self.root = array.array("Q", bytes(_ROOT_CNT * 8))
        markov = array.array("Q", bytes(_MARKOV_CNT * 8))

        count = 0
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                pw = line.rstrip("\n\r")
                plen = len(pw)
                if plen < min_len or plen > max_len:
                    continue
                count += 1
                if progress_cb and count % 500_000 == 0:
                    progress_cb(count)
                for i, ch in enumerate(pw):
                    c = ord(ch) & 0xFF
                    if i >= _PW_MAX:
                        break
                    self.root[i * _CHARSIZ + c] += 1
                    if i > 0:
                        prev = ord(pw[i - 1]) & 0xFF
                        markov[i * _CHARSIZ * _CHARSIZ + prev * _CHARSIZ + c] += 1

        # Serialize to raw bytes (big-endian)
        root_be = array.array("Q", self.root)
        markov_be = array.array("Q", markov)
        if __import__("sys").byteorder == "little":
            root_be.byteswap()
            markov_be.byteswap()
        header = struct.pack(">QQ", _HCSTAT2_VERSION, 0)
        self._raw = header + root_be.tobytes() + markov_be.tobytes()
        return count

    # ----- Saving -----
    def save(self, path: str | Path) -> None:
        if not self._raw or len(self._raw) != _RAW_SIZE:
            raise ValueError("No data to save. Load or train first.")
        compressed = lzma.compress(
            self._raw,
            format=lzma.FORMAT_RAW,
            filters=[
                {"id": lzma.FILTER_LZMA2, "dict_size": _LZMA2_DICT, "preset": 6}
            ],
        )
        Path(path).write_bytes(compressed)


# =====================================================================
# Colour helper for frequency heatmap cells
# =====================================================================

def _freq_color(val: int, max_val: int) -> QColor:
    """Map *val* in [0, max_val] to a blue-to-red heat colour."""
    if max_val == 0:
        return QColor(49, 50, 68)  # Catppuccin base
    ratio = min(val / max_val, 1.0)
    if ratio < 0.5:
        # dark-blue → cyan
        t = ratio * 2
        r = int(30 * (1 - t))
        g = int(30 + 180 * t)
        b = int(180 + 75 * t)
    else:
        # cyan → yellow → red
        t = (ratio - 0.5) * 2
        r = int(30 + 225 * t)
        g = int(210 - 130 * t)
        b = int(255 - 255 * t)
    return QColor(r, g, b)


# =====================================================================
# Module class
# =====================================================================

class MarkovChainModule(BaseModule):
    MODULE_NAME = "Markov Chain GUI"
    MODULE_DESCRIPTION = (
        "Load, visualize, and train hashcat Markov chain statistics "
        "(.hcstat2 files).  Configure Markov parameters for the Hashcat "
        "Command Builder."
    )
    MODULE_CATEGORY = "Utilities"

    _train_done = pyqtSignal(dict)

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._stat: Optional[HcStat2] = None
        self._output_path: Optional[str] = None
        super().__init__(parent)
        self._train_done.connect(self._on_train_done)
        # Pre-fill default hcstat2 if found
        default = self._find_default_hcstat2()
        if default:
            self._hcstat_file.setText(str(default))

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    def _get_base(self) -> Path:
        if self._base_dir:
            return Path(self._base_dir)
        return Path(__file__).resolve().parent.parent.parent

    def _find_default_hcstat2(self) -> Path | None:
        p = self._get_base() / "hashcat-7.1.2" / "hashcat.hcstat2"
        return p if p.is_file() else None

    # ------------------------------------------------------------------
    # UI building
    # ------------------------------------------------------------------
    def build_input_section(self, layout: QVBoxLayout) -> None:
        # Mode selector
        mode_row = QHBoxLayout()
        self._mode_analyze = QRadioButton("Analyze .hcstat2")
        self._mode_train = QRadioButton("Train new .hcstat2")
        self._mode_analyze.setChecked(True)
        self._mode_analyze.toggled.connect(self._on_mode_changed)
        mode_row.addWidget(self._mode_analyze)
        mode_row.addWidget(self._mode_train)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # Analyze: hcstat2 file browser
        self._analyze_container = QWidget()
        a_lay = QVBoxLayout(self._analyze_container)
        a_lay.setContentsMargins(0, 0, 0, 0)
        self._hcstat_file = self.create_file_browser(
            a_lay,
            ".hcstat2 file:",
            "Select a hashcat Markov statistics file (.hcstat2).",
            file_filter="hcstat2 Files (*.hcstat2);;All Files (*)",
        )
        layout.addWidget(self._analyze_container)

        # Train: password list file browser + output path
        self._train_container = QWidget()
        t_lay = QVBoxLayout(self._train_container)
        t_lay.setContentsMargins(0, 0, 0, 0)
        self._pw_list_file = self.create_file_browser(
            t_lay,
            "Password list:",
            "Plain-text password file (one password per line) to train Markov statistics from.",
            file_filter="Text Files (*.txt);;Wordlist (*.dict *.lst);;All Files (*)",
        )
        self._train_output = self.create_file_browser(
            t_lay,
            "Output .hcstat2:",
            "Where to save the trained .hcstat2 file.",
            save=True,
            file_filter="hcstat2 Files (*.hcstat2);;All Files (*)",
        )
        self._train_container.setVisible(False)
        layout.addWidget(self._train_container)

    def build_params_section(self, layout: QVBoxLayout) -> None:
        # --- Analyze params ---
        self._analyze_params = QWidget()
        ap_lay = QVBoxLayout(self._analyze_params)
        ap_lay.setContentsMargins(0, 0, 0, 0)

        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("Position:"))
        pos_row.addWidget(self._info_icon(
            "Character position in the password (0-based). "
            "Position 0 = first character, 1 = second, etc."
        ))
        self._pos_spin = QSpinBox()
        self._pos_spin.setRange(0, 255)
        self._pos_spin.setValue(0)
        self._pos_spin.valueChanged.connect(self._refresh_analysis)
        pos_row.addWidget(self._pos_spin)
        pos_row.addStretch()
        ap_lay.addLayout(pos_row)

        prev_row = QHBoxLayout()
        prev_row.addWidget(QLabel("Previous char (transitions):"))
        prev_row.addWidget(self._info_icon(
            "When viewing transition probabilities, this is the preceding "
            "character. E.g. if 'a' → 's', set previous char to 'a'."
        ))
        self._prev_combo = QComboBox()
        self._prev_combo.setEditable(False)
        self._prev_combo.setMaxVisibleItems(20)
        # Populate with printable ASCII by default
        items = []
        for c in range(32, 127):
            items.append(f"'{chr(c)}'  ({c})")
        items.append("NUL (0)")
        self._prev_char_map: dict[int, int] = {}
        for i, c in enumerate(range(32, 127)):
            self._prev_char_map[i] = c
        self._prev_char_map[len(items) - 1] = 0
        self._prev_combo.addItems(items)
        self._prev_combo.setCurrentIndex(0)
        self._prev_combo.currentIndexChanged.connect(self._refresh_transitions)
        prev_row.addWidget(self._prev_combo, stretch=1)
        ap_lay.addLayout(prev_row)

        layout.addWidget(self._analyze_params)

        # --- Train params ---
        self._train_params = QWidget()
        tp_lay = QVBoxLayout(self._train_params)
        tp_lay.setContentsMargins(0, 0, 0, 0)

        len_row = QHBoxLayout()
        len_row.addWidget(QLabel("Min password length:"))
        self._min_len = QSpinBox()
        self._min_len.setRange(1, 256)
        self._min_len.setValue(1)
        len_row.addWidget(self._min_len)
        len_row.addWidget(QLabel("Max:"))
        self._max_len = QSpinBox()
        self._max_len.setRange(1, 256)
        self._max_len.setValue(64)
        len_row.addWidget(self._max_len)
        len_row.addStretch()
        tp_lay.addLayout(len_row)

        self._train_params.setVisible(False)
        layout.addWidget(self._train_params)

        # --- Hashcat Config (always visible) ---
        cfg_label = QLabel("Hashcat Markov Settings:")
        cfg_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(cfg_label)

        thresh_row = QHBoxLayout()
        thresh_row.addWidget(QLabel("--markov-threshold:"))
        thresh_row.addWidget(self._info_icon(
            "Stop accepting new Markov chains when reaching this threshold. "
            "Lower values = faster but fewer candidates. 0 = unlimited."
        ))
        self._threshold = QSpinBox()
        self._threshold.setRange(0, 65535)
        self._threshold.setValue(0)
        self._threshold.setSpecialValueText("0 (unlimited)")
        thresh_row.addWidget(self._threshold)
        thresh_row.addStretch()
        layout.addLayout(thresh_row)

        check_row = QHBoxLayout()
        self._classic_check = QCheckBox("--markov-classic")
        self._classic_check.setToolTip(
            "Use classic (non-per-position) Markov chains. "
            "All positions share the same transition table."
        )
        self._inverse_check = QCheckBox("--markov-inverse")
        self._inverse_check.setToolTip(
            "Invert Markov chain ordering — least probable candidates first."
        )
        self._disable_check = QCheckBox("--markov-disable")
        self._disable_check.setToolTip(
            "Disable Markov chains entirely — pure brute-force ordering."
        )
        check_row.addWidget(self._classic_check)
        check_row.addWidget(self._inverse_check)
        check_row.addWidget(self._disable_check)
        check_row.addStretch()
        layout.addLayout(check_row)

    def build_output_section(self, layout: QVBoxLayout) -> None:
        # Tab widget for analysis results
        self._tabs = QTabWidget()

        # Tab 1: Root Frequency
        root_tab = QWidget()
        root_lay = QVBoxLayout(root_tab)
        self._root_info = QLabel("")
        self._root_info.setStyleSheet("font-size: 11px; padding: 4px;")
        root_lay.addWidget(self._root_info)
        self._root_table = QTableWidget()
        self._root_table.setColumnCount(4)
        self._root_table.setHorizontalHeaderLabels(
            ["Rank", "Character", "Code", "Count"]
        )
        self._root_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._root_table.setAlternatingRowColors(True)
        self._root_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        hdr = self._root_table.horizontalHeader()
        if hdr:
            hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        root_lay.addWidget(self._root_table)
        self._tabs.addTab(root_tab, "Root Frequencies")

        # Tab 2: Transitions
        trans_tab = QWidget()
        trans_lay = QVBoxLayout(trans_tab)
        self._trans_info = QLabel("")
        self._trans_info.setStyleSheet("font-size: 11px; padding: 4px;")
        trans_lay.addWidget(self._trans_info)
        self._trans_table = QTableWidget()
        self._trans_table.setColumnCount(4)
        self._trans_table.setHorizontalHeaderLabels(
            ["Rank", "Next Char", "Code", "Count"]
        )
        self._trans_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._trans_table.setAlternatingRowColors(True)
        self._trans_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        hdr2 = self._trans_table.horizontalHeader()
        if hdr2:
            hdr2.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        trans_lay.addWidget(self._trans_table)
        self._tabs.addTab(trans_tab, "Transitions")

        # Tab 3: Position Heatmap
        heat_tab = QWidget()
        heat_lay = QVBoxLayout(heat_tab)
        self._heat_info = QLabel(
            "Heatmap of character frequencies across positions. "
            "Rows = printable ASCII characters, Columns = password positions."
        )
        self._heat_info.setWordWrap(True)
        self._heat_info.setStyleSheet("font-size: 11px; padding: 4px;")
        heat_lay.addWidget(self._heat_info)

        heat_range = QHBoxLayout()
        heat_range.addWidget(QLabel("Positions:"))
        self._heat_start = QSpinBox()
        self._heat_start.setRange(0, 255)
        self._heat_start.setValue(0)
        heat_range.addWidget(self._heat_start)
        heat_range.addWidget(QLabel("to"))
        self._heat_end = QSpinBox()
        self._heat_end.setRange(0, 255)
        self._heat_end.setValue(15)
        heat_range.addWidget(self._heat_end)
        refresh_btn = QPushButton("Refresh Heatmap")
        refresh_btn.clicked.connect(self._refresh_heatmap)
        heat_range.addWidget(refresh_btn)
        heat_range.addStretch()
        heat_lay.addLayout(heat_range)

        self._heat_table = QTableWidget()
        self._heat_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._heat_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        heat_lay.addWidget(self._heat_table)
        self._tabs.addTab(heat_tab, "Position Heatmap")

        # Tab 4: Summary
        summary_tab = QWidget()
        summary_lay = QVBoxLayout(summary_tab)
        self._summary_text = QTextEdit()
        self._summary_text.setReadOnly(True)
        self._summary_text.setStyleSheet(
            "font-family: 'Consolas', 'DejaVu Sans Mono', 'Courier New', monospace;"
        )
        summary_lay.addWidget(self._summary_text)
        self._tabs.addTab(summary_tab, "Summary")

        layout.addWidget(self._tabs)

        # Buttons row
        btn_row = QHBoxLayout()
        self._send_btn = QPushButton("Send to Hashcat Command Builder")
        self._send_btn.setToolTip(
            "Send the .hcstat2 file path and Markov settings to the "
            "Hashcat Command Builder."
        )
        self._send_btn.clicked.connect(self._on_send_to_hashcat)
        btn_row.addWidget(self._send_btn)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------
    def _on_mode_changed(self, analyze_checked: bool) -> None:
        self._analyze_container.setVisible(analyze_checked)
        self._train_container.setVisible(not analyze_checked)
        self._analyze_params.setVisible(analyze_checked)
        self._train_params.setVisible(not analyze_checked)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        errors: list[str] = []
        if self._mode_analyze.isChecked():
            p = self._hcstat_file.text().strip()
            if not p:
                errors.append("Select an .hcstat2 file to analyze.")
            elif not Path(p).is_file():
                errors.append(f"File not found: {p}")
        else:
            pw = self._pw_list_file.text().strip()
            if not pw:
                errors.append("Select a password list file for training.")
            elif not Path(pw).is_file():
                errors.append(f"File not found: {pw}")
            out = self._train_output.text().strip()
            if not out:
                errors.append("Specify an output path for the .hcstat2 file.")
            if self._min_len.value() > self._max_len.value():
                errors.append("Min password length cannot exceed max.")
        return errors

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def run_tool(self) -> None:
        if self._mode_analyze.isChecked():
            self._run_analyze()
        else:
            self._run_train()

    def _run_analyze(self) -> None:
        path = self._hcstat_file.text().strip()
        try:
            stat = HcStat2()
            stat.load(path)
            self._stat = stat
            self._output_log.append(
                f"✓ Loaded {Path(path).name} — "
                f"{Path(path).stat().st_size:,} bytes compressed → "
                f"134,742,032 bytes decompressed"
            )
            max_pos = stat.max_useful_position()
            self._output_log.append(
                f"  Max useful position: {max_pos} "
                f"(passwords up to {max_pos + 1} characters)"
            )
            self._refresh_analysis()
            self._refresh_transitions()
            self._refresh_heatmap()
            self._refresh_summary()
        except Exception as e:
            self._output_log.append(f"✗ Failed to load: {e}")
        finally:
            self._run_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._progress.setVisible(False)

    def _run_train(self) -> None:
        pw_path = self._pw_list_file.text().strip()
        out_path = self._train_output.text().strip()
        min_l = self._min_len.value()
        max_l = self._max_len.value()

        def worker():
            try:
                stat = HcStat2()

                def progress_cb(n):
                    self._train_done.emit({"progress": n})

                count = stat.train(
                    pw_path, min_len=min_l, max_len=max_l,
                    progress_cb=progress_cb,
                )
                stat.save(out_path)
                self._stat = stat
                self._output_path = out_path
                self._train_done.emit({
                    "ok": True,
                    "count": count,
                    "out": out_path,
                    "size": Path(out_path).stat().st_size,
                })
            except Exception as e:
                self._train_done.emit({"error": str(e)})

        threading.Thread(target=worker, daemon=True).start()

    def _on_train_done(self, result: dict) -> None:
        if "progress" in result:
            self._output_log.append(
                f"  … processed {result['progress']:,} passwords"
            )
            return
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress.setVisible(False)
        if "error" in result:
            self._output_log.append(f"✗ Training failed: {result['error']}")
            return
        self._output_log.append(
            f"✓ Trained from {result['count']:,} passwords → "
            f"{Path(result['out']).name} ({result['size']:,} bytes)"
        )
        # Auto-load the trained file for analysis
        self._hcstat_file.setText(result["out"])
        self._mode_analyze.setChecked(True)
        self._refresh_analysis()
        self._refresh_transitions()
        self._refresh_heatmap()
        self._refresh_summary()

    # ------------------------------------------------------------------
    # Analysis refresh
    # ------------------------------------------------------------------
    def _refresh_analysis(self) -> None:
        """Update root frequency table for the selected position."""
        if not self._stat:
            return
        pos = self._pos_spin.value()
        stats = self._stat.get_root_stats(pos)
        # Filter to non-zero entries
        non_zero = [(cnt, ch) for cnt, ch in stats if cnt > 0]
        total = sum(cnt for cnt, _ in non_zero)
        self._root_info.setText(
            f"Position {pos}: {len(non_zero)} distinct characters, "
            f"{total:,} total occurrences"
        )
        max_val = non_zero[0][0] if non_zero else 0
        display = non_zero[:100]  # show top 100

        self._root_table.setRowCount(len(display))
        for row, (cnt, ch) in enumerate(display):
            char_str = chr(ch) if 32 <= ch < 127 else f"0x{ch:02X}"
            rank_item = QTableWidgetItem(str(row + 1))
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            char_item = QTableWidgetItem(char_str)
            char_item.setBackground(_freq_color(cnt, max_val))
            code_item = QTableWidgetItem(str(ch))
            code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            cnt_item = QTableWidgetItem(f"{cnt:,}")
            cnt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._root_table.setItem(row, 0, rank_item)
            self._root_table.setItem(row, 1, char_item)
            self._root_table.setItem(row, 2, code_item)
            self._root_table.setItem(row, 3, cnt_item)

    def _refresh_transitions(self) -> None:
        """Update transition table for selected position and prev char."""
        if not self._stat:
            return
        pos = self._pos_spin.value()
        combo_idx = self._prev_combo.currentIndex()
        prev_char = self._prev_char_map.get(combo_idx, 32)

        prev_label = chr(prev_char) if 32 <= prev_char < 127 else f"0x{prev_char:02X}"
        stats = self._stat.get_transition_stats(pos, prev_char)
        non_zero = [(cnt, ch) for cnt, ch in stats if cnt > 0]
        total = sum(cnt for cnt, _ in non_zero)

        self._trans_info.setText(
            f"Position {pos}, after '{prev_label}': "
            f"{len(non_zero)} distinct next chars, {total:,} total"
        )

        max_val = non_zero[0][0] if non_zero else 0
        display = non_zero[:100]

        self._trans_table.setRowCount(len(display))
        for row, (cnt, ch) in enumerate(display):
            char_str = chr(ch) if 32 <= ch < 127 else f"0x{ch:02X}"
            rank_item = QTableWidgetItem(str(row + 1))
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            char_item = QTableWidgetItem(char_str)
            char_item.setBackground(_freq_color(cnt, max_val))
            code_item = QTableWidgetItem(str(ch))
            code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            cnt_item = QTableWidgetItem(f"{cnt:,}")
            cnt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._trans_table.setItem(row, 0, rank_item)
            self._trans_table.setItem(row, 1, char_item)
            self._trans_table.setItem(row, 2, code_item)
            self._trans_table.setItem(row, 3, cnt_item)

    def _refresh_heatmap(self) -> None:
        """Build a heatmap grid: rows = printable chars, cols = positions."""
        if not self._stat:
            return
        start = self._heat_start.value()
        end = min(self._heat_end.value(), 255)
        if end < start:
            end = start
        positions = list(range(start, end + 1))
        # Printable ASCII rows
        chars = list(range(32, 127))  # 95 printable characters

        # Find global max across visible range
        global_max = 0
        for pos in positions:
            base = pos * _CHARSIZ
            for c in chars:
                v = self._stat.root[base + c]
                if v > global_max:
                    global_max = v

        self._heat_table.setRowCount(len(chars))
        self._heat_table.setColumnCount(len(positions))
        self._heat_table.setHorizontalHeaderLabels(
            [str(p) for p in positions]
        )
        self._heat_table.setVerticalHeaderLabels(
            [chr(c) for c in chars]
        )

        for col, pos in enumerate(positions):
            base = pos * _CHARSIZ
            for row, c in enumerate(chars):
                val = self._stat.root[base + c]
                item = QTableWidgetItem()
                item.setBackground(_freq_color(val, global_max))
                item.setToolTip(f"Pos {pos}, '{chr(c)}': {val:,}")
                self._heat_table.setItem(row, col, item)

        self._heat_table.resizeColumnsToContents()
        self._heat_table.resizeRowsToContents()

    def _refresh_summary(self) -> None:
        """Generate a text summary of the loaded .hcstat2 data."""
        if not self._stat:
            return
        lines: list[str] = []
        max_pos = self._stat.max_useful_position()
        lines.append(f"Markov Statistics Summary")
        lines.append(f"{'=' * 40}")
        lines.append(f"Max meaningful position: {max_pos} (pw length {max_pos + 1})")
        lines.append("")

        for pos in range(min(max_pos + 1, 32)):
            stats = self._stat.get_root_stats(pos)
            non_zero = [(cnt, ch) for cnt, ch in stats if cnt > 0]
            total = sum(cnt for cnt, _ in non_zero)
            top5 = non_zero[:5]
            top_str = "  ".join(
                f"'{chr(ch) if 32 <= ch < 127 else f'x{ch:02x}'}'"
                f"({cnt:,})"
                for cnt, ch in top5
            )
            lines.append(
                f"Pos {pos:>3d}: {len(non_zero):>3d} chars, "
                f"{total:>12,} total  |  Top: {top_str}"
            )

        if max_pos >= 32:
            lines.append(f"  ... ({max_pos - 31} more positions)")

        self._summary_text.setPlainText("\n".join(lines))

    # ------------------------------------------------------------------
    # Send to Hashcat
    # ------------------------------------------------------------------
    def _on_send_to_hashcat(self) -> None:
        """Send Markov config to Hashcat Command Builder via DataBus."""
        hcstat_path = self._hcstat_file.text().strip()
        if not hcstat_path or not Path(hcstat_path).is_file():
            QMessageBox.information(
                self, "No .hcstat2 File",
                "Load or train an .hcstat2 file first."
            )
            return

        # Build metadata for Hashcat launcher
        import json
        meta_dir = self._default_output_dir()
        meta_file = meta_dir / "markov_config.json"
        config = {
            "markov_hcstat2": hcstat_path,
            "markov_threshold": self._threshold.value(),
            "markov_classic": self._classic_check.isChecked(),
            "markov_inverse": self._inverse_check.isChecked(),
            "markov_disable": self._disable_check.isChecked(),
        }
        meta_file.write_text(json.dumps(config), encoding="utf-8")

        try:
            from ..app.data_bus import data_bus
            data_bus.send(
                source=self.MODULE_NAME,
                target="Hashcat Command Builder",
                path=str(meta_file),
            )
            self._output_log.append(
                f"Sent Markov config to Hashcat Command Builder: "
                f"--markov-hcstat2 {Path(hcstat_path).name}"
            )
        except Exception:
            self._output_log.append(
                f"Config saved to {meta_file}. "
                "Open Hashcat Command Builder and load it manually."
            )

    # ------------------------------------------------------------------
    # Output path
    # ------------------------------------------------------------------
    def get_output_path(self) -> Optional[str]:
        return self._output_path
