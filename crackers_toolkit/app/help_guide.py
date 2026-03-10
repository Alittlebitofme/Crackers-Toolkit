"""Interactive 'What should I use?' help guide widget.

Provides workflow decision trees and common workflow chains,
with clickable tool links that navigate directly to the tool.
"""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


# Tool ID map — kept in sync with tool_registry.py
_TOOL_IDS: dict[str, int] = {
    "PRINCE Processor": 1,
    "PCFG Guesser": 2,
    "Combinator": 3,
    "PRINCE-LING": 4,
    "Element Extractor": 5,
    "Keyboard Walk Generator": 6,
    "Date & Number Patterns": 7,
    "demeuk — Wordlist Cleaner": 8,
    "PCFG Trainer": 9,
    "Password Scorer": 10,
    "StatsGen (PACK)": 11,
    "Mask Builder": 12,
    "MaskGen (PACK)": 13,
    "PolicyGen (PACK)": 14,
    "Rule Builder": 15,
    "RuleGen (PACK)": 16,
    "PCFG Rule Editor": 17,
    "Hashcat Command Builder": 18,
    "Web Scraper Generator": 19,
}


class HelpGuideWidget(QWidget):
    """Scrollable help guide with clickable workflow decision trees."""

    def __init__(self, navigate_callback: Callable[[int], None], parent=None) -> None:
        super().__init__(parent)
        self._navigate = navigate_callback
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("What Should I Use?")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Click any tool name below to jump directly to it. "
            "Follow the decision trees to find the right tool for your task."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #a6adc8; font-size: 13px; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        # ── Decision Tree: What do you have? ─────────────────────
        layout.addWidget(self._section_label("What do you have?"))

        decisions = [
            (
                "I have a raw/dirty wordlist",
                "Clean it first, then generate candidates:",
                [
                    ("demeuk — Wordlist Cleaner", "Clean encoding, remove junk, deduplicate"),
                    ("PCFG Trainer", "Train a grammar model from your clean list"),
                    ("StatsGen (PACK)", "Analyze password patterns and statistics"),
                ],
            ),
            (
                "I have a clean wordlist",
                "Generate candidates or analyze passwords:",
                [
                    ("PRINCE Processor", "Generate word combinations using PRINCE algorithm"),
                    ("Combinator", "Combine two or more wordlists"),
                    ("PCFG Guesser", "Generate guesses from a trained PCFG model"),
                    ("Hashcat Command Builder", "Launch a dictionary attack directly"),
                ],
            ),
            (
                "I have cracked passwords",
                "Reverse-engineer rules and patterns:",
                [
                    ("RuleGen (PACK)", "Discover what rules transform base words to passwords"),
                    ("StatsGen (PACK)", "Analyze length, charset, and mask distributions"),
                    ("Password Scorer", "Score passwords against a PCFG model"),
                ],
            ),
            (
                "I have nothing (starting from scratch)",
                "Generate candidates from patterns:",
                [
                    ("Mask Builder", "Build character masks by hand (?l?u?d?s)"),
                    ("Keyboard Walk Generator", "Generate keyboard walk patterns (qwerty, etc.)"),
                    ("Date & Number Patterns", "Generate date/number sequences"),
                    ("Web Scraper Generator", "Scrape words from a target website"),
                ],
            ),
        ]

        for question, desc, tools in decisions:
            layout.addWidget(self._decision_block(question, desc, tools))

        # ── Common Workflows ─────────────────────────────────────
        layout.addWidget(self._section_label("Common Workflows"))

        workflows = [
            (
                "Raw Wordlist → Clean → Attack",
                [
                    ("demeuk — Wordlist Cleaner", "Clean & filter"),
                    ("PRINCE Processor", "Generate combinations"),
                    ("Hashcat Command Builder", "Launch attack"),
                ],
            ),
            (
                "Password Analysis → Mask Attack",
                [
                    ("StatsGen (PACK)", "Analyze patterns"),
                    ("MaskGen (PACK)", "Generate optimal masks"),
                    ("Hashcat Command Builder", "Launch mask attack"),
                ],
            ),
            (
                "Train Model → Generate Guesses",
                [
                    ("PCFG Trainer", "Train grammar model"),
                    ("PCFG Guesser", "Generate password guesses"),
                    ("Hashcat Command Builder", "Pipe to hashcat"),
                ],
            ),
            (
                "Cracked Passwords → Rule Discovery → Rule Attack",
                [
                    ("RuleGen (PACK)", "Reverse-engineer rules"),
                    ("Rule Builder", "Refine & combine rules"),
                    ("Hashcat Command Builder", "Launch rule attack"),
                ],
            ),
            (
                "Policy-Compliant Attack",
                [
                    ("PolicyGen (PACK)", "Generate policy-compliant masks"),
                    ("MaskGen (PACK)", "Optimize mask coverage"),
                    ("Hashcat Command Builder", "Launch attack"),
                ],
            ),
        ]

        for wf_title, steps in workflows:
            layout.addWidget(self._workflow_block(wf_title, steps))

        # ── Tool Quick Reference ─────────────────────────────────
        layout.addWidget(self._section_label("Tool Quick Reference"))

        categories = {
            "Candidate Generators": [
                ("PRINCE Processor", "Word combinations via PRINCE algorithm"),
                ("PCFG Guesser", "Grammar-based password guesses"),
                ("Combinator", "Combine 2+ wordlists"),
                ("PRINCE-LING", "Language-aware PRINCE"),
                ("Element Extractor", "Extract charset elements from wordlists"),
                ("Keyboard Walk Generator", "Keyboard walk patterns"),
                ("Date & Number Patterns", "Date/number sequences"),
            ],
            "Wordlist Cleaning": [
                ("demeuk — Wordlist Cleaner", "Clean, filter, deduplicate wordlists"),
            ],
            "Wordlist Analysis": [
                ("PCFG Trainer", "Train probabilistic grammar model"),
                ("Password Scorer", "Score passwords against PCFG model"),
                ("StatsGen (PACK)", "Password statistics & distributions"),
            ],
            "Mask Tools": [
                ("Mask Builder", "Visual mask construction"),
                ("MaskGen (PACK)", "Generate optimal masks from stats"),
                ("PolicyGen (PACK)", "Policy-compliant mask generation"),
            ],
            "Rule Tools": [
                ("Rule Builder", "Visual rule construction & preview"),
                ("RuleGen (PACK)", "Reverse-engineer rules from passwords"),
                ("PCFG Rule Editor", "Edit PCFG rulesets for policies"),
            ],
            "Attack Launcher": [
                ("Hashcat Command Builder", "Build & launch hashcat commands"),
            ],
            "Utilities": [
                ("Web Scraper Generator", "Generate web scraping scripts"),
            ],
        }

        for cat_name, tools in categories.items():
            layout.addWidget(self._category_block(cat_name, tools))

        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ── UI builders ──────────────────────────────────────────────

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "font-size: 18px; font-weight: bold; margin-top: 12px; "
            "border-bottom: 1px solid #45475a; padding-bottom: 4px;"
        )
        return lbl

    def _decision_block(self, question: str, desc: str,
                        tools: list[tuple[str, str]]) -> QWidget:
        block = QWidget()
        lay = QVBoxLayout(block)
        lay.setContentsMargins(0, 4, 0, 8)
        lay.setSpacing(4)

        q = QLabel(f"<b>{question}</b>")
        q.setStyleSheet("font-size: 14px; color: #89b4fa;")
        lay.addWidget(q)

        d = QLabel(desc)
        d.setStyleSheet("color: #a6adc8; font-size: 12px; margin-left: 12px;")
        lay.addWidget(d)

        for tool_name, tool_desc in tools:
            lay.addWidget(self._tool_link(tool_name, tool_desc, indent=24))

        return block

    def _workflow_block(self, title: str,
                        steps: list[tuple[str, str]]) -> QWidget:
        block = QWidget()
        lay = QVBoxLayout(block)
        lay.setContentsMargins(0, 4, 0, 8)
        lay.setSpacing(2)

        t = QLabel(f"<b>{title}</b>")
        t.setStyleSheet("font-size: 14px; color: #f9e2af;")
        lay.addWidget(t)

        arrows: list[str] = []
        for i, (tool_name, step_desc) in enumerate(steps):
            prefix = "  →  " if i > 0 else "     "
            arrows.append(f"{prefix}<b>{i+1}.</b> ")
            lay.addWidget(self._tool_link(tool_name, step_desc, indent=24))

        return block

    def _category_block(self, cat_name: str,
                        tools: list[tuple[str, str]]) -> QWidget:
        block = QWidget()
        lay = QVBoxLayout(block)
        lay.setContentsMargins(0, 2, 0, 6)
        lay.setSpacing(2)

        c = QLabel(f"<b>{cat_name}</b>")
        c.setStyleSheet("font-size: 13px; color: #cba6f7;")
        lay.addWidget(c)

        for tool_name, tool_desc in tools:
            lay.addWidget(self._tool_link(tool_name, tool_desc, indent=16))

        return block

    def _tool_link(self, name: str, desc: str, indent: int = 0) -> QLabel:
        tool_id = _TOOL_IDS.get(name)
        lbl = QLabel(
            f"<a href='tool:{tool_id}' style='color: #89dceb; text-decoration: none;'>"
            f"{name}</a> — {desc}"
        )
        lbl.setStyleSheet(f"margin-left: {indent}px; font-size: 12px;")
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        lbl.setOpenExternalLinks(False)
        if tool_id is not None:
            lbl.linkActivated.connect(lambda link: self._on_link(link))
        return lbl

    def _on_link(self, link: str) -> None:
        if link.startswith("tool:"):
            try:
                tool_id = int(link.split(":")[1])
                self._navigate(tool_id)
            except (ValueError, IndexError):
                pass
