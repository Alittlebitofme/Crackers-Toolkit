# Cracker's Toolkit GUI — Implementation Plan V4 (Hardening & Remaining Gaps)

**Reference:** `SPECIFICATION.md` (v3.0), `IMPLEMENTATION_PLAN_V3.md` (✅ complete)
**Status:** ✅ Complete — 10 of 19 items implemented. Remaining 9 items carried forward to V5.

---

## Priority Levels

- **P1 (High):** Missing spec features that affect correctness or core UX
- **P2 (Medium):** Missing spec features that improve completeness
- **P3 (Low):** Polish, edge cases, nice-to-haves

---

## Phase 15: Missing Spec Features (P1–P2)

### 15.1 Mask Builder — Edit & Reorder Entries (P2) ✅
**File:** `modules/mask_builder.py`

- [x] Edit button per row → loads mask back into position builder via `_load_mask_to_builder()`
- [x] ▲/▼ reorder buttons per row in the action column (▲ ▼ ✏ ×)

### 15.2 Mask Builder — Import from Element Extractor (P2) ✅
**File:** `modules/mask_builder.py`

- [x] "Import…" button on each custom charset slot (1–4)
- [x] Reads Element Extractor output, extracts unique printable characters, populates charset field

### 15.3 Rule Builder — Per-Entry Delete & Net Effect (P2) ✅
**File:** `modules/rule_builder.py`

- [x] 3rd column with ✏ edit + × delete buttons per row
- [x] "Net effect" label below table showing what each rule does to sample word
- [x] `_apply_single_rule_locally()` for per-rule preview

### 15.4 Rule Builder — Per-Entry Edit (P3) ✅
**File:** `modules/rule_builder.py`

- [x] Edit button per row → `_load_rule_to_chain()` parses rule string, matches RULE_FUNCTIONS, reconstructs chain items with parameters

### 15.5 Hashcat Launcher — Auto-fill Pipe from PRINCE/PCFG (P2) ✅
**Files:** `modules/hashcat_launcher.py`, `modules/prince_processor.py`, `modules/pcfg_guesser.py`

- [x] `get_pipe_command()` on PRINCE Processor and PCFG Guesser
- [x] Overridden `_send_to()` sends "pipe:" prefix to Hashcat when target is "Hashcat Command Builder"
- [x] Hashcat `receive_from()` detects "pipe:" prefix, enables pipe checkbox and populates command field

### 15.6 Combinator — Per-Slot Preview Button (P3)
**File:** `modules/combinator.py`
**Spec:** §3.3.1 item 1 — "preview button (shows first 20 lines)"

- [ ] Verify each WordlistSlot preview button shows first 20 lines of the selected file/thematic list
- [ ] Ensure preview works for both file paths and thematic list selections

### 15.7 PCFG Guesser — Session List Metadata (P3)
**File:** `modules/pcfg_guesser.py`
**Spec:** §3.2.1 item 4 — "List saved sessions with metadata (guess count at pause, ruleset used)"

- [ ] Enhance session list to show metadata (guess count at pause, ruleset name) if available from session files
- [ ] Add "Delete Session" button for cleaning up old sessions

### 15.8 PCFG Trainer — Ruleset Browser Enhancement (P3)
**File:** `modules/pcfg_trainer.py`
**Spec:** §3.9.1 item 4 — "List all rulesets with metadata (training source, date, structure count, disk size)"

- [ ] Show metadata alongside each ruleset: creation date, training file count, disk size
- [ ] Add "Copy", "Edit" (→ opens PCFG Rule Editor) buttons alongside existing "Delete"

### 15.9 MaskGen — Coverage Graph (P3)
**File:** `modules/maskgen.py`
**Spec:** §3.13.1 item 3 — "Cumulative coverage graph"

Currently has a coverage progress bar. Spec calls for a graph:
- [ ] Add a simple cumulative coverage line chart (QChart or matplotlib) showing coverage % vs mask count

### 15.10 StatsGen — Bar Charts (P3)
**File:** `modules/statsgen.py`
**Spec:** §3.11.1 item 3 — "Bar charts or tables for each"

Currently has tables with text progress-bar columns. Spec allows either bar charts or tables:
- [ ] Optionally add bar chart visualization (QChart or just keep the text progress bars — current solution is acceptable per spec "or tables")

---

## Phase 16: Input Validation & Error Handling (P2)

### 16.1 Add validate() to All Modules (P2) ✅
**File:** All `modules/*.py`

Added `validate()` overrides to all 13 applicable modules with Path.is_file() checks, required-field checks, and range validation.

### 16.2 Subprocess Timeout Handling (P2) ✅
**File:** `modules/base_module.py`

- [x] Added optional `timeout` parameter to `ProcessRunner.run()` (default: 0 = no timeout)
- [x] Uses `threading.Timer` to terminate process and emit error on timeout

### 16.3 Tool Not Found Error Messages (P2) ✅
**Files:** All modules wrapping external tools

- [x] All 11 modules updated with actionable error messages including expected path and Settings guidance

---

## Phase 17: Cross-Platform Testing & Polish (P3)

### 17.1 Linux Testing
- [ ] Test all modules on Ubuntu/Debian
- [ ] Verify terminal spawning works with gnome-terminal, xfce4-terminal, konsole, xterm
- [ ] Verify file path handling (no Windows-only paths)
- [ ] Test PCFG/demeuk subprocess execution on Linux

### 17.2 Theme Polish
- [ ] Verify dark theme on all widget types (QTabWidget, QTableWidget, QSplitter, progress bars, QSlider)
- [ ] Test light theme rendering (currently only dark Catppuccin is styled)
- [ ] Ensure QSlider tick marks visible in dark theme

### 17.3 Windows Batch Script in Scraper Generator (P3)
**File:** `modules/scraper_generator.py`
**Spec:** §3.19.1 item 4

Currently generates Bash and Python scripts. Windows users may benefit from:
- [ ] Add a Windows .bat / PowerShell script generation option alongside Bash and Python

---

## Phase 18: Deferred V3 Items & Minor Gaps (P3)

### 18.1 ProcessRunner Cleanup (P3) ✅
**File:** `modules/pcfg_guesser.py`

- [x] Cancel and deleteLater() previous runner before creating new one
- [x] Initialize head/tail runners as None in __init__

### 18.2 File Size Warning for Large Wordlists (P3)
**Files:** All modules accepting wordlist input
**Best practice**

- [ ] When a selected file is > 1 GB, show a warning/confirmation before processing
- [ ] Display an estimated processing time for very large files

### 18.3 Regex Input Validation (P3) ✅
**Files:** `modules/demeuk_cleaner.py`, `modules/pcfg_rule_editor.py`

- [x] Added `re.compile()` validation in `validate()` — invalid regex patterns reported before execution
- [x] PCFG Rule Editor validates comma-separated regex patterns individually

---

## Summary

| Phase | Items | Priority | Focus |
|-------|-------|----------|-------|
| 15 — Missing Spec Features | 10 | P2–P3 | Remaining spec feature gaps |
| 16 — Validation & Errors | 3 | P2 | Input validation, timeouts, error messages |
| 17 — Cross-Platform | 3 | P3 | Linux testing, theme, scraper |
| 18 — Deferred & Minor | 3 | P3 | ProcessRunner cleanup, file warnings, regex |
| **Total** | **19** | | |

---

## Recommended Build Order

1. **Phase 16.1** (validate() overrides) — touches many files, high-impact/low-effort
2. **Phase 15.1–15.3** (Mask Builder edit/reorder, Rule Builder delete/net-effect) — P2 spec gaps
3. **Phase 15.5** (Hashcat auto-fill pipe) — P2 data flow gap
4. **Phase 16.2–16.3** (timeout, tool-not-found) — error handling
5. **Phase 15.4, 15.6–15.10** (remaining P3 spec features)
6. **Phase 17** (cross-platform testing)
7. **Phase 18** (cleanup and minor items)

---

## Overall Project Status

| Plan | Scope | Status |
|------|-------|--------|
| V1 (IMPLEMENTATION_PLAN.md) | 19 modules, full skeleton, Phases 1–6 | ✅ Complete |
| V2 (IMPLEMENTATION_PLAN_V2.md) | 29 spec-gap items, Phases 7–10 | ✅ Complete |
| V3 (IMPLEMENTATION_PLAN_V3.md) | 18 polish items, Phases 11–14 | ✅ Complete |
| V4 (this plan) | 19 hardening items, Phases 15–18 | ✅ Closed (10 done, 9 → V5) |

Estimated overall spec compliance: **~96%** → target **~99%** after V5.

**Note:** Module 20 (Markov Chain / .hcstat2 GUI) is marked as "Future" in the specification and is not planned. It will be specified separately once the .hcstat2 format is researched. Remaining 9 items (15.6–15.10, 17.1–17.3, 18.2) are carried forward to IMPLEMENTATION_PLAN_V5.md along with newly identified spec gaps.
