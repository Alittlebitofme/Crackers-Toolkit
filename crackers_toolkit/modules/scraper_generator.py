"""Module 19: Web Scraper Generator — build a self-contained script that
scrapes text from websites, extracts words, and deduplicates them.

The GUI does NOT perform any scraping.  It only generates a runnable
Bash or Python script that the user executes externally.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from .base_module import BaseModule

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# Pool of real browser User-Agent strings for rotation
_UA_POOL = [
    # Chrome – Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    # Chrome – Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Chrome – Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Firefox – Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    # Firefox – Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    # Firefox – Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
    # Edge – Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    # Safari – Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
]

DEFAULT_STOP_WORDS = (
    "a about above after again against all am an and any are aren't as at be because "
    "been before being below between both but by can't cannot could couldn't did didn't "
    "do does doesn't doing don't down during each few for from further get got had "
    "hadn't has hasn't have haven't having he her here hers herself him himself his how "
    "i if in into is isn't it its itself just ll let me more most mustn't my myself no "
    "nor not of off on once only or other our ours ourselves out over own re s same "
    "shan't she should shouldn't so some such t than that the their theirs them "
    "themselves then there these they this those through to too under until up ve very "
    "was wasn't we were weren't what when where which while who whom why will with won't "
    "would wouldn't you your yours yourself yourselves"
)


class _ScriptHighlighter(QSyntaxHighlighter):
    """Simple keyword-based syntax highlighter for generated scripts."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rules: list[tuple] = []

        # Python / Bash keywords
        kw_fmt = QTextCharFormat()
        kw_fmt.setForeground(QColor("#cba6f7"))  # Catppuccin mauve
        kw_fmt.setFontWeight(QFont.Weight.Bold)
        keywords = [
            r"\bimport\b", r"\bfrom\b", r"\bdef\b", r"\bclass\b",
            r"\bif\b", r"\belse\b", r"\belif\b", r"\bfor\b", r"\bin\b",
            r"\bwhile\b", r"\breturn\b", r"\btry\b", r"\bexcept\b",
            r"\bwith\b", r"\bas\b", r"\bnot\b", r"\band\b", r"\bor\b",
            r"\bTrue\b", r"\bFalse\b", r"\bNone\b",
            r"\bset\b", r"\becho\b", r"\bfi\b", r"\bthen\b", r"\bdo\b",
            r"\bdone\b", r"\bfunction\b", r"\blocal\b", r"\bgrep\b",
            r"\bsort\b", r"\bawk\b", r"\bsed\b", r"\btr\b", r"\bcp\b",
        ]
        import re as _re
        for pattern in keywords:
            self._rules.append((_re.compile(pattern), kw_fmt))

        # Strings
        str_fmt = QTextCharFormat()
        str_fmt.setForeground(QColor("#a6e3a1"))  # Catppuccin green
        self._rules.append((_re.compile(r'"[^"]*"'), str_fmt))
        self._rules.append((_re.compile(r"'[^']*'"), str_fmt))

        # Comments
        cmt_fmt = QTextCharFormat()
        cmt_fmt.setForeground(QColor("#6c7086"))  # Catppuccin overlay0
        cmt_fmt.setFontItalic(True)
        self._rules.append((_re.compile(r"#.*$"), cmt_fmt))

        # Numbers
        num_fmt = QTextCharFormat()
        num_fmt.setForeground(QColor("#fab387"))  # Catppuccin peach
        self._rules.append((_re.compile(r"\b\d+\b"), num_fmt))

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for regex, fmt in self._rules:
            for m in regex.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


class ScraperGeneratorModule(BaseModule):
    MODULE_NAME = "Web Scraper Generator"
    MODULE_DESCRIPTION = (
        "Generate a ready-to-run script that scrapes text from a website, "
        "extracts individual words, deduplicates them, and optionally removes "
        "stop words. The GUI just builds the script — it never scrapes."
    )
    MODULE_CATEGORY = "Wordlist Generation"

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        super().__init__(parent)

    # ── Input ────────────────────────────────────────────────────
    def build_input_section(self, layout: QVBoxLayout) -> None:
        layout.addWidget(QLabel("Target URL(s) — one per line:"))
        self._urls = QTextEdit()
        self._urls.setMaximumHeight(80)
        self._urls.setPlaceholderText("https://example.com\nhttps://example.com/wiki/...")
        _url_tip = QHBoxLayout()
        _url_tip.addWidget(self._info_icon("One or more URLs to scrape. One per line."))
        _url_tip.addStretch()
        layout.addLayout(_url_tip)
        layout.addWidget(self._urls)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Crawl depth:"))
        row1.addWidget(self._info_icon(
            "0 = single page only. 1 = follow links one level. "
            "Higher = deeper crawl. Be careful with large sites."
        ))
        self._depth = QSpinBox()
        self._depth.setRange(0, 5)
        self._depth.setValue(0)
        row1.addWidget(self._depth)

        row1.addWidget(QLabel("Request delay (sec):"))
        row1.addWidget(self._info_icon("Seconds to wait between requests. Be polite to servers."))
        self._delay = QSpinBox()
        self._delay.setRange(0, 60)
        self._delay.setValue(1)
        row1.addWidget(self._delay)
        row1.addStretch()
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("URL filter (regex):"))
        row2.addWidget(self._info_icon("Only follow links matching this pattern."))
        self._url_filter = QLineEdit()
        self._url_filter.setPlaceholderText(r"https://example\.com/wiki/.*")
        row2.addWidget(self._url_filter, stretch=1)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("User-Agent:"))
        row3.addWidget(self._info_icon(
            "Fallback browser User-Agent string used when UA rotation is "
            "disabled. When rotation is ON, this field is ignored and a "
            "random UA is picked from a pool of 12 real browser strings."
        ))
        self._ua = QLineEdit(DEFAULT_USER_AGENT)
        row3.addWidget(self._ua, stretch=1)
        layout.addLayout(row3)

    # ── Parameters ───────────────────────────────────────────────
    def build_params_section(self, layout: QVBoxLayout) -> None:
        # Text processing
        proc_grp = QGroupBox("Text Processing Options")
        pl = QVBoxLayout(proc_grp)
        self._tokenize = self.create_checkbox(pl, "Tokenize into words", True,
            "Split text on whitespace/punctuation into individual words.")
        self._lowercase = self.create_checkbox(pl, "Lowercase all", False,
            "Convert all words to lowercase before deduplication.")
        self._sort_unique = self.create_checkbox(pl, "Sort & unique", True,
            "Sort and remove duplicate words.")
        self._strip_html = self.create_checkbox(pl, "Remove HTML tags", True,
            "Strip residual HTML markup.")
        self._rm_numbers = self.create_checkbox(pl, "Remove numbers-only tokens", False,
            "Discard tokens that are purely numeric.")

        minmax = QHBoxLayout()
        minmax.addWidget(QLabel("Min word length:"))
        minmax.addWidget(self._info_icon("Discard words shorter than this."))
        self._min_len = QSpinBox(); self._min_len.setRange(1, 128); self._min_len.setValue(1)
        minmax.addWidget(self._min_len)
        minmax.addWidget(QLabel("Max word length:"))
        minmax.addWidget(self._info_icon("Discard words longer than this."))
        self._max_len = QSpinBox(); self._max_len.setRange(1, 1024); self._max_len.setValue(64)
        minmax.addWidget(self._max_len)
        minmax.addStretch()
        pl.addLayout(minmax)
        layout.addWidget(proc_grp)

        # Stop words
        stop_grp = QGroupBox("Stop Word Filtering")
        sl = QVBoxLayout(stop_grp)
        self._stop_enabled = self.create_checkbox(sl, "Enable stop word filtering", False,
            "Remove common filler words (the, a, is, etc.). Leave OFF for "
            "password cracking — stop words like 'love' and 'the' appear in many passwords.")
        self._stop_words = QTextEdit()
        self._stop_words.setMaximumHeight(80)
        self._stop_words.setPlainText(DEFAULT_STOP_WORDS)
        _sw_tip = QHBoxLayout()
        _sw_tip.addWidget(self._info_icon("Editable stop word list. One word per token, space-separated."))
        _sw_tip.addStretch()
        sl.addLayout(_sw_tip)
        sl.addWidget(self._stop_words)

        load_stop = QPushButton("Load stop words from file…")
        load_stop.clicked.connect(self._load_stop_words)
        sl.addWidget(load_stop)
        layout.addWidget(stop_grp)
        # Anti-detection options
        detect_grp = QGroupBox("Anti-Detection Options")
        dl = QVBoxLayout(detect_grp)
        self._rotate_ua = self.create_checkbox(dl, "Rotate User-Agent", True,
            "Pick a random User-Agent from a pool of 12 real browser strings "
            "for each request. Greatly reduces fingerprinting.")
        self._real_headers = self.create_checkbox(dl, "Send realistic browser headers", True,
            "Add Accept, Accept-Language, Accept-Encoding, DNT, Sec-Fetch-* "
            "and other headers that real browsers send. Missing headers are a "
            "common bot fingerprint.")
        self._jitter = self.create_checkbox(dl, "Random delay jitter (\u00b150%)", True,
            "Randomize the delay between requests by \u00b150%. A fixed interval "
            "between requests is a strong bot signal.")
        retry_row = QHBoxLayout()
        retry_row.addWidget(QLabel("Max retries per request:"))
        retry_row.addWidget(self._info_icon(
            "How many times to retry a failed request with exponential "
            "backoff (2\u02e2 + random). 0 = no retries."
        ))
        self._retries = QSpinBox()
        self._retries.setRange(0, 10)
        self._retries.setValue(3)
        retry_row.addWidget(self._retries)
        retry_row.addStretch()
        dl.addLayout(retry_row)
        proxy_row = QHBoxLayout()
        proxy_row.addWidget(QLabel("Proxy URL:"))
        proxy_row.addWidget(self._info_icon(
            "Route all requests through this proxy. "
            "Supports http://, https://, socks5://. Leave empty for direct."
        ))
        self._proxy = QLineEdit()
        self._proxy.setPlaceholderText("socks5://127.0.0.1:9050  or  http://user:pass@host:port")
        proxy_row.addWidget(self._proxy, stretch=1)
        dl.addLayout(proxy_row)
        layout.addWidget(detect_grp)
        # Script type
        type_grp = QGroupBox("Script Type")
        tl = QHBoxLayout(type_grp)
        self._type_group = QButtonGroup(self)
        self._bash_radio = QRadioButton("Bash (.sh)")
        self._python_radio = QRadioButton("Python (.py)")
        self._ps_radio = QRadioButton("PowerShell (.ps1)")
        self._bash_radio.setChecked(True)
        self._type_group.addButton(self._bash_radio, 0)
        self._type_group.addButton(self._python_radio, 1)
        self._type_group.addButton(self._ps_radio, 2)
        tl.addWidget(self._bash_radio)
        tl.addWidget(self._python_radio)
        import platform
        if platform.system() == "Windows":
            tl.addWidget(self._ps_radio)
        tl.addStretch()
        layout.addWidget(type_grp)

    # ── Output ───────────────────────────────────────────────────
    def build_output_section(self, layout: QVBoxLayout) -> None:
        layout.addWidget(QLabel("Code preview (editable before saving):"))
        self._code_preview = QTextEdit()
        self._code_preview.setFont(QFont("Consolas", 10))
        self._code_preview.setStyleSheet("font-family: Consolas, 'DejaVu Sans Mono', monospace;")
        self._code_preview.setMinimumHeight(200)
        self._highlighter = _ScriptHighlighter(self._code_preview.document())
        layout.addWidget(self._code_preview)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save Script")
        save_btn.setToolTip("Save the generated script to disk.")
        save_btn.clicked.connect(self._save_script)
        btn_row.addWidget(save_btn)

        load_btn = QPushButton("Load Scraped Wordlist")
        load_btn.setToolTip("Import results after running the script externally.")
        load_btn.clicked.connect(self._load_results)
        btn_row.addWidget(load_btn)

        self.send_to_menu(btn_row, ["Hashcat Command Builder", "Element Extractor"])
        btn_row.addStretch()
        layout.addLayout(btn_row)

    # ── Generation ───────────────────────────────────────────────
    def run_tool(self) -> None:
        if self._python_radio.isChecked():
            code = self._gen_python()
        elif self._ps_radio.isChecked():
            code = self._gen_powershell()
        else:
            code = self._gen_bash()
        self._code_preview.setPlainText(code)

    def _params(self) -> dict:
        urls = [u.strip() for u in self._urls.toPlainText().splitlines() if u.strip()]
        stop_list = []
        if self._stop_enabled.isChecked():
            stop_list = self._stop_words.toPlainText().split()
        return dict(
            urls=urls,
            depth=self._depth.value(),
            delay=self._delay.value(),
            url_filter=self._url_filter.text().strip(),
            user_agent=self._ua.text().strip(),
            tokenize=self._tokenize.isChecked(),
            lowercase=self._lowercase.isChecked(),
            sort_unique=self._sort_unique.isChecked(),
            strip_html=self._strip_html.isChecked(),
            rm_numbers=self._rm_numbers.isChecked(),
            min_len=self._min_len.value(),
            max_len=self._max_len.value(),
            stop_words=stop_list,
            output_file="scraped_wordlist.txt",
            rotate_ua=self._rotate_ua.isChecked(),
            real_headers=self._real_headers.isChecked(),
            jitter=self._jitter.isChecked(),
            retries=self._retries.value(),
            proxy=self._proxy.text().strip(),
        )

    # ── Bash script generation ───────────────────────────────────
    def _gen_bash(self) -> str:
        p = self._params()
        urls_str = " ".join(f'"{u}"' for u in p["urls"]) if p["urls"] else '"https://example.com"'

        lines = [
            "#!/usr/bin/env bash",
            "# Web Scraper Script — generated by Cracker's Toolkit",
            "# Run: chmod +x script.sh && ./script.sh",
            "#",
            "# Dependencies: curl, sed, tr, sort",
            f'# Crawl depth: {p["depth"]}, delay: {p["delay"]}s',
            "",
            "set -euo pipefail",
            "",
            f'URLS=({urls_str})',
            f'DEPTH={p["depth"]}',
            f'DELAY={p["delay"]}',
            f'OUTPUT="{p["output_file"]}"',
            f'MIN_LEN={p["min_len"]}',
            f'MAX_LEN={p["max_len"]}',
            f'MAX_RETRIES={p["retries"]}',
            f'JITTER={"1" if p["jitter"] else "0"}',
        ]
        if p["url_filter"]:
            lines.append(f'URL_FILTER="{p["url_filter"]}"')
        if p["stop_words"]:
            sw = " ".join(p["stop_words"])
            lines.append(f'STOP_WORDS="{sw}"')
        if p["proxy"]:
            lines.append(f'PROXY="{p["proxy"]}"')

        # UA pool or single UA
        if p["rotate_ua"]:
            lines += ["", "# User-Agent rotation pool", "UA_POOL=("]
            for ua in _UA_POOL:
                lines.append(f'  "{ua}"')
            lines += [
                ")",
                "",
                "pick_ua() {",
                '  echo "${UA_POOL[$((RANDOM % ${#UA_POOL[@]}))]}"',
                "}",
            ]
        else:
            lines += [
                f'USER_AGENT="{p["user_agent"]}"',
                "",
                "pick_ua() {",
                '  echo "$USER_AGENT"',
                "}",
            ]

        # Jitter sleep function
        lines += [
            "",
            "do_sleep() {",
            '  if [ "$JITTER" = "1" ] && [ "$DELAY" -gt 0 ]; then',
            '    # Random jitter ±50%',
            '    local half=$(( DELAY / 2 + 1 ))',
            '    local jitter=$(( RANDOM % half ))',
            '    local sign=$(( RANDOM % 2 ))',
            '    if [ "$sign" = "0" ]; then',
            '      sleep $(( DELAY - jitter ))',
            '    else',
            '      sleep $(( DELAY + jitter ))',
            '    fi',
            '  else',
            '    sleep "$DELAY"',
            '  fi',
            "}",
        ]

        # Dependencies check
        lines += [
            "",
            "# Check dependencies",
            'for cmd in curl sed tr sort; do',
            '  command -v "$cmd" >/dev/null 2>&1 || { echo "Missing: $cmd"; exit 1; }',
            "done",
            "",
            'TMPDIR=$(mktemp -d)',
            'trap "rm -rf $TMPDIR" EXIT',
        ]

        # Fetch function with retry, headers, proxy, UA rotation
        lines += [
            "",
            "fetch_page() {",
            '  local url="$1"',
            '  local referer="${2:-}"',
            '  local ua',
            '  ua=$(pick_ua)',
            '  local curl_args=(-sL -A "$ua" --connect-timeout 15 --max-time 30)',
        ]
        if p["real_headers"]:
            lines += [
                '  curl_args+=(',
                '    -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"',
                '    -H "Accept-Language: en-US,en;q=0.9"',
                '    -H "Accept-Encoding: gzip, deflate"',
                '    -H "DNT: 1"',
                '    -H "Connection: keep-alive"',
                '    -H "Upgrade-Insecure-Requests: 1"',
                '  )',
            ]
        lines.append('  [ -n "$referer" ] && curl_args+=(-e "$referer")')
        if p["proxy"]:
            lines.append('  curl_args+=(-x "$PROXY")')
        lines += [
            "",
            '  local attempt=0',
            '  while [ "$attempt" -le "$MAX_RETRIES" ]; do',
            '    local result',
            '    if result=$(curl "${curl_args[@]}" "$url" 2>/dev/null); then',
            '      echo "$result"',
            '      return 0',
            '    fi',
            '    if [ "$attempt" -lt "$MAX_RETRIES" ]; then',
            '      local backoff=$(( (1 << (attempt + 1)) + RANDOM % 3 ))',
            '      echo "  Retry $((attempt+1))/$MAX_RETRIES for $url (waiting ${backoff}s)" >&2',
            '      sleep "$backoff"',
            '    else',
            '      echo "  Failed after $((MAX_RETRIES+1)) attempts: $url" >&2',
            '    fi',
            '    attempt=$((attempt + 1))',
            '  done',
            '  return 1',
            "}",
        ]

        # Crawl logic
        lines += [
            "",
            "# Crawl and collect text",
            'RAW="$TMPDIR/raw.txt"',
            '> "$RAW"',
            "",
            'for url in "${URLS[@]}"; do',
            '  echo "Fetching: $url"',
            '  fetch_page "$url" "" >> "$RAW" || true',
            '  do_sleep',
        ]

        if p["depth"] > 0:
            lines += [
                '  # Follow links (depth 1)',
                '  links=$(fetch_page "$url" "" 2>/dev/null | grep -oP \'href="\\K[^"]+\' | head -100) || true',
                '  for link in $links; do',
            ]
            if p["url_filter"]:
                lines.append('    [[ "$link" =~ $URL_FILTER ]] || continue')
            lines += [
                '    echo "  Following: $link"',
                '    fetch_page "$link" "$url" >> "$RAW" || true',
                '    do_sleep',
                '  done',
            ]

        lines += [
            "done",
            "",
            "# Process text",
            'PROCESSED="$TMPDIR/processed.txt"',
            'cp "$RAW" "$PROCESSED"',
            "",
        ]

        if p["strip_html"]:
            lines.append('sed -i "s/<[^>]*>//g" "$PROCESSED"')

        if p["tokenize"]:
            lines.append("# Tokenize")
            lines.append('tr -cs "[:alnum:]" "\\n" < "$PROCESSED" > "$TMPDIR/tokens.txt"')
            lines.append('mv "$TMPDIR/tokens.txt" "$PROCESSED"')

        if p["lowercase"]:
            lines.append('tr "[:upper:]" "[:lower:]" < "$PROCESSED" > "$TMPDIR/lower.txt"')
            lines.append('mv "$TMPDIR/lower.txt" "$PROCESSED"')

        if p["rm_numbers"]:
            lines.append('grep -vP "^\\d+$" "$PROCESSED" > "$TMPDIR/nonum.txt" || true')
            lines.append('mv "$TMPDIR/nonum.txt" "$PROCESSED"')

        # Length filter
        lines.append(f'awk \'length >= {p["min_len"]} && length <= {p["max_len"]}\' "$PROCESSED" > "$TMPDIR/lenfilter.txt"')
        lines.append('mv "$TMPDIR/lenfilter.txt" "$PROCESSED"')

        if p["stop_words"]:
            lines.append("")
            lines.append("# Remove stop words")
            lines.append('STOP_FILE="$TMPDIR/stopwords.txt"')
            lines.append('echo "$STOP_WORDS" | tr " " "\\n" > "$STOP_FILE"')
            lines.append('grep -vxFf "$STOP_FILE" "$PROCESSED" > "$TMPDIR/nostop.txt" || true')
            lines.append('mv "$TMPDIR/nostop.txt" "$PROCESSED"')

        if p["sort_unique"]:
            lines.append("# Sort & deduplicate")
            lines.append('sort -u "$PROCESSED" -o "$PROCESSED"')

        lines += [
            "",
            'cp "$PROCESSED" "$OUTPUT"',
            'LINES=$(wc -l < "$OUTPUT")',
            'echo "Done — $LINES words written to $OUTPUT"',
        ]
        return "\n".join(lines) + "\n"

    # ── Python script generation ─────────────────────────────────
    def _gen_python(self) -> str:
        p = self._params()
        urls_repr = repr(p["urls"]) if p["urls"] else '["https://example.com"]'
        stop_repr = repr(p["stop_words"]) if p["stop_words"] else "[]"

        lines = [
            '#!/usr/bin/env python3',
            '"""Web Scraper — generated by Cracker\'s Toolkit.',
            '',
            'Dependencies: pip install requests beautifulsoup4',
            '"""',
            '',
            'import random, re, sys, time',
            'from pathlib import Path',
            'from urllib.parse import urljoin',
            '',
            'try:',
            '    import requests',
            '    from bs4 import BeautifulSoup',
            'except ImportError:',
            '    sys.exit("Install deps: pip install requests beautifulsoup4")',
            '',
            f'URLS = {urls_repr}',
            f'DEPTH = {p["depth"]}',
            f'DELAY = {p["delay"]}',
            f'URL_FILTER = {repr(p["url_filter"])}',
            f'OUTPUT = {repr(p["output_file"])}',
            f'MIN_LEN = {p["min_len"]}',
            f'MAX_LEN = {p["max_len"]}',
            f'STOP_WORDS = set({stop_repr})',
            f'MAX_RETRIES = {p["retries"]}',
            f'JITTER = {p["jitter"]}',
        ]

        if p["rotate_ua"]:
            lines += ['', 'UA_POOL = [']
            for ua in _UA_POOL:
                lines.append(f'    {repr(ua)},')
            lines.append(']')
        else:
            lines.append(f'USER_AGENT = {repr(p["user_agent"])}')

        if p["proxy"]:
            lines.append(f'PROXY = {repr(p["proxy"])}')

        # Session setup
        lines += ['', 'session = requests.Session()']
        if not p["rotate_ua"]:
            lines.append('session.headers["User-Agent"] = USER_AGENT')
        if p["proxy"]:
            lines.append('session.proxies = {"http": PROXY, "https": PROXY}')
        if p["real_headers"]:
            lines += [
                'session.headers.update({',
                '    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",',
                '    "Accept-Language": "en-US,en;q=0.9",',
                '    "Accept-Encoding": "gzip, deflate, br",',
                '    "DNT": "1",',
                '    "Connection": "keep-alive",',
                '    "Upgrade-Insecure-Requests": "1",',
                '    "Sec-Fetch-Dest": "document",',
                '    "Sec-Fetch-Mode": "navigate",',
                '    "Sec-Fetch-Site": "none",',
                '    "Sec-Fetch-User": "?1",',
                '})',
            ]

        # Wait helper
        lines += [
            '',
            '',
            'def wait():',
            '    """Sleep with optional jitter."""',
            '    d = DELAY',
            '    if JITTER and d > 0:',
            '        d = d * random.uniform(0.5, 1.5)',
            '    time.sleep(d)',
        ]

        # Fetch with retry
        lines += [
            '',
            '',
            'def fetch(url: str, referer: str = "") -> str:',
            '    """Fetch a URL with retry and optional UA rotation."""',
            '    for attempt in range(MAX_RETRIES + 1):',
            '        try:',
        ]
        if p["rotate_ua"]:
            lines.append('            session.headers["User-Agent"] = random.choice(UA_POOL)')
        lines += [
            '            if referer:',
            '                session.headers["Referer"] = referer',
            '            r = session.get(url, timeout=15)',
            '            r.raise_for_status()',
            '            return r.text',
            '        except Exception as e:',
            '            if attempt < MAX_RETRIES:',
            '                backoff = 2 ** (attempt + 1) + random.random()',
            '                print(f"  Retry {attempt+1}/{MAX_RETRIES} for {url} (waiting {backoff:.1f}s): {e}")',
            '                time.sleep(backoff)',
            '            else:',
            '                print(f"  Failed after {MAX_RETRIES+1} attempts: {url}: {e}")',
            '    return ""',
        ]

        # Link extraction
        lines += [
            '',
            '',
            'def extract_links(html: str, base: str) -> list[str]:',
            '    soup = BeautifulSoup(html, "html.parser")',
            '    links = []',
            '    for a in soup.find_all("a", href=True):',
            '        full = urljoin(base, a["href"])',
            '        if URL_FILTER and not re.search(URL_FILTER, full):',
            '            continue',
            '        links.append(full)',
            '    return links',
        ]

        # Crawl
        lines += [
            '',
            '',
            'visited: set[str] = set()',
            'raw_texts: list[str] = []',
            '',
            '',
            'def crawl(url: str, depth: int, referer: str = "") -> None:',
            '    if url in visited:',
            '        return',
            '    visited.add(url)',
            '    print(f"Fetching: {url}")',
            '    html = fetch(url, referer)',
            '    if not html:',
            '        return',
            '    soup = BeautifulSoup(html, "html.parser")',
        ]

        if p["strip_html"]:
            lines.append('    raw_texts.append(soup.get_text(separator=" "))')
        else:
            lines.append('    raw_texts.append(html)')

        lines += [
            '    if depth > 0:',
            '        for link in extract_links(html, url):',
            '            wait()',
            '            crawl(link, depth - 1, referer=url)',
            '',
            '',
            'for u in URLS:',
            '    crawl(u, DEPTH)',
            '    wait()',
            '',
            'text = " ".join(raw_texts)',
            '',
        ]

        if p["tokenize"]:
            lines.append('words = re.findall(r"[A-Za-z0-9]+", text)')
        else:
            lines.append('words = text.split()')

        if p["lowercase"]:
            lines.append('words = [w.lower() for w in words]')

        if p["rm_numbers"]:
            lines.append('words = [w for w in words if not w.isdigit()]')

        lines.append(f'words = [w for w in words if {p["min_len"]} <= len(w) <= {p["max_len"]}]')

        if p["stop_words"]:
            lines.append('words = [w for w in words if w.lower() not in STOP_WORDS]')

        if p["sort_unique"]:
            lines.append('words = sorted(set(words))')

        lines += [
            '',
            'Path(OUTPUT).write_text("\\n".join(words) + "\\n", encoding="utf-8")',
            'print(f"Done — {len(words)} words written to {OUTPUT}")',
        ]
        return "\n".join(lines) + "\n"

    # ── PowerShell script generation ─────────────────────────────
    def _gen_powershell(self) -> str:
        p = self._params()
        urls_ps = ", ".join(f'"{u}"' for u in p["urls"]) if p["urls"] else '"https://example.com"'
        jitter_ps = "$true" if p["jitter"] else "$false"

        lines = [
            "# Web Scraper Script — generated by Cracker's Toolkit",
            "# Run: powershell -ExecutionPolicy Bypass -File scraper.ps1",
            "#",
            f"# Crawl depth: {p['depth']}, delay: {p['delay']}s",
            "",
            f"$urls = @({urls_ps})",
            f"$depth = {p['depth']}",
            f"$delay = {p['delay']}",
            f'$output = "{p["output_file"]}"',
            f"$minLen = {p['min_len']}",
            f"$maxLen = {p['max_len']}",
            f"$maxRetries = {p['retries']}",
            f"$jitter = {jitter_ps}",
        ]
        if p["url_filter"]:
            lines.append(f'$urlFilter = "{p["url_filter"]}"')
        else:
            lines.append('$urlFilter = ""')
        if p["stop_words"]:
            sw_ps = ", ".join(f'"{w}"' for w in p["stop_words"])
            lines.append(f"$stopWords = @({sw_ps})")
        else:
            lines.append("$stopWords = @()")
        if p["proxy"]:
            lines.append(f'$proxy = "{p["proxy"]}"')

        # UA pool or single UA
        if p["rotate_ua"]:
            lines += ["", "$uaPool = @("]
            for ua in _UA_POOL:
                lines.append(f'    "{ua}"')
            lines += [")", ""]
        else:
            lines.append(f'$userAgent = "{p["user_agent"]}"')

        # Jitter sleep function
        lines += [
            "",
            "function Do-Sleep {",
            "    if ($jitter -and $delay -gt 0) {",
            "        $min = [math]::Max(1, [int]($delay * 500))",
            "        $max = [int]($delay * 1500)",
            "        $d = Get-Random -Minimum $min -Maximum ($max + 1)",
            "        Start-Sleep -Milliseconds $d",
            "    } else {",
            "        Start-Sleep -Seconds $delay",
            "    }",
            "}",
        ]

        # Fetch function with retry, headers, proxy, UA rotation
        lines += [
            "",
            "function Fetch-Page($url, $referer) {",
        ]
        if p["rotate_ua"]:
            lines.append("    $ua = $uaPool | Get-Random")
        else:
            lines.append("    $ua = $userAgent")
        # Build headers
        if p["real_headers"]:
            lines += [
                '    $headers = @{',
                '        "Accept" = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"',
                '        "Accept-Language" = "en-US,en;q=0.9"',
                '        "Accept-Encoding" = "gzip, deflate"',
                '        "DNT" = "1"',
                '        "Connection" = "keep-alive"',
                '        "Upgrade-Insecure-Requests" = "1"',
                '    }',
            ]
            lines.append('    if ($referer) { $headers["Referer"] = $referer }')
        else:
            lines += [
                '    $headers = @{}',
                '    if ($referer) { $headers["Referer"] = $referer }',
            ]

        iwr_args = "-Uri $url -UserAgent $ua -UseBasicParsing -TimeoutSec 15 -Headers $headers"
        if p["proxy"]:
            iwr_args += " -Proxy $proxy"
        lines += [
            '    $attempt = 0',
            '    while ($attempt -le $maxRetries) {',
            "        try {",
            f"            $response = Invoke-WebRequest {iwr_args}",
            "            return $response.Content",
            "        } catch {",
            '            if ($attempt -lt $maxRetries) {',
            '                $backoff = [math]::Pow(2, $attempt + 1) + (Get-Random -Minimum 0 -Maximum 3)',
            '                Write-Host "  Retry $($attempt+1)/$maxRetries for $url (waiting ${backoff}s): $_"',
            '                Start-Sleep -Seconds $backoff',
            '            } else {',
            '                Write-Host "  Failed after $($maxRetries+1) attempts: $url : $_"',
            '            }',
            "        }",
            '        $attempt++',
            "    }",
            '    return ""',
            "}",
        ]

        # Main crawl loop
        lines += [
            "",
            "$allText = @()",
            "",
            "foreach ($url in $urls) {",
            '    Write-Host "Fetching: $url"',
            '    $html = Fetch-Page $url ""',
            "    if ($html) {",
        ]

        if p["strip_html"]:
            lines.append('        $text = $html -replace "<[^>]*>", " "')
        else:
            lines.append("        $text = $html")

        lines += [
            "        $allText += $text",
            "    }",
            "    Do-Sleep",
        ]

        if p["depth"] > 0:
            lines += [
                "    # Follow links (depth 1)",
                '    $links = [regex]::Matches($html, \'href="([^"]+)"\') | ForEach-Object { $_.Groups[1].Value } | Select-Object -First 100',
                "    foreach ($link in $links) {",
            ]
            if p["url_filter"]:
                lines.append("        if ($link -notmatch $urlFilter) { continue }")
            lines += [
                '        Write-Host "  Following: $link"',
                '        $subHtml = Fetch-Page $link $url',
                "        if ($subHtml) {",
            ]
            if p["strip_html"]:
                lines.append('            $allText += ($subHtml -replace "<[^>]*>", " ")')
            else:
                lines.append("            $allText += $subHtml")
            lines += [
                "        }",
                "        Do-Sleep",
                "    }",
            ]

        lines += [
            "}",
            "",
            "$combined = $allText -join ' '",
            "",
        ]

        if p["tokenize"]:
            lines.append('$words = [regex]::Matches($combined, "[A-Za-z0-9]+") | ForEach-Object { $_.Value }')
        else:
            lines.append("$words = $combined -split '\\s+'")

        if p["lowercase"]:
            lines.append("$words = $words | ForEach-Object { $_.ToLower() }")

        if p["rm_numbers"]:
            lines.append('$words = $words | Where-Object { $_ -notmatch "^\\d+$" }')

        lines.append(f"$words = $words | Where-Object {{ $_.Length -ge $minLen -and $_.Length -le $maxLen }}")

        if p["stop_words"]:
            lines.append("$words = $words | Where-Object { $stopWords -notcontains $_.ToLower() }")

        if p["sort_unique"]:
            lines.append("$words = $words | Sort-Object -Unique")

        lines += [
            "",
            "$words | Out-File -FilePath $output -Encoding UTF8",
            'Write-Host "Done — $($words.Count) words written to $output"',
        ]
        return "\n".join(lines) + "\n"


    # ── Helpers ──────────────────────────────────────────────────
    def _load_stop_words(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load stop words", "", "Text Files (*.txt);;All (*)")
        if path:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                self._stop_words.setPlainText(f.read())

    def _save_script(self) -> None:
        if self._python_radio.isChecked():
            filt = "Python Scripts (*.py);;All Files (*)"
            default = "scraper.py"
        elif self._ps_radio.isChecked():
            filt = "PowerShell Scripts (*.ps1);;All Files (*)"
            default = "scraper.ps1"
        else:
            filt = "Bash Scripts (*.sh);;All Files (*)"
            default = "scraper.sh"
        path, _ = QFileDialog.getSaveFileName(self, "Save script", str(self._default_output_dir() / default), filt)
        if not path:
            return
        Path(path).write_text(self._code_preview.toPlainText(), encoding="utf-8")
        self._output_log.append(f"Script saved to {path}")

    def _load_results(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load scraped wordlist", "", "Text Files (*.txt);;All (*)")
        if path:
            self._output_path = path
            head: list[str] = []
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        head.append(line)
                        if len(head) >= 1000:
                            break
            except OSError:
                self._output_log.append(f"Error reading {path}")
                return
            size = Path(path).stat().st_size
            size_str = f"{size:,} bytes" if size < 1_048_576 else f"{size / 1_048_576:.1f} MB"
            self._output_log.clear()
            self._output_log.append(f"Loaded preview from {path} ({size_str})\n")
            self._output_log.append("".join(head))

    def receive_from(self, path: str) -> None:
        """Accept a URL list file."""
        if Path(path).is_file():
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                self._urls.setPlainText(f.read())
