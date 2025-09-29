from __future__ import annotations
from PyQt6.QtWidgets import QApplication

from app.config import THEME


def apply_theme(app: QApplication) -> None:
    t = THEME
    qss = f"""
    QWidget {{
        background-color: {t['bg']};
        color: {t['text']};
        selection-background-color: {t['accent']};
    }}
    QMainWindow, QDialog {{
        background-color: {t['bg']};
    }}
    QFrame#Card {{
        background-color: {t['card']};
        border-radius: 10px;
        border: 1px solid #2C2C2C;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{
        background-color: {t['bg_elev']};
        border: 1px solid #333;
        border-radius: 8px;
        padding: 6px 8px;
        color: {t['text']};
    }}
    QPushButton {{
        background-color: {t['accent']};
        color: #fff;
        border-radius: 8px;
        padding: 8px 12px;
        font-weight: 600;
    }}
    QPushButton[flat="true"] {{
        background-color: transparent;
        color: {t['text']};
        border: none;
        padding: 6px 8px;
    }}
    QPushButton:disabled {{
        background-color: #444;
        color: #999;
    }}
    QToolButton {{
        background-color: transparent;
        border: none;
        color: {t['text']};
        padding: 8px;
    }}
    QToolButton#NavButton {{
        text-align: left;
        background-color: transparent;
        border-radius: 6px;
    }}
    QToolButton#NavButton:hover {{
        background-color: {t['bg_elev']};
    }}
    QToolButton#NavButton[active="true"] {{
        background-color: {t['accent']};
        color: #fff;
    }}
    QListWidget, QTreeWidget, QTableWidget, QScrollArea {{
        background-color: {t['bg_elev']};
        border: 1px solid #333;
        border-radius: 8px;
    }}
    QScrollBar:vertical {{
        background: {t['bg_elev']};
        width: 10px;
        margin: 0px 0px 0px 0px;
    }}
    QScrollBar::handle:vertical {{
        background: #444;
        min-height: 20px;
        border-radius: 5px;
    }}
    QLabel#Title {{
        font-size: 18px;
        font-weight: 700;
    }}
    QLabel#Subtitle {{
        font-size: 13px;
        color: {t['muted']};
    }}
    """
    app.setStyleSheet(qss)
