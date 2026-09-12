import json
import sqlite3
from pathlib import Path

DB_PATH = Path("data.db")


def get_connection() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with get_connection() as con:
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


def save_pokemon(data: dict) -> None:
    types = json.dumps([t["type"]["name"] for t in data["types"]])
    with get_connection() as con:
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


def list_pokemon() -> list[sqlite3.Row]:
    with get_connection() as con:
        return con.execute(
            "SELECT id, name, types, fetched_at FROM pokemon ORDER BY id"
        ).fetchall()


def get_pokemon(name: str) -> sqlite3.Row | None:
    with get_connection() as con:
        return con.execute(
            "SELECT * FROM pokemon WHERE name = ?",
            (name.lower(),),
        ).fetchone()