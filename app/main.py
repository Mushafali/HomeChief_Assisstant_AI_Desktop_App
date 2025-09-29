from __future__ import annotations
import sys
from typing import Optional

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStackedWidget,
    QFrame,
    QLabel,
    QToolButton,
    QMessageBox,
)

from app.config import APP_NAME, ensure_dirs
from app.db.database import init_db
from app.db.dao import list_recipes, get_recipe, set_favorite, get_favorites
from app.models.recipe import Recipe
from app.services import GeminiService, ImageService
from app.ui import apply_theme
from app.ui.widgets.recipe_list import RecipeListPage
from app.ui.widgets.recipe_detail import RecipeDetailPage
from app.ui.widgets.pantry_widget import PantryWidget
from app.ui.widgets.grocery_widget import GroceryWidget
from app.ui.widgets.cooking_widget import CookingWidget
from app.ui.widgets.chat_widget import ChatWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1080, 720)

        # Services
        self.gemini = self._build_gemini()
        self.images = ImageService()

        # State
        self.current_recipe: Optional[Recipe] = None

        # UI
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.nav = self._build_nav()
        root_layout.addWidget(self.nav, 0)

        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, 1)

        # Pages
        self.recipes_page = RecipeListPage(self.gemini, self.images, self.open_recipe_detail)
        self.detail_page = RecipeDetailPage(self.gemini, self.images, self.start_cooking, self.add_missing_to_grocery, self.toggle_favorite)
        self.pantry_page = PantryWidget()
        self.grocery_page = GroceryWidget()
        self.cooking_page = CookingWidget(self.gemini)
        self.chat_page = ChatWidget()

        self.stack.addWidget(self.recipes_page)
        self.stack.addWidget(self.detail_page)
        self.stack.addWidget(self.pantry_page)
        self.stack.addWidget(self.grocery_page)
        self.stack.addWidget(self.cooking_page)
        self.stack.addWidget(self.chat_page)

        self.setCentralWidget(root)

        # Top actions
        self._build_menu()

        # Initial data load
        self.refresh_recipes()
        self.show_recipes()

    def _build_gemini(self) -> Optional[GeminiService]:
        try:
            return GeminiService()
        except Exception as e:
            # Allow app to run without API key; AI features will show a warning on use
            print(f"Gemini disabled: {e}")
            return None

    def _build_menu(self) -> None:
        bar = self.menuBar()
        file_menu = bar.addMenu("File")
        quit_act = QAction("Exit", self)
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        help_menu = bar.addMenu("Help")
        about_act = QAction("About", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "About HomeChef",
            "HomeChef – AI-Powered Desktop Recipe Assistant\n\n"
            "Discover recipes, manage pantry and grocery lists, and cook with step-by-step guidance.\n"
            "AI features powered by Google Gemini.",
        )

    def _build_nav(self) -> QWidget:
        nav = QFrame()
        nav.setObjectName("Card")
        nav.setFixedWidth(220)
        lay = QVBoxLayout(nav)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        title = QLabel("HomeChef")
        title.setObjectName("Title")
        lay.addWidget(title)

        def add_btn(text: str, on_click, idx: int) -> QToolButton:
            btn = QToolButton()
            btn.setObjectName("NavButton")
            btn.setText(text)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            btn.clicked.connect(lambda: self.stack.setCurrentIndex(idx))
            btn.clicked.connect(on_click)
            btn.setProperty("active", False)
            btn.setCheckable(False)
            # Improve UX: show pointing-hand cursor on clickable buttons
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            lay.addWidget(btn)
            return btn

        self.btn_recipes = add_btn("Recipes", self.show_recipes, 0)
        self.btn_detail = add_btn("Details", self.show_detail, 1)
        self.btn_pantry = add_btn("Pantry", self.show_pantry, 2)
        self.btn_grocery = add_btn("Grocery", self.show_grocery, 3)
        self.btn_cooking = add_btn("Cooking Guide", self.show_cooking, 4)
        self.btn_chat = add_btn("AI Chat", self.show_chat, 5)

        lay.addStretch(1)
        return nav

    # ----- Navigation handlers -----
    def _set_active_button(self, active_btn: QToolButton) -> None:
        for btn in [self.btn_recipes, self.btn_detail, self.btn_pantry, self.btn_grocery, self.btn_cooking, self.btn_chat]:
            btn.setProperty("active", btn is active_btn)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def show_recipes(self) -> None:
        self.stack.setCurrentIndex(0)
        self._set_active_button(self.btn_recipes)

    def show_detail(self) -> None:
        self.stack.setCurrentIndex(1)
        self._set_active_button(self.btn_detail)

    def show_pantry(self) -> None:
        self.stack.setCurrentIndex(2)
        self._set_active_button(self.btn_pantry)
        self.pantry_page.refresh()

    def show_grocery(self) -> None:
        self.stack.setCurrentIndex(3)
        self._set_active_button(self.btn_grocery)
        self.grocery_page.refresh()

    def show_cooking(self) -> None:
        self.stack.setCurrentIndex(4)
        self._set_active_button(self.btn_cooking)

    def show_chat(self) -> None:
        self.stack.setCurrentIndex(5)
        self._set_active_button(self.btn_chat)

    # ----- Data operations -----
    def refresh_recipes(self) -> None:
        favorites = set(get_favorites())
        recipes = list_recipes()
        self.recipes_page.load_recipes(recipes, favorites)

    def open_recipe_detail(self, recipe: Recipe) -> None:
        self.current_recipe = recipe
        self.detail_page.set_recipe(recipe)
        # Automatically identify and add missing ingredients to grocery list
        try:
            self.add_missing_to_grocery(recipe)
        except Exception as _e:
            pass
        self.show_detail()

    def start_cooking(self, recipe: Optional[Recipe] = None) -> None:
        if recipe is None:
            recipe = self.current_recipe
        if recipe is None:
            QMessageBox.warning(self, "Start Cooking", "Please open a recipe first.")
            return
        self.cooking_page.set_recipe(recipe)
        self.show_cooking()

    def add_missing_to_grocery(self, recipe: Recipe) -> None:
        from app.db.dao import compute_missing_ingredients, upsert_grocery_item
        missing = compute_missing_ingredients(recipe)
        for item in missing:
            upsert_grocery_item(item, "", False)
        QMessageBox.information(self, "Grocery List", f"Added {len(missing)} missing ingredients to your grocery list.")
        self.grocery_page.refresh()

    def toggle_favorite(self, recipe: Recipe, favorite: bool) -> None:
        if recipe.id is None:
            QMessageBox.information(self, "Favorites", "Only saved recipes can be favorited.")
            return
        set_favorite(recipe.id, favorite)
        self.refresh_recipes()


def main() -> None:
    ensure_dirs()
    init_db()
    app = QApplication(sys.argv)
    apply_theme(app)

    win = MainWindow()
    win.show()

    sys.exit(app.exec())
