from __future__ import annotations
from dataclasses import dataclass


@dataclass
class PantryItem:
    item: str
    quantity: str = ""
