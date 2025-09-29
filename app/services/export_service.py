from __future__ import annotations
from pathlib import Path
from typing import Iterable

from PyQt6.QtWidgets import QApplication


class ExportService:
    @staticmethod
    def to_text_file(path: str | Path, lines: Iterable[str]) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(str(line).rstrip() + "\n")
        return p

    @staticmethod
    def to_clipboard(text: str) -> None:
        app = QApplication.instance()
        if app is None:
            # Clipboard requires a Qt app context; silently no-op if absent
            return
        cb = app.clipboard()
        cb.setText(text)
