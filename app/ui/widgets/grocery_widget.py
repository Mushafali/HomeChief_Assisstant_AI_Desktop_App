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
    QFileDialog,
)

from app.db import dao
from app.services.export_service import ExportService


class GroceryWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._changing = False  # guard against re-entrant itemChanged
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Add form
        form = QFrame()
        form.setObjectName("Card")
        fl = QVBoxLayout(form)
        fl.setContentsMargins(10, 10, 10, 10)
        fl.setSpacing(8)

        title = QLabel("Grocery List")
        title.setObjectName("Title")
        fl.addWidget(title)
        subtitle = QLabel("Items missing from recipes or added manually. Check off purchased items and export or copy the list.")
        subtitle.setObjectName("Subtitle")
        fl.addWidget(subtitle)

        row = QHBoxLayout()
        self.item_edit = QLineEdit()
        self.item_edit.setPlaceholderText("Item name (e.g., Butter)")
        row.addWidget(self.item_edit, 2)
        self.qty_edit = QLineEdit()
        self.qty_edit.setPlaceholderText("Quantity (optional)")
        row.addWidget(self.qty_edit, 1)
        add_btn = QPushButton("Add / Update")
        add_btn.clicked.connect(self._on_add)
        row.addWidget(add_btn)
        fl.addLayout(row)

        root.addWidget(form)

        # List & controls
        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 10, 10, 10)
        cl.setSpacing(8)

        ltitle = QLabel("Your Grocery Items")
        ltitle.setObjectName("Title")
        cl.addWidget(ltitle)

        self.list = QListWidget()
        self.list.itemChanged.connect(self._on_item_changed)
        cl.addWidget(self.list, 1)

        controls = QHBoxLayout()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh)
        controls.addWidget(btn_refresh)

        btn_clear_checked = QPushButton("Clear Checked")
        btn_clear_checked.clicked.connect(lambda: self._clear(True))
        controls.addWidget(btn_clear_checked)

        btn_clear_all = QPushButton("Clear All")
        btn_clear_all.clicked.connect(lambda: self._clear(False))
        controls.addWidget(btn_clear_all)

        btn_copy = QPushButton("Copy to Clipboard")
        btn_copy.clicked.connect(self._copy)
        controls.addWidget(btn_copy)

        btn_export = QPushButton("Export to File")
        btn_export.clicked.connect(self._export)
        controls.addWidget(btn_export)

        controls.addStretch(1)
        cl.addLayout(controls)
        root.addWidget(card, 1)

        self.refresh()

    def refresh(self) -> None:
        self.list.blockSignals(True)
        try:
            self.list.clear()
            items: List[Tuple[str, str, bool]] = dao.list_grocery()
            for item, qty, checked in items:
                text = f"{item} — {qty}" if qty else item
                it = QListWidgetItem(text)
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEditable)
                it.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                it.setData(Qt.ItemDataRole.UserRole, (item, qty))
                self.list.addItem(it)
        finally:
            self.list.blockSignals(False)

    def _on_add(self) -> None:
        item = self.item_edit.text().strip()
        qty = self.qty_edit.text().strip()
        if not item:
            return
        dao.upsert_grocery_item(item, qty, False)
        self.item_edit.clear()
        self.qty_edit.clear()
        self.refresh()

    def _on_item_changed(self, it: QListWidgetItem) -> None:
        if self._changing:
            return
        data = it.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        old_item, _old_qty = data
        # Extract current text back into item and optional qty if user edited;
        # if format contains a dash, split; else keep old qty
        txt = it.text()
        item = txt
        qty = ""
        if "—" in txt:
            parts = [p.strip() for p in txt.split("—", 1)]
            item = parts[0]
            qty = parts[1] if len(parts) > 1 else ""
        checked = it.checkState() == Qt.CheckState.Checked
        try:
            self._changing = True
            # Update DB: since item is UNIQUE, we should remove old and add new if renamed
            if item != old_item:
                dao.remove_grocery_item(old_item)
            dao.upsert_grocery_item(item, qty, checked)
            # Avoid re-entrant signals while updating user data
            self.list.blockSignals(True)
            it.setData(Qt.ItemDataRole.UserRole, (item, qty))
        except Exception:
            # Best-effort rollback display to old values
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Grocery", "Failed to update item. Please try again.")
        finally:
            self.list.blockSignals(False)
            self._changing = False

    def _clear(self, only_checked: bool) -> None:
        dao.clear_grocery(only_checked)
        self.refresh()

    def _copy(self) -> None:
        lines: List[str] = []
        for i in range(self.list.count()):
            it = self.list.item(i)
            state = "[x]" if it.checkState() == Qt.CheckState.Checked else "[ ]"
            lines.append(f"{state} {it.text()}")
        ExportService.to_clipboard("\n".join(lines))

    def _export(self) -> None:
        fn, _ = QFileDialog.getSaveFileName(self, "Export Grocery List", "grocery_list.txt", "Text Files (*.txt)")
        if not fn:
            return
        lines: List[str] = []
        for i in range(self.list.count()):
            it = self.list.item(i)
            state = "[x]" if it.checkState() == Qt.CheckState.Checked else "[ ]"
            lines.append(f"{state} {it.text()}")
        ExportService.to_text_file(fn, lines)
