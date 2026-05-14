import sqlite3
from contextlib import contextmanager
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "licitaciones.db"


def ensure_data_dir() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_conn():
    ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS offers (
                codigo_externo TEXT PRIMARY KEY,
                nombre TEXT,
                descripcion TEXT,
                descripcion_producto TEXT,
                organismo TEXT,
                estado TEXT,
                region TEXT,
                comuna TEXT,
                tipo_oferta TEXT,
                moneda TEXT,
                monto_estimado REAL,
                fecha_publicacion TEXT,
                fecha_cierre TEXT,
                link TEXT,
                raw_json TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS saved_filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                keyword TEXT,
                tipo_oferta TEXT,
                estado TEXT,
                organismo TEXT,
                region TEXT,
                comuna TEXT,
                utm_range TEXT,
                min_monto REAL,
                max_monto REAL,
                start_date TEXT,
                end_date TEXT,
                start_close_date TEXT,
                end_close_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS notification_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TEXT DEFAULT CURRENT_TIMESTAMP,
                offers_inserted INTEGER NOT NULL DEFAULT 0,
                offers_updated INTEGER NOT NULL DEFAULT 0,
                matched_saved_filters INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        # Lightweight migrations for existing databases.
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(offers)").fetchall()}
        if "descripcion_producto" not in existing_cols:
            conn.execute("ALTER TABLE offers ADD COLUMN descripcion_producto TEXT")
        saved_filter_cols = {row["name"] for row in conn.execute("PRAGMA table_info(saved_filters)").fetchall()}
        if "utm_range" not in saved_filter_cols:
            conn.execute("ALTER TABLE saved_filters ADD COLUMN utm_range TEXT")
        if "start_close_date" not in saved_filter_cols:
            conn.execute("ALTER TABLE saved_filters ADD COLUMN start_close_date TEXT")
        if "end_close_date" not in saved_filter_cols:
            conn.execute("ALTER TABLE saved_filters ADD COLUMN end_close_date TEXT")
        conn.commit()
