import json

from typer.testing import CliRunner

from mi_cli import db
from mi_cli.main import app

runner = CliRunner()


def test_init_creates_db(tmp_path):
    db_path = tmp_path / "test.db"
    result = runner.invoke(app, ["--db", str(db_path), "init"])

    assert result.exit_code == 0
    assert "Base de datos inicializada" in result.stdout
    assert db_path.exists()


def test_list_empty_db(tmp_path):
    db_path = tmp_path / "test.db"
    result = runner.invoke(app, ["--db", str(db_path), "list"])

    assert result.exit_code == 0
    assert "No hay Pokémon que coincidan" in result.stdout


def test_list_json_empty(tmp_path):
    db_path = tmp_path / "test.db"
    result = runner.invoke(app, ["--db", str(db_path), "list", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == []


def test_show_not_found(tmp_path):
    db_path = tmp_path / "test.db"
    result = runner.invoke(app, ["--db", str(db_path), "show", "noexiste"])

    assert result.exit_code == 1
    assert "No está guardado" in result.output


def test_show_json_not_found(tmp_path):
    db_path = tmp_path / "test.db"
    result = runner.invoke(app, ["--db", str(db_path), "show", "noexiste", "--json"])

    assert result.exit_code == 1
    assert json.loads(result.stdout) is None


def test_invalid_db_directory(tmp_path):
    result = runner.invoke(app, ["--db", str(tmp_path), "init"])

    assert result.exit_code == 1
    assert "directorio" in result.output


def test_invalid_db_missing_parent(tmp_path):
    db_path = tmp_path / "no_existe" / "data.db"
    result = runner.invoke(app, ["--db", str(db_path), "init"])

    assert result.exit_code == 1
    assert "carpeta no existe" in result.output


def test_sync_limit_zero(tmp_path):
    db_path = tmp_path / "test.db"
    result = runner.invoke(app, ["--db", str(db_path), "sync", "--limit", "0"])

    assert result.exit_code != 0


def test_list_filter_by_type(tmp_path):
    db_path = tmp_path / "test.db"
    runner.invoke(app, ["--db", str(db_path), "init"])
    db.save_pokemon(
        {
            "id": 4,
            "name": "charmander",
            "height": 10,
            "weight": 100,
            "types": [{"type": {"name": "fire"}}],
        },
        db_path,
    )
    db.save_pokemon(
        {
            "id": 7,
            "name": "squirtle",
            "height": 10,
            "weight": 100,
            "types": [{"type": {"name": "water"}}],
        },
        db_path,
    )

    result = runner.invoke(app, ["--db", str(db_path), "list", "--type", "fire"])

    assert result.exit_code == 0
    assert "charmander" in result.stdout
    assert "squirtle" not in result.stdout


def test_list_filter_no_matches(tmp_path):
    db_path = tmp_path / "test.db"
    result = runner.invoke(app, ["--db", str(db_path), "list", "--type", "fire"])

    assert result.exit_code == 0
    assert "No hay Pokémon que coincidan" in result.stdout
