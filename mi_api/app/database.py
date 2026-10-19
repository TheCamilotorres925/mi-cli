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


# Envolvemos las funciones síncronas para que no bloqueen el event loop
async def get_all_pokemon():
    return await run_in_threadpool(_fetch_all_sync)


async def get_pokemon_by_name(name: str):
    return await run_in_threadpool(_fetch_one_sync, name)
