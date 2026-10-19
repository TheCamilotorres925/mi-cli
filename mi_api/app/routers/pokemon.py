from fastapi import APIRouter, HTTPException

from ..database import get_all_pokemon, get_pokemon_by_name
from ..schemas import PokemonResponse

router = APIRouter(
    prefix="/pokemon",
    tags=["Pokemon"],  # Esto agrupa las rutas en la documentación automática
)


@router.get("/", response_model=list[PokemonResponse])
async def list_pokemon():
    """Devuelve la lista de todos los Pokémon guardados."""
    rows = await get_all_pokemon()
    return [PokemonResponse.from_db_row(r) for r in rows]


@router.get("/{name}", response_model=PokemonResponse)
async def get_pokemon(name: str):
    """Devuelve un Pokémon por su nombre o un error 404."""
    row = await get_pokemon_by_name(name)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"Pokémon '{name}'no encontrado en la base de datos"
        )
    return PokemonResponse.from_db_row(row)
