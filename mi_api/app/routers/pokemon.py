from fastapi import APIRouter, Depends, Header, HTTPException, status

from ..config import settings
from ..database import get_all_pokemon, get_pokemon_by_name, save_pokemon
from ..schemas import PokemonCreate, PokemonResponse

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
            status_code=404,
            detail=f"Pokémon '{name}' no encontrado en la base de datos",
        )
    return PokemonResponse.from_db_row(row)


async def verificar_api_key(x_api_key: str = Header(default=None)):
    """Dependencia que valida la API Key enviada en la cabecera X-API-Key."""
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida o ausente",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key


@router.post("/", response_model=PokemonResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_pokemon(
    pokemon: PokemonCreate,
    token: str = Depends(verificar_api_key),  # <--- Añadimos la dependencia aquí
):
    """
    Crea un nuevo Pokémon en la base de datos.
    Si el Pokémon ya existe (mismo nombre), lo actualiza.
    """
    # El modelo PokemonCreate ya validó que los datos son correctos.
    # Convertimos a diccionario para pasarlo a la base de datos.
    data = pokemon.model_dump()

    # Guardamos en la DB (nuestro save hace UPSERT)
    await save_pokemon(data)

    # Buscamos el Pokémon recién guardado para devolverlo
    # (Necesitamos buscar para obtener el ID y fetched_at que asigna SQLite)
    row = await get_pokemon_by_name(data["name"])

    if row is None:
        # Esto no debería pasar, pero por seguridad
        raise HTTPException(
            status_code=500, detail="Error interno al recuperar el Pokémon guardado"
        )

    return PokemonResponse.from_db_row(row)
