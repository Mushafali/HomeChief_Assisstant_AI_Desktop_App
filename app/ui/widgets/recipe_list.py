from __future__ import annotations
from typing import Callable, List, Optional, Set

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QScrollArea,
    QLineEdit,
    QPushButton,
    QLabel,
    QSpinBox,
    QComboBox,
    QPlainTextEdit,
    QFrame,
    QMessageBox,
)

from app.db import dao
from app.models.recipe import Recipe
from app.services.gemini_service import GeminiService
from app.services.image_service import ImageService
from app.services.async_worker import run_in_thread
from .recipe_card import RecipeCard


class RecipeListPage(QWidget):
    def __init__(self, gemini: Optional[GeminiService], images: ImageService, on_open_detail: Callable[[Recipe], None]) -> None:
        super().__init__()
        self.gemini = gemini
        self.images = images
        self.on_open_detail = on_open_detail
        self.recipes: List[Recipe] = []
        self.favorites: Set[int] = set()
        # Keep references to background threads and workers to avoid premature GC
        self._threads = []  # list[tuple[QThread, Worker]]

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Search bar
        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search recipes (title, description)...")
        search_row.addWidget(self.search_edit, 2)

        self.diff_combo = QComboBox()
        self.diff_combo.addItem("Any difficulty", "")
        self.diff_combo.addItems(["Easy", "Medium", "Hard"])
        search_row.addWidget(self.diff_combo, 0)

        self.max_time = QSpinBox()
        self.max_time.setRange(0, 300)
        self.max_time.setPrefix("<= ")
        self.max_time.setSuffix(" min")
        self.max_time.setToolTip("Max time (0 for any)")
        search_row.addWidget(self.max_time, 0)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._on_search)
        search_row.addWidget(self.search_btn, 0)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._on_clear)
        search_row.addWidget(self.clear_btn, 0)

        root.addLayout(search_row)

        # AI suggestions
        ai_card = QFrame()
        ai_card.setObjectName("Card")
        ai_lay = QVBoxLayout(ai_card)
        ai_lay.setContentsMargins(10, 10, 10, 10)
        ai_lay.setSpacing(8)
        title = QLabel("Smart Recipe Suggestions (AI)")
        title.setObjectName("Title")
        ai_lay.addWidget(title)
        subtitle = QLabel("Enter available ingredients (comma-separated), then click 'Suggest'.")
        subtitle.setObjectName("Subtitle")
        ai_lay.addWidget(subtitle)
        self.ing_edit = QPlainTextEdit()
        self.ing_edit.setPlaceholderText("eg. flour, eggs, sugar")
        self.ing_edit.setFixedHeight(60)
        ai_lay.addWidget(self.ing_edit)

        ai_btn_row = QHBoxLayout()
        self.suggest_btn = QPushButton("Suggest with AI")
        self.suggest_btn.clicked.connect(self._on_suggest)
        self.suggest_btn.setEnabled(self.gemini is not None)
        self.suggest_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ai_btn_row.addWidget(self.suggest_btn)
        ai_btn_row.addStretch(1)
        ai_lay.addLayout(ai_btn_row)

        root.addWidget(ai_card)

        # Results area inside scroll
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        self.scroll.setWidget(self.container)

        root.addWidget(self.scroll, 1)

        # Headings for sections
        self.header_matches = QLabel("Matches")
        self.header_matches.setObjectName("Title")
        self.header_ai = QLabel("AI Ideas")
        self.header_ai.setObjectName("Title")

        self._clear_cards()

    def load_recipes(self, recipes: List[Recipe], favorites: Set[int]) -> None:
        self.recipes = recipes
        self.favorites = favorites
        # Default view is full list
        self._render_cards(recipes, [], [])

    # ----- UI helpers -----
    def _clear_cards(self) -> None:
        # remove all children from grid
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

    def _render_cards(self, items: List[Recipe], match_items: List[Recipe], ai_ideas: List[Recipe]) -> None:
        self._clear_cards()
        col_count = 3
        row = 0
        col = 0

        def add_card(rec: Recipe, is_ai: bool = False):
            nonlocal row, col
            card = RecipeCard(
                rec,
                self.images,
                self.on_open_detail,
                on_toggle_favorite=self._toggle_favorite,
                on_save_ai_idea=self._save_ai_idea if is_ai else None,
                favorites=self.favorites,
                is_ai_idea=is_ai,
            )
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= col_count:
                col = 0
                row += 1

        # If match_items or ai_ideas present, show them first with headers
        if match_items:
            self.grid.addWidget(self.header_matches, row, 0, 1, col_count)
            row += 1
            col = 0
            for r in match_items:
                add_card(r, is_ai=False)
            if col != 0:
                row += 1
                col = 0

        if ai_ideas:
            self.grid.addWidget(self.header_ai, row, 0, 1, col_count)
            row += 1
            col = 0
            for r in ai_ideas:
                add_card(r, is_ai=True)
            if col != 0:
                row += 1
                col = 0

        # Remaining regular items
        for r in items:
            add_card(r, is_ai=False)

        self.container.adjustSize()

    # ----- Event handlers -----
    def _on_search(self) -> None:
        text = self.search_edit.text().strip()
        difficulty = str(self.diff_combo.currentText())
        if difficulty == "Any difficulty":
            difficulty = ""
        max_t = self.max_time.value() or None
        results = dao.search_recipes(text, None, max_t, difficulty)
        self._render_cards(results, [], [])

    def _on_clear(self) -> None:
        self.search_edit.clear()
        self.max_time.setValue(0)
        self.diff_combo.setCurrentIndex(0)
        self._render_cards(self.recipes, [], [])

    def _on_suggest(self) -> None:
        if self.gemini is None:
            QMessageBox.warning(self, "AI Unavailable", "Gemini API key is not set. Configure .env and restart.")
            return
        raw = self.ing_edit.toPlainText().strip()
        ings = [p.strip() for p in raw.split(",") if p.strip()]
        if not ings:
            QMessageBox.information(self, "Smart Suggestions", "Please enter at least one ingredient.")
            return
        # Run in background to keep UI responsive
        self.suggest_btn.setEnabled(False)
        old_text = self.suggest_btn.text()
        self.suggest_btn.setText("Suggesting…")
        thread, worker = run_in_thread(self.gemini.suggest_from_ingredients, ings, self.recipes)

        def on_result(data):
            match_titles = [str(t) for t in data.get("match_titles", [])]
            ideas_raw = data.get("ideas", [])
            matched = dao.find_recipes_by_titles(match_titles)
            ai_ideas: List[Recipe] = []
            for idea in ideas_raw:
                try:
                    rec = Recipe(
                        title=idea.get("title", "AI Idea"),
                        description=idea.get("description", ""),
                        ingredients=idea.get("ingredients", []),
                        steps=idea.get("steps", []),
                        time_minutes=int(idea.get("time_minutes", 0) or 0),
                        difficulty=str(idea.get("difficulty", "Easy")),
                        image_path="",
                        categories=idea.get("categories", []),
                    )
                    ai_ideas.append(rec)
                except Exception:
                    continue
            # If no results, try a local matching fallback first
            if not matched and not ai_ideas:
                terms = [t.lower() for t in ings]
                scored: List[tuple[int, Recipe]] = []
                for r in self.recipes:
                    names = [str(ing.get("name", "")).lower() for ing in r.ingredients]
                    score = 0
                    for t in terms:
                        if not t:
                            continue
                        if any(t in n for n in names):
                            score += 1
                    if score > 0:
                        scored.append((score, r))
                scored.sort(key=lambda x: (-x[0], x[1].title.lower()))
                local_matches = [r for _s, r in scored[:12]]
                if local_matches:
                    QMessageBox.information(self, "Smart Suggestions", "AI unavailable. Showing local matches based on your ingredients.")
                    self._render_cards(self.recipes, local_matches, [])
                    return
                # Else, include any raw AI text if present
                raw_text = str(data.get("raw", "")).strip()
                if raw_text:
                    ai_ideas.append(Recipe(title="AI Suggestion", description=raw_text, ingredients=[], steps=[], time_minutes=0, difficulty="", image_path="", categories=[]))
                else:
                    QMessageBox.information(self, "Smart Suggestions", "No suggestions found for the provided ingredients.")
            self._render_cards(self.recipes, matched, ai_ideas)

        worker.result.connect(on_result)

        def on_done():
            self.suggest_btn.setEnabled(True)
            self.suggest_btn.setText(old_text)
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

    def _save_ai_idea(self, recipe: Recipe) -> None:
        from app.db.dao import insert_recipe
        rid = insert_recipe(
            title=recipe.title,
            description=recipe.description,
            ingredients=recipe.ingredients,
            steps=recipe.steps,
            time_minutes=recipe.time_minutes,
            difficulty=recipe.difficulty,
            image_path=recipe.image_path,
            categories=recipe.categories,
        )
        QMessageBox.information(self, "Saved", f"Added '{recipe.title}' to your library (ID {rid}).")
        # refresh base list
        from app.db.dao import list_recipes
        self.recipes = list_recipes()
        self._render_cards(self.recipes, [], [])

    def _toggle_favorite(self, recipe: Recipe, favorite: bool) -> None:
        # Persist favorite state and refresh the favorites set so new cards reflect it
        if recipe.id is None:
            return
        from app.db.dao import set_favorite, get_favorites
        set_favorite(recipe.id, favorite)
        self.favorites = set(get_favorites())
