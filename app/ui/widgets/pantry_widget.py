from __future__ import annotations
from typing import List, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QMessageBox,
)

from app.db import dao


class PantryWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Add/Update form
        form = QFrame()
        form.setObjectName("Card")
        fl = QVBoxLayout(form)
        fl.setContentsMargins(10, 10, 10, 10)
        fl.setSpacing(8)

        title = QLabel("Pantry")
        title.setObjectName("Title")
        fl.addWidget(title)
        subtitle = QLabel("Add items you currently have. These will be used to compute missing ingredients for recipes.")
        subtitle.setObjectName("Subtitle")
        fl.addWidget(subtitle)

        row = QHBoxLayout()
        self.item_edit = QLineEdit()
        self.item_edit.setPlaceholderText("Item name (e.g., Eggs)")
        row.addWidget(self.item_edit, 2)
        self.qty_edit = QLineEdit()
        self.qty_edit.setPlaceholderText("Quantity (optional)")
        row.addWidget(self.qty_edit, 1)
        self.add_btn = QPushButton("Add / Update")
        self.add_btn.clicked.connect(self._on_add)
        row.addWidget(self.add_btn)
        fl.addLayout(row)

        root.addWidget(form)

        # List
        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 10, 10, 10)
        cl.setSpacing(8)
        ltitle = QLabel("Pantry Items")
        ltitle.setObjectName("Title")
        cl.addWidget(ltitle)

        self.list = QListWidget()
        cl.addWidget(self.list, 1)

        controls = QHBoxLayout()
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self._on_remove_selected)
        controls.addWidget(self.remove_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        controls.addWidget(self.refresh_btn)

        controls.addStretch(1)
        cl.addLayout(controls)
        root.addWidget(card, 1)

        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        items: List[Tuple[str, str]] = dao.list_pantry()
        for item, qty in items:
            txt = f"{item} — {qty}" if qty else item
            it = QListWidgetItem(txt)
            it.setData(Qt.ItemDataRole.UserRole, (item, qty))
            self.list.addItem(it)

    def _on_add(self) -> None:
        item = self.item_edit.text().strip()
        qty = self.qty_edit.text().strip()
        if not item:
            QMessageBox.information(self, "Pantry", "Please provide an item name.")
            return
        dao.upsert_pantry_item(item, qty)
        self.item_edit.clear()
        self.qty_edit.clear()
        self.refresh()

    def _on_remove_selected(self) -> None:
        row = self.list.currentRow()
        if row < 0:
            return
        data = self.list.item(row).data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        item, _qty = data
        dao.remove_pantry_item(item)
        self.refresh()
