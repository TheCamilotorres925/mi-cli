import json
import sqlite3
from pathlib import Path

DB_PATH = Path("data.db")


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DB_PATH
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def init_db(db_path: Path | str | None = None) -> None:
    with get_connection(db_path) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS pokemon (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            height INTEGER,
            weight INTEGER,
            types TEXT,
            raw_json TEXT NOT NULL,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)


def save_pokemon(data: dict, db_path: Path | str | None = None) -> None:
    types = json.dumps([t["type"]["name"] for t in data["types"]])
    with get_connection(db_path) as con:
        con.execute("""
        INSERT INTO pokemon (id, name, height, weight, types, raw_json)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            height=excluded.height,
            weight=excluded.weight,
            types=excluded.types,
            raw_json=excluded.raw_json,
            fetched_at=CURRENT_TIMESTAMP
        """, (
            data["id"],
            data["name"],
            data["height"],
            data["weight"],
            types,
            json.dumps(data),
        ))


def list_pokemon(db_path: Path | str | None = None) -> list[sqlite3.Row]:
    with get_connection(db_path) as con:
        return con.execute(
            "SELECT id, name, types, fetched_at FROM pokemon ORDER BY id"
        ).fetchall()


def get_pokemon(name: str, db_path: Path | str | None = None) -> sqlite3.Row | None:
    with get_connection(db_path) as con:
        return con.execute(
            "SELECT * FROM pokemon WHERE name = ?",
            (name.lower(),),
        ).fetchone()