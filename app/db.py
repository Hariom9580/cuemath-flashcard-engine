import sqlite3


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS decks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source_filename TEXT NOT NULL,
                created_at TEXT NOT NULL,
                card_count INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deck_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                source_excerpt TEXT,
                created_at TEXT NOT NULL,
                repetitions INTEGER NOT NULL DEFAULT 0,
                interval_days INTEGER NOT NULL DEFAULT 0,
                ease_factor REAL NOT NULL DEFAULT 2.5,
                next_review_at TEXT NOT NULL,
                review_count INTEGER NOT NULL DEFAULT 0,
                correct_count INTEGER NOT NULL DEFAULT 0,
                last_score INTEGER,
                last_reviewed_at TEXT,
                FOREIGN KEY(deck_id) REFERENCES decks(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_cards_deck_id ON cards(deck_id);
            CREATE INDEX IF NOT EXISTS idx_cards_next_review_at ON cards(next_review_at);
            """
        )
