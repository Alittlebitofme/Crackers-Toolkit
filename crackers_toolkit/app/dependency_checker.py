"""First-run dependency checker dialog.

Verifies that external tools are available and guides the user
through resolving any missing requirements.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .settings import Settings

# ── Check result ────────────────────────────────────────────

class _CheckResult(NamedTuple):
    name: str
    found: bool
    detail: str       # path or reason
    required: bool    # True = many modules need it
    hint: str         # guidance when missing


# ── Detection helpers ───────────────────────────────────────

def _check_hashcat(base: Path, settings: Settings) -> _CheckResult:
    hp = settings.get("hashcat_path")
    if hp and Path(hp).is_file():
        return _CheckResult("hashcat", True, hp, True, "")
    for name in ("hashcat.exe", "hashcat.bin", "hashcat"):
        for p in base.glob(f"hashcat-*/{name}"):
            return _CheckResult("hashcat", True, str(p), True, "")
    if shutil.which("hashcat"):
        return _CheckResult("hashcat", True, "on PATH", True, "")
    return _CheckResult(
        "hashcat", False, "not found", True,
        "Place hashcat folder next to the application or set\n"
        "the path in Settings → Hashcat binary.",
    )


def _check_jtr(base: Path) -> _CheckResult:
    for d in sorted(base.iterdir()) if base.is_dir() else []:
        if d.is_dir() and d.name.lower().startswith("john") and (d / "run").is_dir():
            return _CheckResult("John the Ripper", True, str(d / "run"), False, "")
    return _CheckResult(
        "John the Ripper", False, "not found", False,
        "Place a John the Ripper folder next to the application.\n"
        "Used by Hash Extractor for *2john extraction tools.",
    )


def _check_python(settings: Settings) -> _CheckResult:
    py = settings.get("python_path") or "python"
    # Don't test sys.executable – that's the frozen exe in PyInstaller
    if py and py != "python":
        if Path(py).is_file():
            return _CheckResult("Python 3 (external)", True, py, True, "")
    # Try bare "python" on PATH
    try:
        r = subprocess.run(
            ["python", "--version"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        if r.returncode == 0 and "Python 3" in r.stdout:
            return _CheckResult("Python 3 (external)", True, r.stdout.strip(), True, "")
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return _CheckResult(
        "Python 3 (external)", False, "not found", True,
        "Install Python 3.12+ from https://www.python.org/downloads/\n"
        "and ensure it is on PATH, or set the path in\n"
        "Settings → Python interpreter.\n"
        "Needed by: PCFG Guesser, PCFG Trainer, demeuk Cleaner.",
    )


def _check_prince(base: Path, settings: Settings) -> _CheckResult:
    pp = settings.get("prince_path")
    if pp and Path(pp).is_file():
        return _CheckResult("PRINCE Processor", True, pp, False, "")
    src_ext = {".c", ".h", ".py", ".txt", ".md"}
    for name in ("pp64.exe", "pp.exe", "pp64.bin", "pp.bin", "pp"):
        for p in base.glob(f"Scripts_to_use/princeprocessor-master/**/{name}"):
            if p.suffix.lower() not in src_ext:
                return _CheckResult("PRINCE Processor", True, str(p), False, "")
    return _CheckResult(
        "PRINCE Processor", False, "not found", False,
        "Place the compiled pp64 binary inside\n"
        "Scripts_to_use/princeprocessor-master/\n"
        "or set the path in Settings → PRINCE binary.",
    )


def _check_perl() -> _CheckResult:
    if shutil.which("perl"):
        try:
            r = subprocess.run(
                ["perl", "-v"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            if r.returncode == 0:
                return _CheckResult("Perl", True, "on PATH", False, "")
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
    return _CheckResult(
        "Perl", False, "not found", False,
        "Only needed for JtR Perl-based *2john scripts.\n"
        "Install Strawberry Perl from https://strawberryperl.com/\n"
        "These extractors are gracefully disabled without Perl.",
    )


# ── Public API ──────────────────────────────────────────────

def run_checks(base: Path, settings: Settings) -> list[_CheckResult]:
    """Return dependency check results for all external tools."""
    return [
        _check_hashcat(base, settings),
        _check_jtr(base),
        _check_python(settings),
        _check_prince(base, settings),
        _check_perl(),
    ]


# ── Dialog ──────────────────────────────────────────────────

class DependencyDialog(QDialog):
    """Shows a dependency status overview with pass/fail indicators."""

    _CSS = """
        QDialog { background: #1e1e2e; }
        QLabel { color: #cdd6f4; }
        QLabel#title { font-size: 18px; font-weight: bold; }
        QLabel#subtitle { color: #a6adc8; font-size: 12px; }
        QLabel#ok { color: #a6e3a1; font-weight: bold; font-size: 14px; }
        QLabel#fail { color: #f38ba8; font-weight: bold; font-size: 14px; }
        QLabel#name { font-size: 13px; font-weight: bold; }
        QLabel#detail { color: #a6adc8; font-size: 11px; }
        QLabel#hint { color: #fab387; font-size: 11px; }
        QPushButton { background: #45475a; color: #cdd6f4; border: 1px solid #585b70;
                      border-radius: 4px; padding: 6px 18px; font-size: 12px; }
        QPushButton:hover { background: #585b70; }
        QPushButton#primary { background: #89b4fa; color: #1e1e2e; font-weight: bold; }
        QPushButton#primary:hover { background: #74c7ec; }
    """

    def __init__(self, results: list[_CheckResult], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Dependency Check")
        self.setMinimumWidth(520)
        self.setStyleSheet(self._CSS)
        self._build(results)

    def _build(self, results: list[_CheckResult]) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        title = QLabel("Dependency Check")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        all_ok = all(r.found for r in results)
        missing_required = any(not r.found and r.required for r in results)

        if all_ok:
            sub = QLabel("All external tools detected — you're good to go!")
            sub.setObjectName("subtitle")
        elif missing_required:
            sub = QLabel("Some required tools are missing. See details below.")
            sub.setObjectName("subtitle")
        else:
            sub = QLabel("Optional tools missing — core features will still work.")
            sub.setObjectName("subtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(sub)

        # Scrollable list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        inner = QWidget()
        col = QVBoxLayout(inner)
        col.setSpacing(10)

        for r in results:
            row = QHBoxLayout()
            row.setSpacing(8)

            icon = QLabel("✓" if r.found else "✗")
            icon.setObjectName("ok" if r.found else "fail")
            icon.setFixedWidth(22)
            row.addWidget(icon)

            info = QVBoxLayout()
            info.setSpacing(2)

            label = f"{r.name}"
            if not r.found and r.required:
                label += "  (required)"
            elif not r.found:
                label += "  (optional)"
            nm = QLabel(label)
            nm.setObjectName("name")
            info.addWidget(nm)

            det = QLabel(r.detail)
            det.setObjectName("detail")
            det.setWordWrap(True)
            info.addWidget(det)

            if not r.found and r.hint:
                h = QLabel(r.hint)
                h.setObjectName("hint")
                h.setWordWrap(True)
                info.addWidget(h)

            row.addLayout(info, 1)
            col.addLayout(row)

        col.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        recheck = QPushButton("Re-check")
        recheck.clicked.connect(lambda: self.done(2))  # custom code = re-run
        btn_row.addWidget(recheck)

        ok = QPushButton("Continue")
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        ok.setDefault(True)
        btn_row.addWidget(ok)

        root.addLayout(btn_row)
