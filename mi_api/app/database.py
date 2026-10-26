import json
import sqlite3
from pathlib import Path

from fastapi.concurrency import run_in_threadpool

# Reutilizamos la ruta por defecto de tu CLI
DB_PATH = Path("data.db")


def get_connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _fetch_all_sync():
    with get_connection() as con:
        query = (
            "SELECT id, name, height, weight, types, fetched_at "
            "FROM pokemon ORDER BY id"
        )
        rows = con.execute(query).fetchall()
        return [dict(r) for r in rows]


def _fetch_one_sync(name: str):
    with get_connection() as con:
        query = (
            "SELECT id, name, height, weight, types, fetched_at "
            "FROM pokemon WHERE name = ?"
        )
        row = con.execute(query, (name.lower(),)).fetchone()
        return dict(row) if row else None


def _save_pokemon_sync(pokemon_data: dict):
    # Convertimos la lista de tipos a JSON (igual que en tu CLI)
    types_json = json.dumps(pokemon_data["types"])

    # Usamos un INSERT ... ON CONFLICT igual que en tu CLI para hacer el UPSERT
    with get_connection() as con:
        con.execute(
            """
            INSERT INTO pokemon (name, height, weight, types, raw_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                height=excluded.height,
                weight=excluded.weight,
                types=excluded.types
            """,
            (
                pokemon_data["name"].lower(),
                pokemon_data["height"],
                pokemon_data["weight"],
                types_json,
                json.dumps(pokemon_data),  # Guardamos el JSON completo por si acaso
            ),
        )


# Envolvemos las funciones síncronas para que no bloqueen el event loop
async def get_all_pokemon():
    return await run_in_threadpool(_fetch_all_sync)


async def get_pokemon_by_name(name: str):
    return await run_in_threadpool(_fetch_one_sync, name)


async def save_pokemon(pokemon_data: dict):
    return await run_in_threadpool(_save_pokemon_sync, pokemon_data)


def _create_users_table_sync():
    with get_connection() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL
            )
        """)


def _get_user_sync(username: str):
    with get_connection() as con:
        query = "SELECT * FROM users WHERE username = ?"
        row = con.execute(query, (username,)).fetchone()
        return dict(row) if row else None


def _create_user_sync(username: str, hashed_password: str):
    with get_connection() as con:
        query = "INSERT INTO users (username, hashed_password) VALUES (?, ?)"
        con.execute(query, (username, hashed_password))


# Envoltorios async
async def init_users_table():
    await run_in_threadpool(_create_users_table_sync)


async def get_user(username: str):
    return await run_in_threadpool(_get_user_sync, username)


async def create_user(username: str, hashed_password: str):
    return await run_in_threadpool(_create_user_sync, username, hashed_password)
