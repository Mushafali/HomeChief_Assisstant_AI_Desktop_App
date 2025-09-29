from __future__ import annotations
import json
from typing import Iterable, Optional

from app.db.database import query, query_one, execute, executemany, execute_returning_id
from app.models.recipe import Recipe

# ---------- Recipes ----------

def list_recipes() -> list[Recipe]:
    rows = query("SELECT * FROM recipes ORDER BY title ASC")
    return [Recipe.from_row(r) for r in rows]


def search_recipes(text: str = "", categories: list[str] | None = None, max_time: Optional[int] = None, difficulty: str = "") -> list[Recipe]:
    sql = "SELECT * FROM recipes WHERE 1=1"
    params: list = []
    if text:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        like = f"%{text}%"
        params += [like, like]
    if categories:
        for cat in categories:
            sql += " AND categories LIKE ?"
            params.append(f"%{cat}%")
    if max_time is not None:
        sql += " AND (time_minutes <= ?)"
        params.append(max_time)
    if difficulty:
        sql += " AND (difficulty = ?)"
        params.append(difficulty)
    sql += " ORDER BY time_minutes ASC, title ASC"
    rows = query(sql, params)
    return [Recipe.from_row(r) for r in rows]


def get_recipe(recipe_id: int) -> Optional[Recipe]:
    row = query_one("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
    return Recipe.from_row(row) if row else None

def find_recipes_by_titles(titles: list[str]) -> list[Recipe]:
    if not titles:
        return []
    placeholders = ",".join(["?"] * len(titles))
    rows = query(f"SELECT * FROM recipes WHERE title IN ({placeholders})", titles)
    title_to_recipe = {str(r["title"]): Recipe.from_row(r) for r in rows}
    # Preserve the input order
    return [title_to_recipe[t] for t in titles if t in title_to_recipe]

def insert_recipe(
    title: str,
    description: str,
    ingredients: list[dict],
    steps: list[str],
    time_minutes: int,
    difficulty: str,
    image_path: str = "",
    categories: list[str] | None = None,
) -> int:
    rid = execute_returning_id(
        """
        INSERT INTO recipes (title, description, ingredients_json, steps_json, time_minutes, difficulty, image_path, categories)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            description,
            json.dumps(ingredients, ensure_ascii=False),
            json.dumps(steps, ensure_ascii=False),
            int(time_minutes or 0),
            difficulty,
            image_path,
            ",".join(categories or []),
        ),
    )
    return rid


def get_favorites() -> list[int]:
    rows = query("SELECT recipe_id FROM favorites ORDER BY recipe_id")
    return [int(r[0]) for r in rows]


def set_favorite(recipe_id: int, favorite: bool) -> None:
    if favorite:
        try:
            execute("INSERT INTO favorites (recipe_id) VALUES (?)", (recipe_id,))
        except Exception:
            pass
    else:
        execute("DELETE FROM favorites WHERE recipe_id = ?", (recipe_id,))


# ---------- Pantry ----------

def list_pantry() -> list[tuple[str, str]]:
    rows = query("SELECT item, COALESCE(quantity, '') as quantity FROM pantry ORDER BY item ASC")
    return [(str(r[0]), str(r[1])) for r in rows]


def upsert_pantry_item(item: str, quantity: str = "") -> None:
    execute(
        "INSERT INTO pantry (item, quantity) VALUES (?, ?) ON CONFLICT(item) DO UPDATE SET quantity=excluded.quantity",
        (item.strip(), quantity.strip()),
    )


def remove_pantry_item(item: str) -> None:
    execute("DELETE FROM pantry WHERE item = ?", (item,))


# ---------- Grocery ----------

def list_grocery() -> list[tuple[str, str, bool]]:
    rows = query("SELECT item, COALESCE(quantity, ''), COALESCE(checked, 0) FROM grocery ORDER BY checked ASC, item ASC")
    return [(str(r[0]), str(r[1]), bool(r[2])) for r in rows]


def upsert_grocery_item(item: str, quantity: str = "", checked: bool = False) -> None:
    execute(
        "INSERT INTO grocery (item, quantity, checked) VALUES (?, ?, ?) ON CONFLICT(item) DO UPDATE SET quantity=excluded.quantity, checked=excluded.checked",
        (item.strip(), quantity.strip(), int(checked)),
    )


def set_grocery_checked(item: str, checked: bool) -> None:
    execute("UPDATE grocery SET checked = ? WHERE item = ?", (int(checked), item))


def remove_grocery_item(item: str) -> None:
    execute("DELETE FROM grocery WHERE item = ?", (item,))


def clear_grocery(only_checked: bool = False) -> None:
    if only_checked:
        execute("DELETE FROM grocery WHERE checked = 1")
    else:
        execute("DELETE FROM grocery")


# ---------- Utilities ----------

def compute_missing_ingredients(recipe: Recipe) -> list[str]:
    pantry = {name.lower(): qty for name, qty in list_pantry()}
    missing: list[str] = []
    for ing in recipe.ingredients:
        name = ing.get("name", "").lower()
        if not name:
            continue
        if name not in pantry or (pantry.get(name, "") == ""):
            missing.append(ing.get("name", ""))
    return missing
