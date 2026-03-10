# Cracker's Toolkit — Feature Overview

A single desktop GUI that replaces 21 separate command-line tools for password cracking workflows.

---

## Core Features

**All-in-one interface** — 21 tools organized into 8 categories. No more switching between terminals or remembering CLI flags.

**Tooltips everywhere** — Every input control has a hover tooltip explaining what it does, what values are typical, and why you'd change it.

**Cross-module data transfer** — "Send to…" buttons pass output files directly between tools. Generate a wordlist → send it to Hashcat. Extract a hash → send it to the Attack Launcher with the correct mode pre-selected.

**Non-blocking execution** — All tool operations run in background threads. The GUI never freezes. Cancel buttons and progress indicators on every long-running task.

**Standalone executable** — Ships as a single Windows folder (PyInstaller). No Python installation needed.

---

## Tool Highlights

### Generate Wordlists (7 tools)
PRINCE processor, PCFG grammar-based guessing, multi-list combinator, keyboard walk patterns, date/number/PIN generators, and element extraction from existing password lists.

### Clean & Analyze (4 tools)
demeuk-powered wordlist cleaning (encoding fixes, deduplication, length/charset filtering). Statistical analysis with StatsGen. PCFG model training and password scoring.

### Build Masks & Rules (5 tools)
Visual mask builder with live preview. Auto-generate optimized masks from statistics. Visual rule builder supporting all 55 hashcat rule functions with drag-and-drop reordering and live test output.

### Launch Attacks
Full hashcat command builder — select attack mode, hash type (700+ modes with search), wordlists, rules, masks, and advanced options. Launches in an external terminal for native control. Inline rule editing with `-j`/`-k` support.

### Extract Hashes
131 extraction tools (24 hashcat + 107 John the Ripper). Supports encrypted archives, disk images, wallets, databases, Office/PDF documents, Wi-Fi captures, and more. Auto-detects the right extractor, cleans output, and sends directly to Hashcat with the correct hash mode.

### Scrape Websites for Wordlists
Generate Bash, Python, or PowerShell scraper scripts with built-in anti-detection: UA rotation (12 real browser strings), realistic headers, random delay jitter, retry with exponential backoff, and proxy support.

### Markov Chain Statistics
Load and visualize hashcat `.hcstat2` files — character frequency heatmaps, transition tables, position-by-position analysis. Train new `.hcstat2` from password lists. Configure Markov settings and send to Hashcat.

---

## Design Principles

- **No learning curve** — Tooltips and descriptions mean you never need to read a man page.
- **Nothing hidden** — Every tool the toolkit ships with is visible in the sidebar, with a plain-language description.
- **No lock-in** — All generated files (wordlists, masks, rules, scripts) are standard formats that work outside the toolkit.
- **Cross-platform** — Works on Windows and Linux. Path handling adapts automatically.
