# mi-cli

CLI that consumes [PokéAPI](https://pokeapi.co/) and stores data in SQLite.

![CI](https://github.com/TheCamilotorres925/mi-cli/actions/workflows/ci.yml/badge.svg)

## Requirements

- Python 3.11+
- Git

## Install

    git clone https://github.com/TheCamilotorres925/mi-cli.git
    cd mi-cli
    python -m venv .venv

    # Windows
    .venv\Scripts\activate

    # macOS / Linux
    source .venv/bin/activate

    pip install -e ".[dev]"

## Usage

    python -m mi_cli.main init
    python -m mi_cli.main fetch pikachu
    python -m mi_cli.main fetch charmander
    python -m mi_cli.main list
    python -m mi_cli.main --db custom.db init
    python -m mi_cli.main --db custom.db fetch pikachu
    python -m mi_cli.main --db custom.db list
    python -m mi_cli.main sync --limit 20
    python -m mi_cli.main sync --limit 20 --offset 20
    `sync` trae los Pokémon desde PokéAPI y los guarda en lote. Los que ya existan se actualizan (idempotente).

## Development

Run tests:

    pytest -v

Run linter:

    ruff check .

Check formatting:

    ruff format --check .

Run type checker:

    mypy mi_cli