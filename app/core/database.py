import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import settings

DB_PATH: Path = settings.index_store_dir / "images.db"


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                ocr_text TEXT,
                caption TEXT,
                image_type TEXT DEFAULT 'unknown',
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_image(path: str, filename: str, ocr_text: str, caption: str, image_type: str = "unknown") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO images (path, filename, ocr_text, caption, image_type) VALUES (?,?,?,?,?)",
            (path, filename, ocr_text, caption, image_type)
        )
        if cur.lastrowid:
            return cur.lastrowid
        row = conn.execute("SELECT id FROM images WHERE path=?", (path,)).fetchone()
        return row["id"]


def get_image_by_id(db_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM images WHERE id=?", (db_id,)).fetchone()
        return dict(row) if row else None


def path_exists(path: str) -> bool:
    with get_conn() as conn:
        return bool(conn.execute("SELECT 1 FROM images WHERE path=?", (path,)).fetchone())


def count_images() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM images").fetchone()[0]


def clear_all() -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM images")
