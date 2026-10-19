import json

from pydantic import BaseModel


class PokemonResponse(BaseModel):
    id: int
    name: str
    height: int
    weight: int
    types: list[str]
    fetched_at: str

    # Un validador para convertir el string JSON de la DB a una lista real
    @classmethod
    def from_db_row(cls, row: dict):
        return cls(
            id=row["id"],
            name=row["name"],
            height=row["height"],
            weight=row["weight"],
            types=json.loads(row["types"]),
            fetched_at=row["fetched_at"],
        )
