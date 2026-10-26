import json

from pydantic import BaseModel, Field, field_validator, model_validator


class PokemonResponse(BaseModel):
    id: int
    name: str
    height: int
    weight: int
    types: list[str]
    fetched_at: str

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
    name: str = Field(..., min_length=1)
    height: int = Field(..., ge=0)
    weight: int = Field(..., ge=0)
    types: list[str] = Field(..., min_length=1)

    # 1. Validador para campos individuales
    @field_validator("name")
    @classmethod
    def limpiar_nombre(cls, v: str) -> str:
        # Quita espacios y lo pasa a minúsculas
        nombre_limpio = v.strip().lower()
        if not nombre_limpio:
            raise ValueError("El nombre no puede estar vacío")
        return nombre_limpio

    # 2. Validador para los elementos de una lista
    @field_validator("types")
    @classmethod
    def limpiar_tipos(cls, v: list[str]) -> list[str]:
        # Quita espacios en blanco de cada tipo y elimina los que queden vacíos
        tipos_limpios = [t.strip().lower() for t in v if t.strip()]
        if not tipos_limpios:
            raise ValueError("Debe haber al menos un tipo válido")
        return tipos_limpios

    # 3. Validador de modelo (para comparar dos campos entre sí)
    @model_validator(mode="after")
    def validar_legendario(self):
        # self.types ya está limpio gracias al validador anterior
        if "legendary" in self.types and self.weight <= 300:
            raise ValueError("Los Pokémon legendarios deben pesar más de 300")
        return self
