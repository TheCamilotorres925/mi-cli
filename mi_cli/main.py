import json

import typer

from mi_cli import api, db

app = typer.Typer()


@app.callback()
def main():
    """CLI para gestionar datos de Pokémon."""


@app.command(name="init")
def init_cmd():
    """Crea la base de datos y la tabla pokemon."""
    db.init_db()
    typer.echo(f"Base de datos inicializada en {db.DB_PATH}")


@app.command(name="fetch")
def fetch_cmd(
    name: str = typer.Argument(..., help="Nombre o id del Pokémon"),
):
    """Consume PokéAPI y guarda el Pokémon en SQLite."""
    db.init_db()
    try:
        data = api.fetch_pokemon(name)
    except api.PokemonAPIError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None

    db.save_pokemon(data)
    typer.secho(
        f"Guardado: {data['name']} (id={data['id']})",
        fg=typer.colors.GREEN,
    )


@app.command(name="list")
def list_cmd():
    """Lista los Pokémon guardados en SQLite."""
    db.init_db()
    rows = db.list_pokemon()
    if not rows:
        typer.echo("No hay Pokémon guardados. Usa `fetch <nombre>` primero.")
        raise typer.Exit()

    for row in rows:
        types = ", ".join(json.loads(row["types"]))
        typer.echo(f"{row['id']:>4}  {row['name']:<12}  {types}  ({row['fetched_at']})")


if __name__ == "__main__":
    app()
