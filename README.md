# Cracker's Toolkit GUI

A unified desktop application that brings together 21 password cracking tools into a single, categorized interface with tooltips on every option, cross-module data transfer, and non-blocking execution.

Built with **Python 3.12** and **PyQt6**. Packaged as a standalone Windows executable via PyInstaller — no Python installation required to run.

---

## Quick Start

### Run from source

```bash
pip install PyQt6
cd d:\Crackers_toolkit
python -m crackers_toolkit.main
```

### Run the packaged executable

```
dist\CrackersToolkit\CrackersToolkit.exe
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

```powershell
pip install pyinstaller PyQt6
pyinstaller crackers_toolkit.spec --noconfirm
# Output: dist\CrackersToolkit\CrackersToolkit.exe
```

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

## License

This project integrates multiple open-source tools, each under their own license. See `hashcat-7.1.2/docs/license.txt` and individual tool directories for details.
