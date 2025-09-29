from __future__ import annotations
from typing import Callable, Optional

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QMessageBox,
)

from app.models.recipe import Recipe
from app.services.gemini_service import GeminiService
from app.services.async_worker import run_in_thread
from app.services.image_service import ImageService
from app.db import dao


class RecipeDetailPage(QWidget):
    def __init__(
        self,
        gemini: Optional[GeminiService],
        images: ImageService,
        on_start_cooking: Callable[[Optional[Recipe]], None],
        on_add_missing_to_grocery: Callable[[Recipe], None],
        on_toggle_favorite: Callable[[Recipe, bool], None],
    ) -> None:
        super().__init__()
        self.gemini = gemini
        self.images = images
        self.on_start_cooking = on_start_cooking
        self.on_add_missing_to_grocery = on_add_missing_to_grocery
        self.on_toggle_favorite = on_toggle_favorite
        self.recipe: Optional[Recipe] = None
        self._is_fav = False
        self._threads = []  # list[tuple[QThread, Worker]]

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Scroll container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        root.addWidget(scroll)

        lay = QVBoxLayout(content)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        # Header
        hdr = QFrame()
        hdr.setObjectName("Card")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(10, 10, 10, 10)
        hl.setSpacing(12)

        self.img = QLabel()
        self.img.setFixedSize(320, 180)
        self.img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(self.img, 0)

        txt = QVBoxLayout()
        self.title_lbl = QLabel("Recipe")
        self.title_lbl.setObjectName("Title")
        txt.addWidget(self.title_lbl)

        self.meta_lbl = QLabel("")
        self.meta_lbl.setObjectName("Subtitle")
        self.meta_lbl.setWordWrap(True)
        txt.addWidget(self.meta_lbl)

        btn_row = QHBoxLayout()
        self.cook_btn = QPushButton("Start Cooking")
        self.cook_btn.clicked.connect(lambda: self.on_start_cooking(self.recipe))
        btn_row.addWidget(self.cook_btn)

        self.missing_btn = QPushButton("Add Missing to Grocery")
        self.missing_btn.clicked.connect(self._on_add_missing)
        btn_row.addWidget(self.missing_btn)

        self.fav_btn = QPushButton("Favorite")
        self.fav_btn.clicked.connect(self._on_toggle_fav)
        btn_row.addWidget(self.fav_btn)

        self.subs_btn = QPushButton("Ask Substitutions (AI)")
        self.subs_btn.clicked.connect(self._on_substitutions)
        self.subs_btn.setEnabled(self.gemini is not None)
        btn_row.addWidget(self.subs_btn)

        btn_row.addStretch(1)
        txt.addLayout(btn_row)
        hl.addLayout(txt, 1)
        lay.addWidget(hdr)

        # Description
        self.desc_card = QFrame()
        self.desc_card.setObjectName("Card")
        dlay = QVBoxLayout(self.desc_card)
        dlay.setContentsMargins(10, 10, 10, 10)
        dlay.setSpacing(6)
        dtitle = QLabel("Description")
        dtitle.setObjectName("Title")
        dlay.addWidget(dtitle)
        self.desc_lbl = QLabel("")
        self.desc_lbl.setWordWrap(True)
        dlay.addWidget(self.desc_lbl)
        lay.addWidget(self.desc_card)

        # Ingredients
        self.ing_card = QFrame()
        self.ing_card.setObjectName("Card")
        ilay = QVBoxLayout(self.ing_card)
        ilay.setContentsMargins(10, 10, 10, 10)
        ilay.setSpacing(6)
        ititle = QLabel("Ingredients")
        ititle.setObjectName("Title")
        ilay.addWidget(ititle)
        self.ing_lbl = QLabel("")
        self.ing_lbl.setWordWrap(True)
        ilay.addWidget(self.ing_lbl)
        lay.addWidget(self.ing_card)

        # Steps
        self.step_card = QFrame()
        self.step_card.setObjectName("Card")
        slay = QVBoxLayout(self.step_card)
        slay.setContentsMargins(10, 10, 10, 10)
        slay.setSpacing(6)
        stitle = QLabel("Steps")
        stitle.setObjectName("Title")
        slay.addWidget(stitle)
        self.steps_lbl = QLabel("")
        self.steps_lbl.setWordWrap(True)
        slay.addWidget(self.steps_lbl)
        lay.addWidget(self.step_card)

        lay.addStretch(1)

    def set_recipe(self, recipe: Recipe) -> None:
        self.recipe = recipe
        # Load favorite state
        self._is_fav = False
        if recipe.id is not None:
            try:
                self._is_fav = recipe.id in set(dao.get_favorites())
            except Exception:
                self._is_fav = False
        self._update_fav_btn()

        self.title_lbl.setText(recipe.title)
        meta = f"{recipe.time_minutes} min • {recipe.difficulty or 'N/A'}"
        if recipe.categories:
            meta += f"\nCategories: {', '.join(recipe.categories)}"
        self.meta_lbl.setText(meta)

        pix = self.images.load(recipe.image_path, QSize(320, 180))
        self.img.setPixmap(pix)

        self.desc_lbl.setText(recipe.description or "")
        self.ing_lbl.setText("\n".join([f"• {i.get('name','')} — {i.get('quantity','')}" for i in recipe.ingredients]))
        self.steps_lbl.setText("\n\n".join([f"{idx+1}. {s}" for idx, s in enumerate(recipe.steps)]))

    def _update_fav_btn(self) -> None:
        self.fav_btn.setText("Unfavorite" if self._is_fav else "Favorite")

    def _on_add_missing(self) -> None:
        if not self.recipe:
            return
        self.on_add_missing_to_grocery(self.recipe)

    def _on_toggle_fav(self) -> None:
        if not self.recipe:
            return
        if self.recipe.id is None:
            QMessageBox.information(self, "Favorites", "Only saved recipes can be favorited.")
            return
        self._is_fav = not self._is_fav
        self.on_toggle_favorite(self.recipe, self._is_fav)
        self._update_fav_btn()

    def _on_substitutions(self) -> None:
        if self.gemini is None:
            QMessageBox.warning(self, "AI Unavailable", "Gemini API key is not set. Configure .env and restart.")
            return
        if not self.recipe:
            return
        missing = dao.compute_missing_ingredients(self.recipe)
        if not missing:
            QMessageBox.information(self, "Substitutions", "You have all ingredients in your pantry!")
            return
        # Background call
        self.subs_btn.setEnabled(False)
        old_txt = self.subs_btn.text()
        self.subs_btn.setText("Asking…")
        thread, worker = run_in_thread(self.gemini.substitutions_for_recipe, self.recipe, missing)

        def on_result(subs: list[str]):
            if not subs:
                QMessageBox.information(self, "Substitutions", "No suggestions found.")
            else:
                QMessageBox.information(self, "Substitutions", "\n".join([f"• {s}" for s in subs]))

        worker.result.connect(on_result)

        def on_done():
            self.subs_btn.setEnabled(True)
            self.subs_btn.setText(old_txt)
            # remove job and clean thread
            to_remove = None
            for job in self._threads:
                if isinstance(job, tuple) and job and job[0] is thread:
                    to_remove = job
                    break
            if to_remove is not None:
                self._threads.remove(to_remove)
            thread.quit()
            thread.wait()

        worker.finished.connect(on_done)
        worker.error.connect(lambda e: QMessageBox.warning(self, "AI Error", str(e)))
        thread.start()
        self._threads.append((thread, worker))
