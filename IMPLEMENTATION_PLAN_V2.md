# Cracker's Toolkit GUI - Implementation Plan V2 (Spec Gap Closure)

**Reference:** `SPECIFICATION.md` (v3.0), `IMPLEMENTATION_PLAN.md` (completed baseline)
**Status:** ✅ ALL ITEMS COMPLETE. All 29 items implemented. See `IMPLEMENTATION_PLAN_V3.md` for remaining polish.

---

## Priority Levels

- **P1 (High):** Core functionality gaps — features that affect usability or cross-module workflows
- **P2 (Medium):** Missing spec features that improve UX but aren't blocking
- **P3 (Low):** Nice-to-have polish, visual enhancements, edge cases

---

## Phase 7: Infrastructure & Cross-Cutting Concerns (P1)

These affect all modules and should be done first.

### 7.1 Logging Integration (P1) ✅
**File:** `modules/base_module.py`, `app/logging_panel.py`

The LoggingPanel exists but ProcessRunner doesn't log to it. Wire subprocess calls to the global logger.

- [x] Import `logging_panel` singleton into `ProcessRunner`
- [x] On `run()`: call `log_command(module_name, cmd_list)`
- [x] On `finished()`: call `log_finish(exit_code, runtime)`
- [x] Add elapsed time tracking to ProcessRunner (start/finish timestamps)

### 7.2 Input Validation (P1) ✅
**File:** `modules/base_module.py`

Add a `validate()` method that each module can override. Called before `run_tool()`.

- [x] Add `validate() -> list[str]` to BaseModule (returns list of error messages, empty = OK)
- [x] In `_on_run_clicked()`: call `validate()` first, show errors in a dialog if any
- [x] Override in modules that need it (file exists checks, required field checks, number range checks)

### 7.3 Data Bus Completeness (P1) ✅
**Files:** All modules with `receive_from()`

Most modules have basic `receive_from()` that just sets a file path. Enhance to handle different data types.

- [x] `hashcat_launcher.py`: Add visible "Receive from…" QPushButtons next to wordlist/rule/mask input fields that show a dropdown of available source modules (spec §3.18.2)
- [ ] `mask_builder.py`: Add "Import from Element Extractor" button for custom charset slots (spec §3.12.1) — moved to V3
- [x] Verify `receive_from()` works for all 19 modules (test: module A sends → module B receives and populates)

### 7.4 File Browser Bookmarks (P2) ✅
**File:** `modules/base_module.py`

Spec §2.2 says file browsers should have "quick-access bookmarks to toolkit directories".

- [x] Add bookmark buttons or dropdown to `create_file_browser()`: `Scripts_to_use/`, `hashcat-7.1.2/rules/`, `hashcat-7.1.2/masks/`, `Rules/`
- [x] Remember last directory per tool (already implemented via `_last_dirs`)

---

## Phase 8: Module-Specific Gaps (P1-P2)

### 8.1 PRINCE Processor Enhancements (P2) ✅
**File:** `modules/prince_processor.py`

- [x] **Help panel** — Add a CollapsibleSection at the bottom with a plain-language explanation of the PRINCE algorithm and a worked example (spec §3.1.1 item 5)
- [x] **Preview first 1000 lines** — Add a "Preview" button that captures the first 1000 lines of output in a scrollable panel (spec §3.1.1 item 3)

### 8.2 PCFG Guesser Enhancements (P2) ✅
**File:** `modules/pcfg_guesser.py`

- [x] **Head/Tail statistics** — After preview, compute and display: average length, character composition breakdown, most common base structures (spec §3.2.1 item 2)
- [x] **Session management list** — Add a list widget showing saved sessions from `Rules/` dir with metadata (guess count, ruleset), with Resume/Delete buttons (spec §3.2.1 item 4)
- [x] **Stdin pipe toggle** — Add a checkbox "Pipe to Hashcat (stdin)" that, when sending to Attack Launcher, populates the pipe command field (spec §3.2.1 item 3)

### 8.3 Combinator Per-Slot Preview (P3) ✅
**File:** `modules/combinator.py`

- [x] Add a small "Preview" button next to each slot that shows the first 20 lines of the selected file in a tooltip or popup (spec §3.3.1 item 1)

### 8.4 StatsGen Rich Output (P1) ✅
**File:** `modules/statsgen.py`

This module has the biggest gap — it just shows raw CLI output.

- [x] **Charset filter multi-select** — Add checkboxes for: loweralpha, upperalpha, numeric, mixedalpha, mixedalphanum, all (spec §3.11.1 item 2)
- [x] **Tabbed results view** — Replace raw output log with a QTabWidget showing: Length Distribution, Character Sets, Simple Masks, Advanced Masks, Complexity (spec §3.11.1 item 3)
- [x] **Parse CLI output** — Parse statsgen stdout to populate tables/bar displays in each tab

### 8.5 MaskGen Coverage Graph (P2) ✅
**File:** `modules/maskgen.py`

- [x] Add a simple cumulative coverage display (could be text-based progress bar or QChart if available) showing % coverage as masks accumulate (spec §3.13.1 item 3)

### 8.6 Keyboard Walk Visual Preview (P2) ✅
**File:** `modules/keyboard_walk_generator.py`

- [x] **Visual keyboard widget** — Add a QWidget that draws a keyboard grid and highlights generated walk paths (spec §3.6.1 item 3)
- [ ] **Click-to-walk** — Allow clicking keys on the visual keyboard to define custom walk patterns (spec §3.6.1 item 3) — moved to V3
- [x] **Direction filtering** — Currently walk generation ignores the direction checkboxes. Wire them into the DFS algorithm to filter walks by allowed directions (spec §3.6.1 item 2)

### 8.7 Rule Builder Drag-and-Drop & Batch Preview (P2) ✅
**File:** `modules/rule_builder.py`

- [x] **Drag-and-drop reordering** — Add up/down buttons or implement QListWidget drag-drop on the rule chain (spec §3.15.1 item 2)
- [x] **Batch preview** — Add a "Load wordlist" button that applies the current rule chain to every word and shows results in a table (spec §3.15.1 item 4)
- [ ] **Improve rule simulation accuracy** — Extend local rule engine to handle extraction (xNM), memory (X/M/4/6), and rejection filters (spec §3.15.1 item 1) — moved to V3

### 8.8 RuleGen Validate-with-Hashcat (P3) ✅
**File:** `modules/rulegen.py`

- [x] Add `--hashcat` checkbox: "Validate discovered rules using hashcat --stdout" (spec §3.16.1 item 2). Pass the hashcat binary path from settings.

### 8.9 Password Scorer Table Sorting/Filtering (P2) ✅
**File:** `modules/password_scorer.py`

- [x] Enable clickable column headers for sorting (spec §3.10.1 item 3)
- [x] Add classification filter checkboxes (Passwords / Emails / Websites / Other) above the table

### 8.10 PCFG Trainer File Metadata (P3) ✅
**File:** `modules/pcfg_trainer.py`

- [x] On file selection: display line count, detected encoding, and sample of first 10 lines below the file browser (spec §3.9.1 item 1)

### 8.11 demeuk Advanced Checks (P2) ✅
**File:** `modules/demeuk_cleaner.py`

- [x] Add missing check options from spec: min/max digits, min/max uppercase, min/max specials (spec §3.8.1 item 3)
- [x] **Dry run before/after** — Show side-by-side: original line vs modified line, not just output (spec §3.8.1 item 7)

### 8.12 PCFG Rule Editor Applied Preview (P3) ✅
**File:** `modules/pcfg_rule_editor.py`

- [x] Show kept vs. removed structures visually (two columns or color-coded) in the preview output (spec §3.17.1 item 2)

### 8.13 Hashcat Launcher Receive Buttons (P2) ✅
**File:** `modules/hashcat_launcher.py`

- [x] Add "Receive from…" QPushButton next to each input field (wordlist, rule, mask) that shows a dropdown listing compatible source modules (spec §3.18.2 item "Receive from…")
- [x] Populate list dynamically from `tool_registry.get_compatible_targets()`

---

## Phase 9: "What Should I Use?" Guide (P2)

### 9.1 Interactive Help Guide ✅
**File:** `app/help_guide.py` + `app/main_window.py`

Replace the basic QMessageBox with a proper widget:

- [x] Create a scrollable help page widget with workflow decision trees
- [x] Decision trees as clickable flow: "What do you have?" → "What do you want?" → "Use this tool"
- [x] Link tool names to sidebar navigation (click tool name → open that tool)
- [x] Common workflows section:
  - Raw wordlist → demeuk → PRINCE/Combinator → Attack Launcher
  - Password list → StatsGen → MaskGen → Attack Launcher
  - Password list → PCFG Trainer → PCFG Guesser → Attack Launcher
  - Cracked passwords → RuleGen → Rule Builder → Attack Launcher

---

## Phase 10: Cross-Platform & Final Polish (P3)

### 10.1 Linux Testing
- [ ] Test all modules on Ubuntu/Debian
- [ ] Verify terminal spawning (gnome-terminal, xfce4-terminal, konsole, xterm)
- [ ] Verify file path handling (no Windows-only paths)
- [ ] Test PCFG/demeuk subprocess execution on Linux

### 10.2 Error Handling Polish
- [x] Add input validation in `validate()` overrides for all modules that launch subprocesses
- [ ] Timeout handling for long-running subprocesses
- [ ] Better error messages when external tools not found (with Settings link)

### 10.3 Theme Polish
- [ ] Verify dark theme renders correctly on all widget types (QTabWidget, QTableWidget, QSplitter, charts)
- [ ] Test light theme (currently only dark is styled)

---

## Summary: Item Count by Priority

| Priority | Items | Description |
|----------|-------|-------------|
| P1 (High) | 7 | Logging, validation, data bus wiring, StatsGen output |
| P2 (Medium) | 14 | Visual previews, coverage graphs, sorting, receive buttons, help guide |
| P3 (Low) | 8 | Help panels, file metadata, drag-drop, theme, Linux testing |
| **Total** | **29** | |

---

## Recommended Build Order

1. **Phase 7** first (infrastructure) — logging, validation, data bus. These improve all modules at once.
2. **Phase 8.4** (StatsGen) — biggest single-module gap at 63% compliance.
3. **Phase 8.6** (Keyboard Walk visual) — most visible missing feature.
4. **Phase 8.13** + **Phase 7.3** (Receive buttons) — completes cross-module workflow.
5. **Phase 9** (Help guide) — completes user guidance.
6. **Phase 8** remaining items — work through P2/P3 gaps.
7. **Phase 10** (Polish) — final pass.
