import typer

from mi_cli import db

app = typer.Typer()


@app.callback()
def main():
    """CLI para gestionar datos."""


@app.command(name="init")
def init_cmd():
    """Crea la base de datos y la tabla pokemon."""
    db.init_db()
    typer.echo(f"Base de datos inicializada en {db.DB_PATH}")


if __name__ == "__main__":
    app()