# Cracker's Toolkit GUI - Software Specification

**Version:** 3.0
**Date:** 2026-03-07
**Status:** Specification / Awaiting Approval

---

## 1. Overview

### 1.1 Problem Statement

The password cracking workflow involves dozens of separate command-line scripts and tools — PRINCE processor, PCFG trainer/guesser, PACK statistics and mask generators, demeuk wordlist cleaner, combinatorX, hashcat rule utilities, and more. Each tool has its own syntax, flags, and quirks. When spread across separate directories and invoked individually from the terminal, it is easy to forget tools exist, misremember their options, or lose track of which tools feed into which.

### 1.2 Solution

**Cracker's Toolkit GUI** is a single unified desktop application that collects all of these tools into one interface, organized by **functional category**. Each category groups tools by what they do (generate wordlists, clean wordlists, build masks, build rules, analyze passwords, launch attacks). When the user opens a category, they see a list of the available tools with a **brief plain-language description** of what each one does, so nothing gets forgotten or overlooked.

Every tool option is presented as a GUI control (spinbox, checkbox, dropdown, text field, file browser, etc.) with a **tooltip** that appears on hover explaining what the option does and what values are sensible. The goal is that a user should never need to read a man page or `--help` output.

The application runs on **both Windows and Linux**. When launching a hashcat attack, the application **spawns an external terminal window** with the fully constructed hashcat command, giving the user full native terminal control over the cracking session.

### 1.3 Existing Tools to Integrate

| Tool | Location | Language | Purpose |
|------|----------|----------|---------|
| PRINCE Processor (`pp.c`) | `Scripts_to_use/princeprocessor-master/` | C | Chain-element password candidate generator |
| PCFG Trainer (`trainer.py`) | `Scripts_to_use/pcfg_cracker-master/` | Python 3 | Train probabilistic grammars from password lists |
| PCFG Guesser (`pcfg_guesser.py`) | `Scripts_to_use/pcfg_cracker-master/` | Python 3 | Generate guesses from trained PCFG rulesets |
| PRINCE-LING (`prince_ling.py`) | `Scripts_to_use/pcfg_cracker-master/` | Python 3 | Generate PRINCE-optimized wordlists from PCFG |
| Password Scorer (`password_scorer.py`) | `Scripts_to_use/pcfg_cracker-master/` | Python 3 | Score passwords against a PCFG model |
| PCFG Rule Editor (`edit_rules.py`) | `Scripts_to_use/pcfg_cracker-master/` | Python 3 | Post-process PCFG rulesets for password policies |
| StatsGen (`statsgen.py`) | `Scripts_to_use/pack-master/` | Python 2* | Statistical analysis of password lists |
| MaskGen (`maskgen.py`) | `Scripts_to_use/pack-master/` | Python 2* | Generate optimized hashcat masks from statistics |
| PolicyGen (`policygen.py`) | `Scripts_to_use/pack-master/` | Python 2* | Generate policy-compliant hashcat masks |
| RuleGen (`rulegen.py`) | `Scripts_to_use/pack-master/` | Python 2* | Reverse-engineer hashcat rules from passwords |
| demeuk (`demeuk.py`) | `Scripts_to_use/demeuk-master/` | Python 3 | Wordlist cleaning, filtering, and transformation |
| combinatorX (`combinatorX.c`) | `Scripts_to_use/` | C | Multi-wordlist combinator (2-8 lists) |
| Hashcat | `hashcat-7.1.2/` | Binary | Password recovery / cracking engine |

> *PACK scripts are Python 2. They must be ported to Python 3 or called via a compatibility layer.

### 1.4 Technology Stack

- **Language:** Python 3.10+
- **GUI Framework:** PyQt6 or PySide6 (recommended for rich widget support, cross-platform, and native look on both Windows and Linux).
- **Process Execution:** All external tools run as subprocesses with non-blocking I/O and cancellation support.
- **Platforms:** Windows 10/11 and Linux (Ubuntu/Debian/Arch). All file paths use `pathlib` for cross-platform compatibility.

---

## 2. Application Structure — Category-Based Navigation

The main window uses a **sidebar menu** (or top-level menu bar with submenus) organized into functional categories. This is NOT a flat list of tabs — it is a hierarchy that groups tools by purpose.

When the user clicks a category, they see a **tool selection panel** listing every tool in that category. Each tool entry shows:
- **Tool name** (bold)
- **One-line description** (plain language, always visible)
- **Click to open** the full tool interface in the main content area

```
┌─────────────────────────────────────────────────────────────────────┐
│  Cracker's Toolkit                              [Search] [Settings]│
├──────────────────┬──────────────────────────────────────────────────┤
│                  │                                                  │
│  CATEGORIES      │   TOOL SELECTION / ACTIVE TOOL                  │
│                  │                                                  │
│  ▶ Wordlist      │   ┌─────────────────────────────────────────┐   │
│    Generation    │   │ ★ PRINCE Processor                      │   │
│                  │   │   Generate password candidates by        │   │
│  ▶ Wordlist      │   │   chaining words from a wordlist in     │   │
│    Cleaning      │   │   probability order.                    │   │
│                  │   ├─────────────────────────────────────────┤   │
│  ▶ Wordlist      │   │ ★ PCFG Guesser                         │   │
│    Analysis      │   │   Generate guesses in probability order │   │
│                  │   │   using a trained grammar model.        │   │
│  ▶ Mask          │   ├─────────────────────────────────────────┤   │
│    Tools         │   │ ★ Combinator                            │   │
│                  │   │   Combine 2-8 wordlists with optional   │   │
│  ▶ Rule          │   │   separators into candidate passwords.  │   │
│    Tools         │   ├─────────────────────────────────────────┤   │
│                  │   │ ★ PRINCE-LING                           │   │
│  ▶ Attack        │   │   Build PRINCE-optimized wordlists from │   │
│    Launcher      │   │   a trained PCFG ruleset.               │   │
│                  │   ├─────────────────────────────────────────┤   │
│  ▶ Utilities     │   │ ★ Element Extractor                    │   │
│                  │   │   Decompose passwords into building     │   │
│                  │   │   blocks (words, digits, specials).     │   │
│                  │   ├─────────────────────────────────────────┤   │
│                  │   │ ★ Keyboard Walk Generator               │   │
│                  │   │   Generate keyboard pattern candidates  │   │
│                  │   │   across multiple layouts (QWERTY, etc.)│   │
│                  │   ├─────────────────────────────────────────┤   │
│                  │   │ ★ Date & Number Patterns                │   │
│                  │   │   Generate date-formatted strings and   │   │
│                  │   │   common number patterns.               │   │
│                  │   └─────────────────────────────────────────┘   │
│                  │                                                  │
└──────────────────┴──────────────────────────────────────────────────┘
```

### 2.1 Category Breakdown

| Category | Tools Included | Purpose |
|----------|---------------|---------|
| **Wordlist Generation** | PRINCE Processor, PCFG Guesser, Combinator, PRINCE-LING, Element Extractor, Keyboard Walk Generator, Date & Number Pattern Generator | Create new wordlists and password candidates from existing data |
| **Wordlist Cleaning** | demeuk | Clean, filter, deduplicate, fix encoding, and transform raw wordlists |
| **Wordlist Analysis** | PCFG Trainer, Password Scorer, StatsGen (PACK) | Analyze password lists to understand patterns, train models, or score strength |
| **Mask Tools** | Mask Builder, MaskGen (PACK), PolicyGen (PACK) | Build, generate, and manage hashcat mask files (.hcmask) |
| **Rule Tools** | Rule Builder, RuleGen (PACK), PCFG Rule Editor | Build, generate, reverse-engineer, and manage hashcat rule files (.rule) |
| **Attack Launcher** | Hashcat Command Builder | Construct and launch hashcat attacks in an external terminal |
| **Hash Extraction** | Hash Extractor | Extract password hashes from encrypted containers, wallets, archives, documents, and other protected files using hashcat and John the Ripper extraction tools |
| **Utilities** | Web Scraper Generator, Markov Chain GUI | Supporting tools: scrape websites for wordlists, visualize/train Markov chain statistics |

### 2.2 Universal GUI Requirements

These requirements apply to **every tool** in every category:

1. **Tooltips on every input.** Every spinbox, checkbox, dropdown, text field, file browser, and slider must have a tooltip that appears on hover. The tooltip must explain:
   - What the option does in plain language.
   - What values are typical or recommended.
   - Example: hovering over a `--pw-max` spinbox shows: *"Maximum length of generated passwords. Candidates longer than this are discarded. Typical values: 8-16 for fast hashes, 8-32 for slow hashes."*

2. **Tool descriptions at selection.** When browsing a category's tool list, each tool shows its name and a 1-2 sentence description before the user opens it.

3. **File browsers** support drag-and-drop, remember their last directory per tool, and have quick-access bookmarks to toolkit directories (`Scripts_to_use/`, `hashcat-7.1.2/rules/`, `hashcat-7.1.2/masks/`, `Rules/`).

4. **Cross-module data transfer.** A "Send to..." button next to any output (wordlist, rule file, mask file) lets the user send it directly to another tool's input without manually navigating file browsers.

5. **Non-blocking execution.** All subprocess executions run in background threads. The GUI never freezes. A progress indicator and "Cancel" button are always visible during execution.

6. **Cross-platform.** All features work identically on Windows and Linux. Path handling uses `pathlib`. Terminal spawning adapts to the OS (see Module 18).

### 2.3 Usability & Anti-Bloat Design Principles

With 20 modules, the application must stay approachable. The following design principles prevent it from becoming overwhelming:

1. **Progressive disclosure.** Each tool opens showing only its most common/essential options. Advanced or rarely-used options are hidden behind a collapsible "Advanced Options" panel. The user sees a clean, simple interface by default and can expand it when needed.

2. **Category grouping is the primary navigation.** The user never sees all 20 modules at once. They see 7 categories. Clicking a category reveals only the 2-7 tools within it. This keeps the cognitive load per screen low.

3. **Descriptions everywhere.** Every category, every tool, and every option has a plain-language description. The user should be able to understand what something does without prior knowledge. This is the single most important anti-bloat feature — complexity is tolerable when it is well-explained.

4. **Sensible defaults.** Every parameter has a reasonable default value. A user should be able to open any tool, select an input file, and click "Run" without changing any settings and get a useful result. Customization is available but never required.

5. **No dead ends.** Every tool that produces output has a clear "Send to..." action showing where that output can go next. Every tool that needs input has a "Receive from..." showing where it can come from. The user always knows what to do next.

6. **Consistent layout.** All tools follow the same visual structure: input section at top, parameters in the middle, output/action buttons at the bottom. Once the user learns one tool, every other tool feels familiar.

7. **Search.** A global search bar in the sidebar lets the user type keywords (e.g., "clean", "mask", "combine", "keyboard") and instantly filter to matching tools. Searches match against tool names, descriptions, and option names.

8. **"What should I use?" guide.** A help page accessible from the toolbar presents common workflows as decision trees:
   - "I have a raw wordlist and want to clean it up" → demeuk
   - "I have a clean wordlist and want to generate password candidates" → PRINCE, Combinator, or PCFG Guesser
   - "I want to figure out what masks cover a password set" → StatsGen → MaskGen
   - "I want to build a targeted mask by hand" → Mask Builder
   - "I want to understand what rules would crack these passwords" → RuleGen
   - "I want to launch an attack" → Attack Launcher

   This addresses the core problem: "I know what I want to accomplish but not which tool does it."

---

## 3. Module Specifications

---

### Category: Wordlist Generation

---

### Module 1: PRINCE Processor GUI

**Menu description:** *"Generate password candidates by chaining words from a wordlist in probability order. Combines 1-8 words per candidate, prioritizing the most likely combinations first."*

**Underlying tool:** `Scripts_to_use/princeprocessor-master/` — compiled `pp` binary.

#### 3.1.1 Functional Requirements

1. **Wordlist Input**
   - File browser to select one input wordlist file.
   - Display metadata on selection: line count, file size.
   - Accept wordlists from Element Extractor, Combinator, PRINCE-LING, or demeuk via "Send to..." data transfer.

2. **Parameter Panel**
   All parameters exposed as labeled GUI controls. Every control has a tooltip.

   | Parameter | Control | Default | Tooltip Text |
   |-----------|---------|---------|-------------|
   | `--pw-min` | Spinbox (1-256) | 1 | Minimum length of generated passwords. Candidates shorter than this are discarded. Typical: 6-8. |
   | `--pw-max` | Spinbox (1-256) | 16 | Maximum length of generated passwords. Candidates longer than this are discarded. Typical: 12-20. |
   | `--elem-cnt-min` | Spinbox (1-8) | 1 | Minimum number of words chained per candidate. Set to 2 to force at least two words combined. |
   | `--elem-cnt-max` | Spinbox (1-8) | 8 | Maximum words chained per candidate. Higher = more combinations but slower. Typical: 3-4. |
   | `--wl-max` | Spinbox (1-10M) | 10,000,000 | Maximum words to read from the wordlist. Words beyond this limit are ignored. |
   | `--dupe-check-disable` | Checkbox | Off | Disable duplicate checking. Faster but may output duplicate candidates. |
   | `--case-permute` | Checkbox | Off | Also generate variants with first letter of each word toggled upper/lower. Doubles or more the output. |
   | `--skip` | Number input | 0 | Skip the first N candidates. For distributed/resumed processing. |
   | `--limit` | Number input | 0 | Stop after N candidates. 0 = unlimited. |
   | `--keyspace` | Checkbox | Off | Only calculate and display total number of possible candidates, don't generate them. |

3. **Output Options**
   - **Save to file:** File browser to choose output path.
   - **Send to Hashcat:** Transfers the output file path (or pipes stdin) to the Attack Launcher module.
   - **Preview:** Show first N lines (default 1000) in a scrollable panel with a running total counter.

4. **Execution**
   - "Run" button starts the process. Real-time candidate counter. "Stop" button cancels.
   - Session save/restore via `--save-file` / `--restore-file` fields.

5. **Help Panel**
   - Collapsible panel with a plain-language explanation of the PRINCE algorithm: how it reads a frequency-sorted wordlist, builds chains of 1-N elements, and outputs them in probability order. Includes a worked example.

#### 3.1.2 Data Flow

- **In:** Wordlists from Element Extractor, Combinator, PRINCE-LING, demeuk, or file system.
- **Out:** Candidate file/stream to Attack Launcher, or saved to file.

---

### Module 2: PCFG Guesser GUI

**Menu description:** *"Generate password guesses in probability order using a previously trained PCFG grammar model. The most likely passwords come first. Supports session save/restore for long runs."*

**Underlying tool:** `Scripts_to_use/pcfg_cracker-master/pcfg_guesser.py`

#### 3.2.1 Functional Requirements

1. **Configuration Panel**

   | Parameter | Control | Default | Tooltip Text |
   |-----------|---------|---------|-------------|
   | Ruleset (`-r`) | Dropdown (auto-populated from `Rules/`) | `Default` | The trained PCFG ruleset to use. Train new ones in "Wordlist Analysis > PCFG Trainer". |
   | Mode (`-m`) | Radio buttons | `true_prob_order` | **true_prob_order**: guesses in strict probability order (best for cracking). **random_walk**: random sampling. **honeywords**: generate decoy passwords. |
   | Limit (`-n`) | Number input | 0 | Stop after N guesses. 0 = unlimited. Use a small number (100-1000) for previewing. |
   | Skip brute-force | Checkbox | Off | Disable OMEN/Markov brute-force guesses. Only structured PCFG guesses are produced. |
   | All lowercase | Checkbox | Off | Only generate lowercase candidates (no case variations). |
   | Session name (`-s`) | Text field | `default_run` | Name for saving/restoring this session. Allows pausing and resuming. |

2. **Head/Tail Preview**
   A key usability feature — see what the output looks like before committing to a long run:

   - **"Preview Head" button:** Runs the guesser with `--limit 100` and displays the results. These are the **highest-probability** candidates — the most likely real-world passwords.
   - **"Preview Tail" button:** Runs with a large `--skip` value (configurable, e.g. 1,000,000) and `--limit 100`. These are **lower-probability** candidates — less common patterns.
   - Both previews display **side by side** in the GUI.
   - Below each preview: statistics on average length, character composition, and most common base structures observed.
   - **Purpose:** Helps the user judge how the `--coverage` setting (from training) and the current ruleset affect output quality, without waiting for millions of guesses.

3. **Output Options**
   - Save to file, send to Attack Launcher, or preview in GUI.
   - When sending to Attack Launcher, can pipe via stdin (guesser stdout → hashcat stdin).

4. **Session Management**
   - List saved sessions with metadata (guess count at pause, ruleset used).
   - "Resume" button to restore.

#### 3.2.2 Data Flow

- **In:** Trained rulesets from `Rules/` directory (trained via PCFG Trainer in the Analysis category).
- **Out:** Guess stream/file to Attack Launcher or file system.

---

### Module 3: Combinator GUI

**Menu description:** *"Combine 2 to 8 wordlists together, concatenating one word from each list per candidate. Supports custom separators between words. Useful for building passphrase-style candidates."*

**Underlying tool:** `Scripts_to_use/combinatorX.c` — compiled binary.

#### 3.3.1 Functional Requirements

1. **Wordlist Slots**
   - 2 to 8 numbered slots displayed as a vertical list.
   - Each slot: file browser button, dropdown for **built-in thematic lists** (see below), and preview button (shows first 20 lines).
   - "Add Slot" / "Remove Slot" buttons (range: 2-8).

2. **Built-in Thematic Wordlists**
   Bundled with the application for convenience:

   | Theme | Contents | Tooltip |
   |-------|----------|---------|
   | Digits (0-9) | Single digits | Basic single digits. Useful as suffixes or PIN components. |
   | Digits (00-99) | Two-digit combos | All two-digit numbers. Common password suffixes. |
   | Digits (000-999) | Three-digit combos | All three-digit numbers. |
   | Common PINs | Frequent 4-6 digit PINs | PINs like 1234, 0000, 1111, 123456, etc. |
   | Special characters | Each printable ASCII special char | One special character per line: !, @, #, $, etc. |
   | Special combos (2-char) | Common 2-char special sequences | !!, !@, @#, $!, etc. |
   | Years (1950-2030) | Year numbers | Common birth years and recent years. |
   | Days & Months | Day/month numbers and names | 01-31, jan-dec, january-december. |
   | Keyboard walks | QWERTY patterns | qwerty, asdf, zxcv, 1234qwer, etc. |

3. **Separator Configuration**
   - Between each adjacent pair of slots: a text input for a separator string.
   - Maps to `--sep1` through `--sep7` in combinatorX.
   - Start/End separators (`--sepStart`, `--sepEnd`).
   - Tooltip: *"Characters inserted between words from adjacent lists. Leave empty for no separator. Example: '-' produces 'word1-word2'."*

4. **Additional Options**

   | Parameter | Control | Default | Tooltip Text |
   |-----------|---------|---------|-------------|
   | Max output length (`--maxLen`) | Spinbox | 256 | Discard candidates longer than this. Useful to keep output manageable. |
   | Skip (`-s`) | Number input | 0 | Skip first N combinations. For distributed processing. |
   | Limit (`-l`) | Number input | 0 | Stop after N combinations. 0 = unlimited. |

5. **Permutation Mode**
   A toggle that switches from fixed-slot combination to **all-order permutation**:
   - When OFF (default): standard combinatorX behavior — one word from slot 1, one from slot 2, etc., always in that order.
   - When ON: given N input elements (from a single wordlist or paste-box), generate all orderings of those elements. For example, elements `[pass, 123, !]` produce: `pass123!`, `pass!123`, `123pass!`, `123!pass`, `!pass123`, `!123pass`.
   - Configurable max permutation depth (default: 5 elements) to prevent combinatorial explosion.
   - Tooltip: *"Try all orderings of the input elements. Useful when you know which pieces make up a password but not their order. Warning: N elements produce N! (factorial) orderings — 5 elements = 120, 6 = 720, 7 = 5040."*

   > **Implementation note:** This mode does not use combinatorX. It is implemented natively in the application using `itertools.permutations`.

6. **Output Options**
   - Save to file, send to Attack Launcher, or preview.

#### 3.3.2 Data Flow

- **In:** Wordlists from file system, built-in thematic lists, or Element Extractor output.
- **Out:** Combined candidates to Attack Launcher or file.

---

### Module 4: PRINCE-LING GUI

**Menu description:** *"Generate wordlists optimized for PRINCE attacks using a trained PCFG model. Outputs individual words (not full passwords) in probability order — the best input for PRINCE processor."*

**Underlying tool:** `Scripts_to_use/pcfg_cracker-master/prince_ling.py`

#### 3.4.1 Functional Requirements

1. **Configuration**

   | Parameter | Control | Default | Tooltip Text |
   |-----------|---------|---------|-------------|
   | Ruleset (`-r`) | Dropdown (from `Rules/`) | `Default` | PCFG ruleset to use. Train new ones in "Wordlist Analysis > PCFG Trainer". |
   | Output file (`-o`) | File browser | stdout | Where to save the generated wordlist. |
   | Max size (`-s`) | Number input | 0 | Maximum number of words to generate. 0 = all. |
   | All lowercase | Checkbox | Off | Generate only lowercase words. |

2. **Execution & Output**
   - Runs `prince_ling.py` as subprocess with progress display.
   - "Send to PRINCE" button: transfers output wordlist directly to Module 1.

#### 3.4.2 Data Flow

- **In:** Trained rulesets from `Rules/`.
- **Out:** Wordlist to PRINCE Processor, Attack Launcher, or file.

---

### Module 5: Element Extractor

**Menu description:** *"Decompose passwords from a wordlist into their structural building blocks: words, digit runs, special character sequences, years, etc. The extracted elements make excellent input for PRINCE or combinator attacks."*

**Underlying tool:** New — implemented from scratch in the application.

#### 3.5.1 Functional Requirements

1. **Input**
   - File browser for one or more wordlists.
   - Paste-box for manually entering passwords.

2. **Decomposition Rules**
   Each rule is a checkbox the user can enable/disable. Each checkbox has a tooltip explaining the rule.

   | Rule | Tooltip | Example: `MyP@ss2024!` |
   |------|---------|------------------------|
   | Contiguous digits | Extract runs of consecutive digits as single tokens. | → `2024` |
   | Contiguous specials | Extract runs of consecutive special characters as tokens. | → `@`, `!` |
   | Isolated digits | Split digit runs into individual digits. | → `2`, `0`, `2`, `4` |
   | Isolated specials | Split special runs into individual characters. | → `@`, `!` |
   | Alpha words (case-split) | Split alphabetic sequences at lowercase→uppercase transitions. | → `My`, `P`, `ss` |
   | Alpha words (no split) | Keep alphabetic sequences whole. | → `MyP`, `ss` |
   | Full alpha-lower | Extract alphabetic segments and lowercase them. | → `myp`, `ss` |
   | Year detection | Recognize 4-digit sequences resembling years (1900-2099) as a "year" element type. | → `2024` (tagged as year) |
   | Leet-speak decode | Attempt to reverse leet-speak substitutions (@→a, 3→e, 0→o, etc.) and produce a decoded variant. | → `password` (from `P@ss`) |

3. **Output Table**
   - Columns: **Element**, **Type** (alpha / digit / special / year), **Frequency**.
   - Sortable by any column.
   - Deduplicated by default; toggle to show counts.

4. **Decomposition Preview**
   - Enter a single password → see step-by-step tokenization and the resulting element chain.
   - Example display: `MyP@ss2024!` → `[My] [P] [@] [ss] [2024] [!]`

5. **Export**
   - Save as plain text file (one element per line).
   - "Send to..." buttons for PRINCE, Combinator, or Mask Tools (as custom charset source).

#### 3.5.2 Data Flow

- **In:** Wordlists from file system, demeuk output, or Scraper output.
- **Out:** Element lists to PRINCE, Combinator, Mask Tools (custom charsets), or file.

---

### Module 6: Keyboard Walk Generator

**Menu description:** *"Generate password candidates based on keyboard walking patterns — fingers moving across the keyboard in lines, diagonals, or patterns. Supports multiple keyboard layouts (QWERTY, AZERTY, QWERTZ, Dvorak)."*

**Underlying tool:** New — implemented from scratch.

#### 3.6.1 Functional Requirements

1. **Layout Selector**

   | Control | Tooltip |
   |---------|---------|
   | Keyboard layout | Dropdown: QWERTY (US), QWERTY (UK), AZERTY (French), QWERTZ (German), Dvorak. Determines which keys are adjacent. |
   | Include numpad | Checkbox (default: On). Include the numeric keypad as a separate walkable region. |
   | Include shift variants | Checkbox (default: Off). Also generate walks using shifted characters (e.g., `!@#$` as the shifted version of `1234`). |

2. **Walk Parameters**

   | Parameter | Control | Default | Tooltip Text |
   |-----------|---------|---------|-------------|
   | Min walk length | Spinbox | 4 | Minimum number of keys in a walk. Shorter walks are less useful. |
   | Max walk length | Spinbox | 12 | Maximum number of keys in a walk. Typical: 6-12. |
   | Walk directions | Multi-select checkboxes | All | Which directions are allowed: **horizontal** (left-right along a row), **vertical** (up-down across rows), **diagonal** (e.g., 1qaz, 2wsx), **combo** (direction changes mid-walk, e.g., qweasd). |
   | Max direction changes | Spinbox (0-4) | 2 | How many times the walk can change direction. 0 = straight lines only. Common patterns like `1qaz2wsx` have 1-2 changes. |
   | Include reverse | Checkbox (default: On) | — | Also generate the reverse of each walk (e.g., `ytrewq` in addition to `qwerty`). |
   | Include common named | Checkbox (default: On) | — | Include well-known keyboard walks from a built-in list: `qwerty`, `asdfgh`, `zxcvbn`, `1234567890`, `qwer1234`, `1q2w3e4r`, etc. |

3. **Visual Keyboard Preview**
   - Display an interactive keyboard layout diagram.
   - As the user adjusts parameters, highlight which walks would be generated on the keyboard.
   - Click a key to start a manual walk — click subsequent keys to define a custom pattern, and add it to the output.

4. **Output**
   - Generated walks displayed in a scrollable list with total count.
   - Export as wordlist file.
   - "Send to..." PRINCE, Combinator, or Attack Launcher.

#### 3.6.2 Data Flow

- **In:** Layout selection and parameters only (no file input).
- **Out:** Walk wordlist to PRINCE, Combinator, Attack Launcher, or file.

---

### Module 7: Date & Number Pattern Generator

**Menu description:** *"Generate systematic date-formatted strings and number patterns that people commonly use in passwords: birthdays, anniversaries, years, PINs. Covers multiple date formats and configurable year ranges."*

**Underlying tool:** New — implemented from scratch.

#### 3.7.1 Functional Requirements

1. **Date Pattern Configuration**

   | Parameter | Control | Default | Tooltip Text |
   |-----------|---------|---------|-------------|
   | Year range | Two spinboxes (from-to) | 1950-2030 | Range of years to generate dates for. Covers typical birth years through near-future. |
   | Date formats | Multi-select checkboxes | All common | Which date formats to generate. See format table below. |
   | Include month names | Checkbox | On | Also generate dates with month names (Jan, January, etc.) in addition to numeric. |
   | Month name language | Dropdown | English | Language for month names: English, German, French, Spanish, Danish, Dutch, etc. |

   **Date format table** (each is a checkbox):

   | Format | Example | Tooltip |
   |--------|---------|---------|
   | `DDMMYYYY` | `25121990` | Day-Month-Year, no separator. Common in Europe. |
   | `DD/MM/YYYY` | `25/12/1990` | Day/Month/Year with slash. |
   | `DD-MM-YYYY` | `25-12-1990` | Day-Month-Year with dash. |
   | `DD.MM.YYYY` | `25.12.1990` | Day-Month-Year with dot. Common in Germany. |
   | `MMDDYYYY` | `12251990` | Month-Day-Year, no separator. Common in US. |
   | `MM/DD/YYYY` | `12/25/1990` | Month/Day/Year with slash. |
   | `YYYYMMDD` | `19901225` | ISO-style Year-Month-Day. |
   | `YYYY-MM-DD` | `1990-12-25` | ISO format with dashes. |
   | `DDMM` | `2512` | Day-Month short (no year). |
   | `MMDD` | `1225` | Month-Day short (no year). |
   | `DDMMYY` | `251290` | Day-Month-2-digit-Year. |
   | `MMDDYY` | `122590` | Month-Day-2-digit-Year. |
   | `MonYYYY` | `Dec1990` | Abbreviated month + year. |
   | `MonthYYYY` | `December1990` | Full month + year. |
   | `YYYY` | `1990` | Year only. |
   | `YY` | `90` | Two-digit year only. |

2. **Number Pattern Configuration**

   | Parameter | Control | Default | Tooltip Text |
   |-----------|---------|---------|-------------|
   | Digit sequences | Checkbox (default: On) | — | Generate sequential digit runs: 123, 1234, 12345, etc. (ascending and descending). |
   | Repeated digits | Checkbox (default: On) | — | Generate repeated-digit strings: 111, 1111, 0000, 9999, etc. |
   | Min digits | Spinbox | 2 | Minimum length of generated number patterns. |
   | Max digits | Spinbox | 8 | Maximum length. |
   | Common PINs | Checkbox (default: On) | — | Include a curated list of the most common PINs (1234, 0000, 1111, 1212, 6969, 4321, etc.). |

3. **Preview**
   - Show total count and scrollable sample of generated patterns.
   - Toggle between "dates only", "numbers only", or "all".

4. **Output**
   - Export as wordlist file.
   - "Send to..." Combinator (as a slot input), PRINCE, or Attack Launcher.

#### 3.7.2 Data Flow

- **In:** Configuration parameters only (no file input).
- **Out:** Pattern wordlist to Combinator, PRINCE, Attack Launcher, or file.

---

### Category: Wordlist Cleaning

---

### Module 8: demeuk — Wordlist Cleaner

**Menu description:** *"Clean, filter, fix encoding, deduplicate, and transform raw wordlists. Handles common issues like mojibake, HTML artifacts, control characters, hash lines, and email addresses. Essential for preparing raw data before cracking."*

**Underlying tool:** `Scripts_to_use/demeuk-master/demeuk-master/bin/demeuk.py`

#### 3.8.1 Functional Requirements

1. **Input / Output**

   | Control | Tooltip |
   |---------|---------|
   | Input file(s) (`-i`) | One or more raw wordlist files to clean. Supports multiple files. |
   | Output file (`-o`) | Where to write cleaned output. |
   | Log file (`-l`) | Where to log dropped/modified lines for review. |
   | Input encoding | Character encoding of input. "Auto" uses chardet to detect. |
   | Output encoding | Character encoding of output. Default: UTF-8. |
   | Threads (`-j`) | Number of processing threads. Default: all CPU cores. |
   | Limit (`-n`) | Process only the first N lines per thread. 0 = all. |
   | Progress bar | Show a progress bar during processing. |

2. **Separator / Cutting Options**
   For splitting lines (e.g., splitting `user:password` dumps):

   | Control | Tooltip |
   |---------|---------|
   | Enable cut (`-c`) | Split each line on a delimiter and keep only the password portion. Essential for user:pass dumps. |
   | Delimiter (`-d`) | Character(s) to split on. Default: `:`. Common alternatives: `;`, tab, `\|`. |
   | Cut before | Keep the part BEFORE the delimiter instead of after. |
   | Cut fields (`-f`) | Select specific fields (like Unix `cut -f`). Example: `2` keeps only field 2. |

3. **Check Modules (Drop Lines)**
   Each option is a checkbox with tooltip. When enabled, lines matching the condition are **dropped** (removed from output, logged):

   | Option | Tooltip |
   |--------|---------|
   | Min length | Drop lines shorter than N characters. |
   | Max length | Drop lines longer than N characters. Passwords above 64 chars are rarely useful. |
   | Check case | Drop lines where uppercase equals lowercase (no letters). |
   | Check control chars | Drop lines containing control characters (binary junk). |
   | Check email | Drop lines that look like email addresses. |
   | Check hash | Drop lines that look like hash strings (hex, base64 patterns). |
   | Check MAC address | Drop lines matching MAC address patterns. |
   | Check UUID | Drop lines matching UUID patterns. |
   | Check non-ASCII | Drop lines containing non-ASCII characters. |
   | Check replacement char | Drop lines containing the Unicode replacement character (U+FFFD). |
   | Check starts with | Drop lines starting with a specified string. |
   | Check ends with | Drop lines ending with a specified string. |
   | Check contains | Drop lines containing a specified string. |
   | Check regex | Drop lines matching a custom regular expression. |
   | Check empty | Drop empty lines. |
   | Min digits | Drop lines with fewer than N digit characters. |
   | Max digits | Drop lines with more than N digit characters. |
   | Min uppercase | Drop lines with fewer than N uppercase characters. |
   | Max uppercase | Drop lines with more than N uppercase characters. |
   | Min specials | Drop lines with fewer than N special characters. |
   | Max specials | Drop lines with more than N special characters. |

4. **Modify Modules (Transform Lines)**
   Each is a checkbox. When enabled, matching lines are **transformed in-place** (original replaced):

   | Option | Tooltip |
   |--------|---------|
   | Decode $HEX[] | Decode hashcat's `$HEX[...]` encoding back to plain text. |
   | Decode HTML entities | Convert `&amp;`, `&lt;`, etc. to their actual characters. |
   | Decode HTML named | Convert named HTML entities like `&hearts;` to characters. |
   | Lowercase all | Convert all lines to lowercase. |
   | Title case | Convert all lines to title case (first letter of each word capitalized). |
   | Fix umlauts | Fix broken umlaut notation (e.g., `o"` → `ö`). |
   | Fix mojibake | Attempt to fix mojibake — garbled text from wrong encoding (e.g., `Ã©` → `é`). |
   | Auto-fix encoding | Guess the correct encoding and re-encode. Useful for mixed-encoding files. |
   | Fix tabs | Replace tab characters with spaces. |
   | Fix newlines | Normalize mixed line endings (\\r\\n, \\r) to \\n. |
   | Trim whitespace | Remove leading/trailing whitespace from each line. |
   | Replace non-ASCII | Replace non-ASCII characters with their closest ASCII equivalent (é→e, ñ→n). |
   | Transliterate | Transliterate from other scripts (Cyrillic, Greek, Armenian, etc.) to Latin. |
   | **Unicode normalize** | **Normalize Unicode to NFC form. Converts decomposed characters (e + combining accent) to their precomposed equivalents (é). Prevents silent duplicates in wordlists where the same visual character has different byte representations.** |
   | **Homoglyph → ASCII** | **Replace Unicode characters that visually resemble ASCII with their ASCII equivalents. E.g., Cyrillic 'а'→ Latin 'a', Greek 'ο' → Latin 'o', fullwidth 'Ａ' → 'A'. Catches passwords using look-alike characters from other scripts.** |
   | **Strip emoji** | **Remove emoji and other pictographic Unicode characters from lines. Useful for cleaning social media scraped data.** |
   | **Emoji to text** | **Convert common emoji to their text equivalents (❤️→'love', 🔑→'key', 💀→'skull', 🏠→'house', etc.) using a built-in mapping table. Adds the text version alongside or instead of the emoji.** |

5. **Add Modules (Keep Original + Add Variant)**
   When enabled, the original line is kept AND an additional variant is added:

   | Option | Tooltip |
   |--------|---------|
   | Add lowercase | Add a lowercase copy of each line. |
   | Add first-upper | Add a variant with the first character uppercased. |
   | Add title case | Add a title-case variant. |
   | Add without punctuation | Add a variant with all punctuation removed. |
   | Add split | Add variants splitting compound words. |
   | Add umlaut variants | Add variants with umlaut substitutions. |
   | Add Latin ligature variants | Add variants expanding ligatures (æ→ae, etc.). |
   | **Add homoglyph variants** | **Add variants substituting Latin characters with visually similar Unicode characters (a→а[Cyrillic], o→ο[Greek], etc.). Generates candidates for passwords that use look-alike characters from other scripts.** |

6. **Preset Macros**
   Quick buttons that enable sensible combinations:

   | Preset | What It Enables | Tooltip |
   |--------|----------------|---------|
   | **Leak cleanup** | mojibake + encoding fix + newline fix + check control chars | Quick cleanup for a typical leaked password dump. |
   | **Leak full cleanup** | Leak + HEX decode + HTML decode + check hash + check MAC + check UUID + check email + check replacement char + check empty | Thorough cleanup for messy leaked data. |
   | **Google N-gram** | Strip universal POS tags | Clean Google N-gram corpus data for wordlist use. |

7. **Preview**
   - "Dry Run" button processes the first 100 lines and shows before/after comparison.
   - Summary: lines kept, lines dropped (with reasons), lines modified.

8. **Execution**
   - "Run" starts demeuk as a subprocess.
   - Real-time progress bar and line counter.
   - On completion: summary statistics and output file path.

#### 3.8.2 Data Flow

- **In:** Raw wordlist files from the file system or Scraper output.
- **Out:** Cleaned wordlists to any Wordlist Generation tool, PCFG Trainer, or file.

---

### Category: Wordlist Analysis

---

### Module 9: PCFG Trainer GUI

**Menu description:** *"Train a probabilistic grammar model from a plaintext password list. The model learns password structures (e.g., '5 letters + 2 digits + 1 special') and their probabilities. Used by the PCFG Guesser and PRINCE-LING to generate candidates."*

**Underlying tool:** `Scripts_to_use/pcfg_cracker-master/trainer.py`

#### 3.9.1 Functional Requirements

1. **Training Input**
   - File browser for the training password list.
   - Display metadata on selection: line count, detected encoding, sample of first 10 lines.

2. **Parameters**

   | Parameter | Control | Default | Tooltip Text |
   |-----------|---------|---------|-------------|
   | Ruleset name (`-r`) | Text field | `Default` | Name for the trained ruleset. Stored under `Rules/<name>/`. Use a descriptive name like "rockyou" or "company_2024". |
   | Encoding (`-e`) | Dropdown | Auto-detect | Character encoding of the training file. Leave on "Auto" unless you know the encoding is wrong. |
   | Coverage (`-c`) | Slider (0.0-1.0) | 0.6 | Balance between PCFG structured guesses and Markov brute-force guesses. **1.0** = only structured guesses (e.g., "word + digits"). **0.0** = only Markov/brute-force. **0.6** (default) = 60% structured, 40% brute-force. |
   | N-gram depth (`-n`) | Spinbox (2-5) | 4 | Markov chain order. Higher values capture longer character patterns but need more training data. 4 is a good default. |
   | Alphabet size (`-a`) | Spinbox | 100 | Number of most-frequent characters for Markov model. Larger = more coverage but bigger keyspace. |
   | Save sensitive | Checkbox | Off | Save email addresses and URLs found in training data. Useful for targeted attacks. Contains PII — use responsibly. |
   | Multiword file (`-m`) | File browser | None | Optional file for training compound-word detection (helps split "footballplayer" into "football" + "player"). |
   | Prefix count | Checkbox | Off | Enable if input has `uniq -c` style count prefixes (e.g., "  1234 password"). |

3. **Execution**
   - "Train" button starts `trainer.py`.
   - Progress log panel showing trainer stderr output.
   - On completion: summary showing ruleset path, number of base structures learned, top-10 most probable structures.

4. **Ruleset Browser**
   - List all rulesets in `Rules/` with metadata (training source, date, structure count, disk size).
   - "Delete", "Copy", "Edit" (opens PCFG Rule Editor) buttons.

#### 3.9.2 Data Flow

- **In:** Plaintext password files from file system or demeuk output.
- **Out:** Trained rulesets used by PCFG Guesser, PRINCE-LING, Password Scorer, and PCFG Rule Editor.

---

### Module 10: Password Scorer GUI

**Menu description:** *"Score passwords against a trained PCFG model to see how probable each one is. Classifies entries as passwords, emails, websites, or other. Useful for understanding password strength distributions."*

**Underlying tool:** `Scripts_to_use/pcfg_cracker-master/password_scorer.py`

#### 3.10.1 Functional Requirements

1. **Input**
   - File browser for passwords to score, or a paste-box for manual entry.

2. **Parameters**

   | Parameter | Control | Default | Tooltip Text |
   |-----------|---------|---------|-------------|
   | Ruleset (`-r`) | Dropdown | `Default` | PCFG ruleset to score against. |
   | Probability cutoff (`-l`) | Number input | 0 | Minimum probability to classify as "password". 0 = classify everything as password. |
   | Max OMEN level (`-m`) | Spinbox | 9 | Maximum Markov/OMEN level to evaluate. Higher = slower but more complete scoring. |

3. **Output**
   - Table view: Password | Classification | PCFG Probability | OMEN Level.
   - Sortable columns, filterable by classification type.
   - Export to file.

---

### Module 11: StatsGen GUI (PACK)

**Menu description:** *"Analyze a password list to discover statistical patterns: length distributions, character set usage, mask frequency, and complexity ranges. Essential input for the Mask Generator."*

**Underlying tool:** `Scripts_to_use/pack-master/statsgen.py` (port to Python 3).

#### 3.11.1 Functional Requirements

1. **Input**
   - File browser for a plaintext password file.

2. **Parameters**

   | Parameter | Control | Default | Tooltip Text |
   |-----------|---------|---------|-------------|
   | Min length | Spinbox | 0 | Only analyze passwords of at least this length. |
   | Max length | Spinbox | 0 (no limit) | Only analyze passwords up to this length. |
   | Charset filter | Multi-select checkboxes | All | Filter by character set: loweralpha, upperalpha, numeric, mixedalpha, mixedalphanum, all, etc. |
   | Hide rare (< 1%) | Checkbox | Off | Suppress statistics that cover less than 1% of the sample. Reduces noise. |
   | Output CSV (`-o`) | File browser | None | Save mask statistics to CSV for use in Mask Generator (MaskGen). |

3. **Output Display**
   - Tabbed results: Length Distribution, Character Sets, Simple Masks, Advanced Masks (hashcat format), Complexity.
   - Bar charts or tables for each.
   - "Send to MaskGen" button: passes the CSV output directly to Module 13.

#### 3.11.2 Data Flow

- **In:** Password files from file system or demeuk output.
- **Out:** CSV statistics to MaskGen (Mask Tools category).

---

### Category: Mask Tools

---

### Module 12: Mask Builder

**Menu description:** *"Visually build hashcat masks position by position. See in real-time what each mask matches, the total keyspace, and estimated crack time. Build and export .hcmask files."*

**Underlying tool:** New — built from scratch.

#### 3.12.1 Functional Requirements

1. **Character Reference Panel**
   Always-visible reference:

   | Placeholder | Matches | Tooltip |
   |-------------|---------|---------|
   | `?l` | a-z (26 chars) | Any lowercase letter. |
   | `?u` | A-Z (26 chars) | Any uppercase letter. |
   | `?d` | 0-9 (10 chars) | Any digit. |
   | `?s` | Special chars (33) | Any printable non-alphanumeric ASCII character. |
   | `?a` | All printable (95) | Any printable ASCII character (?l?u?d?s combined). |
   | `?b` | All bytes (256) | Any byte value 0x00-0xFF. Rarely needed. |
   | `?1`-`?4` | Custom charsets | User-defined character sets (see below). |

2. **Position-Based Builder**
   - Each position is a column with a dropdown: `?l`, `?u`, `?d`, `?s`, `?a`, `?b`, `?1`-`?4`, or a literal character.
   - "Add Position" / "Remove Position" buttons.
   - The assembled mask string updates live (e.g., `?u?l?l?l?d?d?s`).

3. **Custom Charset Builder**
   - Four slots (`-1` through `-4`).
   - Each slot: text input for literal chars (e.g., `aeiou0123`) or combinations (`?l?d`).
   - **"Import from Element Extractor"**: use unique characters of a given type extracted in Module 5 as a custom charset.
   - Display effective character count per charset.

4. **Real-Time Description**
   Below the builder, auto-updated:
   > "Position 1: One uppercase letter (A-Z). Positions 2-5: One lowercase letter (a-z) each. Positions 6-7: One digit (0-9) each. Position 8: One special character."
   > "Keyspace: 26 x 26^4 x 10^2 x 33 = 15,058,083,200"
   > "Estimated time at 1,000,000,000 H/s: ~15 seconds"

5. **Mask List Accumulator**
   - "Add to List" appends current mask to a growing list.
   - Each entry shows: mask string, description, keyspace, estimated time.
   - Cumulative totals at bottom.
   - Reorder, edit, delete entries.
   - **"Export as .hcmask"** saves the list.
   - **"Import .hcmask"** loads an existing file for viewing/editing.

#### 3.12.2 Data Flow

- **In:** Custom charsets from Element Extractor.
- **Out:** `.hcmask` files to Attack Launcher.

---

### Module 13: MaskGen GUI (PACK)

**Menu description:** *"Generate an optimized set of hashcat masks from password statistics. Ranks masks by efficiency (most passwords cracked per keyspace unit) and builds time-budgeted mask files."*

**Underlying tool:** `Scripts_to_use/pack-master/maskgen.py` (port to Python 3).

#### 3.13.1 Functional Requirements

1. **Input**
   - File browser for StatsGen CSV output, or receive directly from Module 11.

2. **Parameters**

   | Parameter | Control | Default | Tooltip Text |
   |-----------|---------|---------|-------------|
   | Target time (`-t`) | Number input (seconds) | 0 | Time budget in seconds. Stop adding masks once cumulative estimated time exceeds this. 0 = no limit. Example: 86400 = 24 hours. |
   | Passwords/sec (`--pps`) | Number input | 1,000,000,000 | Your estimated hash rate. Check hashcat benchmark for your GPU + hash type. |
   | Sort by | Radio buttons | optindex | **optindex**: best ratio of occurrences to complexity (recommended). **occurrence**: most common masks first. **complexity**: simplest masks first. |
   | Min/Max length | Spinboxes | No filter | Only include masks for passwords within this length range. |
   | Min/Max occurrence | Spinboxes | No filter | Only include masks seen at least / at most this many times. |
   | Show mask details | Checkbox | Off | Display per-mask statistics in the output. |

3. **Output**
   - Table of generated masks with: mask string, occurrence count, keyspace, estimated time, coverage percentage.
   - Cumulative coverage graph.
   - **"Export as .hcmask"** button.
   - "Add selected to Mask Builder list" to merge into Module 12.

---

### Module 14: PolicyGen GUI (PACK)

**Menu description:** *"Generate hashcat masks that comply with (or violate) a specific password policy. For example: 'at least 8 characters, at least 1 uppercase, 1 digit, 1 special'. Useful for targeted attacks against known policies."*

**Underlying tool:** `Scripts_to_use/pack-master/policygen.py` (port to Python 3).

#### 3.14.1 Functional Requirements

1. **Policy Parameters**

   | Parameter | Control | Default | Tooltip Text |
   |-----------|---------|---------|-------------|
   | Min length | Spinbox | 8 | Minimum password length required by the policy. |
   | Max length | Spinbox | 8 | Maximum password length. |
   | Min/Max digits | Spinboxes | 0 / unlimited | Minimum and maximum digit characters required. |
   | Min/Max lowercase | Spinboxes | 0 / unlimited | Minimum and maximum lowercase letters. |
   | Min/Max uppercase | Spinboxes | 0 / unlimited | Minimum and maximum uppercase letters. |
   | Min/Max special | Spinboxes | 0 / unlimited | Minimum and maximum special characters. |
   | Non-compliant mode | Checkbox | Off | Generate masks that VIOLATE the policy instead of complying. Useful for catching users who don't follow rules. |
   | Passwords/sec | Number input | 1,000,000,000 | Hash rate for time estimation. |

2. **Output**
   - Count of compliant masks, total keyspace, estimated time.
   - Table of masks (if "show masks" enabled).
   - **"Export as .hcmask"** button.

---

### Category: Rule Tools

---

### Module 15: Rule Builder

**Menu description:** *"Visually construct hashcat mangling rules. See a plain-language description of what each rule does, preview the transformation on sample words in real-time, and build .rule files."*

**Underlying tool:** New — built from scratch. Uses `hashcat --stdout` for validation.

#### 3.15.1 Functional Requirements

1. **Rule Function Library**
   A searchable/filterable list of all hashcat rule functions, grouped by category. Each entry shows: symbol, name, description, example. Tooltip on each with full explanation.

   Categories:
   - **Case rules:** `l` (lowercase), `u` (uppercase), `c` (capitalize), `C` (invert capitalize), `t` (toggle all), `TN` (toggle at position N)
   - **Append/Prepend:** `$X` (append char), `^X` (prepend char)
   - **Positional:** `DN` (delete at N), `[` (truncate left), `]` (truncate right), `iNX` (insert at N), `oNX` (overwrite at N), `xNM` (extract substring), `ONM` (omit range), `'N` (truncate at N)
   - **Rotation/Reflection:** `r` (reverse), `{` (rotate left), `}` (rotate right), `f` (reflect), `d` (duplicate), `pN` (duplicate N times), `q` (duplicate all chars), `zN` (dup first N), `ZN` (dup last N), `yN` (dup block front), `YN` (dup block back)
   - **Swap:** `k` (swap front), `K` (swap back), `*NM` (swap at N,M)
   - **Substitution:** `sXY` (replace X with Y), `@X` (purge char X)
   - **Rejection:** `>N` (reject if length < N), `<N` (reject if length > N), `!X` (reject if not containing X), `/X` (reject if containing X)
   - **Memory:** `X` (extract from memory), `M` (memorize current word), `4` (append from memory), `6` (prepend from memory)
   - **Advanced (toggle-gated):**
     - *Title Case:* `E` (title case), `eX` (title w/separator)
     - *Bitwise/ASCII:* `+N` (ASCII increment), `-N` (ASCII decrement), `.N` (replace N+1), `,N` (replace N−1), `LN` (bitwise shift left), `RN` (bitwise shift right)
     - *Adv. Rejection:* `_N` (reject ≠ len), `(X` (reject ≠ first), `)X` (reject ≠ last), `=NX` (reject ≠ at N), `%NX` (reject < N of X), `Q` (reject mem match)
     - *Utility:* `:` (nothing / passthrough)

2. **Rule Chain Builder**
   - Click a function in the library to add it to the chain.
   - The chain is displayed as an ordered list in the center panel.
   - Each function shows its symbol and inline parameter fields (position N, character X) where applicable.
   - Drag-and-drop to reorder. Delete button to remove.

3. **Real-Time Description**
   Below the chain, an auto-updating plain-language description:
   > Rule: `l $1 $!`
   > "1. Convert the password to all lowercase. 2. Append '1' to the end. 3. Append '!' to the end."
   > "Net effect: lowercase the word, then add '1!' as a suffix."

4. **Real-Time Preview**
   - Text field: enter a sample word (e.g., `Password`).
   - Result updates live as the rule chain changes.
   - Example: `Password` → `password1!` (for rule `l $1 $!`).
   - Optionally load a small wordlist and show the rule applied to all words in a table.

5. **Rule List Accumulator**
   - "Add to List" appends the current rule chain (as a single rule line) to a growing list.
   - Each entry: raw hashcat notation + plain-language description.
   - Reorder, edit, delete entries.
   - **"Export as .rule"** saves as a hashcat rule file.
   - **"Import .rule"** loads existing rule files for viewing/editing/extending.

#### 3.15.2 Data Flow

- **In:** Existing `.rule` files from `hashcat-7.1.2/rules/` or file system.
- **Out:** `.rule` files to Attack Launcher.

---

### Module 16: RuleGen GUI (PACK)

**Menu description:** *"Reverse-engineer hashcat rules from cracked passwords. Given a list of cracked passwords, this tool figures out what base words and transformations (rules) would produce them. Great for discovering real-world mangling patterns."*

**Underlying tool:** `Scripts_to_use/pack-master/rulegen.py` (port to Python 3).

#### 3.16.1 Functional Requirements

1. **Input**
   - File browser for cracked password file, or paste-box for a single password (`--password`).

2. **Parameters**

   | Parameter | Control | Default | Tooltip Text |
   |-----------|---------|---------|-------------|
   | Dictionary provider | Dropdown | aspell | Spell-check dictionary provider for finding source words. aspell is most common. |
   | Language | Dropdown | en | Dictionary language. |
   | Custom wordlist | File browser | None | Use a custom dictionary file instead of/alongside the system dictionary. |
   | Output basename | Text field | `analysis` | Prefix for output files. Produces: `<name>.word`, `<name>.rule`, `<name>-sorted.word`, `<name>-sorted.rule`. |
   | More words | Checkbox | Off | Generate more possible source words (slower, more thorough). |
   | Simple words | Checkbox | Off | Prefer simpler, shorter source words. |
   | More rules | Checkbox | Off | Generate more possible rule variants (slower). |
   | Simple rules | Checkbox | Off | Prefer simpler, shorter rules. |
   | Validate with hashcat | Checkbox | Off | Cross-validate discovered rules using `hashcat --stdout`. Slower but more accurate. |

3. **Output**
   - Table: Discovered source words (with frequency) and discovered rules (with frequency).
   - "Add rules to Rule Builder list" button.
   - "Add words to wordlist" export.

---

### Module 17: PCFG Rule Editor GUI

**Menu description:** *"Edit a trained PCFG ruleset to match a specific password policy. Filter base structures by length, required character types, and custom regex patterns. Create policy-targeted variants of existing rulesets."*

**Underlying tool:** `Scripts_to_use/pcfg_cracker-master/edit_rules.py`

#### 3.17.1 Functional Requirements

1. **Parameters**

   | Parameter | Control | Default | Tooltip Text |
   |-----------|---------|---------|-------------|
   | Ruleset (`-r`) | Dropdown (from `Rules/`) | — | The PCFG ruleset to edit. |
   | Create copy (`--copy`) | Checkbox | Off | Create a copy of the ruleset before editing, leaving the original intact. |
   | Min length | Spinbox | 0 | Minimum total password length for kept base structures. |
   | Max length | Spinbox | 0 (no limit) | Maximum total password length. |
   | Terminal types | Checkboxes: A, D, Y, O, K, X | All checked | Which terminal types to keep. A=Alpha, D=Digits, Y=Year, O=Special, K=Keyboard walk, X=Context. Unchecked types are removed. |
   | Regex filter | Text field | None | Comma-separated regexes. ALL must match for a structure to be kept. |

2. **Preview & Apply**
   - "Preview" shows structures that would be kept vs. removed, with counts.
   - "Apply" runs `edit_rules.py` and updates the ruleset.

---

### Category: Attack Launcher

---

### Module 18: Hashcat Command Builder & Launcher

**Menu description:** *"Visually construct a hashcat attack command, then launch it in a native terminal window. Supports all attack modes: dictionary, mask, combinator, hybrid. Receives wordlists, rules, and masks from other tools."*

**Underlying tool:** `hashcat-7.1.2/hashcat.exe` (Windows) or `hashcat.bin` (Linux).

#### 3.18.1 Key Design Decision: External Terminal

**The application does NOT embed a hashcat terminal.** Instead, it:
1. Builds the complete hashcat command line from GUI controls.
2. Displays the command in a copyable preview field.
3. On "Launch", **spawns a native OS terminal window** (cmd/PowerShell on Windows, bash/gnome-terminal/xterm on Linux) running the constructed command.

**Rationale:** Hashcat is a long-running, interactive process with its own keyboard controls (s=status, p=pause, r=resume, q=quit, c=checkpoint). Embedding it in a Python GUI would lose these features and risk buffering/display issues. A native terminal gives the user full control.

**Implementation:**
- **Windows:** `subprocess.Popen(['cmd', '/c', 'start', 'cmd', '/k', hashcat_command])` or PowerShell equivalent.
- **Linux:** Detect available terminal emulator (`gnome-terminal`, `xfce4-terminal`, `konsole`, `xterm`) and spawn: `gnome-terminal -- bash -c "hashcat_command; read -p 'Press Enter to close'"`.

#### 3.18.2 Functional Requirements

1. **Attack Mode Selector**
   Dropdown with tooltips:

   | Mode | Name | Tooltip |
   |------|------|---------|
   | 0 | Dictionary | Straight wordlist attack. Try every word, optionally applying mangling rules. |
   | 1 | Combinator | Concatenate one word from each of two wordlists. |
   | 3 | Brute-Force / Mask | Generate candidates from a mask pattern (e.g., ?u?l?l?l?d?d). |
   | 6 | Hybrid: Wordlist + Mask | Append mask-generated suffixes to each word in a wordlist. |
   | 7 | Hybrid: Mask + Wordlist | Prepend mask-generated prefixes to each word in a wordlist. |
   | 9 | Association | Wordlist attack using per-hash hint words. |

2. **Hash Configuration**

   | Control | Tooltip |
   |---------|---------|
   | Hash file | File containing the hashes to crack. One hash per line (or hash:salt depending on format). |
   | Hash mode (`-m`) | Searchable dropdown of all hashcat modes. E.g., "0 - MD5", "1000 - NTLM", "2500 - WPA/WPA2". |
   | Single hash paste | Paste a single hash directly instead of using a file. |

3. **Input Configuration** (adapts to selected attack mode)
   - **Mode 0 (Dictionary):** Wordlist file browser + optional rule file browser.
   - **Mode 3 (Mask):** Mask input field or `.hcmask` file browser. Custom charset fields `-1` through `-4`.
   - **Mode 1 (Combinator):** Two wordlist file browsers.
   - **Modes 6/7 (Hybrid):** Wordlist file browser + mask input.
   - **Stdin pipe mode:** Checkbox "Pipe from external generator". When enabled, the spawned terminal runs: `generator_command | hashcat --stdin ...`. The user specifies the generator command (or it is auto-filled when receiving from PRINCE/PCFG Guesser).

   **"Receive from..." buttons:** For each input field, a button listing available outputs from other modules:
   - Wordlists from: PRINCE, Combinator, PCFG Guesser, Element Extractor, PRINCE-LING, demeuk.
   - Rules from: Rule Builder, RuleGen.
   - Masks from: Mask Builder, MaskGen, PolicyGen.

4. **Advanced Options** (collapsible panel, all with tooltips)

   | Option | Control | Tooltip |
   |--------|---------|---------|
   | `--force` | Checkbox | Ignore warnings. Use when hashcat complains but you know you want to proceed. |
   | `-w` (workload) | Slider (1-4) | Workload profile. 1=Low (desktop usable), 2=Default, 3=High (some lag), 4=Nightmare (system nearly unusable). |
   | `-O` (optimized) | Checkbox | Use optimized GPU kernels. Faster but limits max password length to 32. |
   | `--increment` | Checkbox | Try shorter masks first, incrementing up. E.g., for mask ?a?a?a?a: try 1-char, then 2-char, etc. |
   | `--increment-min/max` | Spinboxes | Range for incremental mode. |
   | `-o` (output) | File browser | File to write cracked hash:password pairs to. |
   | `--outfile-format` | Dropdown | Output format: 1=hash:plain, 2=plain, 3=hex, etc. |
   | `--potfile-disable` | Checkbox | Don't use the potfile. By default hashcat skips already-cracked hashes. |
   | `--session` | Text field | Session name. Allows pausing with 'c' key and restoring with --restore. |
   | `--status` | Checkbox | Auto-display status at regular intervals. |
   | `--status-timer` | Spinbox | Seconds between auto-status updates. |
   | `-j` / `-k` | Text fields | Inline rules applied to left/right wordlists in combinator mode. |

5. **Command Preview**
   - A read-only text field showing the **full hashcat command** as it would be executed, updated live.
   - "Copy to Clipboard" button.
   - "Edit Manually" toggle — switches to editable mode where the user can hand-modify the command.

6. **Launch**
   - **"Launch in Terminal" button** — spawns the external terminal with the command.
   - If the command includes a pipe (stdin mode), the full pipeline is launched: `prince_command | hashcat ...`.
   - The GUI shows a confirmation: "Hashcat launched in external terminal. Use hashcat's keyboard controls: s=status, p=pause, r=resume, q=quit."

#### 3.18.3 Data Flow

- **In:** Wordlists, rules, masks, pipe commands from all other modules.
- **Out:** The external terminal session. Cracked results can be loaded back (via potfile or output file) into Password Scorer or RuleGen.

---

### Category: Utilities

---

### Module 19: Web Scraper Generator

**Menu description:** *"Generate a ready-to-run Linux script that scrapes text from a website, extracts individual words, deduplicates them, and optionally removes filler/stop words. The script runs independently — the GUI just builds it."*

**Underlying tool:** New — generates a script, does not scrape directly.

#### 3.19.1 Functional Requirements

1. **Target Configuration**

   | Control | Tooltip |
   |---------|---------|
   | Target URL(s) | One or more URLs to scrape. One per line. |
   | Crawl depth | 0 = single page only. 1 = follow links one level. Higher = deeper crawl. Be careful with large sites. |
   | URL filter (regex) | Only follow links matching this pattern. Example: `https://example\.com/wiki/.*` |
   | User-Agent | Browser user agent string. Default: generic Chrome UA. |
   | Request delay (sec) | Seconds to wait between requests. Be polite to servers. Default: 1. |

2. **Text Processing Options**

   | Option | Default | Tooltip |
   |--------|---------|---------|
   | Tokenize into words | On | Split text on whitespace/punctuation into individual words. |
   | Lowercase all | Off | Convert all words to lowercase before deduplication. |
   | Sort & unique | On | Sort and remove duplicate words. |
   | Min word length | 1 | Discard words shorter than this. |
   | Max word length | 64 | Discard words longer than this. |
   | Remove HTML tags | On | Strip residual HTML markup. |
   | Remove numbers-only | Off | Discard tokens that are purely numeric. |

3. **Stop Word Filtering**
   - Checkbox: "Enable stop word filtering" (default: Off).
   - Editable text area with default English stop words.
   - Load custom stop word list from file.
   - Tooltip: *"Remove common filler words (the, a, is, etc.). Leave OFF for password cracking — stop words like 'love' and 'the' appear in many passwords."*

4. **Anti-Detection Options**

   | Option | Default | Tooltip |
   |--------|---------|--------|
   | Rotate User-Agent | On | Pick a random User-Agent from a pool of 12 real browser strings (Chrome/Firefox/Edge/Safari on Windows/Mac/Linux) for each request. |
   | Send realistic browser headers | On | Add Accept, Accept-Language, Accept-Encoding, DNT, Sec-Fetch-*, Upgrade-Insecure-Requests, and Referer headers that real browsers send. |
   | Random delay jitter (±50%) | On | Randomize the delay between requests by ±50% to avoid fixed-interval detection. |
   | Max retries per request | 3 | Retry failed requests with exponential backoff (2^attempt + random). 0 = no retries. |
   | Proxy URL | (empty) | Route all requests through http://, https://, or socks5:// proxy. Leave empty for direct. |

   **Implementation details:**
   - UA pool is embedded in the generated script as a constant array (12 browser strings).
   - Retry loop with exponential backoff: 2^(attempt+1) + random(0–3) seconds between retries.
   - Referer header is automatically set to the parent page URL when following links.
   - All three script types (Bash, Python, PowerShell) implement the same anti-detection measures.

5. **Script Generation**
   - Radio: generate Bash (`.sh`), Python (`.py`), or PowerShell (`.ps1`) script.
   - Code preview with syntax highlighting, editable before saving.
   - "Save Script" button.
   - Generated script is self-contained with dependency checks and comments.

6. **Load Results Back**
   - "Load Scraped Wordlist" convenience button to import results after external execution.

---

### Module 20: Markov Chain / .hcstat2 GUI

**Menu description:** *"Load, visualize, and train hashcat Markov chain statistics (.hcstat2 files) for smarter brute-force candidate ordering. Configure Markov parameters for the Hashcat Command Builder."*

**Data flow:**
- **In:** `.hcstat2` files (hashcat Markov statistics), plain-text password lists (for training).
- **Out:** Trained `.hcstat2` files, `markov_config.json` sidecar → Hashcat Command Builder via DataBus.

#### .hcstat2 Binary Format

The module implements a pure-Python parser/writer for hashcat's `.hcstat2` binary format:
- **Compression:** Raw LZMA2 (not `.xz` container), property byte `0x1c` → 64 MB dictionary.
- **Decompressed size:** 134,742,032 bytes.
- **Layout (all big-endian `u64`):**
  - Bytes 0–7: Version — `0x6863737461740002` (`"hcstat\x00\x02"`).
  - Bytes 8–15: Reserved (zero).
  - Bytes 16–524,303: `root[256][256]` — root character frequency counts per position.
  - Bytes 524,304–134,742,031: `markov[256][256][256]` — transition counts `[position][prev_char][char]`.

#### 1. Mode Selector

Radio buttons select the operating mode:
- **Analyze .hcstat2** — load an existing file and visualize frequency data.
- **Train new .hcstat2** — read a password list and generate a new statistics file.

#### 2. Analyze Mode

- File browser for `.hcstat2` file (pre-filled with `hashcat-7.1.2/hashcat.hcstat2` if found).
- **Position spinbox** (0–255): selects the password position to inspect.
- **Previous char combo** (printable ASCII + NUL): selects the preceding character for transition analysis.
- Four output tabs:

  **Tab 1 — Root Frequencies:** QTableWidget with columns: Rank, Character, Code, Count. Shows top 100 characters at the selected position with `_freq_color` heat-coloured cells (blue→cyan→yellow→red). Header label shows distinct character count and total occurrences.

  **Tab 2 — Transitions:** Same table layout as Root Frequencies. Shows top 100 next-characters for the selected position + previous character combination.

  **Tab 3 — Position Heatmap:** QTableWidget with 95 rows (printable ASCII 32–126) × configurable column range (default 0–15). Start/End position spinboxes with "Refresh Heatmap" button. Cell colours reflect root frequency with tooltip showing `Pos N, 'c': count`.

  **Tab 4 — Summary:** Monospaced QTextEdit showing per-position statistics: distinct character count, total occurrences, and top 5 characters. Shows up to positions 0–31 with "… (N more positions)" for longer data.

#### 3. Train Mode

- Password list file browser (`.txt`, `.dict`, `.lst`).
- Output `.hcstat2` file save browser.
- Min/Max password length spinboxes (default 1–64, range 1–256).
- Training runs in a background thread with periodic progress updates (every 500K passwords).
- On completion: saves the compressed `.hcstat2`, auto-loads it for analysis, switches to Analyze mode.

#### 4. Hashcat Markov Settings (always visible)

| Control             | Flag                 | Tooltip / Notes                                                                                        |
|---------------------|----------------------|--------------------------------------------------------------------------------------------------------|
| Threshold (QSpinBox)| `--markov-threshold` | 0–65535, special value text "0 (unlimited)". Lower values = faster but fewer candidates.               |
| Classic (QCheckBox) | `--markov-classic`   | Non-per-position Markov — all positions share same transition table.                                   |
| Inverse (QCheckBox) | `--markov-inverse`   | Invert ordering — least probable candidates first.                                                     |
| Disable (QCheckBox) | `--markov-disable`   | Disable Markov chains entirely — pure brute-force ordering.                                            |

#### 5. Send to Hashcat Command Builder

- Writes `markov_config.json` with keys: `markov_hcstat2`, `markov_threshold`, `markov_classic`, `markov_inverse`, `markov_disable`.
- Sends via DataBus to the Hashcat Command Builder.
- Falls back to manual instruction if DataBus is unavailable.

---

### Category: Hash Extraction

---

### Module 22: Hash Extractor

**Menu description:** *"Extract password hashes from encrypted files, containers, wallets, databases, and archives using hashcat and John the Ripper extraction tools. Supports 24 hashcat extractors and 100+ JtR extractors with automatic format cleanup and one-click send to Hashcat Command Builder."*

**Underlying tools:**
- `hashcat-7.1.2/tools/` — 24 `*2hashcat` scripts (18 Python, 6 Perl)
- `john-1.9.0-jumbo-1-win64/run/` — 105 `*2john` tools (81 Python, 11 Perl, 11 exe, 2 other)

#### 3.22.1 Functional Requirements

1. **Extractor Selection**
   - Categorized QTreeWidget of all available extractors grouped by type (Encryption/Containers, Archive, Document, Wallet/Crypto, Authentication/Keys, System/Disk, Virtual Machines, Backup, Network/Protocol, Database, Other)
   - Each entry shows source badge (🔵 Hashcat / 🟡 JtR) and compatibility indicator (✅ Hashcat Ready / ⚠️ Hashcat Compatible after cleanup / ❌ JtR Format Only)
   - Search/filter field at top for quick lookup by name or category
   - JtR tools auto-discovered by scanning `john-*/run/*2john*` at module initialization

2. **Input Description**
   - Dynamic description label below the tree showing what input file is expected (plain language), required dependencies, and any notes for the selected extractor
   - Yellow dependency banner for tools needing external Python packages (e.g., `pip install cryptography`)

3. **File Input**
   - File browser with appropriate file filter per extractor
   - Drag-and-drop zone that accepts file drops and populates the input path

4. **VeraCrypt / TrueCrypt Special Options** (shown only when applicable)

   | Option | Offset Value | Description |
   |--------|-------------|-------------|
   | Standard volume | 0 | Default — reads from start of container |
   | Bootable partition | 31744 | For system-encrypted boot partitions |
   | Hidden container | 65536 | VeraCrypt hidden volume within outer volume |
   | Bootable + Hidden | 97280 | Combined offset |

   - Radio button group, plus "Extract raw 512 bytes" checkbox for manual analysis
   - **"View all supported hashcat modes" button** opens a modal dialog (`_FDEModeDialog`) with a table of all VeraCrypt (39 modes) or TrueCrypt (21 modes) hashcat modes, showing:
     - Mode ID (`-m` value)
     - Hash Algorithm (RIPEMD-160, SHA-256, SHA-512, Whirlpool, Streebog-512)
     - XTS Key Size (512 / 1024 / 1536 bit)
     - Cipher configuration (single cipher, two-cipher cascade, three-cipher cascade)
     - Boot variant (standard, boot, boot-mode, boot-mode legacy)
   - User can select a specific mode from the table to set as **preferred mode** for "Send to Hashcat" — stored in `_preferred_mode`, displayed below the button, and written to the `.meta` sidecar

5. **BitLocker / MetaMask Special Options** (shown only when applicable)
   - BitLocker: partition offset spinbox
   - MetaMask: "Use short data format (mode 26610)" checkbox

6. **Output**
   - Read-only QTextEdit displaying extracted hash(es)
   - JtR prefix cleanup toggle: checkbox "Strip filename/username prefix for hashcat use" (default: ON), shown only for JtR extractors
   - Copy to clipboard and Save to file buttons
   - Hashcat mode display: suggested `-m` mode(s) for the selected extractor

7. **Send to Hashcat Command Builder**
   - Button enabled when hashcat mode(s) are known; saves hash to file and navigates to Hashcat Command Builder with hash file path pre-filled via DataBus

8. **Execution**
   - Background thread via `subprocess.Popen` with interpreter routing: `.py` → Python, `.pl` → Perl, `.exe` → direct
   - Perl availability checked at init; `.pl` tools disabled if Perl not found
   - ImportError parsing for friendly dependency install messages

#### 3.22.2 Hashcat Extractor Inventory

All 24 scripts from `hashcat-7.1.2/tools/`:

| Script | Input File | External Deps | Notes |
|--------|-----------|---------------|-------|
| `aescrypt2hashcat.pl` | AES Crypt `.aes` | Perl | |
| `apfs2hashcat.py` | APFS disk image | `cryptography` | |
| `bisq2hashcat.py` | Bisq `.wallet` | `protobuf` | |
| `bitlocker2hashcat.py` | BitLocker disk image | None | Requires `-o` offset |
| `bitwarden2hashcat.py` | Bitwarden local data | `snappy`, `leveldb` | |
| `cachedata2hashcat.py` | Windows CloudAP CacheData | None | |
| `cryptoloop2hashcat.py` | Cryptoloop partition | None | |
| `exodus2hashcat.py` | Exodus wallet `.seco` | None | |
| `gitea2hashcat.py` | Gitea DB hash string | None | |
| `keybag2hashcat.py` | iOS/macOS keybag | None | |
| `kremlin2hashcat.py` | Kremlin `.kgb` | None | |
| `lastpass2hashcat.py` | LastPass local DB | None | |
| `luks2hashcat.py` | LUKS container | None | |
| `metamask2hashcat.py` | MetaMask vault JSON | None | `--shortdata` for mode 26610 |
| `mozilla2hashcat.py` | Firefox key3/key4.db | `PyCryptodome`, `pyasn1` | |
| `radmin3_to_hashcat.pl` | Registry `.reg` export | Perl | |
| `securenotes2hashcat.pl` | Apple NoteStore.sqlite | Perl `DBI`, `DBD::SQLite` | |
| `shiro1-to-hashcat.py` | Apache Shiro `.pcl` | None | |
| `sqlcipher2hashcat.pl` | SQLCipher `.db` | Perl | |
| `truecrypt2hashcat.py` | TrueCrypt container | None | `--offset` for bootable/hidden |
| `veeamvbk2hashcat.py` | Veeam `.vbk` | None | |
| `veracrypt2hashcat.py` | VeraCrypt container | None | `--offset` for bootable/hidden |
| `virtualbox2hashcat.py` | VirtualBox `.vbox` | None | |
| `vmwarevmx2hashcat.py` | VMware `.vmx` | None | |

#### 3.22.3 JtR Extractor Auto-Discovery

The module dynamically scans `john-*/run/` for files matching `*2john*`. For each discovered tool:
- Name derived from filename: `office2john.py` → "Office"
- Category assigned by curated override or defaults to "Other"
- Default `hashcat_compatible=False` unless curated with known mode mapping

Approximately 48 popular JtR tools have curated metadata with hashcat mode mappings, compatibility flags, and proper file filters.

#### 3.22.4 Data Flow

- **In:** Encrypted files, containers, wallets, databases, archives from file system
- **Out:** Extracted hash(es) → saved to file → sent to Hashcat Command Builder (Module 18) via DataBus with auto-filled hash path and `-m` mode

---

## 4. Cross-Module Features

### 4.1 Shared Data Bus ("Send to..." System)

Every module that produces output (wordlist file, rule file, mask file, element list, candidate stream) exposes a **"Send to..."** button. Clicking it shows a menu of compatible destination modules. The destination's input is auto-populated.

For streaming/pipe scenarios (PRINCE → hashcat, PCFG Guesser → hashcat), the "Send to..." action populates the Attack Launcher's pipe command field with the correct generator command.

### 4.2 Settings Panel

Accessible from the main toolbar:

| Setting | Description |
|---------|-------------|
| Hashcat binary path | Auto-detected from `hashcat-7.1.2/`. User can override. |
| PRINCE binary path | Path to compiled `pp` / `pp.exe`. |
| Python interpreter | For PCFG and PACK scripts. |
| Default output directory | Where generated files are saved by default. |
| Default hash rate (H/s) | Used for time estimates in Mask Builder and MaskGen. |
| Terminal emulator (Linux) | Which terminal to spawn: gnome-terminal, xfce4-terminal, konsole, xterm. Auto-detected. |
| Terminal emulator (Windows) | cmd or PowerShell. Default: cmd. |
| Theme | Light / Dark. |

### 4.3 Logging

- All subprocess executions logged: full command, timestamp, exit code, runtime.
- Accessible via "View Log" in the menu bar.
- Useful for reproducing commands or debugging.

---

## 5. Non-Functional Requirements

### 5.1 Cross-Platform
- **Windows 10/11** and **Linux** (Ubuntu, Debian, Fedora, Arch) equally supported.
- All paths via `pathlib`. No hardcoded separators.
- OS-specific code isolated to: terminal spawning, default paths, and font rendering.

### 5.2 Performance
- GUI remains responsive during all subprocess executions (background threads with non-blocking I/O).
- Real-time output display uses buffered rendering (no freeze from high-throughput stdout).

### 5.3 Error Handling
- Non-zero exit codes: stderr displayed in a highlighted error panel.
- Input validation before execution (files exist, numbers in range, required fields filled).
- Subprocess timeout with user notification.

### 5.4 Dependencies
- Python 3.10+
- PyQt6 or PySide6
- chardet, ftfy, nltk, tqdm, transliterate, unidecode (for demeuk)
- PyEnchant (for RuleGen)
- All thematic wordlists bundled — no runtime web dependencies.

### 5.5 Security
- Designed for **authorized security testing, CTF competitions, and password security research**.
- Scraper generator produces scripts; does not execute scraping from the GUI.
- No data exfiltration — all operations are local.

---

## 6. Architecture Summary

```
┌──────────────────────────────────────────────────────────────────┐
│                     Cracker's Toolkit GUI                        │
├──────────────────┬───────────────────────────────────────────────┤
│   SIDEBAR        │                                               │
│                  │   MAIN CONTENT AREA                           │
│   Wordlist       │                                               │
│   Generation     │   (Tool selection list when browsing          │
│   ├ PRINCE       │    a category, or the active tool's           │
│   ├ PCFG Guesser │    full interface when a tool is opened)      │
│   ├ Combinator   │                                               │
│   ├ PRINCE-LING  │                                               │
│   ├ Elem.Extract │                                               │
│   ├ Keybd Walks  │                                               │
│   └ Date/Numbers │                                               │
│                  │                                               │
│   Wordlist       │                                               │
│   Cleaning       │                                               │
│   └ demeuk       │                                               │
│                  │                                               │
│   Wordlist       │                                               │
│   Analysis       │                                               │
│   ├ PCFG Trainer │                                               │
│   ├ Passwd Scorer│                                               │
│   └ StatsGen     │                                               │
│                  │                                               │
│   Mask Tools     │                                               │
│   ├ Mask Builder │                                               │
│   ├ MaskGen      │                                               │
│   └ PolicyGen    │                                               │
│                  │                                               │
│   Rule Tools     │                                               │
│   ├ Rule Builder │                                               │
│   ├ RuleGen      │                                               │
│   └ PCFG RuleEd. │                                               │
│                  │                                               │
│   Attack         │                                               │
│   Launcher       │                                               │
│   └ Hashcat      │                                               │
│                  │                                               │
│   Hash           │                                               │
│   Extraction     │                                               │
│   └ Hash Extract.│                                               │
│                  │                                               │
│   Utilities      │                                               │
│   ├ Scraper Gen. │                                               │
│   └ Markov (TBD) │                                               │
│                  │                                               │
│   [Settings]     │                                               │
│   [Log]          │                                               │
└──────────────────┴───────────────────────────────────────────────┘
```

---

## 7. Module Quick Reference

| # | Module | Category | Wraps | New/Existing |
|---|--------|----------|-------|-------------|
| 1 | PRINCE Processor | Wordlist Generation | `pp` binary | Existing (GUI wrapper) |
| 2 | PCFG Guesser | Wordlist Generation | `pcfg_guesser.py` | Existing (GUI wrapper) |
| 3 | Combinator | Wordlist Generation | `combinatorX` binary | Existing (GUI wrapper) |
| 4 | PRINCE-LING | Wordlist Generation | `prince_ling.py` | Existing (GUI wrapper) |
| 5 | Element Extractor | Wordlist Generation | — | **New** |
| 6 | Keyboard Walk Generator | Wordlist Generation | — | **New** |
| 7 | Date & Number Patterns | Wordlist Generation | — | **New** |
| 8 | demeuk Cleaner | Wordlist Cleaning | `demeuk.py` | Existing (GUI wrapper) |
| 9 | PCFG Trainer | Wordlist Analysis | `trainer.py` | Existing (GUI wrapper) |
| 10 | Password Scorer | Wordlist Analysis | `password_scorer.py` | Existing (GUI wrapper) |
| 11 | StatsGen | Wordlist Analysis | `statsgen.py` | Existing (port to Py3 + GUI) |
| 12 | Mask Builder | Mask Tools | — | **New** |
| 13 | MaskGen | Mask Tools | `maskgen.py` | Existing (port to Py3 + GUI) |
| 14 | PolicyGen | Mask Tools | `policygen.py` | Existing (port to Py3 + GUI) |
| 15 | Rule Builder | Rule Tools | — | **New** |
| 16 | RuleGen | Rule Tools | `rulegen.py` | Existing (port to Py3 + GUI) |
| 17 | PCFG Rule Editor | Rule Tools | `edit_rules.py` | Existing (GUI wrapper) |
| 18 | Hashcat Launcher | Attack Launcher | `hashcat` binary | Existing (GUI command builder) |
| 19 | Scraper Generator | Utilities | — | **New** |
| 20 | Markov GUI | Utilities | `markov_gui.py` | **New** |
| 22 | Hash Extractor | Hash Extraction | hashcat `*2hashcat` tools + JtR `*2john` tools | **New** |

---

## 8. Future Considerations

- **PACK Python 3 Port:** Modules 11, 13, 14, 16 require porting PACK from Python 2 to Python 3. This should be done early.
- **Remote Hashcat Execution:** Future version could support launching hashcat on a remote machine via SSH.
- **Plugin System:** Allow users to add custom tools/scripts to the sidebar.
- **demeuk as pre-processing:** Consider adding a "Clean first with demeuk" quick-option in tools that accept wordlist input.
