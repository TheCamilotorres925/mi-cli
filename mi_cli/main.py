import typer

app = typer.Typer()

@app.callback()
def main():
    """CLI para gestionar datos."""

@app.command(name="init")
def init_cmd():
    typer.echo("Base de datos inicializada (fake)")

if __name__ == "__main__":
    app()