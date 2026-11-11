"""Conexiones SQLite con WAL, claves foráneas y transacciones explícitas."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    """Abre una conexión configurada para uso concurrente moderado."""

    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def transaction(path: Path) -> Iterator[sqlite3.Connection]:
    """Ejecuta un bloque dentro de una transacción `BEGIN IMMEDIATE`."""

    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


@contextmanager
def read_connection(path: Path) -> Iterator[sqlite3.Connection]:
    """Abre una conexión de lectura y la cierra al salir."""

    conn = connect(path)
    try:
        yield conn
    finally:
        conn.close()
