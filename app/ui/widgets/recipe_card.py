from __future__ import annotations
from typing import Callable, Optional, Set

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QFrame,
    QToolButton,
)

from app.models.recipe import Recipe
from app.services.image_service import ImageService
from app.config import THEME


class RecipeCard(QFrame):
    def __init__(
        self,
        recipe: Recipe,
        images: ImageService,
        on_open: Callable[[Recipe], None],
        on_toggle_favorite: Optional[Callable[[Recipe, bool], None]] = None,
        on_save_ai_idea: Optional[Callable[[Recipe], None]] = None,
        favorites: Optional[Set[int]] = None,
        is_ai_idea: bool = False,
    ) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.recipe = recipe
        self.on_open = on_open
        self.on_toggle_favorite = on_toggle_favorite
        self.is_ai_idea = is_ai_idea
        self.on_save_ai_idea = on_save_ai_idea
        self._is_fav = bool(recipe.id and favorites and recipe.id in favorites)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        # Image
        self.img = QLabel()
        self.img.setFixedHeight(140)
        self.img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.img)

        # Title
        title = QLabel(recipe.title)
        title.setObjectName("Title")
        title.setWordWrap(True)
        lay.addWidget(title)

        # Subtitle
        subtitle = QLabel(
            f"{recipe.time_minutes} min • {recipe.difficulty or 'N/A'}" +
            (f"\nCategories: {', '.join(recipe.categories)}" if recipe.categories else "")
        )
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        lay.addWidget(subtitle)

        # Controls
        row = QHBoxLayout()
        open_btn = QPushButton("Open")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.clicked.connect(lambda: self.on_open(self.recipe))
        row.addWidget(open_btn, 1)

        if not is_ai_idea:
            fav_btn = QToolButton()
            fav_btn.setText("★" if self._is_fav else "☆")
            fav_btn.setToolTip("Toggle favorite")
            fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            fav_btn.clicked.connect(self._toggle_fav_clicked)
            row.addWidget(fav_btn, 0)
            self.fav_btn = fav_btn
        else:
            badge = QLabel("AI Idea")
            badge.setStyleSheet(f"color: #fff; background-color: {THEME['accent']}; padding: 3px 8px; border-radius: 6px;")
            row.addWidget(badge, 0)
            if self.on_save_ai_idea is not None:
                save_btn = QToolButton()
                save_btn.setText("Add to Library")
                save_btn.setToolTip("Save this AI idea as a new recipe")
                save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                save_btn.clicked.connect(lambda: self.on_save_ai_idea(self.recipe))
                row.addWidget(save_btn, 0)

        lay.addLayout(row)

        # Load image
        pix: QPixmap = images.load(self.recipe.image_path, QSize(320, 180))
        self.img.setPixmap(pix)

    def _toggle_fav_clicked(self) -> None:
        if self.recipe.id is None:
            return
        self._is_fav = not self._is_fav
        if hasattr(self, 'fav_btn'):
            self.fav_btn.setText("★" if self._is_fav else "☆")
        if self.on_toggle_favorite:
            self.on_toggle_favorite(self.recipe, self._is_fav)
