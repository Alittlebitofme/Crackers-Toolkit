# Cracker's Toolkit GUI — Implementation Plan V6 (UI/UX Overhaul)

**Reference:** `IMPLEMENTATION_PLAN_V5.md` (✅ closed — 40/43 items)
**Status:** 🔄 Active

---

## Completed Bug Fixes & UI Polish (Pre-V6)

These items were resolved between V5 completion and the start of V6 feature work.

### Build & Runtime Fixes

| # | Issue | Fix | File(s) |
|---|-------|-----|---------|
| B1 | `BaseModule(QWidget, ABC)` metaclass conflict in frozen exe | Removed `ABC` base; `sip.wrappertype` vs `ABCMeta` incompatible in PyInstaller bundle | `base_module.py` |
| B2 | `from .data_bus import data_bus` wrong relative import in hashcat_launcher | Changed to `from crackers_toolkit.app.data_bus import data_bus` | `hashcat_launcher.py` |
| B3 | Mask Builder `_mask_label` / `_hash_rate` referenced before creation | Moved init loop after widget creation | `mask_builder.py` |
| B4 | Combinator `_sep_container` referenced before creation | Moved slot init into `build_params_section` | `combinator.py` |
| B5 | `QSpinBox.setRange(1, 999_999_999_999)` overflow (>32-bit int) | Capped to `2_147_483_647` | `settings.py` |
| B6 | Frozen exe `base_dir` detection failed (`Path(__file__)` doesn't work frozen) | Uses `Path(sys.executable)` when `sys.frozen` is set | `main.py` |
| B7 | PRINCE binary `pp64.exe` not found | Compiled from source; updated `_find_pp_binary()` to search nested dirs | `prince_processor.py` |
| B8 | PRINCE & hashcat paths not auto-detected in Settings | Updated `_detect_tools()` to search for `pp64.exe` first, broader search | `settings.py` |

### UI Polish: Tooltip Icons (ⓘ)

Replaced invisible `.setToolTip()` on form widgets (text inputs, combos, checkboxes, spinboxes) with visible **ⓘ** info icons using a `_info_icon()` static method. Blue (#89b4fa), WhatsThisCursor, 16px fixed width.

**Scope:** All 5 base helper methods (`create_file_browser`, `create_spinbox`, `create_checkbox`, `create_combo`, `create_line_edit`) + manual tooltip calls in all 16 module files + `SettingsDialog`.

### UI Polish: Hide Empty Advanced Options

Modified `_build_ui()` in `base_module.py`: after calling `build_advanced_section()`, checks if `content_layout().count() > 0`; if empty, hides the collapsible section entirely. Affects 11 modules that don't define advanced options.

---

## Phase 24: PCFG Trainer Integration (✅ Complete)

### 24.1 PCFG Guesser — Trainer Workflow Banner ✅
**File:** `modules/pcfg_guesser.py`

- [x] Added a prominent yellow-bordered "⚠ Requires Trained PCFG Ruleset" banner at the top of the input section
- [x] Banner explains the PCFG workflow dependency with clear text
- [x] "Open PCFG Trainer →" button navigates to the trainer via `data_bus.navigate_to_tool`
- [x] Replaced `create_combo()` with manual QComboBox + "↻" refresh button on the same row
- [x] Added `_refresh_rulesets()` method to reload rulesets from disk after training

### 24.2 PRINCE-LING — Trainer Workflow Banner ✅
**File:** `modules/prince_ling.py`

- [x] Same treatment as 24.1: workflow banner, "Open PCFG Trainer →" button, refresh button
- [x] Banner text customised for PRINCE-LING's specific use case

---

## Phase 25: Mask Builder Redesign (✅ Complete)

### 25.1 Click-to-Add Palette ✅
**File:** `modules/mask_builder.py`

Old design: Each mask position used a QComboBox dropdown to select ?l/?u/?d etc., plus an "Add Position" / "Remove Last" button pair.

New design:
- [x] **Palette** of colour-coded buttons: `[?l a-z]` `[?u A-Z]` `[?d 0-9]` `[?s Special]` `[?a All]` `[?b Bytes]` `[?1]` `[?2]` `[?3]` `[?4]` `[Abc Literal]`
- [x] Clicking any palette button instantly adds a **MaskChip** to the sequence
- [x] Each chip colour-coded by type (green=lowercase, red=uppercase, blue=digits, etc.)

### 25.2 Chip-Based Mask Sequence ✅

- [x] **MaskChip** class: coloured QFrame tag showing token text + × remove button
- [x] Horizontal scrollable **lane** displays the mask as a sequence of chips
- [x] Click a chip to select it (highlighted with purple border)
- [x] Selected chip shows a **detail panel** below with description and edit controls
- [x] **◀ / ▶ buttons** move the selected chip left/right in the sequence
- [x] "Clear All" button removes all chips

### 25.3 Multi-Character Literal Support ✅

- [x] Literal chips accept **multi-character strings** (not limited to 1 char)
- [x] E.g., typing "hello" creates one chip that expands to 5 literal positions in the mask string
- [x] Each character = 1 fixed position (keyspace contribution = 1)
- [x] Detail panel shows editable QLineEdit when a literal chip is selected
- [x] **Input validation**: `?` character is rejected with clear warning (reserved for placeholders)
- [x] Chip display updates live as user types

### 25.4 Preserved Features ✅

- [x] Custom charset section with 4 slots + "Import from Element Extractor" buttons
- [x] Live mask string display, position-by-position description, keyspace calculation
- [x] Hash rate input + estimated crack time
- [x] Mask list accumulator table with reorder/edit/delete actions
- [x] Export/Import .hcmask with custom charset embedding
- [x] `_tokenize_mask()` groups consecutive literal characters into one token when loading masks

---

## Phase 26: Rule Builder Redesign (✅ Complete)

### 26.1 Categorised Palette ✅
**File:** `modules/rule_builder.py`

Old design: QTableWidget with 28 rule functions in 4 columns; select row + "Add to Chain" button.

New design:
- [x] **Categorised palette** with 7 labelled rows: Case, Append/Prepend, Positional, Rotation, Substitution, Rejection, Memory
- [x] Each rule function is a colour-coded button showing `template  name` (e.g., `$X  Append char`)
- [x] Buttons styled per-category (blue=Case, green=Append, yellow=Positional, etc.)
- [x] Hover tooltip shows full description + example transformation

### 26.2 Chip-Based Rule Chain ✅

- [x] **RuleChip** class: coloured QFrame tag showing the assembled rule string + × remove button
- [x] Horizontal scrollable lane displays the rule chain as a sequence of chips
- [x] Click a chip to select it (purple highlight border)
- [x] **Detail panel** shows: rule description, example, and parameter input fields
- [x] Up to 3 parameter fields (N, X, Y, M, I) shown/hidden based on function's param count
- [x] Parameters update the chip display in real-time
- [x] **◀ / ▶ buttons** move the selected chip left/right in the chain
- [x] "Clear Chain" button

### 26.3 Preserved Features ✅

- [x] Live rule string display (hashcat notation)
- [x] Step-by-step description of what each rule in the chain does
- [x] Real-time preview: sample word → transformed word (supports all 28 rule functions)
- [x] Rule list accumulator table with reorder/edit/delete actions
- [x] Export/Import .rule files
- [x] Batch preview: apply all rules to a wordlist file and show results table
- [x] Net effect preview showing each rule's output on the sample word
- [x] `_load_rule_to_chain()` parses rule strings back into chips with correct parameter values

---

## Phase 27: Dark Mode Polish & Controls (✅ Complete)

### 27.1 Checkbox Visibility in Dark Mode ✅

QCheckBox indicators were invisible against the dark theme. Added full `QCheckBox::indicator` stylesheet rules in `main_window.py` `_apply_theme()`: 16×16px, `#7f849c` border, `#313244` background, `#89b4fa` checked border/fill with SVG checkmark.

**Files:** `main_window.py`

### 27.2 Radio Button Visibility in Dark Mode ✅

Same treatment as checkboxes: `QRadioButton::indicator` styled with 9px border-radius (circle), `#89b4fa` checked fill, with an SVG filled circle for the dot.

**Files:** `main_window.py`

### 27.3 SVG Checkmark & Radio Dot ✅

Instead of a solid-fill rectangle when checked, both controls now render proper SVG icons:
- Checkmark: white polyline stroke in 16×16 SVG (`ct_checkmark.svg`)
- Radio dot: white filled circle in 16×16 SVG (`ct_radiodot.svg`)

Both are generated at runtime in `tempfile.gettempdir()`. Stylesheets reference them via `image: url(...)`. CSS braces conflict with f-strings is solved by using string concatenation for `_checked_css`.

**Files:** `main_window.py` (added `import os, tempfile`)

### 27.4 Instant Tooltips ✅

Added `_InstantTooltipStyle(QProxyStyle)` that overrides `SH_ToolTip_WakeUpDelay` and `SH_ToolTip_FallAsleepDelay` to 0ms. Applied via `app.setStyle()` at startup.

**Files:** `main.py` (added `QProxyStyle`, `QStyle` imports)

---

## Phase 28: Bug Fixes & Performance (✅ Complete)

### 28.1 PRINCE Processor pp.c Error ✅

User's `settings.json` had `prince_path` pointing to `pp.c` (source file) instead of `pp64.exe`. Fixed the saved config. Hardened both `_find_pp_binary()` and `_detect_tools()` to reject files with source extensions (`.c`, `.h`, `.py`, `.txt`, `.md`).

**Files:** `prince_processor.py`, `settings.py`, user's `~/.crackers_toolkit/settings.json`

### 28.2 Large File Preview Freeze (5 modules) ✅

Five modules were reading entire files for preview/inspection, causing GUI freezes on large wordlists:

| Module | Problem | Fix |
|--------|---------|-----|
| Combinator | `get_words()[:20]` loaded entire file | `_peek_head(20)` reads first 20 lines + estimates total from file size |
| PCFG Trainer | `sum(1 for _ in f)` counted all lines | Estimates line count from average of first 10 lines × file size |
| Prince Processor | `sum(1 for _ in f)` in `_on_wordlist_changed` | Samples 64 lines, estimates total |
| PCFG Guesser | Line count in `_on_process_finished` | Samples 64 lines of output file |
| Scraper Generator | `f.readlines()` in `_load_results` | Reads only first 1000 lines |

**New methods in Combinator:** `_peek_head(n)` returns `(head_lines, estimated_total)`, `has_words()` for validation without loading entire file.

**Files:** `combinator.py`, `pcfg_trainer.py`, `prince_processor.py`, `pcfg_guesser.py`, `scraper_generator.py`

### 28.3 👁 Emoji Not Rendering ✅

The eye emoji on the Peek button didn't render in some fonts. Changed to text "Peek" button, widened from 42px fixed to 50px minimum width.

**Files:** `combinator.py`

---

## Phase 29: Combinator Preview Mode (✅ Complete)

Added "Preview (first 100 candidates)" button + `QTextEdit` preview box in Combinator output section. Uses `_peek_head(50)` from each slot, runs `itertools.product` capped at 100 results. Allows users to preview combined output before committing to a full run.

**Files:** `combinator.py` (`_on_preview()` method, `build_output_section` additions)

---

## Phase 30: Reset to Defaults & Default Output Folders (✅ Complete)

### 30.1 Reset to Defaults Button ✅

Every module now has a "Reset to Defaults" button in the execution controls row (next to Run/Stop). The mechanism:

1. `_snapshot_defaults()` — called after `_build_ui()` in `BaseModule.__init__()`. Walks all child `QSpinBox`, `QCheckBox`, `QRadioButton`, `QComboBox`, `QLineEdit`, and writable `QTextEdit` widgets, recording their initial values.
2. `_reset_to_defaults()` — restores all recorded widgets to their snapshotted values and clears the output log.

**Files:** `base_module.py` (added `import re, sys`, `QRadioButton` import; `_snapshot_defaults()`, `_reset_to_defaults()` methods; "Reset to Defaults" `QPushButton` in exec_layout)

### 30.2 Default Output Folders ✅

Each module's output file browser is now pre-filled with a sensible default path:

`<base_dir>/output/<module_slug>_output/<filename>`

The `_default_output_dir()` method in `BaseModule` generates the slug from `MODULE_NAME` and creates the directory if needed.

| Module | Default filename |
|--------|-----------------|
| Date Number Generator | `date_number_patterns.txt` |
| Element Extractor | `extracted_elements.txt` |
| Keyboard Walk Generator | `keyboard_walks.txt` |
| Combinator | `combined.txt` |
| Prince Processor | `prince_candidates.txt` |
| PCFG Guesser | `pcfg_guesses.txt` |
| PRINCE-LING | `prince_ling_words.txt` |
| Demeuk Cleaner | `cleaned.txt` |
| MaskGen | `generated.hcmask` |
| PolicyGen | `policy_masks.hcmask` |
| StatsGen | `statsgen_output.csv` |
| Hashcat Launcher | `cracked.txt` |

**Files:** `base_module.py` (`_default_output_dir()`), all 12 module files above (`.setText()` after `create_file_browser`)

---

## Build Notes

- `crackers_toolkit.spec` `console` flag reverted from `True` (debug) to `False` (release)
- Exe rebuilt: `dist/CrackersToolkit/CrackersToolkit.exe`

---

## Remaining Items (Carried from V5)

| # | Item | Priority | Status |
|---|------|----------|--------|
| 23.5 | StatsGen bar charts (optional — text tables are spec-compliant) | P3 | Deferred |
| 23.6 | Linux testing (all modules, terminal spawning, path handling) | P3 | Not started |
| 23.7 | Theme polish (dark/light theme on all widget types) | P3 | Not started |

---

## Overall Project Status

| Plan | Scope | Status |
|------|-------|--------|
| V1 | 19 modules, full skeleton, Phases 1–6 | ✅ Complete |
| V2 | 29 spec-gap items, Phases 7–10 | ✅ Complete |
| V3 | 18 polish items, Phases 11–14 | ✅ Complete |
| V4 | 19 hardening items, Phases 15–18 | ✅ Closed |
| V5 | ~40 final compliance items, Phases 19–23 | ✅ Closed (40/43 done) |
| V6 (this plan) | UI/UX overhaul + bug fixes, Phases 24–34 | ✅ Complete |

Estimated overall spec compliance: **~96%** (remaining: Linux testing, optional charts, theme polish).

---

## Phase 31: Incomplete Chip Warning Indicators (✅ Complete)

### 31.1 Mask Builder — Incomplete Chip Warnings ✅
**File:** `modules/mask_builder.py`

Chips that require user input (empty literals, custom charsets with no definition) now display a visual `!` warning badge and are excluded from output.

- [x] Added `INCOMPLETE_BORDER = "#f38ba8"` constant (Catppuccin red)
- [x] `MaskChip._warn_label` — QLabel showing `!` in red, 12px wide when active, 0px when complete
- [x] `MaskChip.is_complete(charsets)` — returns `False` for empty literals or undefined custom charsets
- [x] `MaskChip.set_charsets(charsets)` — refreshes warning badge when charset definitions change
- [x] `MaskChip._update_warn(charsets)` — toggles `!` visibility based on completeness
- [x] `_apply_style()` uses red border (`INCOMPLETE_BORDER`) for incomplete chips, 2px width
- [x] `_get_mask_string()` skips incomplete chips via `c.is_complete(cs)` filter
- [x] `_get_keyspace()` skips incomplete chips
- [x] `_update_mask_display()` skips incomplete chips in description loop
- [x] `_generate_preview()` skips incomplete chips in candidate generation
- [x] `_on_charset_text_changed()` propagates charset changes to all custom chips via `set_charsets()`
- [x] `_add_chip()` calls `chip.set_charsets(self._charsets)` so new chips get immediate warning state

### 31.2 Rule Builder — Incomplete Chip Warnings ✅
**File:** `modules/rule_builder.py`

Same pattern applied to `RuleChip`: chips with required parameters that are still empty show a `!` badge.

- [x] Added `INCOMPLETE_BORDER = "#f38ba8"` constant
- [x] `RuleChip._warn_label` — same QLabel pattern as MaskChip
- [x] `RuleChip.is_complete()` — returns `False` when `param_count > 0` and any param is empty
- [x] `RuleChip._update_warn()` — toggles badge visibility
- [x] `_apply_style()` uses red border for incomplete chips
- [x] `set_param()` calls `_update_warn()` + `_apply_style()` on every change
- [x] Constructor calls `_update_warn()` so newly added parameterized chips start with the warning
- [x] `_get_rule_string()` skips incomplete chips
- [x] `_update_preview()` skips incomplete chips in description list
- [x] `_apply_rules_locally()` skips incomplete chips during preview
- [x] `_add_to_list()` skips incomplete chips in description

---

## Phase 32: UI Cleanup — Remove Unused Controls (✅ Complete)

### 32.1 Remove Send To Menu from Mask Builder & Rule Builder ✅
**Files:** `modules/mask_builder.py`, `modules/rule_builder.py`

- [x] Removed `send_to_menu()` call and associated `send_row` QHBoxLayout from both `build_output_section()` methods
- [x] These modules produce .hcmask / .rule files directly; "Send To" was unnecessary

### 32.2 Remove Reset to Defaults from Mask Builder & Rule Builder ✅
**Files:** `modules/mask_builder.py`, `modules/rule_builder.py`

- [x] Added `self._reset_btn.setVisible(False)` in both `__init__()` methods
- [x] These chip-based builders don't benefit from a generic field reset; "Clear All/Chain" serves the same purpose

### 32.3 Remove Batch Preview from Rule Builder ✅
**File:** `modules/rule_builder.py`

- [x] Removed the "Batch Preview — Apply Rules to Wordlist" QGroupBox from `build_output_section()`
- [x] Removed `_browse_batch_file()` and `_run_batch_preview()` methods
- [x] The real-time single-word preview + net effect display are sufficient for rule validation

---

## Phase 33: Complete Hashcat Rule Coverage (✅ Complete)

### 33.1 Missing Standard Rules Added ✅
**File:** `modules/rule_builder.py`

Compared `RULE_FUNCTIONS` against the full hashcat wiki (`rule_based_attack`) and added 11 missing standard rules:

| Rule | Name | Category | Params |
|------|------|----------|--------|
| `[` | Truncate left | Positional | 0 |
| `]` | Truncate right | Positional | 0 |
| `ONM` | Omit range | Positional | 2 |
| `q` | Duplicate chars | Rotation | 0 |
| `zN` | Dup first N | Rotation | 1 |
| `ZN` | Dup last N | Rotation | 1 |
| `yN` | Dup block front | Rotation | 1 |
| `YN` | Dup block back | Rotation | 1 |
| `k` | Swap front | Swap (new) | 0 |
| `K` | Swap back | Swap (new) | 0 |
| `*NM` | Swap @ N,M | Swap (new) | 2 |

Total standard rules: **40** (was 29).

### 33.2 Advanced Rules Behind Toggle ✅
**File:** `modules/rule_builder.py`

Added `ADVANCED_RULE_FUNCTIONS` list (15 niche rules) shown only when "Show Advanced Rules" checkbox is checked:

| Rule | Name | Category | Params |
|------|------|----------|--------|
| `E` | Title case | Title Case | 0 |
| `eX` | Title w/separator | Title Case | 1 |
| `+N` | ASCII increment | Bitwise/ASCII | 1 |
| `-N` | ASCII decrement | Bitwise/ASCII | 1 |
| `.N` | Replace N+1 | Bitwise/ASCII | 1 |
| `,N` | Replace N−1 | Bitwise/ASCII | 1 |
| `LN` | Bitwise shift left | Bitwise/ASCII | 1 |
| `RN` | Bitwise shift right | Bitwise/ASCII | 1 |
| `_N` | Reject ≠ len N | Adv. Rejection | 1 |
| `(X` | Reject ≠ first X | Adv. Rejection | 1 |
| `)X` | Reject ≠ last X | Adv. Rejection | 1 |
| `=NX` | Reject ≠ at N | Adv. Rejection | 2 |
| `%NX` | Reject < N of X | Adv. Rejection | 2 |
| `Q` | Reject mem match | Adv. Rejection | 0 |
| `:` | Nothing (passthrough) | Utility | 0 |

### 33.3 Implementation Details ✅

- [x] New `ADVANCED_RULE_FUNCTIONS` list alongside `RULE_FUNCTIONS`
- [x] New category colours: `Swap`, `Title Case`, `Bitwise/ASCII`, `Adv. Rejection`, `Utility`
- [x] `build_input_section()` builds palette from both lists; advanced rows wrapped in `QWidget` and hidden by default
- [x] `QCheckBox("Show Advanced Rules")` at bottom of palette toggles visibility via `_toggle_advanced_rules()`
- [x] All 26 new rules have full preview support in both `_apply_rules_locally()` and `_apply_single_rule_locally()`
- [x] `_match_rule_func()` searches both lists so imported .rule files with advanced functions parse correctly
- [x] Added `QCheckBox` to PyQt6 imports

---

## Phase 34: Hex Charset Support in Mask Builder (✅ Complete)

*Completed in earlier session, documented here for completeness.*

- [x] Added `?h` (hex lowercase 0-9a-f) and `?H` (hex uppercase 0-9A-F) to `PLACEHOLDERS` and `CHIP_COLORS`
- [x] Expanded custom charsets from `?1`–`?4` to `?1`–`?8`
- [x] Single "Custom Charset" button auto-assigns next available number (`_add_next_custom_chip()`)
- [x] Inline charset definition in detail panel (replaces separate QGroupBox)

**File:** `modules/mask_builder.py`
