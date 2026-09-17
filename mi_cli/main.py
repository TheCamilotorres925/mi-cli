import json

import typer

from mi_cli import api, db

app = typer.Typer()


@app.callback()
def main(
    ctx: typer.Context,
    db_path: str = typer.Option(
        "data.db",
        "--db",
        help="Ruta al archivo SQLite (por defecto: data.db)",
    ),
):
    """CLI para gestionar datos de Pokémon."""
    ctx.obj = {"db_path": db_path}


def _resolve_db(ctx: typer.Context) -> str:
    """Valida la DB y devuelve la ruta, o sale con error claro."""
    try:
        return str(db.ensure_db_ready(ctx.obj["db_path"]))
    except db.DatabaseError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None


@app.command(name="init")
def init_cmd(ctx: typer.Context):
    """Crea la base de datos y la tabla pokemon."""
    db_path = _resolve_db(ctx)
    typer.echo(f"Base de datos inicializada en {db_path}")


@app.command(name="fetch")
def fetch_cmd(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Nombre o id del Pokémon"),
):
    """Consume PokéAPI y guarda el Pokémon en SQLite."""
    db_path = _resolve_db(ctx)
    try:
        data = api.fetch_pokemon(name)
    except api.PokemonAPIError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None

    db.save_pokemon(data, db_path)
    typer.secho(
        f"Guardado: {data['name']} (id={data['id']})",
        fg=typer.colors.GREEN,
    )


@app.command(name="list")
def list_cmd(ctx: typer.Context):
    """Lista los Pokémon guardados en SQLite."""
    db_path = _resolve_db(ctx)
    rows = db.list_pokemon(db_path)
    if not rows:
        typer.echo("No hay Pokémon guardados. Usa `fetch <nombre>` primero.")
        raise typer.Exit()

    for row in rows:
        types = ", ".join(json.loads(row["types"]))
        typer.echo(f"{row['id']:>4}  {row['name']:<12}  {types}  ({row['fetched_at']})")


@app.command(name="show")
def show_cmd(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Nombre del Pokémon guardado"),
):
    """Muestra el detalle de un Pokémon desde SQLite."""
    db_path = _resolve_db(ctx)
    row = db.get_pokemon(name, db_path)
    if row is None:
        typer.secho(
            f"No está guardado: {name}. Usa `fetch {name}` primero.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    types = ", ".join(json.loads(row["types"]))
    typer.echo(f"Name:    {row['name']}")
    typer.echo(f"ID:      {row['id']}")
    typer.echo(f"Height:  {row['height']}")
    typer.echo(f"Weight:  {row['weight']}")
    typer.echo(f"Types:   {types}")
    typer.echo(f"Fetched: {row['fetched_at']}")


@app.command(name="sync")
def sync_cmd(
    ctx: typer.Context,
    limit: int = typer.Option(
        20,
        "--limit",
        "-n",
        help="Número de Pokémon a sincronizar",
        min=1,
    ),
    offset: int = typer.Option(
        0,
        "--offset",
        help="Desde qué posición empezar",
        min=0,
    ),
):
    """Trae Pokémon desde PokéAPI y los guarda en SQLite."""
    db_path = _resolve_db(ctx)

    try:
        names = api.list_pokemon_names(limit=limit, offset=offset)
    except api.PokemonAPIError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None

    saved = 0
    failed = 0

    with typer.progressbar(names, label="Sincronizando") as progress:
        for entry in progress:
            name = entry["name"]
            try:
                data = api.fetch_pokemon(name)
                db.save_pokemon(data, db_path)
                saved += 1
            except api.PokemonAPIError as exc:
                failed += 1
                typer.secho(
                    f"\nError con {name}: {exc}",
                    fg=typer.colors.YELLOW,
                    err=True,
                )

    typer.secho(
        f"Listo. Guardados: {saved}. Fallidos: {failed}.",
        fg=typer.colors.GREEN if failed == 0 else typer.colors.YELLOW,
    )


if __name__ == "__main__":
    app()
