"""Central registry of all tools, their categories, and descriptions.

Used by the sidebar, global search, and Send-to/Receive-from menus.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolInfo:
    module_id: int
    name: str
    description: str
    category: str
    module_class: str  # dotted import path
    keywords: list[str] = field(default_factory=list)
    accepts_input_types: list[str] = field(default_factory=list)  # wordlist, rule, mask, …
    produces_output_types: list[str] = field(default_factory=list)


CATEGORIES = [
    {
        "name": "Wordlist Generation",
        "icon": "📝",
        "description": "Create new wordlists and password candidates from existing data.",
    },
    {
        "name": "Wordlist Cleaning",
        "icon": "🧹",
        "description": "Clean, filter, deduplicate, fix encoding, and transform raw wordlists.",
    },
    {
        "name": "Wordlist Analysis",
        "icon": "📊",
        "description": "Analyze password lists to understand patterns, train models, or score strength.",
    },
    {
        "name": "Mask Tools",
        "icon": "🎭",
        "description": "Build, generate, and manage hashcat mask files (.hcmask).",
    },
    {
        "name": "Rule Tools",
        "icon": "⚙️",
        "description": "Build, generate, reverse-engineer, and manage hashcat rule files (.rule).",
    },
    {
        "name": "Attack Launcher",
        "icon": "🚀",
        "description": "Construct and launch hashcat attacks in an external terminal.",
    },
    {
        "name": "Utilities",
        "icon": "🔧",
        "description": "Supporting tools: scrape websites for wordlists, etc.",
    },
    {
        "name": "Hash Extraction",
        "icon": "🔓",
        "description": "Extract password hashes from encrypted files, containers, wallets, and archives.",
    },
]

TOOLS: list[ToolInfo] = [
    # ── Wordlist Generation ──────────────────────────────────────
    ToolInfo(
        module_id=1,
        name="PRINCE Processor",
        description=(
            "Generate password candidates by chaining words from a wordlist "
            "in probability order. Combines 1-8 words per candidate, "
            "prioritizing the most likely combinations first."
        ),
        category="Wordlist Generation",
        module_class="crackers_toolkit.modules.prince_processor.PrinceProcessorModule",
        keywords=["prince", "chain", "wordlist", "candidate", "probability"],
        accepts_input_types=["wordlist"],
        produces_output_types=["wordlist"],
    ),
    ToolInfo(
        module_id=2,
        name="PCFG Guesser",
        description=(
            "Generate password guesses in probability order using a "
            "previously trained PCFG grammar model. The most likely "
            "passwords come first. Supports session save/restore for long runs."
        ),
        category="Wordlist Generation",
        module_class="crackers_toolkit.modules.pcfg_guesser.PCFGGuesserModule",
        keywords=["pcfg", "guesser", "grammar", "probability", "guess"],
        accepts_input_types=["ruleset"],
        produces_output_types=["wordlist"],
    ),
    ToolInfo(
        module_id=3,
        name="Combinator",
        description=(
            "Combine 2 to 8 wordlists together, concatenating one word from "
            "each list per candidate. Supports custom separators between words. "
            "Useful for building passphrase-style candidates."
        ),
        category="Wordlist Generation",
        module_class="crackers_toolkit.modules.combinator.CombinatorModule",
        keywords=["combine", "combinator", "passphrase", "separator", "permutation"],
        accepts_input_types=["wordlist"],
        produces_output_types=["wordlist"],
    ),
    ToolInfo(
        module_id=4,
        name="PRINCE-LING",
        description=(
            "Generate wordlists optimized for PRINCE attacks using a "
            "trained PCFG model. Outputs individual words (not full "
            "passwords) in probability order — the best input for PRINCE processor."
        ),
        category="Wordlist Generation",
        module_class="crackers_toolkit.modules.prince_ling.PrinceLingModule",
        keywords=["prince", "ling", "pcfg", "words", "optimized"],
        accepts_input_types=["ruleset"],
        produces_output_types=["wordlist"],
    ),
    ToolInfo(
        module_id=5,
        name="Element Extractor",
        description=(
            "Decompose passwords from a wordlist into their structural "
            "building blocks: words, digit runs, special character "
            "sequences, years, etc. The extracted elements make excellent "
            "input for PRINCE or combinator attacks."
        ),
        category="Wordlist Generation",
        module_class="crackers_toolkit.modules.element_extractor.ElementExtractorModule",
        keywords=["element", "extract", "decompose", "tokenize", "building blocks"],
        accepts_input_types=["wordlist"],
        produces_output_types=["wordlist"],
    ),
    ToolInfo(
        module_id=6,
        name="Keyboard Walk Generator",
        description=(
            "Generate password candidates based on keyboard walking "
            "patterns — fingers moving across the keyboard in lines, "
            "diagonals, or patterns. Supports multiple keyboard layouts "
            "(QWERTY, AZERTY, QWERTZ, Dvorak)."
        ),
        category="Wordlist Generation",
        module_class="crackers_toolkit.modules.keyboard_walk_generator.KeyboardWalkModule",
        keywords=["keyboard", "walk", "pattern", "qwerty", "layout"],
        accepts_input_types=[],
        produces_output_types=["wordlist"],
    ),
    ToolInfo(
        module_id=7,
        name="Date & Number Patterns",
        description=(
            "Generate systematic date-formatted strings and number "
            "patterns that people commonly use in passwords: birthdays, "
            "anniversaries, years, PINs. Covers multiple date formats "
            "and configurable year ranges."
        ),
        category="Wordlist Generation",
        module_class="crackers_toolkit.modules.date_number_generator.DateNumberModule",
        keywords=["date", "number", "pin", "birthday", "year", "pattern"],
        accepts_input_types=[],
        produces_output_types=["wordlist"],
    ),
    # ── Wordlist Cleaning ────────────────────────────────────────
    ToolInfo(
        module_id=8,
        name="demeuk — Wordlist Cleaner",
        description=(
            "Clean, filter, fix encoding, deduplicate, and transform "
            "raw wordlists. Handles common issues like mojibake, HTML "
            "artifacts, control characters, hash lines, and email "
            "addresses. Essential for preparing raw data before cracking."
        ),
        category="Wordlist Cleaning",
        module_class="crackers_toolkit.modules.demeuk_cleaner.DemeukModule",
        keywords=["clean", "filter", "demeuk", "encoding", "deduplicate", "mojibake"],
        accepts_input_types=["wordlist"],
        produces_output_types=["wordlist"],
    ),
    ToolInfo(
        module_id=21,
        name="Simple Cleaner",
        description=(
            "Quick wordlist cleanup: deduplicate, sort, and filter "
            "passwords by length. Shows a frequency report ranking "
            "passwords by how often they appeared — the most common "
            "are likely the best candidates."
        ),
        category="Wordlist Cleaning",
        module_class="crackers_toolkit.modules.simple_cleaner.SimpleCleanerModule",
        keywords=["simple", "clean", "sort", "unique", "deduplicate", "frequency", "length"],
        accepts_input_types=["wordlist"],
        produces_output_types=["wordlist"],
    ),
    # ── Wordlist Analysis ────────────────────────────────────────
    ToolInfo(
        module_id=9,
        name="PCFG Trainer",
        description=(
            "Train a probabilistic grammar model from a plaintext "
            "password list. The model learns password structures and "
            "their probabilities. Used by the PCFG Guesser and "
            "PRINCE-LING to generate candidates."
        ),
        category="Wordlist Analysis",
        module_class="crackers_toolkit.modules.pcfg_trainer.PCFGTrainerModule",
        keywords=["pcfg", "train", "grammar", "model", "structure"],
        accepts_input_types=["wordlist"],
        produces_output_types=["ruleset"],
    ),
    ToolInfo(
        module_id=10,
        name="Password Scorer",
        description=(
            "Score passwords against a trained PCFG model to see how "
            "probable each one is. Classifies entries as passwords, "
            "emails, websites, or other."
        ),
        category="Wordlist Analysis",
        module_class="crackers_toolkit.modules.password_scorer.PasswordScorerModule",
        keywords=["score", "strength", "probability", "classify"],
        accepts_input_types=["wordlist", "ruleset"],
        produces_output_types=[],
    ),
    ToolInfo(
        module_id=11,
        name="StatsGen (PACK)",
        description=(
            "Analyze a password list to discover statistical patterns: "
            "length distributions, character set usage, mask frequency, "
            "and complexity ranges. Essential input for the Mask Generator."
        ),
        category="Wordlist Analysis",
        module_class="crackers_toolkit.modules.statsgen.StatsGenModule",
        keywords=["statistics", "stats", "length", "charset", "mask", "frequency"],
        accepts_input_types=["wordlist"],
        produces_output_types=["csv"],
    ),
    # ── Mask Tools ───────────────────────────────────────────────
    ToolInfo(
        module_id=12,
        name="Mask Builder",
        description=(
            "Visually build hashcat masks position by position. See in "
            "real-time what each mask matches, the total keyspace, and "
            "estimated crack time. Build and export .hcmask files."
        ),
        category="Mask Tools",
        module_class="crackers_toolkit.modules.mask_builder.MaskBuilderModule",
        keywords=["mask", "build", "keyspace", "position", "charset"],
        accepts_input_types=["charset"],
        produces_output_types=["mask"],
    ),
    ToolInfo(
        module_id=13,
        name="MaskGen (PACK)",
        description=(
            "Generate an optimized set of hashcat masks from password "
            "statistics. Ranks masks by efficiency (most passwords "
            "cracked per keyspace unit) and builds time-budgeted mask files."
        ),
        category="Mask Tools",
        module_class="crackers_toolkit.modules.maskgen.MaskGenModule",
        keywords=["mask", "generate", "optimize", "efficiency", "pack"],
        accepts_input_types=["csv"],
        produces_output_types=["mask"],
    ),
    ToolInfo(
        module_id=14,
        name="PolicyGen (PACK)",
        description=(
            "Generate hashcat masks that comply with (or violate) a "
            "specific password policy. Useful for targeted attacks "
            "against known policies."
        ),
        category="Mask Tools",
        module_class="crackers_toolkit.modules.policygen.PolicyGenModule",
        keywords=["policy", "generate", "comply", "violate", "mask"],
        accepts_input_types=[],
        produces_output_types=["mask"],
    ),
    # ── Rule Tools ───────────────────────────────────────────────
    ToolInfo(
        module_id=15,
        name="Rule Builder",
        description=(
            "Visually construct hashcat mangling rules. See a plain-language "
            "description of what each rule does, preview the transformation "
            "on sample words in real-time, and build .rule files."
        ),
        category="Rule Tools",
        module_class="crackers_toolkit.modules.rule_builder.RuleBuilderModule",
        keywords=["rule", "build", "mangle", "transform", "hashcat"],
        accepts_input_types=["rule"],
        produces_output_types=["rule"],
    ),
    ToolInfo(
        module_id=16,
        name="RuleGen (PACK)",
        description=(
            "Reverse-engineer hashcat rules from cracked passwords. "
            "Figures out what base words and transformations would "
            "produce them. Great for discovering real-world mangling patterns."
        ),
        category="Rule Tools",
        module_class="crackers_toolkit.modules.rulegen.RuleGenModule",
        keywords=["rule", "generate", "reverse", "engineer", "pack"],
        accepts_input_types=["wordlist"],
        produces_output_types=["rule", "wordlist"],
    ),
    ToolInfo(
        module_id=17,
        name="PCFG Rule Editor",
        description=(
            "Edit a trained PCFG ruleset to match a specific password policy. "
            "Filter base structures by length, character types, and regex."
        ),
        category="Rule Tools",
        module_class="crackers_toolkit.modules.pcfg_rule_editor.PCFGRuleEditorModule",
        keywords=["pcfg", "edit", "rule", "policy", "filter"],
        accepts_input_types=["ruleset"],
        produces_output_types=["ruleset"],
    ),
    # ── Attack Launcher ──────────────────────────────────────────
    ToolInfo(
        module_id=18,
        name="Hashcat Command Builder",
        description=(
            "Visually construct a hashcat attack command, then launch it "
            "in a native terminal window. Supports all attack modes: "
            "dictionary, mask, combinator, hybrid."
        ),
        category="Attack Launcher",
        module_class="crackers_toolkit.modules.hashcat_launcher.HashcatLauncherModule",
        keywords=["hashcat", "attack", "launch", "crack", "terminal", "command"],
        accepts_input_types=["wordlist", "rule", "mask"],
        produces_output_types=[],
    ),
    # ── Utilities ────────────────────────────────────────────────
    ToolInfo(
        module_id=19,
        name="Web Scraper Generator",
        description=(
            "Generate a ready-to-run script that scrapes text from a "
            "website, extracts individual words, deduplicates them, and "
            "optionally removes filler/stop words."
        ),
        category="Utilities",
        module_class="crackers_toolkit.modules.scraper_generator.ScraperGeneratorModule",
        keywords=["scrape", "web", "website", "script", "words"],
        accepts_input_types=[],
        produces_output_types=["wordlist"],
    ),
    ToolInfo(
        module_id=20,
        name="Markov Chain GUI",
        description=(
            "Load, visualize, and train hashcat Markov chain statistics "
            "(.hcstat2 files) for smarter brute-force ordering. "
            "Configure --markov-hcstat2 and --markov-threshold for the "
            "Hashcat Command Builder."
        ),
        category="Utilities",
        module_class="crackers_toolkit.modules.markov_gui.MarkovChainModule",
        keywords=["markov", "hcstat2", "brute-force", "statistics", "chain"],
        accepts_input_types=[],
        produces_output_types=[],
    ),
    # ── Hash Extraction ──────────────────────────────────────────
    ToolInfo(
        module_id=22,
        name="Hash Extractor",
        description=(
            "Extract password hashes from encrypted files, containers, "
            "wallets, databases, and archives using hashcat and John the "
            "Ripper extraction tools. Supports 24 hashcat extractors and "
            "100+ JtR extractors with automatic format cleanup and "
            "one-click send to Hashcat Command Builder."
        ),
        category="Hash Extraction",
        module_class="crackers_toolkit.modules.hash_extractor.HashExtractorModule",
        keywords=[
            "hash", "extract", "2hashcat", "2john", "veracrypt", "truecrypt",
            "bitlocker", "metamask", "wallet", "archive", "zip", "rar",
            "office", "pdf", "ssh", "keepass", "bitcoin", "ethereum",
        ],
        accepts_input_types=[],
        produces_output_types=["hash"],
    ),
]


def get_tools_by_category(category: str) -> list[ToolInfo]:
    return [t for t in TOOLS if t.category == category]


def get_tool_by_id(module_id: int) -> ToolInfo | None:
    for t in TOOLS:
        if t.module_id == module_id:
            return t
    return None


def get_tool_by_name(name: str) -> ToolInfo | None:
    for t in TOOLS:
        if t.name == name:
            return t
    return None


def search_tools(query: str) -> list[ToolInfo]:
    """Search tools by keyword across names, descriptions, keywords, and option names."""
    q = query.lower()
    results = []
    for t in TOOLS:
        searchable = (
            f"{t.name} {t.description} {' '.join(t.keywords)} "
            f"{' '.join(t.accepts_input_types)} {' '.join(t.produces_output_types)}"
        ).lower()
        if q in searchable:
            results.append(t)
    return results


def get_compatible_targets(output_type: str) -> list[str]:
    """Return tool names that accept the given output type as input."""
    return [t.name for t in TOOLS if output_type in t.accepts_input_types]
