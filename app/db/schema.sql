-- HomeChef database schema
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    ingredients_json TEXT NOT NULL,
    steps_json TEXT NOT NULL,
    time_minutes INTEGER,
    difficulty TEXT,
    image_path TEXT,
    categories TEXT
);

CREATE INDEX IF NOT EXISTS idx_recipes_title ON recipes(title);

CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL UNIQUE,
    FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pantry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT NOT NULL UNIQUE,
    quantity TEXT
);

CREATE TABLE IF NOT EXISTS grocery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item TEXT NOT NULL UNIQUE,
    quantity TEXT,
    checked INTEGER DEFAULT 0
);
