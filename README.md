# Cracker's Toolkit GUI

A unified desktop application that brings together 21 password cracking tools into a single, categorized interface with tooltips on every option, cross-module data transfer, and non-blocking execution.

Built with **Python 3.12** and **PyQt6**. Runs on **Windows** and **Linux (Debian/Ubuntu)**. Packaged as a standalone executable via PyInstaller — no Python installation required to run.

---

## Quick Start

### Windows

**From release (recommended):**
1. Download `CrackersToolkit-v1.0-win64.zip` from [Releases](https://github.com/Alittlebitofme/Crackers-Toolkit/releases)
2. Extract the ZIP
3. Run `setup.bat` to download external tools (hashcat, JtR, PRINCE, PCFG)
4. Run `CrackersToolkit.exe`

**From source:**
```bash
pip install PyQt6
python -m crackers_toolkit.main
```

### Linux (Debian/Ubuntu)

**From release:**
1. Download `CrackersToolkit-linux-amd64.tar.gz` from [Releases](https://github.com/Alittlebitofme/Crackers-Toolkit/releases)
2. Extract: `tar xzf CrackersToolkit-linux-amd64.tar.gz`
3. Run: `chmod +x setup.sh CrackersToolkit && ./setup.sh`
4. Launch: `./CrackersToolkit`

**From source:**
```bash
sudo apt install python3 python3-pip
pip install PyQt6
python3 -m crackers_toolkit.main
```

---

## Modules (21 tools across 8 categories)

### Wordlist Generation
| # | Module | Description |
|---|--------|-------------|
| 1 | **PRINCE Processor** | Chain-element password candidate generator using the PRINCE algorithm |
| 2 | **PCFG Guesser** | Generate password guesses from trained probabilistic context-free grammars |
| 3 | **Combinator** | Combine 2–8 wordlists (Cartesian product) via combinatorX |
| 4 | **PRINCE-LING** | Generate PRINCE-optimized wordlists from PCFG training data |
| 5 | **Element Extractor** | Extract base words, numbers, and special patterns from password lists |
| 6 | **Keyboard Walk Generator** | Generate keyboard walk patterns (qwerty, azerty, etc.) |
| 7 | **Date & Number Patterns** | Generate dates, PINs, phone numbers, zip codes, and other numeric patterns |

### Wordlist Cleaning
| # | Module | Description |
|---|--------|-------------|
| 8 | **demeuk Cleaner** | Clean, filter, deduplicate, fix encoding, and transform raw wordlists |

### Wordlist Analysis
| # | Module | Description |
|---|--------|-------------|
| 9 | **PCFG Trainer** | Train probabilistic grammars from password lists for use with PCFG Guesser |
| 10 | **Password Scorer** | Score individual passwords against a trained PCFG model |
| 11 | **StatsGen** | Statistical analysis of password lists — length, charset, mask distributions |

### Mask Tools
| # | Module | Description |
|---|--------|-------------|
| 12 | **Mask Builder** | Visually build hashcat mask files (.hcmask) with live preview |
| 13 | **MaskGen** | Auto-generate optimized mask sets from StatsGen statistics |
| 14 | **PolicyGen** | Generate policy-compliant hashcat masks (min length, required charsets) |

### Rule Tools
| # | Module | Description |
|---|--------|-------------|
| 15 | **Rule Builder** | Visual drag-and-drop hashcat rule builder with 55 rule functions and live preview |
| 16 | **RuleGen** | Reverse-engineer hashcat rules from known password → plaintext pairs |
| 17 | **PCFG Rule Editor** | Post-process PCFG rulesets to enforce password policies |

### Attack Launcher
| # | Module | Description |
|---|--------|-------------|
| 18 | **Hashcat Command Builder** | Construct and launch hashcat attacks in an external terminal window |

### Hash Extraction
| # | Module | Description |
|---|--------|-------------|
| 22 | **Hash Extractor** | Extract hashes from 130+ file types using 24 hashcat and 107 JtR extraction tools |

### Utilities
| # | Module | Description |
|---|--------|-------------|
| 19 | **Web Scraper Generator** | Generate ready-to-run scraper scripts (Bash/Python/PowerShell) with anti-detection features |
| 20 | **Markov Chain GUI** | Load, visualize, and train hashcat Markov statistics (.hcstat2 files) |

---

## Project Structure

```
Crackers_toolkit/
├── crackers_toolkit/           # Python package
│   ├── main.py                 # Entry point
│   ├── app/                    # Application framework
│   │   ├── main_window.py      # Main window, sidebar, module loader
│   │   ├── tool_registry.py    # Module registry (all 21 tools)
│   │   ├── sidebar.py          # Category sidebar with search
│   │   ├── data_bus.py         # Cross-module data transfer
│   │   ├── settings.py         # Persistent user settings
│   │   ├── logging_panel.py    # Output log panel
│   │   └── help_guide.py       # In-app help system
│   ├── modules/                # One file per tool (21 modules)
│   │   ├── base_module.py      # Base class for all modules
│   │   ├── prince_processor.py
│   │   ├── hashcat_launcher.py
│   │   ├── hash_extractor.py
│   │   ├── markov_gui.py
│   │   └── ...
│   ├── resources/              # Static data files
│   │   ├── hashcat_modes.json  # All hashcat hash modes
│   │   ├── hashcat_rules_ref.json
│   │   ├── keyboard_layouts/
│   │   └── thematic_lists/
│   └── pack_ports/             # PACK tools ported to Python 3
├── hashcat-7.1.2/              # Hashcat binary + charsets, masks, rules
├── john-1.9.0-jumbo-1-win64/   # John the Ripper (for hash extraction)
├── Scripts_to_use/             # External tools (PCFG, PACK, demeuk, etc.)
├── crackers_toolkit.spec       # PyInstaller build spec
├── SPECIFICATION.md            # Full software specification
└── IMPLEMENTATION_PLAN_V8.md   # Current implementation plan
```

---

## Building the Executable

### Windows

```powershell
pip install pyinstaller PyQt6
pyinstaller crackers_toolkit.spec --noconfirm
# Output: dist\CrackersToolkit\CrackersToolkit.exe
```

### Linux (Debian/Ubuntu)

```bash
sudo apt install python3 python3-pip python3-dev
pip install pyinstaller PyQt6
python -m PyInstaller crackers_toolkit_linux.spec --noconfirm
# Output: dist/CrackersToolkit/CrackersToolkit
# Package: tar czf CrackersToolkit-linux-amd64.tar.gz -C dist/CrackersToolkit .
```

> **Note:** PyInstaller cannot cross-compile. The Linux build must be done on a Linux machine.

---

## Dependencies

**Runtime (from source):**
- Python 3.10+
- PyQt6

**Bundled tools (included in the distribution):**
- hashcat 7.1.2
- John the Ripper 1.9.0 Jumbo 1
- PCFG Cracker suite
- PACK suite (ported to Python 3)
- demeuk wordlist cleaner
- combinatorX
- PRINCE Processor

---

## Theme

The application uses the **Catppuccin Mocha** dark theme with custom SVG icons for all 8 categories.

---

## Acknowledgements & Credits

Cracker's Toolkit is a GUI wrapper — the real heavy lifting is done by these incredible open-source projects and their authors:

### Core Cracking Engines

| Project | Author / Team | License | Link |
|---------|--------------|---------|------|
| **Hashcat** | Jens "atom" Steube & the hashcat team | MIT | [hashcat.net](https://hashcat.net/) |
| **John the Ripper** | Openwall / Solar Designer & contributors | GPL v2 | [openwall.com/john](https://www.openwall.com/john/) |

### Wordlist & Candidate Tools

| Project | Author / Team | License | Link |
|---------|--------------|---------|------|
| **PRINCE Processor** | hashcat team | MIT | [github.com/hashcat/princeprocessor](https://github.com/hashcat/princeprocessor) |
| **PCFG Cracker** | Matt Weir (lakiw) | GPL v3 | [github.com/lakiw/pcfg_cracker](https://github.com/lakiw/pcfg_cracker) |
| **demeuk** | Roel van Dijk (roeldev) | MIT | [github.com/roeldev/demeuk](https://github.com/roeldev/demeuk) |
| **PACK** (Password Analysis & Cracking Kit) | Peter Kacherginsky (iphelix) | GPL v2 | [github.com/iphelix/pack](https://github.com/iphelix/pack) |
| **combinatorX** | hashcat community | MIT | Included in source |

### Libraries & Frameworks

| Project | Role | Link |
|---------|------|------|
| **PyQt6** / Qt 6 | GUI framework | [riverbankcomputing.com](https://riverbankcomputing.com/software/pyqt/) |
| **PyInstaller** | Freeze to standalone exe | [pyinstaller.org](https://pyinstaller.org/) |
| **Catppuccin** | Mocha color palette / theme | [github.com/catppuccin](https://github.com/catppuccin) |
| **7-Zip** | Archive extraction (setup) | [7-zip.org](https://www.7-zip.org/) |

### Optional Runtime Dependencies

- **Python 3** — [python.org](https://www.python.org/) — required for PCFG, demeuk, and scraper modules
- **Strawberry Perl** — [strawberryperl.com](https://strawberryperl.com/) — optional, for JtR Perl-based extractors

### A Note of Thanks

This project would not exist without the years of research, engineering, and open-source generosity from the teams above. If you find Cracker's Toolkit useful, please consider starring or contributing to the upstream projects as well.

---

## License

Cracker's Toolkit (the GUI wrapper) is provided as-is for educational and authorized security-testing purposes. Each bundled tool retains its own license — see the respective project directories and links above for details.
