import json
import time

import typer

from mi_cli import api, db

app = typer.Typer()


def _row_to_dict(row) -> dict:
    """Convierte una fila de SQLite en un dict serializable."""
    return {
        "id": row["id"],
        "name": row["name"],
        "height": row["height"],
        "weight": row["weight"],
        "types": json.loads(row["types"]),
        "fetched_at": row["fetched_at"],
    }


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
def list_cmd(
    ctx: typer.Context,
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Salida en formato JSON",
    ),
    type_name: str | None = typer.Option(
        None,
        "--type",
        "-t",
        help="Filtrar por tipo (ej: fire, water)",
    ),
    name_contains: str | None = typer.Option(
        None,
        "--name",
        help="Filtrar por nombre parcial (case-insensitive)",
    ),
):
    """Lista los Pokémon guardados en SQLite, con filtros opcionales."""
    db_path = _resolve_db(ctx)
    rows = db.find_pokemon(
        name_contains=name_contains,
        type_name=type_name,
        db_path=db_path,
    )

    if not rows:
        if as_json:
            typer.echo("[]")
        else:
            typer.echo("No hay Pokémon que coincidan.")
        raise typer.Exit()

    if as_json:
        data = [
            {
                "id": row["id"],
                "name": row["name"],
                "types": json.loads(row["types"]),
                "fetched_at": row["fetched_at"],
            }
            for row in rows
        ]
        typer.echo(json.dumps(data, ensure_ascii=False, indent=2))
        return

    for row in rows:
        types = ", ".join(json.loads(row["types"]))
        typer.echo(f"{row['id']:>4}  {row['name']:<12}  {types}  ({row['fetched_at']})")


@app.command(name="show")
def show_cmd(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Nombre del Pokémon guardado"),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Salida en formato JSON",
    ),
):
    """Muestra el detalle de un Pokémon desde SQLite."""
    db_path = _resolve_db(ctx)
    row = db.get_pokemon(name, db_path)
    if row is None:
        if as_json:
            typer.echo("null")
        else:
            typer.secho(
                f"No está guardado: {name}. Usa `fetch {name}` primero.",
                fg=typer.colors.RED,
                err=True,
            )
        raise typer.Exit(code=1)

    if as_json:
        typer.echo(json.dumps(_row_to_dict(row), ensure_ascii=False, indent=2))
        return

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
    sleep_ms: int = typer.Option(
        100,
        "--sleep",
        help="Milisegundos a esperar entre requests",
        min=0,
    ),
    retries: int = typer.Option(
        2,
        "--retries",
        help="Reintentos por Pokémon ante errores temporales",
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
    interrupted = False
    last_processed = offset
    total = len(names)

    try:
        with typer.progressbar(names, label="Sincronizando") as progress:
            for index, entry in enumerate(progress):
                name = entry["name"]
                last_processed += 1
                try:
                    data = api.fetch_pokemon_with_retries(name, retries=retries)
                    db.save_pokemon(data, db_path)
                    saved += 1
                except api.PokemonAPIError as exc:
                    failed += 1
                    typer.secho(
                        f"\nError con {name}: {exc}",
                        fg=typer.colors.YELLOW,
                        err=True,
                    )

                if sleep_ms > 0 and index < total - 1:
                    time.sleep(sleep_ms / 1000)
    except KeyboardInterrupt:
        interrupted = True
        typer.secho("\nInterrumpido por el usuario.", fg=typer.colors.YELLOW)

    typer.secho(
        f"Listo. Guardados: {saved}. Fallidos: {failed}.",
        fg=typer.colors.GREEN if failed == 0 else typer.colors.YELLOW,
    )

    if interrupted:
        typer.echo(
            f"Puedes continuar desde --offset {last_processed} "
            f"(el último Pokémon procesado fue el índice {last_processed - 1})."
        )
        raise typer.Exit(code=130) from None


if __name__ == "__main__":
    app()
