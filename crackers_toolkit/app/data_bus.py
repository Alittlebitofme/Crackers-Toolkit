"""Cross-module data transfer bus ('Send to…' / 'Receive from…' system).

Singleton that routes output paths between modules.  When a module
produces output, it calls ``data_bus.send(source, target, path)``.
The bus resolves the target module and calls ``receive_from(path)`` on it.
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal


class DataBus(QObject):
    """Global event bus for transferring file paths between modules."""

    # signal: (source_name, target_name, path)
    transfer_requested = pyqtSignal(str, str, str)
    # Emitted after a successful send so main window can navigate to the target
    navigate_to_tool = pyqtSignal(str)  # target tool name
    # Broadcast: trained PCFG rulesets on disk have changed
    rulesets_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._receivers: dict[str, Callable[[str], None]] = {}
        # Lazy-loader callback set by MainWindow to load modules on demand
        self._ensure_loaded: Optional[Callable[[str], None]] = None

    def register(self, tool_name: str, callback: Callable[[str], None]) -> None:
        """Register a module as a potential receiver."""
        self._receivers[tool_name] = callback

    def unregister(self, tool_name: str) -> None:
        self._receivers.pop(tool_name, None)

    def send(self, source: str, target: str, path: str) -> None:
        """Send an output path from *source* module to *target* module."""
        self.transfer_requested.emit(source, target, path)
        # If target not yet loaded, ask main window to load it first
        if target not in self._receivers and self._ensure_loaded:
            self._ensure_loaded(target)
        cb = self._receivers.get(target)
        if cb:
            cb(path)
            self.navigate_to_tool.emit(target)

    def get_registered_targets(self) -> list[str]:
        return list(self._receivers.keys())


# Singleton instance used application-wide
data_bus = DataBus()
