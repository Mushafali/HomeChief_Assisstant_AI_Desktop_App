# HomeChef – AI-Powered Desktop Recipe Assistant

HomeChef is a modern, beautiful, and professional desktop application that helps you plan, discover, and cook meals with an AI assistant powered by Google Gemini. It includes a recipe library, smart recipe suggestions from your ingredients, a real-time AI cooking assistant, pantry and grocery list management, and a step-by-step cooking guide.

## Key Features
- **Recipe Management**: Browse, search, and favorite recipes with images, time, and difficulty.
- **Smart Suggestions (Gemini)**: Enter ingredients you have and get recipe matches or creative ideas; get ingredient substitutions.
- **AI Chatbot**: Ask cooking questions, get step-by-step guidance, and nutrition info.
- **Grocery List**: Auto-add missing ingredients from selected recipes; manage and export or copy list.
- **Cooking Guide**: Step-by-step mode with contextual AI tips for each step.
- **Windows & VS Code Friendly**: One-click run with clear structure; no functionality compromises.

## Tech Stack
- **Language**: Python 3.10+
- **GUI**: PyQt6
- **AI**: Google Gemini (google-generativeai)
- **DB**: SQLite (serverless, local)
- **Config**: .env via python-dotenv

## Project Structure
```
HomeChef/
├─ app/
│  ├─ assets/
│  │  └─ images/
│  │     └─ default_recipe.svg
│  ├─ db/
│  │  ├─ schema.sql
│  │  ├─ database.py
│  │  ├─ dao.py
│  │  └─ seed_data.json
│  ├─ models/
│  │  ├─ __init__.py
│  │  ├─ recipe.py
│  │  ├─ pantry.py
│  │  └─ grocery.py
│  ├─ services/
│  │  ├─ __init__.py
│  │  ├─ gemini_service.py
│  │  ├─ image_service.py
│  │  ├─ export_service.py
│  │  └─ async_worker.py
│  ├─ ui/
│  │  ├─ __init__.py
│  │  ├─ theme.py
│  │  └─ widgets/
│  │     ├─ __init__.py
│  │     ├─ nav.py
│  │     ├─ recipe_card.py
│  │     ├─ recipe_list.py
│  │     ├─ recipe_detail.py
│  │     ├─ pantry_widget.py
│  │     ├─ grocery_widget.py
│  │     ├─ cooking_widget.py
│  │     └─ chat_widget.py
│  ├─ __init__.py
│  ├─ main.py
│  └─ config.py
├─ data/  (auto-created at runtime)
├─ .env.example
├─ requirements.txt
└─ main.py
```

## Setup (Windows + VS Code)
1. Install Python 3.10 or newer from https://python.org.
2. Open this folder (`HomeChef/`) in VS Code.
3. Create a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
5. Create an environment file by copying `.env.example` to `.env` and set your Gemini API key:
   ```
   GEMINI_API_KEY=YOUR_GEMINI_API_KEY
   # Optional: override the default model
   GEMINI_MODEL=gemini-2.0-flash
   ```
6. Run the app:
   ```powershell
   python main.py
   ```

The first run initializes the SQLite database from `app/db/schema.sql` and seeds sample recipes from `app/db/seed_data.json` into `data/homechef.db`.

## Notes
- The app stores data in the `data/` folder. You can safely delete `data/homechef.db` to reset; it will re-initialize on next run.
- Gemini is used for:
  - Recipe ideas from your ingredients.
  - Ingredient substitutions in context.
  - Chatbot assistance and step-by-step tips.

## Packaging to Windows EXE (optional)
You can create a Windows executable using PyInstaller:

1. Install packaging deps (already listed in `requirements.txt`):
   ```powershell
   pip install -r requirements.txt
   ```
2. Build the EXE:
   ```powershell
   pyinstaller --noconfirm --clean ^
     --name HomeChef --windowed --onefile main.py ^
     --add-data "app/assets;app/assets" ^
     --add-data "app/db/schema.sql;app/db" ^
     --add-data "app/db/seed_data.json;app/db" ^
     --collect-all PyQt6 ^
     --hidden-import PyQt6.QtCore --hidden-import PyQt6.QtGui --hidden-import PyQt6.QtWidgets ^
     --hidden-import google.generativeai ^
     --collect-submodules google --collect-submodules google.generativeai --collect-submodules google.api_core --collect-submodules grpc ^
     --collect-data certifi
   ```
3. Put a `.env` next to `dist/HomeChef.exe` or set system environment variables.
4. Double‑click `dist/HomeChef.exe` to run.

Notes:
- In packaged mode, the app writes its database to a user‑writable folder: `%LOCALAPPDATA%/HomeChef/HomeChef/homechef.db`.
- gRPC/ALTS warnings in console are benign.

## Publish to GitHub (ignore private/build files)
1. Ensure `.gitignore` exists (we include one) so sensitive/build files are ignored:
   - Ignored: `.env`, `.venv/`, `dist/`, `build/`, `*.spec`, `data/`, editor caches.
2. Initialize and push:
   ```upload to github repository using github bash 
   ```

## Cloning from GitHub and running next time
1. Clone and open the folder in VS Code.
2. Create and activate a virtualenv.
3. Install deps: `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and set your keys.
5. Run: `python main.py`.
6. Build EXE (optional): run the PyInstaller command above.

## License
MIT

## .env
Create a `.env` file in the project root (and for a packaged EXE, place a copy next to `HomeChef.exe`).

```
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
# Optionally override the default model
GEMINI_MODEL=gemini-2.0-flash
```

