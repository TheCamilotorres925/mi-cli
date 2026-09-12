import json

import pytest

from mi_cli import db


@pytest.fixture
def temp_db(tmp_path):
    """Crea una base de datos temporal y devuelve su ruta."""
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    return db_path


def make_pokemon(pokemon_id: int, name: str, types: list[str]) -> dict:
    return {
        "id": pokemon_id,
        "name": name,
        "height": 10,
        "weight": 100,
        "types": [{"type": {"name": t}} for t in types],
    }


def test_init_creates_table(temp_db):
    rows = db.list_pokemon(temp_db)
    assert rows == []


def test_save_and_list(temp_db):
    db.save_pokemon(make_pokemon(25, "pikachu", ["electric"]), temp_db)
    db.save_pokemon(make_pokemon(4, "charmander", ["fire"]), temp_db)

    rows = db.list_pokemon(temp_db)
    assert len(rows) == 2
    assert rows[0]["name"] == "charmander"
    assert rows[1]["name"] == "pikachu"


def test_save_is_idempotent(temp_db):
    poke = make_pokemon(25, "pikachu", ["electric"])
    db.save_pokemon(poke, temp_db)
    db.save_pokemon(poke, temp_db)

    rows = db.list_pokemon(temp_db)
    assert len(rows) == 1
    assert rows[0]["name"] == "pikachu"


def test_types_are_stored_as_json(temp_db):
    db.save_pokemon(make_pokemon(25, "pikachu", ["electric"]), temp_db)
    row = db.get_pokemon("pikachu", temp_db)

    assert row is not None
    assert json.loads(row["types"]) == ["electric"]


def test_get_pokemon_not_found(temp_db):
    assert db.get_pokemon("noexiste", temp_db) is None