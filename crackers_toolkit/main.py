"""Entry point for Cracker's Toolkit GUI."""

import faulthandler
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QProxyStyle, QStyle

from crackers_toolkit.app.main_window import MainWindow


def _find_logo() -> Path | None:
    """Locate logo.png in resources (works both frozen and source)."""
    base = Path(__file__).resolve().parent
    logo = base / "resources" / "logo.png"
    if logo.is_file():
        return logo
    # PyInstaller _MEIPASS fallback
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        logo = Path(meipass) / "crackers_toolkit" / "resources" / "logo.png"
        if logo.is_file():
            return logo
    return None


def _find_icon() -> Path | None:
    """Locate icon.ico in resources."""
    base = Path(__file__).resolve().parent
    ico = base / "resources" / "icon.ico"
    if ico.is_file():
        return ico
    # PyInstaller _MEIPASS fallback
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        ico = Path(meipass) / "crackers_toolkit" / "resources" / "icon.ico"
        if ico.is_file():
            return ico
    return None


class _InstantTooltipStyle(QProxyStyle):
    """Override tooltip delays so they appear instantly."""
    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint in (QStyle.StyleHint.SH_ToolTip_WakeUpDelay,
                    QStyle.StyleHint.SH_ToolTip_FallAsleepDelay):
            return 0
        return super().styleHint(hint, option, widget, returnData)


def main() -> None:
    # Tell Windows this is its own app (critical for taskbar icon)
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "CrackersToolkit.CrackersToolkit.1"
        )

    # Write C-level crash tracebacks to a log file for debugging
    _crash_log = open(Path(sys.executable).parent / "crash.log" if getattr(sys, 'frozen', False) else "crash.log", "w")
    faulthandler.enable(file=_crash_log)

    app = QApplication(sys.argv)
    app.setStyle(_InstantTooltipStyle())
    app.setApplicationName("Cracker's Toolkit")
    app.setOrganizationName("CrackersToolkit")

    # ── App icon (taskbar, title bar, Alt-Tab) ──────────────
    logo_path = _find_logo()
    icon_path = _find_icon()
    app_icon = QIcon()
    if icon_path:
        # addFile loads all sizes from the ICO automatically
        app_icon.addFile(str(icon_path))
    if logo_path:
        # Also add the high-res PNG as a fallback / extra size
        app_icon.addFile(str(logo_path))
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    # ── Splash screen ──────────────────────────────────────
    splash = None
    if logo_path:
        pixmap = QPixmap(str(logo_path)).scaled(
            420, 420, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        splash = QLabel()
        splash.setPixmap(pixmap)
        splash.setAlignment(Qt.AlignmentFlag.AlignCenter)
        splash.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        splash.setStyleSheet("background: #1e1e2e; padding: 30px;")
        splash.adjustSize()
        # Centre on screen
        screen = app.primaryScreen()
        if screen:
            geo = screen.geometry()
            splash.move(
                geo.center().x() - splash.width() // 2,
                geo.center().y() - splash.height() // 2,
            )
        splash.show()
        app.processEvents()

    # Determine workspace base directory (where this repo lives)
    if getattr(sys, 'frozen', False):
        # Frozen exe: walk up from exe location to find the workspace root
        exe_dir = Path(sys.executable).resolve().parent
        # dist/CrackersToolkit/CrackersToolkit.exe -> workspace is 2 levels up
        base_dir = exe_dir.parent.parent
    else:
        base_dir = Path(__file__).resolve().parent.parent

    window = MainWindow(base_dir=base_dir)

    # Close splash after a short delay and show the main window
    def _finish_splash():
        if splash:
            splash.close()
        window.show()

    if splash:
        QTimer.singleShot(1800, _finish_splash)
    else:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
