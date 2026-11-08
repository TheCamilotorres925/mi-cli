# ruff: noqa: B008
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from ..auth import decode_access_token
from ..config import settings
from ..database import get_all_pokemon, get_pokemon_by_name, get_user, save_pokemon
from ..schemas import PokemonCreate, PokemonResponse

router = APIRouter(
    prefix="/pokemon",
    tags=["Pokemon"],
)

# Esquemas de seguridad para Swagger
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


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


async def verificar_autenticacion(
    api_key: str | None = Depends(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    """
    Acepta autenticación vía API Key (X-API-Key) o JWT (Authorization: Bearer <token>).
    """
    # 1. ¿Viene una API Key?
    if api_key:
        if api_key == settings.API_KEY:
            return "api_key_user"
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key inválida",
            )

    # 2. ¿Viene un token JWT?
    if bearer:
        token = bearer.credentials
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
            )

        username = payload.get("sub")
        user = await get_user(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado",
            )
        return username

    # 3. No hay ninguna credencial
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se proporcionó autenticación (X-API-Key o Bearer token)",
    )


@router.post("/", response_model=PokemonResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_pokemon(
    pokemon: PokemonCreate,
    authenticated_user: str = Depends(verificar_autenticacion),  # <-- Aquí
):
    """Crea o actualiza un Pokémon. Requiere API Key o JWT."""
    data = pokemon.model_dump()
    await save_pokemon(data)
    row = await get_pokemon_by_name(data["name"])
    if row is None:
        raise HTTPException(status_code=500, detail="Error interno")
    return PokemonResponse.from_db_row(row)
