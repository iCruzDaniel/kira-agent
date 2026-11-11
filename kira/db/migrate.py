"""Creación idempotente de las dos bases SQLite de Kira."""

from __future__ import annotations

from pathlib import Path

from kira.config import Settings
from kira.db.connection import connect

SCHEMA_DIR = Path(__file__).resolve().parent


def _apply_schema(path: Path, schema_file: Path) -> None:
    sql = schema_file.read_text(encoding="utf-8")
    conn = connect(path)
    try:
        conn.executescript(sql)
    finally:
        conn.close()


def init_databases(settings: Settings) -> None:
    """Aplica ambos esquemas y siembra datos demo si la base está vacía."""

    _apply_schema(settings.db1_path, SCHEMA_DIR / "schema_business.sql")
    _apply_schema(settings.db2_path, SCHEMA_DIR / "schema_sessions.sql")

    from kira.db.seed import seed_if_empty

    seed_if_empty(settings)
