import json
import sqlite3

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


def test_get_pokemon_returns_all_fields(temp_db):
    db.save_pokemon(make_pokemon(25, "pikachu", ["electric"]), temp_db)
    row = db.get_pokemon("pikachu", temp_db)

    assert row is not None
    assert row["id"] == 25
    assert row["name"] == "pikachu"
    assert row["height"] == 10
    assert row["weight"] == 100
    assert json.loads(row["types"]) == ["electric"]
    assert row["fetched_at"] is not None


def test_ensure_db_ready_creates_new_db(tmp_path):
    db_path = tmp_path / "nueva.db"
    result = db.ensure_db_ready(db_path)

    assert result == db_path
    assert db_path.exists()


def test_ensure_db_ready_rejects_directory(tmp_path):
    with pytest.raises(db.DatabaseError, match="directorio"):
        db.ensure_db_ready(tmp_path)


def test_ensure_db_ready_rejects_missing_parent(tmp_path):
    db_path = tmp_path / "no_existe" / "data.db"

    with pytest.raises(db.DatabaseError, match="carpeta no existe"):
        db.ensure_db_ready(db_path)


def test_ensure_db_ready_rejects_invalid_sqlite(tmp_path):
    bad = tmp_path / "bad.db"
    bad.write_text("esto no es sqlite")

    with pytest.raises(db.DatabaseError, match="no es una base SQLite válida"):
        db.ensure_db_ready(bad)


def test_get_pokemon_row_is_dict_serializable(temp_db):
    db.save_pokemon(make_pokemon(25, "pikachu", ["electric", "flying"]), temp_db)
    row = db.get_pokemon("pikachu", temp_db)

    assert row is not None
    data = {
        "id": row["id"],
        "name": row["name"],
        "height": row["height"],
        "weight": row["weight"],
        "types": json.loads(row["types"]),
        "fetched_at": row["fetched_at"],
    }
    serialized = json.dumps(data)
    parsed = json.loads(serialized)

    assert parsed["name"] == "pikachu"
    assert parsed["types"] == ["electric", "flying"]
    assert isinstance(parsed["id"], int)


def test_ensure_db_ready_handles_operational_error(tmp_path, monkeypatch):
    def raise_operational_error(*args, **kwargs):
        raise sqlite3.OperationalError("permiso denegado")

    monkeypatch.setattr(db.sqlite3, "connect", raise_operational_error)

    db_path = tmp_path / "test.db"

    with pytest.raises(db.DatabaseError, match="No se pudo abrir"):
        db.ensure_db_ready(db_path)


def test_find_pokemon_no_filters(temp_db):
    db.save_pokemon(make_pokemon(1, "bulbasaur", ["grass", "poison"]), temp_db)
    db.save_pokemon(make_pokemon(4, "charmander", ["fire"]), temp_db)
    db.save_pokemon(make_pokemon(7, "squirtle", ["water"]), temp_db)

    rows = db.find_pokemon(db_path=temp_db)
    assert len(rows) == 3


def test_find_pokemon_by_type(temp_db):
    db.save_pokemon(make_pokemon(1, "bulbasaur", ["grass", "poison"]), temp_db)
    db.save_pokemon(make_pokemon(4, "charmander", ["fire"]), temp_db)
    db.save_pokemon(make_pokemon(7, "squirtle", ["water"]), temp_db)

    rows = db.find_pokemon(type_name="fire", db_path=temp_db)
    assert len(rows) == 1
    assert rows[0]["name"] == "charmander"


def test_find_pokemon_by_type_matches_secondary(temp_db):
    db.save_pokemon(make_pokemon(6, "charizard", ["fire", "flying"]), temp_db)

    rows = db.find_pokemon(type_name="flying", db_path=temp_db)
    assert len(rows) == 1
    assert rows[0]["name"] == "charizard"


def test_find_pokemon_by_name_partial(temp_db):
    db.save_pokemon(make_pokemon(4, "charmander", ["fire"]), temp_db)
    db.save_pokemon(make_pokemon(5, "charmeleon", ["fire"]), temp_db)
    db.save_pokemon(make_pokemon(7, "squirtle", ["water"]), temp_db)

    rows = db.find_pokemon(name_contains="char", db_path=temp_db)
    assert len(rows) == 2


def test_find_pokemon_name_is_case_insensitive(temp_db):
    db.save_pokemon(make_pokemon(4, "charmander", ["fire"]), temp_db)

    rows = db.find_pokemon(name_contains="CHAR", db_path=temp_db)
    assert len(rows) == 1


def test_find_pokemon_combines_filters(temp_db):
    db.save_pokemon(make_pokemon(4, "charmander", ["fire"]), temp_db)
    db.save_pokemon(make_pokemon(7, "squirtle", ["water"]), temp_db)
    db.save_pokemon(make_pokemon(8, "wartortle", ["water"]), temp_db)

    rows = db.find_pokemon(name_contains="squ", type_name="water", db_path=temp_db)
    assert len(rows) == 1
    assert rows[0]["name"] == "squirtle"


def test_find_pokemon_no_matches(temp_db):
    db.save_pokemon(make_pokemon(4, "charmander", ["fire"]), temp_db)

    rows = db.find_pokemon(name_contains="zzz", db_path=temp_db)
    assert rows == []
