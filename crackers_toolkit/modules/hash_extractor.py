"""Module 22: Hash Extractor.

Extract password hashes from encrypted files, containers, wallets,
databases, and archives using hashcat ``*2hashcat`` tools and John the
Ripper ``*2john`` tools.  Supports automatic JtR prefix cleanup and
one-click "Send to Hashcat Command Builder".
"""

from __future__ import annotations

import re
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .base_module import BaseModule

# =====================================================================
# ExtractorInfo data structure
# =====================================================================

@dataclass
class ExtractorInfo:
    """Metadata for a single hash-extraction tool."""

    name: str
    script_name: str
    script_path: Path = field(default_factory=lambda: Path())
    source: str = "hashcat"          # "hashcat" | "john"
    language: str = "python"         # "python" | "perl" | "exe" | "js" | "lua"
    category: str = "Other"
    input_description: str = ""
    file_filter: str = "All Files (*)"
    hashcat_modes: list[int] = field(default_factory=list)
    hashcat_compatible: bool = True
    needs_cleanup: bool = False
    notes: str = ""
    has_special_ui: str = ""         # "", "veracrypt", "bitlocker", "metamask"
    dependencies: list[str] = field(default_factory=list)


# =====================================================================
# Hashcat *2hashcat extractor registry  (24 tools)
# =====================================================================

_HASHCAT_EXTRACTORS: list[ExtractorInfo] = [
    ExtractorInfo(
        name="VeraCrypt",
        script_name="veracrypt2hashcat.py",
        source="hashcat", language="python",
        category="Encryption / Containers",
        input_description=(
            "VeraCrypt encrypted container file (.hc).  This is the "
            "volume file itself — not the mounted drive letter."
        ),
        file_filter="VeraCrypt Container (*.hc);;All Files (*)",
        hashcat_modes=[13711, 13712, 13713, 13721, 13722, 13723,
                       13731, 13732, 13733, 13741, 13742, 13743,
                       13751, 13752, 13753, 13761, 13762, 13763,
                       13771, 13772, 13773,
                       29411, 29412, 29413, 29421, 29422, 29423,
                       29431, 29432, 29433, 29441, 29442, 29443,
                       29451, 29452, 29453, 29461, 29462, 29463],
        hashcat_compatible=True, needs_cleanup=False,
        notes="Supports hidden containers and bootable partitions via offset options.",
        has_special_ui="veracrypt",
    ),
    ExtractorInfo(
        name="TrueCrypt",
        script_name="truecrypt2hashcat.py",
        source="hashcat", language="python",
        category="Encryption / Containers",
        input_description=(
            "TrueCrypt encrypted container file.  Same offset options "
            "as VeraCrypt (bootable, hidden, bootable+hidden)."
        ),
        file_filter="TrueCrypt Container (*.tc);;All Files (*)",
        hashcat_modes=[6211, 6212, 6213, 6221, 6222, 6223,
                       6231, 6232, 6233, 6241, 6242, 6243,
                       29311, 29312, 29313, 29321, 29322, 29323,
                       29331, 29332, 29333],
        hashcat_compatible=True, needs_cleanup=False,
        notes="Identical extraction logic to VeraCrypt but with $truecrypt$ prefix.",
        has_special_ui="veracrypt",
    ),
    ExtractorInfo(
        name="BitLocker",
        script_name="bitlocker2hashcat.py",
        source="hashcat", language="python",
        category="Encryption / Containers",
        input_description=(
            "BitLocker encrypted disk image or partition dump.  "
            "You must specify the partition offset (in bytes) using "
            "the offset field below."
        ),
        file_filter="Disk Image (*.img *.raw *.dd *.bin);;All Files (*)",
        hashcat_modes=[22100],
        hashcat_compatible=True, needs_cleanup=False,
        notes="Only extracts password-protected VMK hashes. TPM/recovery key hashes not supported.",
        has_special_ui="bitlocker",
    ),
    ExtractorInfo(
        name="Cryptoloop",
        script_name="cryptoloop2hashcat.py",
        source="hashcat", language="python",
        category="Encryption / Containers",
        input_description="Linux Cryptoloop encrypted partition file.",
        file_filter="All Files (*)",
        hashcat_modes=[14511, 14512, 14513, 14521, 14522, 14523,
                       14531, 14532, 14533, 14541, 14542, 14543,
                       14551, 14552, 14553],
        hashcat_compatible=True, needs_cleanup=False,
    ),
    ExtractorInfo(
        name="LUKS",
        script_name="luks2hashcat.py",
        source="hashcat", language="python",
        category="Encryption / Containers",
        input_description="LUKS encrypted volume (v1 or v2) container file.",
        file_filter="All Files (*)",
        hashcat_modes=[14600],
        hashcat_compatible=True, needs_cleanup=False,
    ),
    ExtractorInfo(
        name="APFS",
        script_name="apfs2hashcat.py",
        source="hashcat", language="python",
        category="System / Disk",
        input_description=(
            "APFS disk image file (.dmg, .img).  Works with image files on "
            "Windows — cannot read live macOS partitions."
        ),
        file_filter="Disk Image (*.dmg *.img *.raw);;All Files (*)",
        hashcat_modes=[18300],
        hashcat_compatible=True, needs_cleanup=False,
        notes="Requires the 'cryptography' Python package.",
        dependencies=["cryptography"],
    ),
    ExtractorInfo(
        name="MetaMask",
        script_name="metamask2hashcat.py",
        source="hashcat", language="python",
        category="Wallet / Crypto",
        input_description=(
            "MetaMask vault JSON file exported from browser extension "
            "storage or mobile wallet backup."
        ),
        file_filter="JSON Files (*.json);;All Files (*)",
        hashcat_modes=[26600, 26610],
        hashcat_compatible=True, needs_cleanup=False,
        notes="Use 'short data' option for hashcat mode 26610.",
        has_special_ui="metamask",
    ),
    ExtractorInfo(
        name="Exodus",
        script_name="exodus2hashcat.py",
        source="hashcat", language="python",
        category="Wallet / Crypto",
        input_description="Exodus wallet encrypted seed file (.seco).",
        file_filter="Exodus Seed (*.seco);;All Files (*)",
        hashcat_modes=[28200],
        hashcat_compatible=True, needs_cleanup=False,
    ),
    ExtractorInfo(
        name="Bisq",
        script_name="bisq2hashcat.py",
        source="hashcat", language="python",
        category="Wallet / Crypto",
        input_description="Bisq .wallet file (Bitcoinj protobuf format).",
        file_filter="Wallet File (*.wallet);;All Files (*)",
        hashcat_modes=[28501],
        hashcat_compatible=True, needs_cleanup=False,
        dependencies=["protobuf"],
    ),
    ExtractorInfo(
        name="Bitwarden",
        script_name="bitwarden2hashcat.py",
        source="hashcat", language="python",
        category="Authentication / Keys",
        input_description=(
            "Bitwarden local data directory from Chrome, Firefox, or "
            "Desktop application."
        ),
        file_filter="All Files (*)",
        hashcat_modes=[13400],
        hashcat_compatible=True, needs_cleanup=False,
        dependencies=["snappy", "leveldb"],
    ),
    ExtractorInfo(
        name="LastPass",
        script_name="lastpass2hashcat.py",
        source="hashcat", language="python",
        category="Authentication / Keys",
        input_description="LastPass local database or vault export.",
        file_filter="Database (*.db *.sqlite);;All Files (*)",
        hashcat_modes=[6800],
        hashcat_compatible=True, needs_cleanup=False,
    ),
    ExtractorInfo(
        name="Mozilla / Firefox",
        script_name="mozilla2hashcat.py",
        source="hashcat", language="python",
        category="Authentication / Keys",
        input_description=(
            "Firefox master password database: key3.db (older) or "
            "key4.db (newer versions)."
        ),
        file_filter="Firefox Key DB (key3.db key4.db);;All Files (*)",
        hashcat_modes=[26100, 26200],
        hashcat_compatible=True, needs_cleanup=False,
        dependencies=["PyCryptodome", "pyasn1"],
    ),
    ExtractorInfo(
        name="Gitea",
        script_name="gitea2hashcat.py",
        source="hashcat", language="python",
        category="Authentication / Keys",
        input_description=(
            "Gitea database PBKDF2 hash string in SALT:HASH format.  "
            "Paste the hash directly or provide a file containing it."
        ),
        file_filter="Text Files (*.txt);;All Files (*)",
        hashcat_modes=[10900],
        hashcat_compatible=True, needs_cleanup=False,
    ),
    ExtractorInfo(
        name="Apache Shiro",
        script_name="shiro1-to-hashcat.py",
        source="hashcat", language="python",
        category="Authentication / Keys",
        input_description="Apache Shiro 1 serialized session files (.pcl).",
        file_filter="PCL Files (*.pcl);;All Files (*)",
        hashcat_modes=[12150],
        hashcat_compatible=True, needs_cleanup=False,
    ),
    ExtractorInfo(
        name="Radmin3",
        script_name="radmin3_to_hashcat.pl",
        source="hashcat", language="perl",
        category="Authentication / Keys",
        input_description="Windows registry export (.reg) containing Radmin3 hashes.",
        file_filter="Registry File (*.reg);;All Files (*)",
        hashcat_modes=[29200],
        hashcat_compatible=True, needs_cleanup=False,
        dependencies=["Perl"],
    ),
    ExtractorInfo(
        name="VirtualBox",
        script_name="virtualbox2hashcat.py",
        source="hashcat", language="python",
        category="Virtual Machines",
        input_description="VirtualBox machine configuration file (.vbox).",
        file_filter="VBox Config (*.vbox);;All Files (*)",
        hashcat_modes=[27600],
        hashcat_compatible=True, needs_cleanup=False,
    ),
    ExtractorInfo(
        name="VMware",
        script_name="vmwarevmx2hashcat.py",
        source="hashcat", language="python",
        category="Virtual Machines",
        input_description="VMware virtual machine configuration file (.vmx).",
        file_filter="VMX Config (*.vmx);;All Files (*)",
        hashcat_modes=[27400],
        hashcat_compatible=True, needs_cleanup=False,
    ),
    ExtractorInfo(
        name="Veeam Backup",
        script_name="veeamvbk2hashcat.py",
        source="hashcat", language="python",
        category="Backup",
        input_description="Veeam Backup & Replication VBK file (.vbk).",
        file_filter="VBK Backup (*.vbk);;All Files (*)",
        hashcat_modes=[29100],
        hashcat_compatible=True, needs_cleanup=False,
    ),
    ExtractorInfo(
        name="AES Crypt",
        script_name="aescrypt2hashcat.pl",
        source="hashcat", language="perl",
        category="Other",
        input_description="AES Crypt encrypted file (.aes).",
        file_filter="AES Files (*.aes);;All Files (*)",
        hashcat_modes=[22500],
        hashcat_compatible=True, needs_cleanup=False,
        dependencies=["Perl"],
    ),
    ExtractorInfo(
        name="Kremlin",
        script_name="kremlin2hashcat.py",
        source="hashcat", language="python",
        category="Other",
        input_description="Kremlin Encrypt 3.0 encrypted file (.kgb).",
        file_filter="KGB Files (*.kgb);;All Files (*)",
        hashcat_modes=[29700],
        hashcat_compatible=True, needs_cleanup=False,
    ),
    ExtractorInfo(
        name="Apple Secure Notes",
        script_name="securenotes2hashcat.pl",
        source="hashcat", language="perl",
        category="Other",
        input_description="Apple NoteStore.sqlite database file.",
        file_filter="SQLite DB (*.sqlite *.db);;All Files (*)",
        hashcat_modes=[16200],
        hashcat_compatible=True, needs_cleanup=False,
        dependencies=["Perl", "DBI", "DBD::SQLite"],
    ),
    ExtractorInfo(
        name="SQLCipher",
        script_name="sqlcipher2hashcat.pl",
        source="hashcat", language="perl",
        category="Database",
        input_description="SQLCipher encrypted SQLite database (.db).",
        file_filter="SQLite DB (*.db *.sqlite);;All Files (*)",
        hashcat_modes=[24600],
        hashcat_compatible=True, needs_cleanup=False,
        dependencies=["Perl"],
    ),
    ExtractorInfo(
        name="Windows CloudAP Cache",
        script_name="cachedata2hashcat.py",
        source="hashcat", language="python",
        category="System / Disk",
        input_description=(
            "Windows CloudAP CacheData binary file from "
            "MicrosoftAccount or AzureAD cache directory."
        ),
        file_filter="All Files (*)",
        hashcat_modes=[28100],
        hashcat_compatible=True, needs_cleanup=False,
    ),
    ExtractorInfo(
        name="iOS / macOS Keybag",
        script_name="keybag2hashcat.py",
        source="hashcat", language="python",
        category="System / Disk",
        input_description="iOS or macOS device keybag binary file.",
        file_filter="All Files (*)",
        hashcat_modes=[29000],
        hashcat_compatible=True, needs_cleanup=False,
    ),
]

# =====================================================================
# Curated JtR *2john tools with known hashcat compatibility
# =====================================================================

_CURATED_JTR: dict[str, ExtractorInfo] = {}


def _build_curated_jtr() -> dict[str, ExtractorInfo]:
    """Build a mapping of filename → ExtractorInfo for popular JtR tools."""
    data: list[tuple] = [
        # (script, name, category, input_description, file_filter,
        #  hashcat_modes, compatible, notes, language, deps)
        ("office2john.py", "MS Office", "Document",
         "Microsoft Office file (.doc/.docx/.xls/.xlsx/.ppt/.pptx).",
         "Office Files (*.doc *.docx *.xls *.xlsx *.ppt *.pptx);;All Files (*)",
         [9400, 9500, 9600, 9700, 9800, 25300], True,
         "Strip prefix then use with hashcat. Mode depends on Office version.", "python", []),
        ("zip2john.exe", "ZIP Archive", "Archive",
         "Password-protected ZIP archive file (.zip).",
         "ZIP Files (*.zip);;All Files (*)",
         [17200, 17210, 17220, 17225, 17230, 13600], True,
         "Hashcat supports PKZIP and WinZip formats.", "exe", []),
        ("rar2john.exe", "RAR Archive", "Archive",
         "Password-protected RAR archive file (.rar).",
         "RAR Files (*.rar);;All Files (*)",
         [12500, 13000, 23700, 23800], True,
         "Mode depends on RAR version (3 vs 5).", "exe", []),
        ("7z2john.pl", "7-Zip Archive", "Archive",
         "Password-protected 7-Zip archive file (.7z).",
         "7z Files (*.7z);;All Files (*)",
         [11600], True,
         "Requires Perl.", "perl", ["Perl"]),
        ("keepass2john.exe", "KeePass", "Authentication / Keys",
         "KeePass password database (.kdbx / .kdb).",
         "KeePass DB (*.kdbx *.kdb);;All Files (*)",
         [13400], True, "", "exe", []),
        ("ssh2john.py", "SSH Private Key", "Authentication / Keys",
         "SSH private key file (id_rsa, id_ed25519, id_ecdsa, etc.).",
         "SSH Keys (id_rsa id_ed25519 id_ecdsa *.pem);;All Files (*)",
         [22911, 22921, 22931, 22941], True,
         "JtR format may differ from hashcat's expected format.", "python", []),
        ("gpg2john.exe", "GPG / PGP", "Authentication / Keys",
         "GPG/PGP private key or encrypted file.",
         "GPG Files (*.gpg *.pgp *.asc);;All Files (*)",
         [17010, 17020], True,
         "Limited compatibility — format may differ.", "exe", []),
        ("pdf2john.pl", "PDF", "Document",
         "Password-protected PDF document (.pdf).",
         "PDF Files (*.pdf);;All Files (*)",
         [10400, 10500, 10600, 10700], True,
         "Requires Perl.", "perl", ["Perl"]),
        ("bitcoin2john.py", "Bitcoin Wallet", "Wallet / Crypto",
         "Bitcoin Core wallet.dat file.",
         "Wallet (wallet.dat);;All Files (*)",
         [11300], True,
         "Limited format compatibility with hashcat.", "python", []),
        ("ethereum2john.py", "Ethereum Wallet", "Wallet / Crypto",
         "Ethereum JSON wallet file (Geth, Mist, MyEtherWallet).",
         "JSON Files (*.json);;All Files (*)",
         [15600, 15700], True,
         "Mode depends on key derivation: 15600=Scrypt, 15700=PBKDF2.", "python", []),
        ("1password2john.py", "1Password", "Authentication / Keys",
         "1Password vault (Agile Keychain or OPVault directory).",
         "All Files (*)", [], False,
         "JtR-only format — no direct hashcat equivalent.", "python", []),
        ("dashlane2john.py", "Dashlane", "Authentication / Keys",
         "Dashlane encrypted database (.aes / .dash file).",
         "Dashlane (*.aes *.dash);;All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("signal2john.py", "Signal Messenger", "Other",
         "Signal Messenger encrypted backup (SecureSMS-Preferences.xml).",
         "XML Files (*.xml);;All Files (*)", [], False,
         "JtR-only format. Modern Signal no longer supports passphrases.", "python", []),
        ("telegram2john.py", "Telegram", "Other",
         "Telegram Desktop tdata directory.",
         "All Files (*)", [20261], True,
         "Limited compatibility.", "python", []),
        ("dmg2john.py", "macOS DMG", "System / Disk",
         "macOS encrypted disk image (.dmg).",
         "DMG Files (*.dmg);;All Files (*)", [22100], True,
         "Limited format compatibility.", "python", []),
        ("keychain2john.py", "macOS Keychain", "System / Disk",
         "macOS Keychain file.", "All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("android2john.py", "Android Backup", "System / Disk",
         "Android device backup file (.ab).",
         "Android Backup (*.ab);;All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("krb2john.py", "Kerberos", "Network / Protocol",
         "Kerberos ticket cache or kirbi file.",
         "All Files (*)", [7500, 13100, 18200], True,
         "Hashcat supports AS-REQ, TGS-REP, AS-REP roasting.", "python", []),
        ("wpapcap2john.exe", "WPA/WPA2 PCAP", "Network / Protocol",
         "WPA/WPA2 pcap capture file (.pcap / .cap).",
         "PCAP Files (*.pcap *.cap);;All Files (*)", [2500, 22000], True,
         "Format may differ — hashcat prefers .hccapx/.hc22000 directly.", "exe", []),
        ("iwork2john.py", "Apple iWork", "Document",
         "Apple iWork file (.pages / .numbers / .key).",
         "iWork Files (*.pages *.numbers *.key);;All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("libreoffice2john.py", "LibreOffice", "Document",
         "LibreOffice encrypted document (.odt / .ods / .odp).",
         "LibreOffice (*.odt *.ods *.odp);;All Files (*)", [18400], True,
         "", "python", []),
        ("pfx2john.py", "PFX / PKCS#12", "Authentication / Keys",
         "PKCS#12 / PFX certificate file (.pfx / .p12).",
         "PFX Files (*.pfx *.p12);;All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("pem2john.py", "PEM Key", "Authentication / Keys",
         "PEM-encoded private key file.",
         "PEM Files (*.pem);;All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("openssl2john.py", "OpenSSL Encrypted", "Authentication / Keys",
         "OpenSSL encrypted file.",
         "All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("blockchain2john.py", "Blockchain.com", "Wallet / Crypto",
         "Blockchain.com wallet backup.",
         "All Files (*)", [12700], True,
         "", "python", []),
        ("electrum2john.py", "Electrum Wallet", "Wallet / Crypto",
         "Electrum Bitcoin wallet file.",
         "All Files (*)", [16600, 21700, 21800], True,
         "", "python", []),
        ("monero2john.py", "Monero Wallet", "Wallet / Crypto",
         "Monero wallet file.",
         "All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("mozilla2john.py", "Mozilla / Firefox (JtR)", "Authentication / Keys",
         "Firefox key3.db / key4.db password database.",
         "Firefox Key DB (key3.db key4.db);;All Files (*)", [26100, 26200], True,
         "", "python", []),
        ("staroffice2john.py", "StarOffice", "Document",
         "StarOffice encrypted document.",
         "All Files (*)", [18600], True, "", "python", []),
        ("putty2john.exe", "PuTTY Key", "Authentication / Keys",
         "PuTTY private key file (.ppk).",
         "PPK Files (*.ppk);;All Files (*)", [], False,
         "JtR-only format.", "exe", []),
        ("bitlocker2john.exe", "BitLocker (JtR)", "Encryption / Containers",
         "BitLocker encrypted disk image.",
         "Disk Image (*.img *.raw *.dd *.bin);;All Files (*)", [22100], True,
         "", "exe", []),
        ("luks2john.py", "LUKS (JtR)", "Encryption / Containers",
         "LUKS encrypted volume.",
         "All Files (*)", [14600], True,
         "JtR extraction format differs from hashcat's luks2hashcat.", "python", []),
        ("truecrypt2john.py", "TrueCrypt (JtR)", "Encryption / Containers",
         "TrueCrypt encrypted container.",
         "All Files (*)", [6211, 6221, 6231, 6241], True,
         "hashcat's truecrypt2hashcat is recommended instead.", "python", []),
        ("dmg2john.exe", "macOS DMG (exe)", "System / Disk",
         "macOS encrypted disk image (.dmg).",
         "DMG Files (*.dmg);;All Files (*)", [22100], True,
         "", "exe", []),
        ("diskcryptor2john.py", "DiskCryptor", "Encryption / Containers",
         "DiskCryptor encrypted volume.",
         "All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("ecryptfs2john.py", "eCryptfs", "Encryption / Containers",
         "eCryptfs encrypted home directory wrapped-passphrase file.",
         "All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("encfs2john.py", "EncFS", "Encryption / Containers",
         "EncFS encrypted filesystem config (.encfs6.xml).",
         "XML Files (*.xml);;All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("bestcrypt2john.py", "BestCrypt", "Encryption / Containers",
         "BestCrypt encrypted container.",
         "All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("ansible2john.py", "Ansible Vault", "Authentication / Keys",
         "Ansible Vault encrypted YAML file.",
         "YAML Files (*.yml *.yaml);;All Files (*)", [16900], True,
         "", "python", []),
        ("cisco2john.pl", "Cisco Config", "Network / Protocol",
         "Cisco router/switch configuration file.",
         "Config Files (*.conf *.cfg *.txt);;All Files (*)", [], False,
         "Requires Perl. Various Cisco hash types.", "perl", ["Perl"]),
        ("pcap2john.py", "PCAP Network Capture", "Network / Protocol",
         "Network packet capture file (.pcap).",
         "PCAP Files (*.pcap *.cap);;All Files (*)", [], False,
         "Extracts various authentication hashes from network traffic.", "python", []),
        ("applenotes2john.py", "Apple Notes", "Other",
         "Apple Notes encrypted note database.",
         "All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("bitwarden2john.py", "Bitwarden (JtR)", "Authentication / Keys",
         "Bitwarden local data (Chrome/Firefox/Desktop).",
         "All Files (*)", [13400], True,
         "", "python", ["snappy", "leveldb"]),
        ("lastpass2john.py", "LastPass (JtR)", "Authentication / Keys",
         "LastPass local database.",
         "All Files (*)", [6800], True,
         "", "python", []),
        ("enpass2john.py", "Enpass", "Authentication / Keys",
         "Enpass password manager database.",
         "All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("kwallet2john.py", "KWallet", "Authentication / Keys",
         "KDE Wallet file (.kwl).",
         "Wallet Files (*.kwl);;All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("keyring2john.py", "GNOME Keyring", "Authentication / Keys",
         "GNOME Keyring file.",
         "All Files (*)", [], False,
         "JtR-only format.", "python", []),
        ("keystore2john.py", "Java Keystore", "Authentication / Keys",
         "Java KeyStore file (.jks / .bks).",
         "KeyStore (*.jks *.bks);;All Files (*)", [], False,
         "JtR-only format.", "python", []),
    ]
    out: dict[str, ExtractorInfo] = {}
    for row in data:
        (script, name, cat, idesc, ffilter, modes, compat,
         notes, lang, deps) = row
        info = ExtractorInfo(
            name=name, script_name=script, source="john",
            language=lang, category=cat,
            input_description=idesc, file_filter=ffilter,
            hashcat_modes=modes, hashcat_compatible=compat,
            needs_cleanup=True, notes=notes, dependencies=deps,
        )
        out[script] = info
        # On Linux, JtR .exe tools are bare names (e.g. 'zip2john' not
        # 'zip2john.exe').  Register the bare name too so discovery matches.
        if script.endswith(".exe"):
            out[script[:-4]] = info
    return out


_CURATED_JTR = _build_curated_jtr()

# Category order for the tree widget
_CATEGORY_ORDER = [
    "Encryption / Containers",
    "Archive",
    "Document",
    "Wallet / Crypto",
    "Authentication / Keys",
    "System / Disk",
    "Virtual Machines",
    "Backup",
    "Network / Protocol",
    "Database",
    "Other",
]


# =====================================================================
# FDE mode detail data (VeraCrypt / TrueCrypt)
# =====================================================================

_CIPHER_LABEL = {
    1: "AES / Twofish / Serpent / Camellia / Kuznyechik  (single)",
    2: "AES-Twofish / Serpent-AES / Twofish-Serpent  (cascade)",
    3: "AES-Twofish-Serpent / Serpent-Twofish-AES  (triple cascade)",
}

_VC_MODES: list[tuple[int, str, int, str]] = [
    # (mode_id, hash_algo, xts_bits, boot_note)
    (13711, "RIPEMD-160", 512,  ""),
    (13712, "RIPEMD-160", 1024, ""),
    (13713, "RIPEMD-160", 1536, ""),
    (13721, "SHA-512",    512,  ""),
    (13722, "SHA-512",    1024, ""),
    (13723, "SHA-512",    1536, ""),
    (13731, "Whirlpool",  512,  ""),
    (13732, "Whirlpool",  1024, ""),
    (13733, "Whirlpool",  1536, ""),
    (13741, "RIPEMD-160", 512,  "boot"),
    (13742, "RIPEMD-160", 1024, "boot"),
    (13743, "RIPEMD-160", 1536, "boot"),
    (13751, "SHA-256",    512,  ""),
    (13752, "SHA-256",    1024, ""),
    (13753, "SHA-256",    1536, ""),
    (13761, "SHA-256",    512,  "boot"),
    (13762, "SHA-256",    1024, "boot"),
    (13763, "SHA-256",    1536, "boot"),
    (13771, "Streebog-512", 512,  ""),
    (13772, "Streebog-512", 1024, ""),
    (13773, "Streebog-512", 1536, ""),
    (29411, "RIPEMD-160", 512,  "boot-mode (legacy)"),
    (29412, "RIPEMD-160", 1024, "boot-mode (legacy)"),
    (29413, "RIPEMD-160", 1536, "boot-mode (legacy)"),
    (29421, "SHA-512",    512,  "boot-mode"),
    (29422, "SHA-512",    1024, "boot-mode"),
    (29423, "SHA-512",    1536, "boot-mode"),
    (29431, "Whirlpool",  512,  "boot-mode"),
    (29432, "Whirlpool",  1024, "boot-mode"),
    (29433, "Whirlpool",  1536, "boot-mode"),
    (29441, "RIPEMD-160", 512,  "boot-mode"),
    (29442, "RIPEMD-160", 1024, "boot-mode"),
    (29443, "RIPEMD-160", 1536, "boot-mode"),
    (29451, "SHA-256",    512,  "boot-mode"),
    (29452, "SHA-256",    1024, "boot-mode"),
    (29453, "SHA-256",    1536, "boot-mode"),
    (29461, "Streebog-512", 512,  "boot-mode"),
    (29462, "Streebog-512", 1024, "boot-mode"),
    (29463, "Streebog-512", 1536, "boot-mode"),
]

_TC_MODES: list[tuple[int, str, int, str]] = [
    (6211,  "RIPEMD-160", 512,  ""),
    (6212,  "RIPEMD-160", 1024, ""),
    (6213,  "RIPEMD-160", 1536, ""),
    (6221,  "SHA-512",    512,  ""),
    (6222,  "SHA-512",    1024, ""),
    (6223,  "SHA-512",    1536, ""),
    (6231,  "Whirlpool",  512,  ""),
    (6232,  "Whirlpool",  1024, ""),
    (6233,  "Whirlpool",  1536, ""),
    (6241,  "RIPEMD-160", 512,  "boot"),
    (6242,  "RIPEMD-160", 1024, "boot"),
    (6243,  "RIPEMD-160", 1536, "boot"),
    (29311, "RIPEMD-160", 512,  "boot-mode"),
    (29312, "RIPEMD-160", 1024, "boot-mode"),
    (29313, "RIPEMD-160", 1536, "boot-mode"),
    (29321, "SHA-512",    512,  "boot-mode"),
    (29322, "SHA-512",    1024, "boot-mode"),
    (29323, "SHA-512",    1536, "boot-mode"),
    (29331, "Whirlpool",  512,  "boot-mode"),
    (29332, "Whirlpool",  1024, "boot-mode"),
    (29333, "Whirlpool",  1536, "boot-mode"),
]


class _FDEModeDialog(QDialog):
    """Dialog listing all VeraCrypt or TrueCrypt hashcat modes with attributes."""

    def __init__(
        self,
        title: str,
        modes: list[tuple[int, str, int, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(720, 460)
        self.selected_mode: int | None = None

        lay = QVBoxLayout(self)

        info = QLabel(
            f"<b>{title}</b> — {len(modes)} hashcat modes.  "
            "Select a row and click <i>Use Selected Mode</i> to set it as "
            "the preferred mode for <b>Send to Hashcat</b>."
        )
        info.setWordWrap(True)
        info.setStyleSheet("padding: 6px;")
        lay.addWidget(info)

        self._table = QTableWidget(len(modes), 5)
        self._table.setHorizontalHeaderLabels([
            "Mode (-m)", "Hash Algorithm", "XTS Key Size",
            "Cipher(s)", "Boot",
        ])
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self._table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._table.setAlternatingRowColors(True)
        hdr = self._table.horizontalHeader()
        if hdr is not None:
            hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        for row, (mid, algo, bits, boot) in enumerate(modes):
            cipher_idx = bits // 512
            cipher_text = _CIPHER_LABEL.get(cipher_idx, str(bits))

            self._table.setItem(row, 0, QTableWidgetItem(str(mid)))
            self._table.setItem(row, 1, QTableWidgetItem(algo))
            self._table.setItem(row, 2, QTableWidgetItem(f"{bits} bit"))
            self._table.setItem(row, 3, QTableWidgetItem(cipher_text))
            self._table.setItem(row, 4, QTableWidgetItem(boot if boot else "—"))

        self._table.resizeColumnsToContents()
        lay.addWidget(self._table)

        btn_row = QHBoxLayout()
        use_btn = QPushButton("Use Selected Mode")
        use_btn.clicked.connect(self._on_use)
        btn_row.addWidget(use_btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)

    def _on_use(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if item:
            self.selected_mode = int(item.text())
        self.accept()


# =====================================================================
# Drop-zone frame widget
# =====================================================================

class _DropZoneFrame(QFrame):
    """A framed area that accepts file drag-and-drop."""

    file_dropped = pyqtSignal(str)

    _STYLE_NORMAL = (
        "QFrame { border: 2px dashed #585b70; border-radius: 6px; "
        "padding: 12px; background: transparent; }"
    )
    _STYLE_HOVER = (
        "QFrame { border: 2px dashed #89b4fa; border-radius: 6px; "
        "padding: 12px; background: rgba(137,180,250,0.05); }"
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setStyleSheet(self._STYLE_NORMAL)
        lay = QVBoxLayout(self)
        self._label = QLabel("Drag && drop input file here")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("color: #a6adc8; font-size: 12px; border: none;")
        lay.addWidget(self._label)
        self.setMinimumHeight(48)
        self.setMaximumHeight(56)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # type: ignore[override]
        if event.mimeData() and event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self._STYLE_HOVER)

    def dragLeaveEvent(self, event) -> None:  # type: ignore[override]
        self.setStyleSheet(self._STYLE_NORMAL)

    def dropEvent(self, event: QDropEvent) -> None:  # type: ignore[override]
        self.setStyleSheet(self._STYLE_NORMAL)
        if event.mimeData() and event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                if path:
                    self.file_dropped.emit(path)


# =====================================================================
# Module class
# =====================================================================

class HashExtractorModule(BaseModule):
    MODULE_NAME = "Hash Extractor"
    MODULE_DESCRIPTION = (
        "Extract password hashes from encrypted files, containers, "
        "wallets, databases, and archives using hashcat and John the "
        "Ripper extraction tools."
    )
    MODULE_CATEGORY = "Hash Extraction"

    _work_done = pyqtSignal(dict)

    def __init__(self, settings=None, base_dir=None, parent=None) -> None:
        self._settings = settings
        self._base_dir = base_dir
        self._output_path: Optional[str] = None
        self._perl_available: Optional[bool] = None
        self._all_extractors: list[ExtractorInfo] = []
        self._selected_extractor: Optional[ExtractorInfo] = None
        self._preferred_mode: int | None = None
        super().__init__(parent)
        self._work_done.connect(self._on_work_done)
        self._reset_btn.setVisible(False)
        # Build extractor list after UI so tree exists
        self._build_extractor_list()
        self._populate_tree()

    # ------------------------------------------------------------------
    # Extractor discovery
    # ------------------------------------------------------------------
    def _get_base(self) -> Path:
        """Return the project root directory."""
        if self._base_dir:
            return Path(self._base_dir)
        return Path(__file__).resolve().parent.parent.parent

    def _find_hashcat_tools_dir(self) -> Path | None:
        base = self._get_base()
        tools = base / "hashcat-7.1.2" / "tools"
        return tools if tools.is_dir() else None

    def _find_jtr_run_dir(self) -> Path | None:
        base = self._get_base()
        for d in sorted(base.iterdir()):
            if d.is_dir() and d.name.lower().startswith("john") and (d / "run").is_dir():
                return d / "run"
        return None

    def _check_perl(self) -> bool:
        if self._perl_available is not None:
            return self._perl_available
        import shutil
        if shutil.which("perl"):
            self._perl_available = True
        else:
            try:
                subprocess.run(
                    ["perl", "--version"],
                    capture_output=True, timeout=5,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                self._perl_available = True
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                self._perl_available = False
        return self._perl_available

    def _build_extractor_list(self) -> None:
        """Discover all extractors from hashcat tools + JtR run dir."""
        extractors: list[ExtractorInfo] = []

        # 1. Hashcat extractors
        hc_dir = self._find_hashcat_tools_dir()
        for ext in _HASHCAT_EXTRACTORS:
            info = ExtractorInfo(**ext.__dict__)  # copy
            if hc_dir:
                info.script_path = hc_dir / info.script_name
            extractors.append(info)

        # 2. JtR extractors — auto-discover
        jtr_dir = self._find_jtr_run_dir()
        seen_scripts: set[str] = set()
        if jtr_dir:
            for f in sorted(jtr_dir.iterdir()):
                if "2john" not in f.name:
                    continue
                sname = f.name
                if sname in seen_scripts:
                    continue
                seen_scripts.add(sname)

                curated = _CURATED_JTR.get(sname)
                if curated:
                    info = ExtractorInfo(**curated.__dict__)
                    info.script_path = f
                else:
                    # Generic auto-discovered entry
                    suffix = f.suffix.lstrip(".")
                    lang = {"py": "python", "pl": "perl", "exe": "exe",
                            "js": "js", "lua": "lua"}.get(suffix, "")
                    if not lang and not suffix and f.is_file():
                        # Linux: extensionless executable (ELF binary)
                        lang = "exe"
                    if not lang:
                        lang = "unknown"
                    raw_name = sname.split("2john")[0]
                    display = raw_name.replace("_", " ").replace("-", " ").title()
                    deps = ["Perl"] if lang == "perl" else []
                    info = ExtractorInfo(
                        name=display,
                        script_name=sname,
                        script_path=f,
                        source="john", language=lang,
                        category="Other",
                        input_description=f"Input file for {display} hash extraction.",
                        file_filter="All Files (*)",
                        hashcat_modes=[], hashcat_compatible=False,
                        needs_cleanup=True,
                        notes="Auto-discovered JtR tool.",
                        dependencies=deps,
                    )
                extractors.append(info)

        self._all_extractors = extractors

    # ------------------------------------------------------------------
    # UI building
    # ------------------------------------------------------------------
    def build_input_section(self, layout: QVBoxLayout) -> None:
        # --- Search filter ---
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter extractors by name or category…")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self._search_edit, stretch=1)
        layout.addLayout(search_row)

        # --- Extractor tree ---
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Extractor", "Compatibility"])
        self._tree.setColumnWidth(0, 320)
        self._tree.setMinimumHeight(220)
        self._tree.setRootIsDecorated(True)
        self._tree.setAlternatingRowColors(True)
        self._tree.currentItemChanged.connect(self._on_tree_selection_changed)
        layout.addWidget(self._tree)

        # --- Description panel ---
        self._desc_label = QLabel("")
        self._desc_label.setWordWrap(True)
        self._desc_label.setMinimumHeight(40)
        self._desc_label.setStyleSheet(
            "padding: 8px; background: rgba(49,50,68,0.6); "
            "border-radius: 4px; font-size: 12px;"
        )
        layout.addWidget(self._desc_label)

        # --- Dependency banner ---
        self._dep_banner = QLabel("")
        self._dep_banner.setWordWrap(True)
        self._dep_banner.setStyleSheet(
            "padding: 6px; background: rgba(249,226,175,0.15); "
            "color: #f9e2af; border-radius: 4px; font-size: 11px;"
        )
        self._dep_banner.setVisible(False)
        layout.addWidget(self._dep_banner)

        # --- Drop zone + file browser ---
        self._drop_zone = _DropZoneFrame()
        self._drop_zone.file_dropped.connect(self._on_file_dropped)
        layout.addWidget(self._drop_zone)

        self._input_file = self.create_file_browser(
            layout,
            "Input file:",
            "Select the file to extract a hash from. File type depends on the selected extractor.",
            file_filter="All Files (*)",
        )

    def build_params_section(self, layout: QVBoxLayout) -> None:
        # --- VeraCrypt / TrueCrypt offset options ---
        self._vc_container = QWidget()
        vc_lay = QVBoxLayout(self._vc_container)
        vc_lay.setContentsMargins(0, 0, 0, 0)
        vc_title = QLabel("Container type:")
        vc_title.setStyleSheet("font-weight: bold;")
        vc_lay.addWidget(vc_title)

        self._vc_group = QButtonGroup(self)
        vc_options = [
            ("Standard volume (offset 0)", 0),
            ("Bootable partition (offset 31744)", 31744),
            ("Hidden container (offset 65536)", 65536),
            ("Bootable + Hidden (offset 97280)", 97280),
        ]
        self._vc_offsets: dict[QRadioButton, int] = {}
        for i, (label, offset) in enumerate(vc_options):
            rb = QRadioButton(label)
            if i == 0:
                rb.setChecked(True)
            self._vc_group.addButton(rb)
            self._vc_offsets[rb] = offset
            vc_lay.addWidget(rb)

        self._vc_raw_check = QCheckBox(
            "Extract raw 512 bytes (binary + hex dump) instead of hash format"
        )
        self._vc_raw_check.setToolTip(
            "Read raw bytes from the container at the selected offset. "
            "Useful for manual analysis or feeding to other tools."
        )
        vc_lay.addWidget(self._vc_raw_check)

        self._vc_modes_btn = QPushButton("View all supported hashcat modes…")
        self._vc_modes_btn.setToolTip(
            "Show a detailed table of every VeraCrypt / TrueCrypt hashcat mode "
            "with hash algorithm, cipher configuration, and boot-mode info."
        )
        self._vc_modes_btn.clicked.connect(self._on_view_fde_modes)
        vc_lay.addWidget(self._vc_modes_btn)

        self._vc_mode_label = QLabel("")
        self._vc_mode_label.setStyleSheet("font-size: 11px; color: #89b4fa; padding: 2px;")
        self._vc_mode_label.setVisible(False)
        vc_lay.addWidget(self._vc_mode_label)

        self._vc_container.setVisible(False)
        layout.addWidget(self._vc_container)

        # --- BitLocker offset ---
        self._bl_container = QWidget()
        bl_lay = QVBoxLayout(self._bl_container)
        bl_lay.setContentsMargins(0, 0, 0, 0)
        bl_row = QHBoxLayout()
        bl_row.addWidget(QLabel("Partition offset (bytes):"))
        bl_row.addWidget(self._info_icon(
            "BitLocker partition offset in bytes. Use disk analysis tools "
            "(e.g. fdisk, diskpart) to determine the correct offset."
        ))
        self._bl_offset = QSpinBox()
        self._bl_offset.setRange(0, 2_147_483_647)
        self._bl_offset.setValue(0)
        bl_row.addWidget(self._bl_offset, stretch=1)
        bl_lay.addLayout(bl_row)
        self._bl_container.setVisible(False)
        layout.addWidget(self._bl_container)

        # --- MetaMask short data option ---
        self._mm_container = QWidget()
        mm_lay = QVBoxLayout(self._mm_container)
        mm_lay.setContentsMargins(0, 0, 0, 0)
        self._mm_shortdata = QCheckBox("Use short data format (hashcat mode 26610)")
        self._mm_shortdata.setToolTip(
            "Truncate ciphertext to first 32 bytes for faster cracking with hashcat mode 26610."
        )
        mm_lay.addWidget(self._mm_shortdata)
        self._mm_container.setVisible(False)
        layout.addWidget(self._mm_container)

        # --- JtR cleanup checkbox ---
        self._cleanup_check = QCheckBox(
            "Strip filename / username prefix for hashcat use"
        )
        self._cleanup_check.setToolTip(
            "John the Ripper tools output hashes with a 'filename:' prefix. "
            "Enable this to strip the prefix for hashcat compatibility."
        )
        self._cleanup_check.setChecked(True)
        self._cleanup_check.setVisible(False)
        layout.addWidget(self._cleanup_check)

    def build_output_section(self, layout: QVBoxLayout) -> None:
        # --- Compatibility / mode label ---
        self._compat_label = QLabel("")
        self._compat_label.setStyleSheet("font-size: 11px; padding: 4px;")
        layout.addWidget(self._compat_label)

        # --- Output text ---
        self._hash_output = QTextEdit()
        self._hash_output.setReadOnly(True)
        self._hash_output.setMinimumHeight(100)
        self._hash_output.setMaximumHeight(200)
        self._hash_output.setPlaceholderText("Extracted hash will appear here…")
        self._hash_output.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace;")
        layout.addWidget(self._hash_output)

        # --- Buttons row ---
        btn_row = QHBoxLayout()

        self._copy_btn = QPushButton("Copy to Clipboard")
        self._copy_btn.clicked.connect(self._on_copy_clicked)
        btn_row.addWidget(self._copy_btn)

        self._save_hash_btn = QPushButton("Save to File")
        self._save_hash_btn.clicked.connect(self._on_save_hash_clicked)
        btn_row.addWidget(self._save_hash_btn)

        self._send_btn = QPushButton("Send to Hashcat Command Builder")
        self._send_btn.setToolTip(
            "Save the extracted hash to a file and open Hashcat Command "
            "Builder with the hash file and suggested -m mode pre-filled."
        )
        self._send_btn.clicked.connect(self._on_send_to_hashcat)
        self._send_btn.setEnabled(False)
        btn_row.addWidget(self._send_btn)

        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Tree population
    # ------------------------------------------------------------------
    def _populate_tree(self) -> None:
        self._tree.clear()
        perl_ok = self._check_perl()

        # Group by category
        cats: dict[str, list[ExtractorInfo]] = {}
        for ext in self._all_extractors:
            cats.setdefault(ext.category, []).append(ext)

        # Sort categories in preferred order
        ordered = []
        for c in _CATEGORY_ORDER:
            if c in cats:
                ordered.append((c, cats.pop(c)))
        for c in sorted(cats):
            ordered.append((c, cats[c]))

        for cat_name, tools in ordered:
            cat_item = QTreeWidgetItem([cat_name, ""])
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            font = cat_item.font(0)
            font.setBold(True)
            cat_item.setFont(0, font)

            for ext in sorted(tools, key=lambda e: e.name):
                # Build display name with source badge
                badge = "🔵" if ext.source == "hashcat" else "🟡"
                display_name = f"{badge}  {ext.name}"

                # Compatibility text
                if ext.source == "hashcat":
                    compat_text = "✅ Hashcat Ready"
                elif ext.hashcat_compatible and ext.hashcat_modes:
                    compat_text = "⚠️ Hashcat Compatible"
                else:
                    compat_text = "❌ JtR Format Only"

                child = QTreeWidgetItem([display_name, compat_text])
                child.setData(0, Qt.ItemDataRole.UserRole, ext)

                # Disable Perl tools if Perl not found
                if ext.language == "perl" and not perl_ok:
                    child.setFlags(child.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                    child.setToolTip(0,
                        "Perl not installed. Install Strawberry Perl (Windows) "
                        "or system perl (Linux) to enable this tool."
                    )

                cat_item.addChild(child)

            self._tree.addTopLevelItem(cat_item)

        self._tree.expandAll()

    # ------------------------------------------------------------------
    # Signals / slots
    # ------------------------------------------------------------------
    def _on_search_changed(self, text: str) -> None:
        """Filter tree items based on search text."""
        q = text.strip().lower()
        for i in range(self._tree.topLevelItemCount()):
            cat = self._tree.topLevelItem(i)
            if cat is None:
                continue
            any_visible = False
            for j in range(cat.childCount()):
                child = cat.child(j)
                if child is None:
                    continue
                ext = child.data(0, Qt.ItemDataRole.UserRole)
                if not q:
                    child.setHidden(False)
                    any_visible = True
                else:
                    searchable = f"{ext.name} {ext.category} {ext.script_name}".lower()
                    visible = q in searchable
                    child.setHidden(not visible)
                    if visible:
                        any_visible = True
            cat.setHidden(not any_visible)

    def _on_tree_selection_changed(self, current: QTreeWidgetItem | None, _prev) -> None:
        if current is None:
            return
        ext = current.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(ext, ExtractorInfo):
            return
        self._selected_extractor = ext
        self._update_description(ext)
        self._update_special_options(ext)
        self._update_compat_label(ext)

    def _update_description(self, ext: ExtractorInfo) -> None:
        parts = [f"<b>{ext.name}</b>"]
        if ext.input_description:
            parts.append(ext.input_description)
        if ext.notes:
            parts.append(f"<i>{ext.notes}</i>")
        self._desc_label.setText("<br>".join(parts))

        # Dependency banner
        non_perl_deps = [d for d in ext.dependencies if d != "Perl"]
        if non_perl_deps:
            deps_str = " ".join(non_perl_deps)
            self._dep_banner.setText(f"⚠ Requires: pip install {deps_str}")
            self._dep_banner.setVisible(True)
        else:
            self._dep_banner.setVisible(False)

    def _update_special_options(self, ext: ExtractorInfo) -> None:
        self._vc_container.setVisible(ext.has_special_ui == "veracrypt")
        self._bl_container.setVisible(ext.has_special_ui == "bitlocker")
        self._mm_container.setVisible(ext.has_special_ui == "metamask")
        self._cleanup_check.setVisible(ext.source == "john")
        # Reset preferred mode when switching extractors
        self._preferred_mode = None
        self._vc_mode_label.setVisible(False)

    def _on_view_fde_modes(self) -> None:
        """Open the FDE mode detail dialog for the current extractor."""
        ext = self._selected_extractor
        if not ext:
            return
        if "VeraCrypt" in ext.name and "TrueCrypt" not in ext.name:
            title = "VeraCrypt Hashcat Modes"
            modes = _VC_MODES
        else:
            title = "TrueCrypt Hashcat Modes"
            modes = _TC_MODES
        dlg = _FDEModeDialog(title, modes, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_mode is not None:
            self._preferred_mode = dlg.selected_mode
            self._vc_mode_label.setText(
                f"Preferred mode: -m {dlg.selected_mode}"
            )
            self._vc_mode_label.setVisible(True)

    def _update_compat_label(self, ext: ExtractorInfo) -> None:
        if ext.source == "hashcat":
            color = "#a6e3a1"
            text = "✅ Hashcat Ready"
            if ext.hashcat_modes:
                n = len(ext.hashcat_modes)
                if n > 10:
                    text += (
                        f"  —  {n} supported modes.  "
                        "Use \"View all supported hashcat modes\" for details."
                    )
                else:
                    modes = ", ".join(str(m) for m in ext.hashcat_modes)
                    text += f"  —  Suggested mode(s): -m {modes}"
        elif ext.hashcat_compatible and ext.hashcat_modes:
            color = "#f9e2af"
            modes = ", ".join(str(m) for m in ext.hashcat_modes)
            text = f"⚠️ Hashcat Compatible (after cleanup)  —  Mode(s): -m {modes}"
        else:
            color = "#f38ba8"
            text = (
                "❌ JtR Format Only — this hash can be cracked with John "
                "the Ripper but may not work with hashcat."
            )
        self._compat_label.setText(text)
        self._compat_label.setStyleSheet(f"color: {color}; font-size: 11px; padding: 4px;")

        # Enable/disable send button
        can_send = bool(ext.hashcat_modes)
        self._send_btn.setEnabled(can_send)

    def _on_file_dropped(self, path: str) -> None:
        self._input_file.setText(path)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self._selected_extractor:
            errors.append("Select an extractor from the list above.")
        inp = self._input_file.text().strip()
        if not inp:
            errors.append("Input file is required.")
        elif not Path(inp).is_file():
            errors.append(f"Input file not found: {inp}")
        ext = self._selected_extractor
        if ext and ext.language == "perl" and not self._check_perl():
            errors.append(
                "Perl is not installed. Install Strawberry Perl (Windows) "
                "or system perl (Linux) to use this extractor."
            )
        return errors

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def run_tool(self) -> None:
        ext = self._selected_extractor
        if not ext:
            return

        # VeraCrypt raw byte extraction (pure Python, no subprocess)
        if ext.has_special_ui == "veracrypt" and self._vc_raw_check.isChecked():
            thread = threading.Thread(
                target=self._extract_raw_bytes, daemon=True,
            )
            thread.start()
            return

        thread = threading.Thread(target=self._run_extraction, daemon=True)
        thread.start()

    def _get_vc_offset(self) -> int:
        for rb, off in self._vc_offsets.items():
            if rb.isChecked():
                return off
        return 0

    def _build_command(self, ext: ExtractorInfo, input_path: str) -> list[str]:
        """Build the subprocess command list."""
        script = str(ext.script_path)
        args: list[str] = []

        # Interpreter
        if ext.language == "python":
            args.append(sys.executable)
        elif ext.language == "perl":
            args.append("perl")
        # exe → no interpreter prefix

        args.append(script)

        # Special arguments per tool type
        if ext.has_special_ui == "veracrypt":
            offset = self._get_vc_offset()
            if offset:
                args.extend(["--offset", str(offset)])
            args.append(input_path)
        elif ext.has_special_ui == "bitlocker":
            args.extend(["-o", str(self._bl_offset.value())])
            args.append(input_path)
        elif ext.has_special_ui == "metamask":
            args.extend(["--vault", input_path])
            if self._mm_shortdata.isChecked():
                args.append("--shortdata")
        else:
            args.append(input_path)

        return args

    def _run_extraction(self) -> None:
        ext = self._selected_extractor
        if not ext:
            return
        input_path = self._input_file.text().strip()
        cmd = self._build_command(ext, input_path)

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(ext.script_path.parent),
                text=True,
                errors="replace",
            )
            stdout, stderr = proc.communicate(timeout=120)
            self._work_done.emit({
                "stdout": stdout,
                "stderr": stderr,
                "returncode": proc.returncode,
            })
        except subprocess.TimeoutExpired:
            proc.kill()
            self._work_done.emit({"error": "Extraction timed out after 120 seconds."})
        except FileNotFoundError as e:
            self._work_done.emit({"error": f"Script not found: {e}"})
        except Exception as e:
            self._work_done.emit({"error": str(e)})

    def _extract_raw_bytes(self) -> None:
        """Read 512 raw bytes from a VeraCrypt/TrueCrypt container."""
        input_path = self._input_file.text().strip()
        offset = self._get_vc_offset()
        try:
            with open(input_path, "rb") as f:
                f.seek(offset)
                data = f.read(512)
            if len(data) < 512:
                self._work_done.emit({
                    "error": f"File too small: read {len(data)} bytes at offset {offset}, expected 512.",
                })
                return
            # Build hex dump
            lines = []
            lines.append(f"# Raw 512 bytes at offset {offset} (0x{offset:X})")
            lines.append(f"# Salt (first 64 bytes) + Encrypted data (448 bytes)")
            lines.append("")
            for i in range(0, 512, 16):
                chunk = data[i:i + 16]
                hex_part = " ".join(f"{b:02x}" for b in chunk)
                ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                lines.append(f"{i:04x}  {hex_part:<48s}  {ascii_part}")
            self._work_done.emit({
                "stdout": "\n".join(lines),
                "stderr": "",
                "returncode": 0,
                "raw_data": data,
            })
        except Exception as e:
            self._work_done.emit({"error": str(e)})

    def _on_work_done(self, results: dict) -> None:
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress.setVisible(False)

        if "error" in results:
            stderr = results.get("error", "")
            # Check for dependency errors
            dep_msg = self._parse_dependency_error(stderr)
            if dep_msg:
                self._hash_output.setPlainText(
                    f"Missing dependency: {dep_msg}\n\n"
                    f"Install with:  pip install {dep_msg}\n\n"
                    f"Full error:\n{stderr}"
                )
            else:
                self._hash_output.setPlainText(f"ERROR: {stderr}")
            self._output_log.append(f"✗ Extraction failed.")
            return

        rc = results.get("returncode", -1)
        stderr = results.get("stderr", "").strip()
        stdout = results.get("stdout", "").strip()

        if rc != 0 and not stdout:
            dep_msg = self._parse_dependency_error(stderr)
            if dep_msg:
                self._hash_output.setPlainText(
                    f"Missing dependency: {dep_msg}\n\n"
                    f"Install with:  pip install {dep_msg}\n\n"
                    f"Full error:\n{stderr}"
                )
            else:
                self._hash_output.setPlainText(
                    f"Extraction failed (exit code {rc}):\n\n{stderr}"
                )
            self._output_log.append(f"✗ Extraction failed (exit code {rc}).")
            return

        # Apply JtR prefix cleanup if enabled
        ext = self._selected_extractor
        if ext and ext.needs_cleanup and self._cleanup_check.isChecked():
            stdout = self._strip_jtr_prefix(stdout)

        self._hash_output.setPlainText(stdout)

        # Store raw data for binary save if present
        self._raw_bytes = results.get("raw_data")

        line_count = len(stdout.splitlines())
        self._output_log.append(
            f"✓ Extraction complete — {line_count} line(s) of output."
        )
        if stderr:
            self._output_log.append(f"Warnings: {stderr[:300]}")

    @staticmethod
    def _strip_jtr_prefix(text: str) -> str:
        """Remove 'filename:' prefix from each JtR output line."""
        lines = []
        for line in text.splitlines():
            if not line.strip():
                lines.append(line)
                continue
            # JtR format: "something:$hash$..." — strip up to first ':'
            # but only if the part after ':' starts with '$' (looks like a hash)
            colon_idx = line.find(":")
            if colon_idx > 0 and colon_idx < len(line) - 1:
                after = line[colon_idx + 1:]
                if after.startswith("$") or after.startswith("*"):
                    lines.append(after)
                    continue
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _parse_dependency_error(text: str) -> str | None:
        m = re.search(r"(?:ImportError|ModuleNotFoundError).*?['\"](\w+)['\"]", text)
        if m:
            return m.group(1)
        return None

    # ------------------------------------------------------------------
    # Output actions
    # ------------------------------------------------------------------
    def _on_copy_clicked(self) -> None:
        text = self._hash_output.toPlainText().strip()
        if text:
            QApplication.clipboard().setText(text)
            self._output_log.append("Copied to clipboard.")

    def _on_save_hash_clicked(self) -> None:
        text = self._hash_output.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Nothing to Save", "Run an extraction first.")
            return

        out_dir = str(self._default_output_dir())
        path, _ = QFileDialog.getSaveFileName(
            self, "Save extracted hash", out_dir,
            "Text Files (*.txt);;Hash Files (*.hash);;All Files (*)",
        )
        if not path:
            return

        Path(path).write_text(text, encoding="utf-8")
        self._output_path = path
        self._output_log.append(f"Saved to {path}")

    def _on_send_to_hashcat(self) -> None:
        """Save hash to file and navigate to Hashcat Command Builder."""
        text = self._hash_output.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Nothing to Send", "Run an extraction first.")
            return

        ext = self._selected_extractor
        if not ext or not ext.hashcat_modes:
            return

        # Use preferred mode (from dialog) or first mode as default
        mode = self._preferred_mode if self._preferred_mode is not None else ext.hashcat_modes[0]

        # Save hash to output directory
        out = self._default_output_dir() / "extracted_hash.txt"
        out.write_text(text, encoding="utf-8")
        self._output_path = str(out)

        # Write sidecar metadata for Hashcat Command Builder
        import json as _json
        meta = out.with_suffix(".txt.meta")
        meta.write_text(_json.dumps({
            "hashcat_mode": mode,
            "source": ext.name,
        }), encoding="utf-8")

        # Navigate via DataBus
        try:
            from ..app.data_bus import data_bus
            data_bus.send(
                source=self.MODULE_NAME,
                target="Hashcat Command Builder",
                path=str(out),
            )
            self._output_log.append(
                f"Sent hash to Hashcat Command Builder (mode -m {mode})."
            )
        except Exception:
            self._output_log.append(
                f"Hash saved to {out}. Open Hashcat Command Builder and load it manually."
            )

    def get_output_path(self) -> Optional[str]:
        return self._output_path
