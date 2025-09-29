from __future__ import annotations
import os
from pathlib import Path
import sys
from platformdirs import user_data_dir
from dotenv import load_dotenv

# Load environment from .env if present
load_dotenv()

APP_NAME = "HomeChef"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
# In frozen (packaged) mode, write data under the user's profile
if getattr(sys, "frozen", False):
    DATA_DIR = Path(user_data_dir("HomeChef", "HomeChef"))
else:
    DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = PROJECT_ROOT / "app" / "assets"
DB_PATH = DATA_DIR / "homechef.db"
SCHEMA_PATH = PROJECT_ROOT / "app" / "db" / "schema.sql"
SEED_JSON_PATH = PROJECT_ROOT / "app" / "db" / "seed_data.json"
DEFAULT_IMAGE = ASSETS_DIR / "images" / "default_recipe.svg"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")

THEME = {
    "accent": "#4CAF50",
    "bg": "#121212",
    "bg_elev": "#1E1E1E",
    "card": "#232323",
    "text": "#EAEAEA",
    "muted": "#9AA0A6",
    "danger": "#E53935",
    "warning": "#FDD835",
}


def ensure_dirs() -> None:
    # Always ensure data directory exists
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    # Only ensure assets in development; packaged app bundles assets read-only
    if not getattr(sys, "frozen", False):
        try:
            (ASSETS_DIR / "images").mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

