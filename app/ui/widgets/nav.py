from __future__ import annotations
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QToolButton


class NavList(QWidget):
    """Reusable vertical navigation list of buttons.

    Note: The main window builds its own nav, but this widget is kept for reuse and design consistency.
    """

    def __init__(self, items: list[tuple[str, callable]]) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.buttons: list[QToolButton] = []
        for text, callback in items:
            btn = QToolButton()
            btn.setObjectName("NavButton")
            btn.setText(text)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            btn.clicked.connect(callback)
            lay.addWidget(btn)
            self.buttons.append(btn)
        lay.addStretch(1)

    def set_active(self, index: int) -> None:
        for i, b in enumerate(self.buttons):
            b.setProperty("active", i == index)
            b.style().unpolish(b)
            b.style().polish(b)
