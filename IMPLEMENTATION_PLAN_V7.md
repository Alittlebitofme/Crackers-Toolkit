# Implementation Plan V7 — Hashcat Launcher Overhaul & UI Fixes

**Scope:** Hashcat Command Builder refinements, terminal launch fixes, global stylesheet fixes, save dialog defaults.

**Phases:** 35–39

**Previous:** V6 covered Phases 24–34 (PCFG Trainer, Mask/Rule Builder redesign, dark mode polish, chip warnings, UI cleanup, 55 rules, hex charsets)

---

## Phase 35: Hashcat Command Builder — Inline Rules & Increment Toggle (✅ Complete)

### 35.1 Inline Rule Fields Hidden Behind Checkbox ✅
**File:** `modules/hashcat_launcher.py`

Inline rule fields (`-j` / `-k`) are now hidden by default and shown only when a checkbox is enabled. This reduces visual clutter for users who don't use inline rules.

- [x] Added `_m0_inline_check` QCheckBox → toggles `_m0_inline_container` (mode 0 — Straight)
- [x] Added `_m1_inline_check` QCheckBox → toggles `_m1_inline_container` (mode 1 — Combinator)
- [x] Added `_m6_inline_check` QCheckBox → toggles `_m6_inline_container` (mode 6 — Hybrid WL+Mask)
- [x] Added `_m7_inline_check` QCheckBox → toggles `_m7_inline_container` (mode 7 — Hybrid Mask+WL)
- [x] Labels: "Enable inline rules (-j / -k)" for all four modes
- [x] `_toggle_container(container, visible)` helper method for proper geometry recalculation after toggling

### 35.2 Both -j and -k in All Applicable Modes ✅
**File:** `modules/hashcat_launcher.py`

Previously only mode 1 (Combinator) had both `-j` and `-k` fields. Now all four inline-rule modes have both.

| Mode | -j field | -k field |
|------|----------|----------|
| 0 — Straight | `_m0_inline_j` | `_m0_inline_k` |
| 1 — Combinator | `_m1_inline_j` | `_m1_inline_k` |
| 6 — Hybrid WL+Mask | `_m6_inline_j` | `_m6_inline_k` |
| 7 — Hybrid Mask+WL | `_m7_inline_j` | `_m7_inline_k` |

- [x] `_build_command()` reads both `-j` and `-k` values for all four modes
- [x] `_connect_preview_signals()` connects all new `-k` widgets to live command preview

### 35.3 Increment Min/Max Hidden Behind Toggle ✅
**File:** `modules/hashcat_launcher.py`

Increment min/max spinboxes are hidden until the `--increment` checkbox is enabled.

- [x] Mode 3: `_m3_increment` checkbox → toggles `_m3_inc_container` (min/max spinboxes)
- [x] Mode 6: `_m6_increment` checkbox → toggles `_m6_inc_container`
- [x] Mode 7: `_m7_increment` checkbox → toggles `_m7_inc_container`

---

## Phase 36: Hashcat Terminal Launch Fixes (✅ Complete)

### 36.1 OpenCL Device Discovery ✅
**File:** `modules/hashcat_launcher.py`

**Problem:** hashcat failed with "No devices found/left" because OpenCL kernel files are resolved relative to hashcat's own directory.

**Fix:** `_spawn_terminal()` now extracts `hc_dir` from `_hashcat_path()` and passes `cwd=hc_dir` to `subprocess.Popen`.

### 36.2 Command Syntax Fix ✅
**File:** `modules/hashcat_launcher.py`

**Problem:** `cmd /c start cmd /k <command>` mangled compound commands with pipes and redirections.

**Fix:** Changed to `cmd /k <command>` with `cwd=` parameter, which opens a persistent terminal that stays open after hashcat finishes.

### 36.3 Quote Escaping Fix ✅
**File:** `modules/hashcat_launcher.py`

**Problem:** Python's `subprocess.list2cmdline()` escapes inner double quotes with backslashes (`\"`), but `cmd.exe` doesn't understand `\"` — it expects `""` or unescaped quotes.

**Fix:** Changed `Popen` from list form to raw string form: `f'cmd /k {cmd}'`, bypassing `list2cmdline()` entirely.

---

## Phase 37: QStackedWidget Replacement (✅ Complete)

### 37.1 Plain Visibility-Toggled Panels ✅
**File:** `modules/hashcat_launcher.py`

**Problem:** `QStackedWidget` caused geometry/clipping issues — spinbox arrow buttons were unclickable because the stacked widget allocated only the exact height of the current page, clipping child widgets.

**Fix:** Replaced `QStackedWidget` with a plain `_mode_panels: list[QWidget]` where all panels are added to the layout but only the active one is visible. The attack-mode combo's `currentIndexChanged` signal calls `_on_mode_changed()` which hides all panels then shows the selected one.

- [x] Removed `QStackedWidget` and `QSizePolicy` from imports
- [x] `_mode_panels` list holds 6 `QWidget` panels (modes 0, 1, 3, 6, 7, 9)
- [x] `_on_mode_changed()` iterates list, sets visibility accordingly
- [x] All panels except the initial one start hidden

---

## Phase 38: QSpinBox Arrow Button Fix (✅ Complete)

### 38.1 Global Stylesheet Fix ✅
**File:** `main_window.py`

**Problem:** The global Catppuccin stylesheet applied `padding: 4px` to all `QSpinBox` widgets. This compressed the up/down arrow sub-controls, making them nearly unclickable — the effective click target was only ~2px tall.

**Fix:** Added explicit sub-control stylesheet rules:

```css
QSpinBox::up-button, QSpinBox::down-button {
    subcontrol-origin: border;
    width: 18px;
}
QSpinBox::up-button { subcontrol-position: top right; }
QSpinBox::down-button { subcontrol-position: bottom right; }
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: #45475a;
}
QSpinBox { padding-right: 18px; }
```

### 38.2 SVG Arrow Icons ✅
**File:** `main_window.py`

**Problem:** After applying the sub-control styling, the default arrow icons disappeared because Qt's native arrows are suppressed once custom stylesheet rules are applied to `::up-button` / `::down-button`.

**Fix:** Created SVG arrow icons (`ct_spin_up.svg`, `ct_spin_dn.svg`) written to `tempfile.gettempdir()` — same approach used for checkbox and radio button SVGs:

- Up arrow: `<polygon points="4,1 7,7 1,7" fill="#cdd6f4"/>` (8×8 viewBox)
- Down arrow: `<polygon points="1,1 7,1 4,7" fill="#cdd6f4"/>` (8×8 viewBox)

Injected via stylesheet:
```css
QSpinBox::up-arrow   { image: url(<tempdir>/ct_spin_up.svg); width: 8px; height: 8px; }
QSpinBox::down-arrow { image: url(<tempdir>/ct_spin_dn.svg); width: 8px; height: 8px; }
```

---

## Phase 39: Save Dialog Default Paths (✅ Complete)

### 39.1 Export Dialogs Now Open at Module Output Folder ✅

**Problem:** Six export/save dialogs used empty string `""` as the start path for `QFileDialog.getSaveFileName()`, causing the OS dialog to open at the filesystem root or last-used directory — confusing for users.

**Fix:** All six now use `_default_output_dir()` (which returns `<base_dir>/output/<module_slug>_output/`) as the starting directory.

| Module | Method | File |
|--------|--------|------|
| Mask Builder | `_export_hcmask()` | `modules/mask_builder.py` |
| Rule Builder | `_export_rule()` | `modules/rule_builder.py` |
| Password Scorer | `_export_results()` | `modules/password_scorer.py` |
| RuleGen | `_export_words()` | `modules/rulegen.py` |
| Scraper Generator | `_save_script()` | `modules/scraper_generator.py` |
| BaseModule (Run > Save As) | `_on_run_save_as_clicked()` | `base_module.py` |

---

## Files Modified (V7)

| File | Changes |
|------|---------|
| `modules/hashcat_launcher.py` | Inline rules toggle, -j/-k for all modes, increment toggle, terminal launch fixes (cwd, cmd syntax, quote escaping), QStackedWidget → plain panels |
| `main_window.py` | QSpinBox sub-control styling, SVG arrow icons |
| `base_module.py` | `_on_run_save_as_clicked()` default path fallback |
| `modules/mask_builder.py` | `_export_hcmask()` default path |
| `modules/rule_builder.py` | `_export_rule()` default path |
| `modules/password_scorer.py` | `_export_results()` default path |
| `modules/rulegen.py` | `_export_words()` default path |
| `modules/scraper_generator.py` | `_save_script()` default path |

---

## Overall Project Status

| Plan | Scope | Status |
|------|-------|--------|
| V1 | 19 modules, full skeleton, Phases 1–6 | ✅ Complete |
| V2 | 29 spec-gap items, Phases 7–10 | ✅ Complete |
| V3 | 18 polish items, Phases 11–14 | ✅ Complete |
| V4 | 19 hardening items, Phases 15–18 | ✅ Closed |
| V5 | ~40 final compliance items, Phases 19–23 | ✅ Closed (40/43 done) |
| V6 | UI/UX overhaul + bug fixes, Phases 24–34 | ✅ Complete |
| V7 (this plan) | Hashcat launcher overhaul + UI fixes, Phases 35–39 | ✅ Complete |

Estimated overall spec compliance: **~97%** (remaining: Linux testing, optional charts).

---

## Remaining Items (Carried Forward)

| # | Item | Priority | Status |
|---|------|----------|--------|
| 23.5 | StatsGen bar charts (optional — text tables are spec-compliant) | P3 | Deferred |
| 23.6 | Linux testing (all modules, terminal spawning, path handling) | P3 | Not started |
