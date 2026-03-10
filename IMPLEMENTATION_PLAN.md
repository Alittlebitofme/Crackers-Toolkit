# Cracker's Toolkit GUI - Implementation Plan (COMPLETED)

**Reference:** `SPECIFICATION.md` (v3.0) in this same directory.
**Existing tools:** `Scripts_to_use/` folder contains all scripts to wrap.
**Target:** Python 3.10+ with PyQt6. Cross-platform (Windows + Linux).
**Status:** All 6 phases completed. See `IMPLEMENTATION_PLAN_V2.md` for remaining spec gaps.

---

## Phase 1: Application Skeleton ✅ COMPLETE

1. ✅ **Project structure** — Full package layout created:
   - `crackers_toolkit/main.py` — Entry point
   - `crackers_toolkit/app/main_window.py` — Main window with sidebar + stacked content
   - `crackers_toolkit/app/sidebar.py` — Category tree with tool cards and search
   - `crackers_toolkit/app/tool_registry.py` — 20 ToolInfo entries, 7 categories
   - `crackers_toolkit/app/data_bus.py` — Singleton DataBus with register/send/transfer
   - `crackers_toolkit/app/settings.py` — Settings persistence + dialog + terminal commands
   - `crackers_toolkit/app/logging_panel.py` — Log viewer with timestamps
   - `crackers_toolkit/modules/base_module.py` — ProcessRunner + CollapsibleSection + BaseModule ABC
   - `crackers_toolkit/resources/` — hashcat_modes.json, hashcat_rules_ref.json, emoji_map.json, thematic_lists/, keyboard_layouts/

2. ✅ **Base module class** — Input/Params/Advanced/Output layout, ProcessRunner with threaded subprocess, helpers: create_file_browser, create_spinbox, create_checkbox, create_combo, create_line_edit, send_to_menu

3. ✅ **Sidebar + tool selection** — 7-category tree with ToolCards, click-to-load

4. ✅ **Global search** — Keyword filter across names, descriptions, keywords

5. ✅ **Settings panel** — Hashcat/PRINCE/Python paths, output dir, hash rate, terminal pref, theme

---

## Phase 2: Pure-Python Modules ✅ COMPLETE

6. ✅ **Module 7: Date & Number Pattern Generator** — All 16 date formats, 6 languages, digit sequences, PINs (100% spec compliant)
7. ✅ **Module 5: Element Extractor** — 9 decomposition rules, output table, preview, leet-decode
8. ✅ **Module 6: Keyboard Walk Generator** — 4 layouts, walk params, direction controls, common walks
9. ✅ **Module 12: Mask Builder** — Position builder, 4 custom charsets, keyspace calc, time estimate, .hcmask import/export
10. ✅ **Module 15: Rule Builder** — 26 rule functions searchable library, chain builder, real-time description + preview, .rule import/export
11. ✅ **Module 3: Combinator** — 2-8 slots, thematic lists, separators, permutation mode with itertools
12. ✅ **Module 19: Scraper Generator** — Bash/Python script gen, crawl depth, URL filter, stop words

---

## Phase 3: External Tool Wrappers ✅ COMPLETE

13. ✅ **Module 1: PRINCE Processor** — All params, file metadata, session save/restore, keyspace mode
14. ✅ **Module 3: Combinator (standard mode)** — Combined with permutation in single module
15. ✅ **Module 8: demeuk Cleaner** — 14 checks, 18 modifiers, 8 add modules, 3 presets, dry run
16. ✅ **Module 9: PCFG Trainer** — Coverage slider, n-gram, alphabet, ruleset browser
17. ✅ **Module 2: PCFG Guesser** — 3 modes, head/tail preview side-by-side, session name
18. ✅ **Module 4: PRINCE-LING** — Ruleset dropdown, max words, all-lowercase (100% spec compliant)
19. ✅ **Module 10: Password Scorer** — File + paste input, ruleset, probability cutoff, table output
20. ✅ **Module 17: PCFG Rule Editor** — Terminal type checkboxes, regex filter, preview mode

---

## Phase 4: PACK Python 3 Port + Wrappers ✅ COMPLETE

21. ✅ **Ported `statsgen.py`** → `crackers_toolkit/pack_ports/statsgen.py`
22. ✅ **Module 11: StatsGen GUI** — Min/max length, hide rare, CSV output, send-to MaskGen
23. ✅ **Ported `maskgen.py`** → `crackers_toolkit/pack_ports/maskgen.py`
24. ✅ **Module 13: MaskGen GUI** — Target time, PPS, sort-by, showmasks, .hcmask export
25. ✅ **Ported `policygen.py`** → `crackers_toolkit/pack_ports/policygen.py`
26. ✅ **Module 14: PolicyGen GUI** — Policy params, non-compliant mode, .hcmask export
27. ✅ **Ported `rulegen.py`** → `crackers_toolkit/pack_ports/rulegen.py` (with PyEnchant fallback)
28. ✅ **Module 16: RuleGen GUI** — File/single-password input, all checkboxes, threads

---

## Phase 5: Attack Launcher + Integration ✅ COMPLETE

29. ✅ **Module 18: Hashcat Command Builder** — 6 attack modes, searchable hash-mode dropdown, per-mode stacked panels, stdin pipe, advanced options, live command preview, native terminal spawn
30. ✅ **"Send to..." / "Receive from..." wiring** — DataBus singleton, auto-registration on module load, send_to_menu on all modules
31. ✅ **"What should I use?" guide** — Basic workflow guide in Help menu

---

## Phase 6: Polish ✅ COMPLETE (baseline)

32. ✅ **Thematic wordlists** — 9 files bundled in resources/thematic_lists/
33. ✅ **Hashcat hash mode reference** — 300+ modes in resources/hashcat_modes.json
34. ✅ **Logging** — LoggingPanel with timestamps and log_command/log_finish methods
35. ✅ **Error handling** — ProcessRunner catches FileNotFoundError, non-zero exit codes displayed
36. ⬜ **Cross-platform testing** — Not yet verified on Linux
37. ✅ **Module 20: Markov GUI** — Left as placeholder (deferred per spec)

---

## File Inventory (35 files)

```
crackers_toolkit/
  __init__.py, main.py
  app/  __init__.py, main_window.py, sidebar.py, tool_registry.py,
        data_bus.py, settings.py, logging_panel.py
  modules/  __init__.py, base_module.py,
    prince_processor.py, pcfg_guesser.py, combinator.py, prince_ling.py,
    element_extractor.py, keyboard_walk_generator.py, date_number_generator.py,
    demeuk_cleaner.py, pcfg_trainer.py, password_scorer.py, statsgen.py,
    mask_builder.py, maskgen.py, policygen.py,
    rule_builder.py, rulegen.py, pcfg_rule_editor.py,
    hashcat_launcher.py, scraper_generator.py
  pack_ports/  __init__.py, statsgen.py, maskgen.py, policygen.py, rulegen.py
  resources/  __init__.py, hashcat_modes.json, hashcat_rules_ref.json, emoji_map.json,
    thematic_lists/ (9 files), keyboard_layouts/ (5 files)
```

---

## Spec Compliance Audit (~85% average)

A full audit identified gaps between the built modules and the SPECIFICATION.md.
These are tracked in **`IMPLEMENTATION_PLAN_V2.md`** as the next round of work.
