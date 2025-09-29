from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QFont

from app.config import DEFAULT_IMAGE, THEME


class ImageService:
    def __init__(self) -> None:
        self._cache: Dict[str, QPixmap] = {}

    def _placeholder(self, size: QSize) -> QPixmap:
        w = max(size.width(), 1)
        h = max(size.height(), 1)
        image = QImage(w, h, QImage.Format.Format_ARGB32)
        image.fill(QColor(THEME["card"]))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.GlobalColor.transparent)
        painter.setBrush(QColor(THEME["accent"]))
        radius = int(min(w, h) * 0.18)
        painter.drawRoundedRect(int(w*0.15), int(h*0.15), int(w*0.7), int(h*0.7), radius, radius)
        painter.setPen(QColor(THEME["text"]))
        f = QFont()
        f.setPointSize(max(10, int(min(w, h) * 0.12)))
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "HomeChef")
        painter.end()
        return QPixmap.fromImage(image)

    def load(self, path: Optional[str | Path], size: QSize) -> QPixmap:
        key = f"{str(path) if path else 'default'}::{size.width()}x{size.height()}"
        if key in self._cache:
            return self._cache[key]
        pix = QPixmap()
        p = Path(path) if path else Path(DEFAULT_IMAGE)
        if p.exists():
            ok = pix.load(str(p))
            if not ok:
                pix = self._placeholder(size)
        else:
            pix = self._placeholder(size)
        if not pix.isNull():
            pix = pix.scaled(size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        self._cache[key] = pix
        return pix
