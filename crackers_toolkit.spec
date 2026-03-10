# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Cracker's Toolkit GUI."""

import os
import sys

block_cipher = None

# Paths
BASE = os.path.abspath('.')
SRC = os.path.join(BASE, 'crackers_toolkit')

# Data files that must be bundled alongside the exe
datas = [
    # Resource JSON / text files (used at runtime)
    (os.path.join(SRC, 'resources', 'hashcat_modes.json'),
     os.path.join('crackers_toolkit', 'resources')),
    (os.path.join(SRC, 'resources', 'hashcat_rules_ref.json'),
     os.path.join('crackers_toolkit', 'resources')),
    (os.path.join(SRC, 'resources', 'emoji_map.json'),
     os.path.join('crackers_toolkit', 'resources')),
    (os.path.join(SRC, 'resources', 'keyboard_layouts'),
     os.path.join('crackers_toolkit', 'resources', 'keyboard_layouts')),
    (os.path.join(SRC, 'resources', 'thematic_lists'),
     os.path.join('crackers_toolkit', 'resources', 'thematic_lists')),
    (os.path.join(SRC, 'resources', 'logo.png'),
     os.path.join('crackers_toolkit', 'resources')),
    (os.path.join(SRC, 'resources', 'icon.ico'),
     os.path.join('crackers_toolkit', 'resources')),

    # pack_ports scripts — launched as subprocesses, must remain as .py files
    (os.path.join(SRC, 'pack_ports', 'statsgen.py'),
     os.path.join('crackers_toolkit', 'pack_ports')),
    (os.path.join(SRC, 'pack_ports', 'maskgen.py'),
     os.path.join('crackers_toolkit', 'pack_ports')),
    (os.path.join(SRC, 'pack_ports', 'policygen.py'),
     os.path.join('crackers_toolkit', 'pack_ports')),
    (os.path.join(SRC, 'pack_ports', 'rulegen.py'),
     os.path.join('crackers_toolkit', 'pack_ports')),
    (os.path.join(SRC, 'pack_ports', '__init__.py'),
     os.path.join('crackers_toolkit', 'pack_ports')),
]

a = Analysis(
    [os.path.join(SRC, 'main.py')],
    pathex=[BASE],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'crackers_toolkit.app',
        'crackers_toolkit.app.tool_registry',
        'crackers_toolkit.app.data_bus',
        'crackers_toolkit.app.settings',
        'crackers_toolkit.app.logging_panel',
        'crackers_toolkit.app.sidebar',
        'crackers_toolkit.app.main_window',
        'crackers_toolkit.app.help_guide',
        'crackers_toolkit.modules',
        'crackers_toolkit.modules.base_module',
        'crackers_toolkit.modules.prince_processor',
        'crackers_toolkit.modules.pcfg_guesser',
        'crackers_toolkit.modules.combinator',
        'crackers_toolkit.modules.prince_ling',
        'crackers_toolkit.modules.element_extractor',
        'crackers_toolkit.modules.keyboard_walk_generator',
        'crackers_toolkit.modules.date_number_generator',
        'crackers_toolkit.modules.demeuk_cleaner',
        'crackers_toolkit.modules.pcfg_trainer',
        'crackers_toolkit.modules.password_scorer',
        'crackers_toolkit.modules.pcfg_rule_editor',
        'crackers_toolkit.modules.statsgen',
        'crackers_toolkit.modules.maskgen',
        'crackers_toolkit.modules.policygen',
        'crackers_toolkit.modules.rulegen',
        'crackers_toolkit.modules.mask_builder',
        'crackers_toolkit.modules.rule_builder',
        'crackers_toolkit.modules.hashcat_launcher',
        'crackers_toolkit.modules.scraper_generator',
        'crackers_toolkit.modules.simple_cleaner',
        'crackers_toolkit.modules.hash_extractor',
        'crackers_toolkit.modules.markov_gui',
        'crackers_toolkit.app.dependency_checker',
        'json',
        're',
        'configparser',
        'shutil',
        'threading',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'scipy', 'pandas', 'tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CrackersToolkit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=os.path.join(BASE, 'icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CrackersToolkit',
)
