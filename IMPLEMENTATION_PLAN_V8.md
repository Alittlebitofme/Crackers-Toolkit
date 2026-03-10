# Implementation Plan V8 — Hash Extractor Module

**Scope:** New Hash Extractor module (Module 22) integrating 24 hashcat `*2hashcat` tools + auto-discovered JtR `*2john` tools with categorized tree selection, drag-and-drop input, special options for VeraCrypt/BitLocker/MetaMask, JtR prefix cleanup, and "Send to Hashcat Command Builder" integration via DataBus.

**Phases:** 40–44

**Previous:** V7 covered Phases 35–39 (Hashcat launcher overhaul, terminal launch fixes, spinbox arrow fix, save dialog defaults)

---

## Phase 40: Core Module & Extractor Registry (✅ Complete)

### 40.1 Register Module in tool_registry.py ✅
**File:** `crackers_toolkit/app/tool_registry.py`

- [x] Added `"Hash Extraction"` category with icon `"🔓"` to `CATEGORIES` list
- [x] Added `ToolInfo(module_id=22, name="Hash Extractor", ...)` to `TOOLS` list
  - `category="Hash Extraction"`
  - `module_class="crackers_toolkit.modules.hash_extractor.HashExtractorModule"`
  - `keywords=["hash", "extract", "2hashcat", "2john", "veracrypt", "truecrypt", "bitlocker", "metamask", "wallet", "archive", "zip", "rar", "office", "pdf", "ssh", "keepass"]`
  - `produces_output_types=["hash"]`

### 40.2 ExtractorInfo Data Structure ✅
**File:** `crackers_toolkit/modules/hash_extractor.py` (**NEW**)

Defined `ExtractorInfo` dataclass with fields: name, script_name, script_path, source, language, category, input_description, file_filter, hashcat_modes, hashcat_compatible, needs_cleanup, notes, has_special_ui, dependencies.

### 40.3 Hashcat Extractor Registry ✅

Defined `_HASHCAT_EXTRACTORS` list with all 24 hashcat `*2hashcat` tools from `hashcat-7.1.2/tools/`:

| Category | Extractors |
|----------|-----------|
| Encryption / Containers | VeraCrypt, TrueCrypt, BitLocker, Cryptoloop, LUKS |
| System / Disk | APFS, CacheData, Keybag |
| Wallet / Crypto | MetaMask, Exodus, Bisq |
| Authentication / Keys | Bitwarden, LastPass, Mozilla, Gitea, Shiro1, Radmin3 |
| Virtual Machines | VirtualBox, VMware |
| Backup | Veeam VBK |
| Database | SQLCipher |
| Other | AES Crypt, Kremlin, Secure Notes |

Each entry has: proper file filters, hashcat mode numbers, dependency lists, special UI flags, and detailed input descriptions.

### 40.4 Curated JtR Overrides ✅

Defined `_CURATED_JTR` dict with ~48 popular JtR `*2john` tools that have known hashcat mode mappings:

- Archive: ZIP, RAR, 7-Zip
- Document: MS Office, PDF, LibreOffice, iWork, StarOffice
- Wallet/Crypto: Bitcoin, Ethereum, Blockchain, Electrum, Monero
- Authentication: SSH, GPG, PuTTY, KeePass, 1Password, Dashlane, PFX, PEM, OpenSSL, Ansible, Enpass, KWallet, GNOME Keyring, Java Keystore
- Encryption: BitLocker, LUKS, TrueCrypt, DiskCryptor, eCryptfs, EncFS, BestCrypt
- System: DMG, macOS Keychain, Android
- Network: WPA, Kerberos, Cisco, PCAP
- Other: Signal, Telegram, Apple Notes

---

## Phase 41: Module UI & Execution Engine (✅ Complete)

### 41.1 JtR Auto-Discovery ✅
**File:** `crackers_toolkit/modules/hash_extractor.py`

- [x] `_find_hashcat_tools_dir()` — resolves `hashcat-7.1.2/tools/` relative to project root
- [x] `_find_jtr_run_dir()` — scans for `john-*/run/` directories dynamically
- [x] `_check_perl()` — probes for `perl` in PATH (cached result)
- [x] `_build_extractor_list()` — assembles all hashcat + JtR extractors:
  - Copies hashcat extractors with resolved script paths
  - Discovers JtR tools by scanning `john-*/run/*2john*` files
  - Matches discovered files against curated overrides for enriched metadata
  - Auto-generates generic ExtractorInfo for uncurated tools

### 41.2 Input UI ✅

- [x] Search filter QLineEdit with real-time filtering by name/category/script_name
- [x] QTreeWidget with tools grouped by category (11 categories in preferred order)
  - Source badges: 🔵 Hashcat / 🟡 JtR
  - Compatibility column: ✅ Hashcat Ready / ⚠️ Hashcat Compatible / ❌ JtR Format Only
  - Perl tools greyed out with tooltip when Perl not available
  - Categories shown bold, non-selectable
- [x] Dynamic description label showing input description, notes, and dependencies
- [x] Yellow dependency banner for tools requiring `pip install` packages
- [x] `_DropZoneFrame` widget — drag-and-drop framed area with hover highlighting
  - Accepts file URLs, emits `file_dropped(str)` signal
  - Connected to input file QLineEdit
- [x] Standard `create_file_browser` for input file

### 41.3 Special Options ✅

- [x] **VeraCrypt/TrueCrypt container** (shown when applicable):
  - QRadioButton group: Standard (0), Bootable (31744), Hidden (65536), Bootable+Hidden (97280)
  - "Extract raw 512 bytes" checkbox for binary hex dump mode
- [x] **BitLocker offset** spinbox (0–2,147,483,647)
- [x] **MetaMask short data** checkbox (mode 26610)
- [x] **JtR prefix cleanup** toggle (default ON, visible only for JtR tools)
- [x] All containers toggle visibility based on selected extractor

### 41.4 Execution Engine ✅

- [x] `_build_command()` — constructs subprocess argument list with interpreter routing:
  - `.py` → `sys.executable`
  - `.pl` → `perl`
  - `.exe` → direct (no interpreter prefix)
  - Special args per tool: `--offset` for VeraCrypt, `-o` for BitLocker, `--vault` + `--shortdata` for MetaMask
- [x] `_run_extraction()` — background thread with `subprocess.Popen`:
  - Captures stdout + stderr with 120s timeout
  - cwd set to script's parent directory
  - Emits `_work_done` signal with results dict
- [x] `_extract_raw_bytes()` — pure Python reader for VeraCrypt raw mode:
  - Seeks to offset, reads 512 bytes
  - Produces formatted hex dump with offset/hex/ASCII columns
- [x] `_on_work_done()` — main thread handler:
  - Applies JtR prefix stripping when enabled
  - Parses ImportError/ModuleNotFoundError for friendly install messages
  - Updates hash output display and log

### 41.5 Output & Integration ✅

- [x] Read-only QTextEdit with monospace font for extracted hash display
- [x] Compatibility/mode label with color coding (green/yellow/red)
- [x] Copy to Clipboard button
- [x] Save to File button (dialog with default output dir)
- [x] "Send to Hashcat Command Builder" button:
  - Saves hash to `output/hash_extractor_output/extracted_hash.txt`
  - Navigates to Hashcat Command Builder via `data_bus.send()`
  - Enabled only when hashcat modes are known

---

## Phase 42: Integration & Build (✅ Complete)

### 42.1 Hashcat Launcher Integration ✅
**File:** `crackers_toolkit/modules/hashcat_launcher.py`

- [x] Added `receive_type="hash"` to hash file browser `create_file_browser()` call
- [x] Hashcat Command Builder now appears as a receive target for hash data

### 42.2 PyInstaller Build Config ✅
**File:** `crackers_toolkit.spec`

- [x] Added `'crackers_toolkit.modules.hash_extractor'` to `hiddenimports` list

### 42.3 Specification Update ✅
**File:** `SPECIFICATION.md`

- [x] Added "Hash Extraction" row to Section 2.1 category breakdown table
- [x] Added Hash Extraction category to Section 6 architecture ASCII diagram
- [x] Added Module 22 row to Section 7 quick reference table
- [x] Inserted full Module 22 specification (Sections 3.22.1–3.22.4) with:
  - Functional requirements (8 items)
  - Full 24-tool hashcat extractor inventory table
  - JtR auto-discovery documentation
  - Data flow documentation

---

## Phase 43: Post-Launch Fixes (✅ Complete)

### 43.1 Fix Unclickable Perl Tools in Tree ✅
**File:** `crackers_toolkit/modules/hash_extractor.py`

SQLCipher, AES Crypt, and Apple Secure Notes (all `.pl` scripts) were not selectable in the exe. Root cause: `subprocess.run(["perl", "--version"])` silently failed inside the PyInstaller-bundled exe because the bundled process environment doesn't reliably inherit the full system PATH.

- [x] Changed `_check_perl()` to first try `shutil.which("perl")` (searches PATH more reliably)
- [x] Added `creationflags=CREATE_NO_WINDOW` fallback for the subprocess probe on Windows
- [x] All four Perl tools now selectable: Radmin3, SQLCipher, AES Crypt, Apple Secure Notes

### 43.2 Remove Hash Mode Truncation ✅
**File:** `crackers_toolkit/modules/hash_extractor.py`

VeraCrypt and other tools with many hashcat modes were displaying "13711, 13712, 13713, 13721, 13722, …" with truncation at 5 modes.

- [x] Removed `[:5]` slice from both hashcat-ready and JtR-compatible branches of `_update_compat_label()`
- [x] Removed `if len > 5: modes += "…"` truncation logic
- [x] All modes now display in full (e.g. VeraCrypt shows all 15 modes)

### 43.3 Remove Tree Max Height Constraint ✅
**File:** `crackers_toolkit/modules/hash_extractor.py`

- [x] Removed `setMaximumHeight(320)` from QTreeWidget to allow full scrolling of all extractor entries

### 43.4 Install Python Dependencies ✅

Installed all pip packages required by hashcat extraction scripts:

| Package | Required By | Status |
|---------|------------|--------|
| `cryptography` | apfs2hashcat.py | Already installed |
| `protobuf` | bisq2hashcat.py | Already installed |
| `pycryptodome` | mozilla2hashcat.py | Already installed |
| `pyasn1` | mozilla2hashcat.py | Already installed |
| `python-snappy` | bitwarden2hashcat.py | Newly installed |
| `plyvel-ci` | bitwarden2hashcat.py (LevelDB) | Newly installed |

---

## Phase 44: Send to Hashcat Integration (✅ Complete)

### 44.1 Hashcat Launcher `receive_from()` — Hash File Routing ✅
**File:** `crackers_toolkit/modules/hashcat_launcher.py`

The `receive_from(path)` method only handled wordlist/rule/mask inputs. Hash files sent from the Hash Extractor were being placed into the wordlist field of the current attack mode instead of the hash file field.

- [x] Added hash-file detection at the top of `receive_from()`: checks for `hash_extractor`, `extracted_hash`, or `.hash` extension in path
- [x] When a hash file is detected, populates `_hash_file` instead of wordlist fields

### 44.2 Auto-Set Hash Mode from Sidecar Metadata ✅
**Files:** `crackers_toolkit/modules/hash_extractor.py`, `crackers_toolkit/modules/hashcat_launcher.py`

When the Hash Extractor sends a hash to the Hashcat Command Builder, the hash mode should be auto-selected.

- [x] Hash Extractor now writes a `.meta` JSON sidecar file alongside the extracted hash containing `{"hashcat_mode": <int>, "source": "<name>"}`
- [x] Hashcat Launcher reads the `.meta` file when receiving a hash, searches the hash mode combo for the matching mode ID, and auto-selects it
- [x] Falls back gracefully if `.meta` file doesn't exist or can't be parsed

---

## Phase 45: JtR Discovery Path Fix (✅ Complete)

### 45.1 Fix Path Resolution in PyInstaller Exe ✅
**File:** `crackers_toolkit/modules/hash_extractor.py`

JtR tools did not appear in the bundled exe because `_find_hashcat_tools_dir()` and `_find_jtr_run_dir()` used `Path(__file__).parent.parent.parent` which resolves to the internal `_internal/` directory inside the PyInstaller bundle instead of the project root.

- [x] Added `_get_base()` method that uses `self._base_dir` (set by `MainWindow`, correctly points to the project root in both source and exe)
- [x] `_find_hashcat_tools_dir()` and `_find_jtr_run_dir()` now call `_get_base()` instead of hardcoded `Path(__file__)` traversal
- [x] Verified all hashcat and JtR tools are discovered in the exe

---

## Phase 46: VeraCrypt / TrueCrypt Mode Expansion & Mode Detail Dialog (✅ Complete)

### 46.1 Expand VeraCrypt Hashcat Modes (15 → 39) ✅
**File:** `crackers_toolkit/modules/hash_extractor.py`

The VeraCrypt `ExtractorInfo.hashcat_modes` list was incomplete — it only contained 15 modes from the 137xx range, missing all boot-mode variants and the entire 294xx series.

Expanded to all 39 supported modes:

| Range | Hash Algorithm | XTS Key Sizes | Boot Variant | Count |
|-------|---------------|---------------|--------------|-------|
| 13711–13713 | RIPEMD-160 | 512/1024/1536 | — | 3 |
| 13721–13723 | SHA-512 | 512/1024/1536 | — | 3 |
| 13731–13733 | Whirlpool | 512/1024/1536 | — | 3 |
| 13741–13743 | RIPEMD-160 | 512/1024/1536 | boot | 3 |
| 13751–13753 | SHA-256 | 512/1024/1536 | — | 3 |
| 13761–13763 | SHA-256 | 512/1024/1536 | boot | 3 |
| 13771–13773 | Streebog-512 | 512/1024/1536 | — | 3 |
| 29411–29413 | RIPEMD-160 | 512/1024/1536 | boot-mode (legacy) | 3 |
| 29421–29423 | SHA-512 | 512/1024/1536 | boot-mode | 3 |
| 29431–29433 | Whirlpool | 512/1024/1536 | boot-mode | 3 |
| 29441–29443 | RIPEMD-160 | 512/1024/1536 | boot-mode | 3 |
| 29451–29453 | SHA-256 | 512/1024/1536 | boot-mode | 3 |
| 29461–29463 | Streebog-512 | 512/1024/1536 | boot-mode | 3 |

### 46.2 Expand TrueCrypt Hashcat Modes (12 → 21) ✅
**File:** `crackers_toolkit/modules/hash_extractor.py`

The TrueCrypt `ExtractorInfo.hashcat_modes` list was also incomplete — it only had the 62xx range (12 modes). The 293xx boot-mode series (9 modes) was entirely missing.

Expanded to all 21 supported modes:

| Range | Hash Algorithm | XTS Key Sizes | Boot Variant | Count |
|-------|---------------|---------------|--------------|-------|
| 6211–6213 | RIPEMD-160 | 512/1024/1536 | — | 3 |
| 6221–6223 | SHA-512 | 512/1024/1536 | — | 3 |
| 6231–6233 | Whirlpool | 512/1024/1536 | — | 3 |
| 6241–6243 | RIPEMD-160 | 512/1024/1536 | boot | 3 |
| 29311–29313 | RIPEMD-160 | 512/1024/1536 | boot-mode | 3 |
| 29321–29323 | SHA-512 | 512/1024/1536 | boot-mode | 3 |
| 29331–29333 | Whirlpool | 512/1024/1536 | boot-mode | 3 |

### 46.3 FDE Mode Detail Dialog ✅
**File:** `crackers_toolkit/modules/hash_extractor.py`

Created `_FDEModeDialog(QDialog)` — a modal table dialog listing all VeraCrypt or TrueCrypt hashcat modes with detailed attributes.

- [x] `_VC_MODES` list — 39 tuples `(mode_id, hash_algo, xts_bits, boot_note)`
- [x] `_TC_MODES` list — 21 tuples with same structure
- [x] `_CIPHER_LABEL` dict — maps XTS key sizes to cipher descriptions:
  - 512 bit → single cipher (AES / Twofish / Serpent / Camellia / Kuznyechik)
  - 1024 bit → cascade (AES-Twofish / Serpent-AES / Twofish-Serpent)
  - 1536 bit → triple cascade (AES-Twofish-Serpent / Serpent-Twofish-AES)
- [x] QTableWidget with 5 columns: **Mode (-m)**, **Hash Algorithm**, **XTS Key Size**, **Cipher(s)**, **Boot**
- [x] Single-row selection mode — click "Use Selected Mode" to set as preferred mode
- [x] Dialog returns `selected_mode: int | None` on accept

### 46.4 "View All Supported Modes" Button ✅
**File:** `crackers_toolkit/modules/hash_extractor.py`

- [x] Added QPushButton "View all supported hashcat modes…" inside the VeraCrypt/TrueCrypt options panel
- [x] `_on_view_fde_modes()` handler: detects VeraCrypt vs TrueCrypt by extractor name, opens `_FDEModeDialog` with the appropriate mode list
- [x] When user selects a mode and clicks "Use Selected Mode", stores it in `_preferred_mode` and shows a label "Preferred mode: -m XXXXX"
- [x] Preferred mode resets when switching extractors (`_update_special_options()`)

### 46.5 Smart Compat Label for Large Mode Lists ✅
**File:** `crackers_toolkit/modules/hash_extractor.py`

- [x] `_update_compat_label()` now checks mode count: if >10, shows "39 supported modes. Use View all supported hashcat modes for details" instead of listing all 39 comma-separated mode numbers
- [x] Tools with ≤10 modes still show the inline list as before

### 46.6 Send to Hashcat Preferred Mode Support ✅
**File:** `crackers_toolkit/modules/hash_extractor.py`

- [x] `_on_send_to_hashcat()` now checks `_preferred_mode` first — if user chose a specific mode from the dialog, that mode is written to the `.meta` sidecar instead of defaulting to the first mode in the list
- [x] Falls back to `ext.hashcat_modes[0]` when no preferred mode is set

---

## Phase 47: Markov Chain / .hcstat2 GUI — Module 20 (✅ Complete)

### 47.1 .hcstat2 Format Research ✅

Reverse-engineered the hashcat `.hcstat2` binary format:
- [x] Raw LZMA2 compression (property byte `0x1c` → 64 MB dictionary, not `.xz` container)
- [x] Decompressed to 134,742,032 bytes
- [x] Layout: `u64 version (BE) + u64 zero (BE) + u64[65536] root_stats (BE) + u64[16777216] markov_stats (BE)`
- [x] `root_stats[pos * 256 + char]` = frequency of `char` at position `pos`
- [x] `markov_stats[pos * 256 * 256 + prev * 256 + char]` = frequency of `char` following `prev` at position `pos`
- [x] Verified decompression and roundtrip compression using Python `lzma` stdlib module with `FORMAT_RAW` + `FILTER_LZMA2`

### 47.2 HcStat2 Parser / Writer / Trainer Class ✅
**File:** `crackers_toolkit/modules/markov_gui.py`

- [x] Constants: `_HCSTAT2_VERSION`, `_CHARSIZ=256`, `_PW_MAX=256`, `_ROOT_CNT=65536`, `_MARKOV_CNT=16777216`, `_RAW_SIZE=134742032`, `_LZMA2_DICT=67108864`
- [x] `HcStat2.load(path)` — LZMA2 decompress → validate header (version + zero) → parse root stats into `array.array('Q')` with byte-swap, keep raw bytes for on-demand markov access
- [x] `HcStat2.get_root_stats(position)` — returns sorted `[(count, char_code), ...]` for root at position
- [x] `HcStat2.get_transition_stats(position, prev_char)` — unpacks 256-entry slice from raw bytes on demand, returns sorted `[(count, char_code), ...]`
- [x] `HcStat2.max_useful_position()` — scans for highest position with non-zero root data
- [x] `HcStat2.train(path, min_len, max_len, progress_cb)` — reads password file, counts root + markov stats using `array.array('Q')`, serializes to big-endian raw bytes
- [x] `HcStat2.save(path)` — LZMA2 compress (preset 6) and write

### 47.3 MarkovChainModule UI ✅
**File:** `crackers_toolkit/modules/markov_gui.py`

- [x] `MarkovChainModule(BaseModule)` registered as Module 20, category "Utilities"
- [x] **Mode selector**: Analyze / Train radio buttons with container visibility toggling
- [x] **Analyze input**: `.hcstat2` file browser, pre-fills `hashcat-7.1.2/hashcat.hcstat2`
- [x] **Train input**: password list browser + output `.hcstat2` save browser + min/max length spinboxes
- [x] **Hashcat settings** (always visible): `--markov-threshold` spinbox (0–65535, "0 (unlimited)"), `--markov-classic` / `--markov-inverse` / `--markov-disable` checkboxes with tooltips
- [x] **4 output tabs**:
  - Tab 1 "Root Frequencies": Rank/Character/Code/Count table, top 100, heat-coloured cells
  - Tab 2 "Transitions": same layout, position + previous char → next char
  - Tab 3 "Position Heatmap": 95 rows × N columns, start/end spinboxes, Refresh button, colour-mapped cells with count tooltips
  - Tab 4 "Summary": monospaced text with per-position stats (distinct chars, total, top 5)
- [x] `_freq_color(val, max_val)` colour helper: blue → cyan → yellow → red gradient
- [x] "Send to Hashcat Command Builder" button via DataBus with `markov_config.json` sidecar
- [x] Training runs in background thread (`threading.Thread`) with `_train_done` signal for progress + completion
- [x] Path helpers: `_get_base()` using `self._base_dir` for PyInstaller compatibility

### 47.4 Registration & Build Config ✅

- [x] `tool_registry.py` Module 20 entry: `module_class` set to `"crackers_toolkit.modules.markov_gui.MarkovChainModule"`, description updated, keywords expanded
- [x] `crackers_toolkit.spec`: added `'crackers_toolkit.modules.markov_gui'` to `hiddenimports`

### 47.5 Testing ✅

- [x] Syntax check: `python -c "import py_compile; py_compile.compile('markov_gui.py')"` — passed
- [x] Import test: `from crackers_toolkit.modules.markov_gui import MarkovChainModule` — passed
- [x] Load test: loaded `hashcat-7.1.2/hashcat.hcstat2` — `max_useful_position=254`, top 5 chars at pos 0 correct (`s`, `m`, `1`, `c`, `b`)
- [x] Training roundtrip: trained from `example.dict` (128,416 passwords) → saved 48,571 bytes → reloaded and verified
- [x] PyInstaller build: `CrackersToolkit.exe` built successfully (2,079,293 bytes)

---

## Phase 48: Web Scraper Anti-Detection Upgrade — Module 19 (✅ Complete)

### 48.1 Anti-Detection GUI Controls ✅
**File:** `crackers_toolkit/modules/scraper_generator.py`

- [x] New "Anti-Detection Options" QGroupBox in `build_params_section` (between Stop Words and Script Type groups)
- [x] `_rotate_ua` checkbox — Rotate User-Agent (default ON), picks from pool of 12 real browser UA strings
- [x] `_real_headers` checkbox — Send realistic browser headers (default ON), adds Accept, Accept-Language, Accept-Encoding, DNT, Sec-Fetch-*, Upgrade-Insecure-Requests
- [x] `_jitter` checkbox — Random delay jitter ±50% (default ON)
- [x] `_retries` QSpinBox — Max retries per request (0–10, default 3) with exponential backoff
- [x] `_proxy` QLineEdit — Proxy URL (http://, https://, socks5://) with placeholder text
- [x] Updated User-Agent field tooltip to explain rotation behavior

### 48.2 Module-Level Constants ✅
**File:** `crackers_toolkit/modules/scraper_generator.py`

- [x] `_UA_POOL` — list of 12 real browser User-Agent strings:
  - Chrome 129/130/131 on Windows, Mac, Linux (6 entries)
  - Firefox 132/133 on Windows, Mac, Linux (4 entries)
  - Edge 131 on Windows (1 entry)
  - Safari 18.2 on Mac (1 entry)
- [x] `DEFAULT_USER_AGENT` updated from Chrome 124 to Chrome 131
- [x] `_params()` expanded with 5 new fields: `rotate_ua`, `real_headers`, `jitter`, `retries`, `proxy`

### 48.3 Script Generator Upgrades ✅
**File:** `crackers_toolkit/modules/scraper_generator.py`

All three generators (`_gen_bash`, `_gen_python`, `_gen_powershell`) upgraded with:

- [x] **UA rotation**: embed `_UA_POOL` as constant array in generated script, pick random UA per request
- [x] **Realistic browser headers**: Accept, Accept-Language, Accept-Encoding, DNT, Connection, Upgrade-Insecure-Requests, Sec-Fetch-* (Python only for Sec-Fetch)
- [x] **Referer header**: automatically set to parent URL when following links
- [x] **Retry with exponential backoff**: `2^(attempt+1) + random(0–3)` seconds between retries; configurable 0–10 retries
- [x] **Random delay jitter**: ±50% variation on delay between requests via `do_sleep`/`wait`/`Do-Sleep` helper
- [x] **Proxy support**: Bash `curl -x`, Python `session.proxies`, PowerShell `Invoke-WebRequest -Proxy`
- [x] **PowerShell script type**: added as third radio option alongside Bash and Python

### 48.4 Testing ✅

- [x] AST parse check — passed
- [x] Import check — `from crackers_toolkit.modules.scraper_generator import ScraperGeneratorModule` — passed
- [x] PyInstaller build — `CrackersToolkit.exe` 2,082,821 bytes

---

## Summary

| Phase | Description | Steps | Status |
|-------|-------------|-------|--------|
| 40 | Core scaffold & extractor registry | 40.1–40.4 | ✅ Complete |
| 41 | Module UI & execution engine | 41.1–41.5 | ✅ Complete |
| 42 | Integration & build | 42.1–42.3 | ✅ Complete |
| 43 | Post-launch fixes | 43.1–43.4 | ✅ Complete |
| 44 | Send to Hashcat integration | 44.1–44.2 | ✅ Complete |
| 45 | JtR discovery path fix | 45.1 | ✅ Complete |
| 46 | VeraCrypt/TrueCrypt mode expansion + mode dialog | 46.1–46.6 | ✅ Complete |
| 47 | Markov Chain / .hcstat2 GUI (Module 20) | 47.1–47.5 | ✅ Complete |
| 48 | Web Scraper anti-detection upgrade (Module 19) | 48.1–48.4 | ✅ Complete |

**Files created:** 2 (`crackers_toolkit/modules/hash_extractor.py`, `crackers_toolkit/modules/markov_gui.py`)
**Files modified:** 4 (`tool_registry.py`, `hashcat_launcher.py`, `crackers_toolkit.spec`, `scraper_generator.py`)
**Docs updated:** 2 (`SPECIFICATION.md`, `IMPLEMENTATION_PLAN_V8.md`)
