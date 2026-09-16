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

## Development

Run tests:

    pytest -v

Run linter:

    ruff check .

Check formatting:

    ruff format --check .

Run type checker:

    mypy mi_cli