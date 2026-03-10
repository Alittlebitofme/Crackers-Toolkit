"""Sidebar with category tree, tool list, and global search."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .tool_registry import CATEGORIES, TOOLS, ToolInfo, get_tools_by_category, search_tools


class ToolCard(QFrame):
    """Clickable card representing a single tool in the sidebar."""

    clicked = pyqtSignal(int)  # module_id

    def __init__(self, tool: ToolInfo, parent=None) -> None:
        super().__init__(parent)
        self.tool = tool
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            ToolCard {
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px;
                margin: 2px 0;
            }
            ToolCard:hover {
                background-color: #3a3a5a;
                border-color: #7a7aff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        name_label = QLabel(f"★ {tool.name}")
        name_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(name_label)

        desc_label = QLabel(tool.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(desc_label)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tool.module_id)
        super().mousePressEvent(event)


class CategoryHeader(QFrame):
    """Clickable header that reveals / hides its tool list."""

    toggled_signal = pyqtSignal(str, bool)

    def __init__(self, name: str, icon: str, description: str, parent=None) -> None:
        super().__init__(parent)
        self.category_name = name
        self._expanded = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            CategoryHeader {
                padding: 6px 4px;
                border-bottom: 1px solid #444;
            }
            CategoryHeader:hover {
                background-color: #2a2a4a;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self._arrow = QLabel("▶")
        self._arrow.setFixedWidth(16)
        layout.addWidget(self._arrow)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        title = QLabel(f"{icon} {name}")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        text_layout.addWidget(title)
        desc = QLabel(description)
        desc.setStyleSheet("color: #999; font-size: 10px;")
        desc.setWordWrap(True)
        text_layout.addWidget(desc)
        layout.addLayout(text_layout, stretch=1)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._expanded = not self._expanded
            self._arrow.setText("▼" if self._expanded else "▶")
            self.toggled_signal.emit(self.category_name, self._expanded)
        super().mousePressEvent(event)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._arrow.setText("▼" if expanded else "▶")


class Sidebar(QWidget):
    """Main sidebar with search, categories, and tool cards."""

    tool_selected = pyqtSignal(int)  # module_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(260)
        self.setMaximumWidth(340)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Search bar
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 Search tools…")
        self._search.setToolTip("Filter tools by keyword across names, descriptions, and option names.")
        self._search.textChanged.connect(self._on_search)
        root.addWidget(self._search)

        # Scrollable category/tool area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(0)

        self._category_widgets: dict[str, tuple[CategoryHeader, QWidget]] = {}

        for cat in CATEGORIES:
            header = CategoryHeader(cat["name"], cat["icon"], cat["description"])
            header.toggled_signal.connect(self._on_category_toggled)
            self._container_layout.addWidget(header)

            tools_container = QWidget()
            tools_layout = QVBoxLayout(tools_container)
            tools_layout.setContentsMargins(12, 4, 4, 4)
            tools_layout.setSpacing(4)

            for tool in get_tools_by_category(cat["name"]):
                card = ToolCard(tool)
                card.clicked.connect(self._on_tool_clicked)
                tools_layout.addWidget(card)

            tools_container.setVisible(False)
            self._container_layout.addWidget(tools_container)
            self._category_widgets[cat["name"]] = (header, tools_container)

        self._container_layout.addStretch()
        scroll.setWidget(self._container)
        root.addWidget(scroll)

    def _on_category_toggled(self, name: str, expanded: bool) -> None:
        _, tools_widget = self._category_widgets[name]
        tools_widget.setVisible(expanded)

    def _on_tool_clicked(self, module_id: int) -> None:
        self.tool_selected.emit(module_id)

    def _on_search(self, text: str) -> None:
        if not text.strip():
            # Reset: collapse all, show all cards
            for name, (header, tools_widget) in self._category_widgets.items():
                header.setVisible(True)
                header.set_expanded(False)
                tools_widget.setVisible(False)
                for i in range(tools_widget.layout().count()):
                    item = tools_widget.layout().itemAt(i)
                    if item and item.widget():
                        item.widget().setVisible(True)
            return

        matches = search_tools(text)
        matched_ids = {t.module_id for t in matches}
        matched_cats = {t.category for t in matches}

        for name, (header, tools_widget) in self._category_widgets.items():
            if name in matched_cats:
                header.setVisible(True)
                header.set_expanded(True)
                tools_widget.setVisible(True)
                # Show/hide individual cards
                for i in range(tools_widget.layout().count()):
                    item = tools_widget.layout().itemAt(i)
                    w = item.widget() if item else None
                    if isinstance(w, ToolCard):
                        w.setVisible(w.tool.module_id in matched_ids)
            else:
                header.setVisible(False)
                tools_widget.setVisible(False)
