from __future__ import annotations
from typing import Any, List, Optional
from pydantic import BaseModel, Field
import json


class Recipe(BaseModel):
    id: Optional[int] = Field(default=None)
    title: str
    description: str = ""
    ingredients: List[dict] = Field(default_factory=list)  # [{name, quantity}]
    steps: List[str] = Field(default_factory=list)
    time_minutes: int = 0
    difficulty: str = ""
    image_path: str = ""
    categories: List[str] = Field(default_factory=list)

    @staticmethod
    def from_row(row: Any) -> "Recipe":
        if row is None:
            raise ValueError("Row is None")
        ingredients = []
        steps = []
        categories: list[str] = []
        try:
            ingredients = json.loads(row["ingredients_json"]) if row["ingredients_json"] else []
        except Exception:
            ingredients = []
        try:
            steps = json.loads(row["steps_json"]) if row["steps_json"] else []
        except Exception:
            steps = []
        try:
            categories = [c.strip() for c in (row["categories"] or "").split(",") if c.strip()]
        except Exception:
            categories = []
        return Recipe(
            id=int(row["id"]),
            title=str(row["title"]),
            description=str(row["description"] or ""),
            ingredients=ingredients,
            steps=steps,
            time_minutes=int(row["time_minutes"] or 0),
            difficulty=str(row["difficulty"] or ""),
            image_path=str(row["image_path"] or ""),
            categories=categories,
        )
