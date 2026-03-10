# Cracker's Toolkit GUI — Implementation Plan V5 (Final Spec Compliance)

**Reference:** `SPECIFICATION.md` (v3.0), `IMPLEMENTATION_PLAN_V4.md` (✅ closed)
**Status:** ✅ Near-complete — 40 of 43 sections implemented (remaining: StatsGen charts, Linux testing, theme polish)

---

## Priority Levels

- **P1 (High):** Missing spec features that affect correctness, core UX, or data flow
- **P2 (Medium):** Missing spec features that improve completeness
- **P3 (Low):** Polish, edge cases, nice-to-haves, carried-forward V4 items

---

## Phase 19: Data Bus & Cross-Module Flow Fixes (P1)

### 19.1 Data Bus — Auto-Navigate on "Send to…" (P1)
**Files:** `app/data_bus.py`, `app/main_window.py`, `modules/base_module.py`
**Spec:** §4.1 — "Send to..." should switch UI to the target module

- [x] After `data_bus.send()`, emit a signal that navigates the main window to the target tool
- [x] Show a brief toast/status bar message confirming the transfer

### 19.2 Data Bus — Handle Unloaded Modules (P1)
**Files:** `app/data_bus.py`, `app/main_window.py`
**Spec:** §4.1 — transfer should work even if target hasn't been opened

- [x] If target module is not yet loaded, lazy-load it before calling `receive_from()`
- [x] Alternatively, queue the data until the module is first opened

### 19.3 Data Bus — Pipe Command Support (P1)
**Files:** `app/data_bus.py`, `modules/prince_processor.py`, `modules/pcfg_guesser.py`, `modules/hashcat_launcher.py`
**Spec:** §4.1 — pipe scenarios should populate Attack Launcher's pipe command

- [x] Verify `get_pipe_command()` on PRINCE Processor and PCFG Guesser returns correct command strings
- [x] Verify Hashcat Launcher's `receive_from()` detects "pipe:" prefix and enables pipe mode
- [x] Test full pipeline: PRINCE → Send to Hashcat → pipe command auto-filled

### 19.4 "Send to…" Menu — Dynamic Population (P2)
**File:** `modules/base_module.py`
**Spec:** §4.1 — menu should show compatible destination modules

- [x] Make `send_to_menu()` dynamically query compatible targets from the registry (like `receive_from_menu()` already does)
- [x] Remove hardcoded target lists from individual modules

### 19.5 Post-Completion "What Next?" Suggestions (P2)
**File:** `modules/base_module.py`
**Spec:** §2.3.5 — "No dead ends — always a what next? suggestion"

- [x] After process finishes successfully, show suggested next actions based on module type
- [x] E.g., after PRINCE: "Send to demeuk for cleaning" or "Send to Hashcat for cracking"
- [x] Implement as clickable links/buttons in the output status area

---

## Phase 20: Module-Specific Spec Gaps — Wordlist Generation (P1–P2)

### 20.1 PRINCE Processor — Send-to Destinations (P1)
**File:** `modules/prince_processor.py`
**Spec:** §3.1 — Send to: demeuk, combinator, hashcat (pipe mode)

- [x] Add demeuk and Combinator as "Send to…" destinations
- [x] (Pipe to Hashcat already done in V4 15.5 — verify working)

### 20.2 PRINCE Processor — Output File Size Display (P3)
**File:** `modules/prince_processor.py`
**Spec:** §3.1 — output shows "line count, file size"

- [x] Display output file size alongside line count in the output section

### 20.3 PCFG Guesser — Send-to Destinations (P1)
**File:** `modules/pcfg_guesser.py`
**Spec:** §3.2 — Send to: demeuk, hashcat (pipe mode)

- [x] Replace or add demeuk as "Send to…" destination (spec says demeuk, not PRINCE)

### 20.4 PCFG Guesser — Output File Size Display (P3)
**File:** `modules/pcfg_guesser.py`
**Spec:** §3.2 — output shows "count, size"

- [x] Display output file size alongside line count

### 20.5 Combinator — Missing Thematic Wordlists (P2)
**File:** `modules/combinator.py`
**Spec:** §3.3 — built-in thematic wordlists: names, dates, seasons, colors, sports teams, pet names, keyboard patterns, leet-speak

- [x] Add missing thematic lists: names, seasons, colors, sports teams, pet names, leet-speak
- [x] (Digits, Common PINs, Special chars, Years, Days & Months, Keyboard walks already present)

### 20.6 Combinator — validate() Bug Fix (P1)
**File:** `modules/combinator.py`
**Bug:** `validate()` calls `s.get_lines()` but `WordlistSlot` only defines `get_words()` → AttributeError

- [x] Fix: change `s.get_lines()` to `s.get_words()` (or add `get_lines` alias)

### 20.7 Element Extractor — Keyboard Patterns Extraction (P2)
**File:** `modules/element_extractor.py`
**Spec:** §3.5 — extraction options include "Keyboard patterns"

- [x] Add keyboard pattern detection (identify sequences like "qwerty", "asdf", etc.)

### 20.8 Element Extractor — Capitalization Patterns (P2)
**File:** `modules/element_extractor.py`
**Spec:** §3.5 — extraction options include "Capitalization patterns"

- [x] Add capitalization pattern extraction (first-upper, all-caps, camelCase, etc.)

### 20.9 Element Extractor — Per-Row Extract Buttons (P3)
**File:** `modules/element_extractor.py`
**Spec:** §3.5 — "each element row should be individually extractable"

- [x] Add per-row extract/export button in the results table

### 20.10 Keyboard Walk Generator — Multi-Layout Checkboxes (P2)
**File:** `modules/keyboard_walk_generator.py`
**Spec:** §3.6 — layout selection as checkboxes allowing simultaneous multi-layout generation

- [x] Change layout selection from single dropdown to checkboxes (QWERTY, AZERTY, QWERTZ, Numpad)
- [x] Generate walks for all selected layouts in a single run

### 20.11 Keyboard Walk Generator — Allow Repeats Option (P2)
**File:** `modules/keyboard_walk_generator.py`
**Spec:** §3.6 — "allow repeats" parameter

- [x] Add "Allow repeats" checkbox that permits revisiting keys during walk generation

### 20.12 Date & Number Patterns — Phone Patterns (P2)
**File:** `modules/date_number_generator.py`
**Spec:** §3.7 — phone patterns with area codes and format options

- [x] Add phone number pattern generation section with configurable area codes and formats

### 20.13 Date & Number Patterns — Custom Templates (P2)
**File:** `modules/date_number_generator.py`
**Spec:** §3.7 — "Custom templates text field"

- [x] Add free-text field for user-defined custom templates (e.g., `{YYYY}{DD}`, `{PIN4}@{YEAR}`)

### 20.14 Date & Number Patterns — PIN Length Selection (P2)
**File:** `modules/date_number_generator.py`
**Spec:** §3.7 — PIN patterns with selectable 4/6/8 digit lengths

- [x] Add PIN length selection (4/6/8 digit) for systematic PIN generation
- [x] (Current "common PINs" list exists but doesn't allow user-selected lengths)

### 20.15 Date & Number Patterns — MM-DD-YY Format (P3)
**File:** `modules/date_number_generator.py`
**Spec:** §3.7 — date format "MM-DD-YY" with dashes

- [x] Add `MM-DD-YY` format option (currently has `MMDDYY` without separators)

---

## Phase 21: Module-Specific Spec Gaps — Analysis & Mask & Rule Tools (P2–P3)

### 21.1 PCFG Trainer — Ruleset Browser Metadata (P2)
**File:** `modules/pcfg_trainer.py`
**Spec:** §3.9.1.4 — "metadata: training source, date, structure count, disk size"

- [x] Display metadata alongside each ruleset in the browser (creation date, file count, disk size)

### 21.2 PCFG Trainer — Copy & Edit Buttons (P2)
**File:** `modules/pcfg_trainer.py`
**Spec:** §3.9.1.4 — Copy and Edit buttons alongside Delete

- [x] Add "Copy" button to duplicate a ruleset
- [x] Add "Edit" button that navigates to PCFG Rule Editor with the selected ruleset

### 21.3 Password Scorer — Color-Coded Score Ranges (P3)
**File:** `modules/password_scorer.py`
**Spec:** §3.10 — "Color-coded score ranges (red/yellow/green)"

- [x] Add background color coding to score cells (red = weak, yellow = medium, green = strong)

### 21.4 MaskGen — Per-Mask Estimated Time Column (P2)
**File:** `modules/maskgen.py`
**Spec:** §3.13.1.3 — table includes "estimated time" per mask

- [x] Add "Est. Time" column to the results table (keyspace / PPS)

### 21.5 MaskGen — Cumulative Coverage Graph (P3)
**File:** `modules/maskgen.py`
**Spec:** §3.13.1.3 — "Cumulative coverage graph"

- [x] Replace or supplement the single progress bar with a line chart showing coverage % vs mask count

### 21.6 PolicyGen — Mask Table Display (P2)
**File:** `modules/policygen.py`
**Spec:** §3.14.1.2 — "Table of masks (if 'show masks' enabled)"

- [x] Add a QTableWidget that displays individual masks when `_showmasks` checkbox is on
- [x] Parse masks from stdout and populate the table

### 21.7 Rule Builder — Rule List Reorder Buttons (P2)
**File:** `modules/rule_builder.py`
**Spec:** §3.15.1.5 — "Reorder, edit, delete entries" in rule list accumulator

- [x] Add ▲/▼ reorder buttons to each row in the rule list accumulator table

### 21.8 Rule Builder — Memory Rule `X` Function (P3)
**File:** `modules/rule_builder.py`
**Spec:** §3.15.1.1 — Memory rules include `X` (extract from memory)

- [x] Add `X` (extract from memory) to the RULE_FUNCTIONS list under the Memory category

### 21.9 RuleGen — Dictionary Provider & Language Dropdowns (P2)
**File:** `modules/rulegen.py`
**Spec:** §3.16.1.2 — Dictionary provider dropdown (aspell) + Language dropdown (en)

- [x] Add "Dictionary provider" dropdown (aspell, hunspell, etc.)
- [x] Add "Language" dropdown (en, de, fr, es, etc.)
- [x] Wire to `--provider` and `--language` CLI flags

### 21.10 RuleGen — Output Table for Words & Rules (P2)
**File:** `modules/rulegen.py`
**Spec:** §3.16.1.3 — table of discovered source words and rules with frequency

- [x] Parse output files and display discovered words and rules in a QTableWidget
- [x] Include frequency counts, sortable columns

### 21.11 RuleGen — "Add Words to Wordlist" Export (P3)
**File:** `modules/rulegen.py`
**Spec:** §3.16.1.3 — "Add words to wordlist" export button

- [x] Add button to export discovered words as a wordlist file

### 21.12 Hashcat Launcher — `-j`/`-k` as Global Advanced Options (P3)
**File:** `modules/hashcat_launcher.py`
**Spec:** §3.18.2.4 — `-j`/`-k` inline rules listed as advanced options

- [x] Move `-j`/`-k` text fields from Mode 1 panel to the global Advanced Options section
- [x] Make visible regardless of selected attack mode

---

## Phase 22: demeuk Tooltips & Enhancements (P3)

### 22.1 demeuk — Spec-Matching Tooltips (P3)
**File:** `modules/demeuk_cleaner.py`
**Spec:** §3.8 — detailed tooltip text for every checkbox

- [x] Replace generic tooltips with spec-matching detailed descriptions for all check/modify/add options
- [x] Check modules: replace `f"Drop lines matching: {label}"` with specific descriptions
- [x] Modify modules: replace `label` tooltip with detailed descriptions
- [x] Add modules: replace `label` tooltip with detailed descriptions

### 22.2 demeuk — Dry Run Per-Reason Breakdown (P3)
**File:** `modules/demeuk_cleaner.py`
**Spec:** §3.8 — dry run summary includes "lines kept, lines dropped (with reasons), lines modified"

- [x] Parse dry run output for per-reason drop counts and modification counts
- [x] Display breakdown in the results summary

---

## Phase 23: Carried Forward from V4 (P3)

### 23.1 Combinator — Per-Slot Preview Button (P3)
**File:** `modules/combinator.py`
**Spec:** §3.3.1.1 — "preview button (shows first 20 lines)"

- [x] Verify each WordlistSlot preview button shows first 20 lines of the selected file/thematic list

### 23.2 PCFG Guesser — Session List Metadata (P3)
**File:** `modules/pcfg_guesser.py`
**Spec:** §3.2.1.4 — "metadata: guess count at pause, ruleset used"

- [x] Enhance session list to show metadata from session files
- [x] Add "Delete Session" button

### 23.3 PCFG Trainer — Ruleset Browser Enhancement (P3)
**File:** `modules/pcfg_trainer.py`
**Spec:** §3.9.1.4 — metadata, copy, edit

- [x] (Covered by 21.1 and 21.2 — this item is a duplicate reference)

### 23.4 MaskGen — Coverage Graph (P3)
**File:** `modules/maskgen.py`
**Spec:** §3.13.1.3 — "Cumulative coverage graph"

- [x] (Covered by 21.5 — this item is a duplicate reference)

### 23.5 StatsGen — Bar Charts (P3)
**File:** `modules/statsgen.py`
**Spec:** §3.11.1.3 — "Bar charts or tables for each"

- [ ] Current text progress bars are acceptable per spec ("or tables" — ✅ spec-compliant)
- [ ] Optionally upgrade to QChart bar charts for visual polish

### 23.6 Linux Testing (P3)
- [ ] Test all modules on Ubuntu/Debian
- [ ] Verify terminal spawning with gnome-terminal, xfce4-terminal, konsole, xterm
- [ ] Verify file path handling (no Windows-only paths)
- [ ] Test PCFG/demeuk subprocess execution on Linux

### 23.7 Theme Polish (P3)
- [ ] Verify dark theme on all widget types (QTabWidget, QTableWidget, QSplitter, progress bars, QSlider)
- [ ] Test light theme rendering
- [ ] Ensure QSlider tick marks visible in dark theme

### 23.8 Windows Batch Script in Scraper Generator (P3)
**File:** `modules/scraper_generator.py`
**Spec:** §3.19.1.4

- [x] Add Windows .bat / PowerShell script generation option alongside Bash and Python

### 23.9 File Size Warning for Large Wordlists (P3)
**Files:** All modules accepting wordlist input

- [x] When a selected file is > 1 GB, show a warning/confirmation before processing

---

## Summary

| Phase | Items | Priority | Focus |
|-------|-------|----------|-------|
| 19 — Data Bus & Cross-Module Flow | 5 | P1–P2 | Send-to navigation, unloaded modules, pipes, what-next |
| 20 — Wordlist Generation Gaps | 15 | P1–P3 | PRINCE, PCFG, Combinator, Element Extractor, Kbd Walk, Date/Number |
| 21 — Analysis, Mask & Rule Tool Gaps | 12 | P2–P3 | Trainer, Scorer, MaskGen, PolicyGen, Rule Builder, RuleGen, Hashcat |
| 22 — demeuk Enhancements | 2 | P3 | Tooltips, dry run breakdown |
| 23 — Carried Forward (V4 remainder) | 9 | P3 | Preview, metadata, charts, testing, polish, scraper, file warnings |
| **Total** | **43** | | |

> **Note:** Items 23.3, 23.4, 23.5 overlap with Phase 21 items. Effective unique items: **~40**.

---

## Recommended Build Order

1. **Phase 19.1–19.3** (P1 data bus fixes — navigation, unloaded modules, pipe verification)
2. **Phase 20.6** (P1 combinator bug fix)
3. **Phase 20.1, 20.3** (P1 send-to destinations)
4. **Phase 19.4–19.5** (P2 dynamic menus, what-next suggestions)
5. **Phase 20.5, 20.7–20.8, 20.10–20.14** (P2 module spec gaps)
6. **Phase 21.1–21.2, 21.4, 21.6–21.7, 21.9–21.10** (P2 analysis/mask/rule gaps)
7. **Phase 20.2, 20.4, 20.9, 20.15** (P3 minor wordlist gaps)
8. **Phase 21.3, 21.5, 21.8, 21.11–21.12** (P3 minor tool gaps)
9. **Phase 22** (P3 demeuk tooltips)
10. **Phase 23** (P3 carried forward items)

---

## Overall Project Status

| Plan | Scope | Status |
|------|-------|--------|
| V1 (IMPLEMENTATION_PLAN.md) | 19 modules, full skeleton, Phases 1–6 | ✅ Complete |
| V2 (IMPLEMENTATION_PLAN_V2.md) | 29 spec-gap items, Phases 7–10 | ✅ Complete |
| V3 (IMPLEMENTATION_PLAN_V3.md) | 18 polish items, Phases 11–14 | ✅ Complete |
| V4 (IMPLEMENTATION_PLAN_V4.md) | 19 hardening items, Phases 15–18 | ✅ Closed (10 done, 9 → V5) |
| V5 (this plan) | ~40 final compliance items, Phases 19–23 | 🔄 Active |

Estimated overall spec compliance: **~90%** → target **~99%** after V5.

**Note:** Module 20 (Markov Chain / .hcstat2 GUI) remains deferred per spec §3.20. PRINCE-LING (Module 4) has significant architectural divergence from spec — it uses PCFG rulesets instead of source wordlists + language packs. This is acknowledged but not addressed in V5 as the current approach is the practical implementation matching the underlying tool.
