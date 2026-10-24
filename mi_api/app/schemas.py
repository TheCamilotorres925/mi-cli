import json

from pydantic import BaseModel, Field


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


class PokemonCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Nombre del Pokémon")
    height: int = Field(..., ge=0, description="Altura en decímetros")
    weight: int = Field(..., ge=0, description="Peso en hectogramos")
    types: list[str] = Field(..., min_length=1, description="Lista de tipos")
