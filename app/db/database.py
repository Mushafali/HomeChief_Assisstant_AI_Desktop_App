from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional

from app.config import DB_PATH, SCHEMA_PATH, SEED_JSON_PATH, ensure_dirs


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the database and seed sample data if empty."""
    ensure_dirs()
    first_time = not Path(DB_PATH).exists()
    with _connect() as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        # Seed only on first creation or when recipes table is empty
        cur = conn.execute("SELECT COUNT(*) AS c FROM recipes")
        count = int(cur.fetchone()["c"]) if cur else 0
        if first_time or count == 0:
            if SEED_JSON_PATH.exists():
                with open(SEED_JSON_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for r in data.get("recipes", []):
                    conn.execute(
                        """
                        INSERT INTO recipes (title, description, ingredients_json, steps_json, time_minutes, difficulty, image_path, categories)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            r.get("title"),
                            r.get("description", ""),
                            json.dumps(r.get("ingredients", []), ensure_ascii=False),
                            json.dumps(r.get("steps", []), ensure_ascii=False),
                            int(r.get("time_minutes", 0)),
                            r.get("difficulty", ""),
                            r.get("image_path", ""),
                            ",".join(r.get("categories", [])),
                        ),
                    )


def execute(sql: str, params: Iterable[Any] | None = None) -> None:
    with _connect() as conn:
        conn.execute(sql, tuple(params or ()))

def executemany(sql: str, seq_of_params: Iterable[Iterable[Any]]) -> None:
    with _connect() as conn:
        conn.executemany(sql, seq_of_params)

def execute_returning_id(sql: str, params: Iterable[Any] | None = None) -> int:
    with _connect() as conn:
        cur = conn.execute(sql, tuple(params or ()))
        return int(cur.lastrowid)

def query(sql: str, params: Iterable[Any] | None = None) -> list[sqlite3.Row]:
    with _connect() as conn:
        cur = conn.execute(sql, tuple(params or ()))
        return list(cur.fetchall())

def query_one(sql: str, params: Iterable[Any] | None = None) -> Optional[sqlite3.Row]:
    with _connect() as conn:
        cur = conn.execute(sql, tuple(params or ()))
        row = cur.fetchone()
        return row
