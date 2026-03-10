"""Module 6: Keyboard Walk Generator.

Generate password candidates based on keyboard walking patterns —
fingers moving across the keyboard in lines, diagonals, or patterns.
Supports QWERTY, AZERTY, QWERTZ, Dvorak.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .base_module import BaseModule

# Keyboard layouts: each row is a list of (unshifted, shifted) tuples.
# Position within the list = column.  Row index = row number.
LAYOUTS = {
    "QWERTY (US)": {
        "rows": [
            [('`','~'),('1','!'),('2','@'),('3','#'),('4','$'),('5','%'),('6','^'),('7','&'),('8','*'),('9','('),('0',')'),('-','_'),('=','+')],
            [('q','Q'),('w','W'),('e','E'),('r','R'),('t','T'),('y','Y'),('u','U'),('i','I'),('o','O'),('p','P'),('[','{'),(']','}'),('\\','|')],
            [('a','A'),('s','S'),('d','D'),('f','F'),('g','G'),('h','H'),('j','J'),('k','K'),('l','L'),(';',':'),(  "'",'"')],
            [('z','Z'),('x','X'),('c','C'),('v','V'),('b','B'),('n','N'),('m','M'),(',','<'),('.','>'),('/','?')],
        ],
        "offsets": [0, 0.5, 0.75, 1.25],  # row stagger in key-widths
    },
    "QWERTY (UK)": {
        "rows": [
            [('`','¬'),('1','!'),('2','"'),('3','£'),('4','$'),('5','%'),('6','^'),('7','&'),('8','*'),('9','('),('0',')'),('-','_'),('=','+')],
            [('q','Q'),('w','W'),('e','E'),('r','R'),('t','T'),('y','Y'),('u','U'),('i','I'),('o','O'),('p','P'),('[','{'),(']','}')],
            [('a','A'),('s','S'),('d','D'),('f','F'),('g','G'),('h','H'),('j','J'),('k','K'),('l','L'),(';',':'),('\'','@'),('#','~')],
            [('\\','|'),('z','Z'),('x','X'),('c','C'),('v','V'),('b','B'),('n','N'),('m','M'),(',','<'),('.','>'),('/','?')],
        ],
        "offsets": [0, 0.5, 0.75, 1.25],
    },
    "AZERTY (French)": {
        "rows": [
            [('²',''),('&','1'),('é','2'),('"','3'),("'",'4'),('(','5'),('-','6'),('è','7'),('_','8'),('ç','9'),('à','0'),(')','°'),('=','+')],
            [('a','A'),('z','Z'),('e','E'),('r','R'),('t','T'),('y','Y'),('u','U'),('i','I'),('o','O'),('p','P'),('^','¨'),('$','£')],
            [('q','Q'),('s','S'),('d','D'),('f','F'),('g','G'),('h','H'),('j','J'),('k','K'),('l','L'),('m','M'),('ù','%'),('*','µ')],
            [('w','W'),('x','X'),('c','C'),('v','V'),('b','B'),('n','N'),(',','?'),(';','.'),(':','/'),('!','§')],
        ],
        "offsets": [0, 0.5, 0.75, 1.25],
    },
    "QWERTZ (German)": {
        "rows": [
            [('^','°'),('1','!'),('2','"'),('3','§'),('4','$'),('5','%'),('6','&'),('7','/'),('8','('),('9',')'),('0','='),('ß','?'),('´','`')],
            [('q','Q'),('w','W'),('e','E'),('r','R'),('t','T'),('z','Z'),('u','U'),('i','I'),('o','O'),('p','P'),('ü','Ü'),('+','*')],
            [('a','A'),('s','S'),('d','D'),('f','F'),('g','G'),('h','H'),('j','J'),('k','K'),('l','L'),('ö','Ö'),('ä','Ä'),('#',"'")],
            [('y','Y'),('x','X'),('c','C'),('v','V'),('b','B'),('n','N'),('m','M'),(',',';'),('.',':'),('-','_')],
        ],
        "offsets": [0, 0.5, 0.75, 1.25],
    },
    "Dvorak": {
        "rows": [
            [('`','~'),('1','!'),('2','@'),('3','#'),('4','$'),('5','%'),('6','^'),('7','&'),('8','*'),('9','('),('0',')'),('[','{'),(']','}')],
            [("'",'"'),(',','<'),('.','>'),(  'p','P'),('y','Y'),('f','F'),('g','G'),('c','C'),('r','R'),('l','L'),('/','?'),('=','+')],
            [('a','A'),('o','O'),('e','E'),('u','U'),('i','I'),('d','D'),('h','H'),('t','T'),('n','N'),('s','S'),('-','_')],
            [(';',':'),('q','Q'),('j','J'),('k','K'),('x','X'),('b','B'),('m','M'),('w','W'),('v','V'),('z','Z')],
        ],
        "offsets": [0, 0.5, 0.75, 1.25],
    },
    # ── Scandinavian ──────────────────────────────────────────────────
    "QWERTY (Danish)": {
        "rows": [
            [('½','§'),('1','!'),('2','"'),('3','#'),('4','¤'),('5','%'),('6','&'),('7','/'),('8','('),('9',')'),('0','='),('+','?'),('´','`')],
            [('q','Q'),('w','W'),('e','E'),('r','R'),('t','T'),('y','Y'),('u','U'),('i','I'),('o','O'),('p','P'),('å','Å'),('¨','^')],
            [('a','A'),('s','S'),('d','D'),('f','F'),('g','G'),('h','H'),('j','J'),('k','K'),('l','L'),('æ','Æ'),('ø','Ø'),("'",'*')],
            [('<','>'),('z','Z'),('x','X'),('c','C'),('v','V'),('b','B'),('n','N'),('m','M'),(',',';'),('.',':'),('-','_')],
        ],
        "offsets": [0, 0.5, 0.75, 1.25],
    },
    "QWERTY (Norwegian)": {
        "rows": [
            [('|','§'),('1','!'),('2','"'),('3','#'),('4','¤'),('5','%'),('6','&'),('7','/'),('8','('),('9',')'),('0','='),('+','?'),('\\','`')],
            [('q','Q'),('w','W'),('e','E'),('r','R'),('t','T'),('y','Y'),('u','U'),('i','I'),('o','O'),('p','P'),('å','Å'),('¨','^')],
            [('a','A'),('s','S'),('d','D'),('f','F'),('g','G'),('h','H'),('j','J'),('k','K'),('l','L'),('ø','Ø'),('æ','Æ'),("'",'*')],
            [('<','>'),('z','Z'),('x','X'),('c','C'),('v','V'),('b','B'),('n','N'),('m','M'),(',',';'),('.',':'),('-','_')],
        ],
        "offsets": [0, 0.5, 0.75, 1.25],
    },
    "QWERTY (Swedish/Finnish)": {
        "rows": [
            [('§','½'),('1','!'),('2','"'),('3','#'),('4','¤'),('5','%'),('6','&'),('7','/'),('8','('),('9',')'),('0','='),('+','?'),('´','`')],
            [('q','Q'),('w','W'),('e','E'),('r','R'),('t','T'),('y','Y'),('u','U'),('i','I'),('o','O'),('p','P'),('å','Å'),('¨','^')],
            [('a','A'),('s','S'),('d','D'),('f','F'),('g','G'),('h','H'),('j','J'),('k','K'),('l','L'),('ö','Ö'),('ä','Ä'),("'",'*')],
            [('<','>'),('z','Z'),('x','X'),('c','C'),('v','V'),('b','B'),('n','N'),('m','M'),(',',';'),('.',':'),('-','_')],
        ],
        "offsets": [0, 0.5, 0.75, 1.25],
    },
    # ── Southern European ─────────────────────────────────────────────
    "QWERTY (Spanish)": {
        "rows": [
            [('º','ª'),('1','!'),('2','"'),('3','·'),('4','$'),('5','%'),('6','&'),('7','/'),('8','('),('9',')'),('0','='),("'",'?'),('¡','¿')],
            [('q','Q'),('w','W'),('e','E'),('r','R'),('t','T'),('y','Y'),('u','U'),('i','I'),('o','O'),('p','P'),('`','^'),('+','*')],
            [('a','A'),('s','S'),('d','D'),('f','F'),('g','G'),('h','H'),('j','J'),('k','K'),('l','L'),('ñ','Ñ'),('´','¨'),('ç','Ç')],
            [('<','>'),('z','Z'),('x','X'),('c','C'),('v','V'),('b','B'),('n','N'),('m','M'),(',',';'),('.',':'),('-','_')],
        ],
        "offsets": [0, 0.5, 0.75, 1.25],
    },
    "QWERTY (Portuguese)": {
        "rows": [
            [('\\','|'),('1','!'),('2','"'),('3','#'),('4','$'),('5','%'),('6','&'),('7','/'),('8','('),('9',')'),('0','='),("'",'?'),('«','»')],
            [('q','Q'),('w','W'),('e','E'),('r','R'),('t','T'),('y','Y'),('u','U'),('i','I'),('o','O'),('p','P'),('+','*'),('´','`')],
            [('a','A'),('s','S'),('d','D'),('f','F'),('g','G'),('h','H'),('j','J'),('k','K'),('l','L'),('ç','Ç'),('º','ª'),('~','^')],
            [('<','>'),('z','Z'),('x','X'),('c','C'),('v','V'),('b','B'),('n','N'),('m','M'),(',',';'),('.',':'),('-','_')],
        ],
        "offsets": [0, 0.5, 0.75, 1.25],
    },
    "QWERTY (Italian)": {
        "rows": [
            [('\\','|'),('1','!'),('2','"'),('3','£'),('4','$'),('5','%'),('6','&'),('7','/'),('8','('),('9',')'),('0','='),("'",'?'),('ì','^')],
            [('q','Q'),('w','W'),('e','E'),('r','R'),('t','T'),('y','Y'),('u','U'),('i','I'),('o','O'),('p','P'),('è','é'),('+','*')],
            [('a','A'),('s','S'),('d','D'),('f','F'),('g','G'),('h','H'),('j','J'),('k','K'),('l','L'),('ò','ç'),('à','°'),('ù','§')],
            [('<','>'),('z','Z'),('x','X'),('c','C'),('v','V'),('b','B'),('n','N'),('m','M'),(',',';'),('.',':'),('-','_')],
        ],
        "offsets": [0, 0.5, 0.75, 1.25],
    },
    # ── AZERTY variants ───────────────────────────────────────────────
    "AZERTY (Belgian)": {
        "rows": [
            [('²','³'),('&','1'),('é','2'),('"','3'),("'",'4'),('(','5'),('§','6'),('è','7'),('!','8'),('ç','9'),('à','0'),(')','°'),('-','_')],
            [('a','A'),('z','Z'),('e','E'),('r','R'),('t','T'),('y','Y'),('u','U'),('i','I'),('o','O'),('p','P'),('^','¨'),('$','*')],
            [('q','Q'),('s','S'),('d','D'),('f','F'),('g','G'),('h','H'),('j','J'),('k','K'),('l','L'),('m','M'),('ù','%'),('µ','£')],
            [('<','>'),('w','W'),('x','X'),('c','C'),('v','V'),('b','B'),('n','N'),(',','?'),(';','.'),(':','/'),('=','+')],
        ],
        "offsets": [0, 0.5, 0.75, 1.25],
    },
    # ── QWERTZ variants ───────────────────────────────────────────────
    "QWERTZ (Swiss)": {
        "rows": [
            [('§','°'),('1','+'),('2','"'),('3','*'),('4','ç'),('5','%'),('6','&'),('7','/'),('8','('),('9',')'),('0','='),("'",'?'),('^','`')],
            [('q','Q'),('w','W'),('e','E'),('r','R'),('t','T'),('z','Z'),('u','U'),('i','I'),('o','O'),('p','P'),('ü','è'),('¨','!')],
            [('a','A'),('s','S'),('d','D'),('f','F'),('g','G'),('h','H'),('j','J'),('k','K'),('l','L'),('ö','é'),('ä','à'),('$','£')],
            [('<','>'),('y','Y'),('x','X'),('c','C'),('v','V'),('b','B'),('n','N'),('m','M'),(',',';'),('.',':'),('-','_')],
        ],
        "offsets": [0, 0.5, 0.75, 1.25],
    },
}

# Numpad layout
NUMPAD_ROWS = [
    [('7',''),('8',''),('9','')],
    [('4',''),('5',''),('6','')],
    [('1',''),('2',''),('3','')],
    [('0',''),('.','')],
]

# Well-known keyboard walks
COMMON_WALKS = [
    "qwerty", "qwert", "qwer", "asdf", "asdfgh", "zxcv", "zxcvbn",
    "1234567890", "123456789", "12345678", "1234567", "123456", "12345", "1234",
    "qwer1234", "1q2w3e4r", "1qaz2wsx", "qazwsx", "qazwsxedc",
    "zaq1", "zaq12wsx", "!@#$%", "!@#$%^", "1q2w3e",
    "poiuy", "lkjhg", "mnbvc", "0987654321",
    "qaswed", "wsxedc", "edcrfv", "rfvtgb",
]


def _build_adjacency(layout_data: dict, include_numpad: bool, shift: bool) -> tuple[dict[str, list[str]], dict[str, tuple[int, float]]]:
    """Build char→[neighbors] adjacency from layout data.

    Returns (adjacency, char_to_pos) where char_to_pos maps each character
    to its (row, effective_col) for direction classification.
    """
    adjacency: dict[str, list[str]] = defaultdict(list)
    rows = layout_data["rows"]
    offsets = layout_data["offsets"]
    idx = 0 if not shift else 1

    pos_to_char: dict[tuple[int, float], str] = {}
    char_to_pos: dict[str, tuple[int, float]] = {}

    for r, row in enumerate(rows):
        for c, keys in enumerate(row):
            ch = keys[idx] if idx < len(keys) and keys[idx] else keys[0]
            eff_col = c + offsets[r]
            pos_to_char[(r, eff_col)] = ch
            char_to_pos[ch] = (r, eff_col)

    for ch, (r1, c1) in char_to_pos.items():
        for ch2, (r2, c2) in char_to_pos.items():
            if ch == ch2:
                continue
            dr = abs(r1 - r2)
            dc = abs(c1 - c2)
            if dr <= 1 and dc <= 1.5:
                adjacency[ch].append(ch2)

    if include_numpad:
        np_pos = {}
        for r, row in enumerate(NUMPAD_ROWS):
            for c, keys in enumerate(row):
                ch = keys[idx] if idx < len(keys) and keys[idx] else keys[0]
                np_pos[ch] = (r, c)
                char_to_pos[ch] = (r + 10, float(c))  # offset row to avoid overlap
        for ch, (r1, c1) in np_pos.items():
            for ch2, (r2, c2) in np_pos.items():
                if ch != ch2 and abs(r1 - r2) <= 1 and abs(c1 - c2) <= 1:
                    adjacency[ch].append(ch2)

    return adjacency, char_to_pos


def _generate_walks(
    adjacency: dict[str, list[str]],
    min_len: int,
    max_len: int,
    max_direction_changes: int,
    include_reverse: bool,
    horizontal: bool,
    vertical: bool,
    diagonal: bool,
    combo: bool,
    char_to_pos: dict[str, tuple[int, float]] | None = None,
    allow_repeats: bool = False,
) -> set[str]:
    """DFS walk generation through the adjacency graph.

    When *char_to_pos* is provided and direction booleans are set, the
    generator filters moves by allowed directions:
      - horizontal: same row
      - vertical: same effective column (within 0.5)
      - diagonal: different row *and* different column
    If *combo* is True, direction changes are allowed up to *max_direction_changes*.
    """
    results: set[str] = set()

    def _classify_dir(fr: str, to: str) -> str | None:
        """Classify a move as 'h', 'v', 'd', or None if disallowed."""
        if char_to_pos is None:
            return "h"  # no position data → allow
        r1, c1 = char_to_pos.get(fr, (0, 0))
        r2, c2 = char_to_pos.get(to, (0, 0))
        dr, dc = abs(r1 - r2), abs(c1 - c2)
        if dr == 0 and dc > 0:
            return "h" if horizontal else None
        if dc < 0.5 and dr > 0:
            return "v" if vertical else None
        if dr > 0 and dc >= 0.5:
            return "d" if diagonal else None
        return None

    def _dfs(path: list[str], last_dir: str | None, changes: int) -> None:
        if len(path) >= min_len:
            results.add("".join(path))
        if len(path) >= max_len:
            return
        current = path[-1]
        for neighbor in adjacency.get(current, []):
            if not allow_repeats and neighbor in path:
                continue
            d = _classify_dir(current, neighbor)
            if d is None:
                continue
            new_changes = changes
            if last_dir is not None and d != last_dir:
                if not combo:
                    continue
                new_changes += 1
                if new_changes > max_direction_changes:
                    continue
            path.append(neighbor)
            _dfs(path, d, new_changes)
            path.pop()

    for start_key in adjacency:
        _dfs([start_key], None, 0)
        if len(results) > 50000:
            break

    if include_reverse:
        reversed_walks = {w[::-1] for w in results}
        results.update(reversed_walks)

    return results


# ── Visual keyboard widget ───────────────────────────────────────────
class _KeyboardWidget(QWidget):
    """Draws an interactive keyboard grid and highlights walk paths.
    Supports click-to-walk: click keys to build a custom walk."""

    walk_committed = pyqtSignal(str)  # emitted when user commits a custom walk

    _KEY_W = 38
    _KEY_H = 34
    _GAP = 3

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout_data: dict | None = None
        self._show_numpad: bool = False
        self._highlighted: set[str] = set()
        self._walk_path: list[str] = []  # ordered keys in current walk
        self._click_path: list[str] = []  # user-built click walk
        self._key_rects: dict[str, QRectF] = {}  # char -> bounding rect
        self.setMinimumHeight(170)
        self.setMinimumWidth(560)

    def set_layout(self, layout_data: dict) -> None:
        self._layout_data = layout_data
        self._rebuild_key_rects()
        self.update()

    def highlight_walk(self, walk: str) -> None:
        self._walk_path = list(walk)
        self._highlighted = set(walk)
        self.update()

    def clear_highlight(self) -> None:
        self._highlighted.clear()
        self._walk_path.clear()
        self.update()

    def clear_click_path(self) -> None:
        self._click_path.clear()
        self.update()

    def get_click_walk(self) -> str:
        return "".join(self._click_path)

    def set_show_numpad(self, show: bool) -> None:
        self._show_numpad = show
        self.setMinimumWidth(720 if show else 560)
        self.update()

    def _rebuild_key_rects(self) -> None:
        """Pre-compute bounding rectangles for hit testing."""
        self._key_rects.clear()
        if not self._layout_data:
            return
        rows = self._layout_data["rows"]
        offsets = self._layout_data["offsets"]
        kw, kh, gap = self._KEY_W, self._KEY_H, self._GAP
        for r, row in enumerate(rows):
            ox = offsets[r] * kw
            for c, keys in enumerate(row):
                ch = keys[0]
                x = ox + c * (kw + gap)
                y = r * (kh + gap) + 4
                self._key_rects[ch] = QRectF(x, y, kw, kh)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle click-to-walk key selection."""
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()
        for ch, rect in self._key_rects.items():
            if rect.contains(pos):
                if self._click_path and self._click_path[-1] == ch:
                    # clicking same key again -> undo last
                    self._click_path.pop()
                else:
                    self._click_path.append(ch)
                self.update()
                break

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._layout_data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont("Consolas", 9)
        painter.setFont(font)

        rows = self._layout_data["rows"]
        offsets = self._layout_data["offsets"]
        kw, kh, gap = self._KEY_W, self._KEY_H, self._GAP

        click_set = set(self._click_path)
        char_positions: dict[str, tuple[float, float]] = {}

        for r, row in enumerate(rows):
            ox = offsets[r] * kw
            for c, keys in enumerate(row):
                ch = keys[0]
                x = ox + c * (kw + gap)
                y = r * (kh + gap) + 4

                # Determine color
                if ch in click_set:
                    painter.setBrush(QBrush(QColor("#89b4fa")))  # Catppuccin blue for click path
                    painter.setPen(QPen(QColor("#89b4fa").darker(120), 1))
                elif ch in self._highlighted:
                    painter.setBrush(QBrush(QColor("#f38ba8")))  # Catppuccin red
                    painter.setPen(QPen(QColor("#f38ba8").darker(120), 1))
                else:
                    painter.setBrush(QBrush(QColor("#45475a")))  # Catppuccin surface1
                    painter.setPen(QPen(QColor("#585b70"), 1))

                painter.drawRoundedRect(QRectF(x, y, kw, kh), 4, 4)

                # Key label
                painter.setPen(QPen(QColor("#cdd6f4"), 1))  # Catppuccin text
                painter.drawText(QRectF(x, y, kw, kh), Qt.AlignmentFlag.AlignCenter, ch)

                char_positions[ch] = (x + kw / 2, y + kh / 2)

        # Draw walk path lines (red/peach for generated walk)
        if len(self._walk_path) > 1:
            pen = QPen(QColor("#fab387"), 2)  # Catppuccin peach
            painter.setPen(pen)
            for i in range(len(self._walk_path) - 1):
                p1 = char_positions.get(self._walk_path[i])
                p2 = char_positions.get(self._walk_path[i + 1])
                if p1 and p2:
                    from PyQt6.QtCore import QPointF
                    painter.drawLine(QPointF(*p1), QPointF(*p2))

        # Draw click path lines (blue for user click walk)
        if len(self._click_path) > 1:
            pen = QPen(QColor("#89b4fa"), 2.5)  # Catppuccin blue
            painter.setPen(pen)
            for i in range(len(self._click_path) - 1):
                p1 = char_positions.get(self._click_path[i])
                p2 = char_positions.get(self._click_path[i + 1])
                if p1 and p2:
                    from PyQt6.QtCore import QPointF
                    painter.drawLine(QPointF(*p1), QPointF(*p2))

        # Render numpad keys if enabled
        if self._show_numpad:
            max_right = 0
            for r, row in enumerate(rows):
                ox = offsets[r] * kw
                right_edge = ox + len(row) * (kw + gap)
                if right_edge > max_right:
                    max_right = right_edge
            np_x = max_right + 20
            font_small = QFont("Consolas", 7)
            painter.setFont(font_small)
            painter.setPen(QPen(QColor("#6c7086"), 1))
            painter.drawText(
                QRectF(np_x, 0, 3 * (kw + gap), 14),
                Qt.AlignmentFlag.AlignCenter, "Numpad",
            )
            painter.setFont(font)
            for r, np_row in enumerate(NUMPAD_ROWS):
                for c, keys in enumerate(np_row):
                    ch = keys[0]
                    x = np_x + c * (kw + gap)
                    y = r * (kh + gap) + 16
                    if ch in self._highlighted:
                        painter.setBrush(QBrush(QColor("#f38ba8")))
                        painter.setPen(QPen(QColor("#f38ba8").darker(120), 1))
                    else:
                        painter.setBrush(QBrush(QColor("#45475a")))
                        painter.setPen(QPen(QColor("#585b70"), 1))
                    painter.drawRoundedRect(QRectF(x, y, kw, kh), 4, 4)
                    painter.setPen(QPen(QColor("#cdd6f4"), 1))
                    painter.drawText(
                        QRectF(x, y, kw, kh),
                        Qt.AlignmentFlag.AlignCenter, ch,
                    )

        painter.end()


class KeyboardWalkModule(BaseModule):
    MODULE_NAME = "Keyboard Walk Generator"
    MODULE_DESCRIPTION = (
        "Generate a wordlist of password candidates based on keyboard walking patterns \u2014 "
        "fingers moving across the keyboard in lines, diagonals, or patterns. "
        "Output is a plain-text wordlist (one candidate per line) ready for use in "
        "hashcat, PRINCE, or other cracking tools. "
        "Supports QWERTY, AZERTY, QWERTZ, Dvorak, and many European layouts."
    )
    MODULE_CATEGORY = "Wordlist Generation"

    _generation_done = pyqtSignal(list)

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        self._generated: list[str] = []
        super().__init__(parent)
        self._generation_done.connect(self._on_done)

    def build_input_section(self, layout: QVBoxLayout) -> None:
        note = QLabel("This tool generates patterns from keyboard layout data — no file input needed.")
        note.setStyleSheet("color: #888;")
        layout.addWidget(note)

    def build_params_section(self, layout: QVBoxLayout) -> None:
        # Layout selector — single-choice combo box
        self._layout_combo = self.create_combo(
            layout, "Keyboard layout:",
            list(LAYOUTS.keys()),
            tooltip="Select the keyboard layout to generate walks for. "
                    "Each layout has different key positions and adjacencies.",
        )
        self._layout_combo.currentTextChanged.connect(self._on_layout_changed)

        self._include_numpad = self.create_checkbox(
            layout, "Include numpad", default=True,
            tooltip="Include the numeric keypad as a separate walkable region.",
        )
        self._include_shift = self.create_checkbox(
            layout, "Include shift variants", default=False,
            tooltip="Also generate walks using shifted characters (e.g., !@#$ as the shifted version of 1234).",
        )
        self._allow_repeats = self.create_checkbox(
            layout, "Allow repeats (revisit keys)", default=False,
            tooltip="Allow the walk to revisit keys already in the path. Produces more walks but many less realistic.",
        )

        # Walk parameters
        self._min_walk = self.create_spinbox(
            layout, "Min walk length:", 2, 20, 4,
            "Minimum number of keys in a walk. Shorter walks are less useful.",
        )
        self._max_walk = self.create_spinbox(
            layout, "Max walk length:", 2, 20, 8,
            "Maximum number of keys in a walk. Typical: 6-12.",
        )
        self._max_dir_changes = self.create_spinbox(
            layout, "Max direction changes:", 0, 4, 2,
            "How many times the walk can change direction. 0 = straight lines only.",
        )

        # Directions
        dir_label = QLabel("Walk directions:")
        dir_label.setStyleSheet("font-weight: bold; margin-top: 4px;")
        layout.addWidget(dir_label)
        self._dir_horizontal = self.create_checkbox(layout, "Horizontal (left-right along a row)", default=True)
        self._dir_vertical = self.create_checkbox(layout, "Vertical (up-down across rows)", default=True)
        self._dir_diagonal = self.create_checkbox(layout, "Diagonal (e.g., 1qaz, 2wsx)", default=True)
        self._dir_combo = self.create_checkbox(layout, "Combo (direction changes mid-walk)", default=True)

        self._include_reverse = self.create_checkbox(
            layout, "Include reverse of each walk", default=True,
            tooltip="Also generate the reverse of each walk (e.g., ytrewq in addition to qwerty).",
        )
        self._include_common = self.create_checkbox(
            layout, "Include well-known named walks", default=True,
            tooltip="Include well-known keyboard walks: qwerty, asdfgh, zxcvbn, 1q2w3e4r, etc.",
        )

    def build_output_section(self, layout: QVBoxLayout) -> None:
        self._output_file = self.create_file_browser(
            layout, "Output file:", "Export generated walks as a wordlist file.",
            save=True, file_filter="Text Files (*.txt);;All Files (*)",
        )
        self._output_file.setText(str(self._default_output_dir() / "keyboard_walks.txt"))

        # ── Visual keyboard ──
        self._kbd_widget = _KeyboardWidget()
        self._kbd_widget.set_layout(LAYOUTS["QWERTY (US)"])
        self._kbd_widget.set_show_numpad(self._include_numpad.isChecked())
        self._include_numpad.toggled.connect(self._kbd_widget.set_show_numpad)
        layout.addWidget(self._kbd_widget)

        # Click-to-walk controls
        walk_ctl = QHBoxLayout()
        self._walk_label = QLabel("Click keys to build a walk: (none)")
        self._walk_label.setStyleSheet("font-family: monospace; color: #89b4fa;")
        walk_ctl.addWidget(self._walk_label, stretch=1)

        add_walk_btn = QPushButton("Add Walk")
        add_walk_btn.setToolTip("Commit the clicked key sequence as a custom walk pattern.")
        add_walk_btn.clicked.connect(self._commit_click_walk)
        walk_ctl.addWidget(add_walk_btn)

        clear_walk_btn = QPushButton("Clear Walk")
        clear_walk_btn.setToolTip("Reset the in-progress click walk.")
        clear_walk_btn.clicked.connect(self._clear_click_walk)
        walk_ctl.addWidget(clear_walk_btn)
        layout.addLayout(walk_ctl)

        # Connect keyboard mouse updates to label
        self._kbd_widget.installEventFilter(self)

        send_row = QHBoxLayout()
        self.send_to_menu(send_row, ["PRINCE Processor", "Combinator", "Hashcat Command Builder"])
        send_row.addStretch()
        layout.addLayout(send_row)

        # Update keyboard visual when layout check changes
        # Default visual to first checked layout

    def _on_layout_changed(self, name: str) -> None:
        """Update visual keyboard when layout combo changes."""
        data = LAYOUTS.get(name, LAYOUTS["QWERTY (US)"])
        self._kbd_widget.set_layout(data)

    def eventFilter(self, obj, event) -> bool:
        """Update walk label when keyboard widget is clicked."""
        if obj is self._kbd_widget and hasattr(event, 'type'):
            from PyQt6.QtCore import QEvent
            if event.type() == QEvent.Type.MouseButtonRelease:
                walk = self._kbd_widget.get_click_walk()
                self._walk_label.setText(
                    f"Click keys to build a walk: {walk}" if walk else "Click keys to build a walk: (none)"
                )
        return False

    def _commit_click_walk(self) -> None:
        """Add the click-built walk to the output."""
        walk = self._kbd_widget.get_click_walk()
        if len(walk) < 2:
            self._output_log.append("Click at least 2 keys to create a walk.")
            return
        if walk not in self._generated:
            self._generated.append(walk)
        self._output_log.append(f"Added custom walk: {walk}")
        self._kbd_widget.clear_click_path()
        self._walk_label.setText("Click keys to build a walk: (none)")

    def _clear_click_walk(self) -> None:
        self._kbd_widget.clear_click_path()
        self._walk_label.setText("Click keys to build a walk: (none)")

    def run_tool(self) -> None:
        thread = threading.Thread(target=self._generate, daemon=True)
        thread.start()

    def _generate(self) -> None:
        layout_name = self._layout_combo.currentText() or "QWERTY (US)"
        layout_data = LAYOUTS.get(layout_name, LAYOUTS["QWERTY (US)"])

        include_numpad = self._include_numpad.isChecked()
        shift = self._include_shift.isChecked()
        allow_repeats = self._allow_repeats.isChecked()
        walks: set[str] = set()

        adjacency, char_to_pos = _build_adjacency(layout_data, include_numpad, shift=False)
        walks |= _generate_walks(
            adjacency,
            self._min_walk.value(),
            self._max_walk.value(),
            self._max_dir_changes.value(),
            self._include_reverse.isChecked(),
            self._dir_horizontal.isChecked(),
            self._dir_vertical.isChecked(),
            self._dir_diagonal.isChecked(),
            self._dir_combo.isChecked(),
            char_to_pos=char_to_pos,
            allow_repeats=allow_repeats,
        )

        if shift:
            adj_shift, ctp_shift = _build_adjacency(layout_data, include_numpad, shift=True)
            walks |= _generate_walks(
                adj_shift,
                self._min_walk.value(),
                self._max_walk.value(),
                self._max_dir_changes.value(),
                self._include_reverse.isChecked(),
                self._dir_horizontal.isChecked(),
                self._dir_vertical.isChecked(),
                self._dir_diagonal.isChecked(),
                self._dir_combo.isChecked(),
                char_to_pos=ctp_shift,
                allow_repeats=allow_repeats,
            )

        if self._include_common.isChecked():
            min_l = self._min_walk.value()
            max_l = self._max_walk.value()
            for cw in COMMON_WALKS:
                if min_l <= len(cw) <= max_l:
                    walks.add(cw)

        result = sorted(walks)
        self._generation_done.emit(result)

    def _on_done(self, results: list[str]) -> None:
        self._generated = results
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress.setVisible(False)

        self._output_log.clear()
        self._output_log.append(f"Generated {len(results):,} keyboard walks.\n")
        preview = results[:1000]
        self._output_log.append("\n".join(preview))
        if len(results) > 1000:
            self._output_log.append(f"\n… and {len(results) - 1000:,} more.")

        # Highlight first walk on visual keyboard
        if results:
            self._kbd_widget.highlight_walk(results[0])
        else:
            self._kbd_widget.clear_highlight()

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
