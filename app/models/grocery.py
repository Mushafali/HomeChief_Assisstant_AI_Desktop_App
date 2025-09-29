from __future__ import annotations
from dataclasses import dataclass


@dataclass
class GroceryItem:
    item: str
    quantity: str = ""
    checked: bool = False
