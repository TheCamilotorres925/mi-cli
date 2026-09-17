import httpx

BASE_URL = "https://pokeapi.co/api/v2"


class PokemonAPIError(Exception):
    """Error al consumir PokéAPI."""


def fetch_pokemon(name: str) -> dict:
    """Obtiene un Pokémon por nombre o id desde PokéAPI."""
    url = f"{BASE_URL}/pokemon/{name.strip().lower()}"
    try:
        response = httpx.get(url, timeout=10.0)
    except httpx.TimeoutException as exc:
        raise PokemonAPIError(f"Timeout al consultar {url}") from exc
    except httpx.RequestError as exc:
        raise PokemonAPIError(f"Error de red: {exc}") from exc

    if response.status_code == 404:
        raise PokemonAPIError(f"Pokémon no encontrado: {name}")
    if response.status_code != 200:
        raise PokemonAPIError(f"Respuesta inesperada de la API: {response.status_code}")

    return response.json()


def list_pokemon_names(limit: int = 20, offset: int = 0) -> list[dict]:
    """Devuelve una página de nombres de Pokémon desde PokéAPI."""
    url = f"{BASE_URL}/pokemon"
    params = {"limit": limit, "offset": offset}
    try:
        response = httpx.get(url, params=params, timeout=10.0)
    except httpx.TimeoutException as exc:
        raise PokemonAPIError(f"Timeout al consultar {url}") from exc
    except httpx.RequestError as exc:
        raise PokemonAPIError(f"Error de red: {exc}") from exc

    if response.status_code != 200:
        raise PokemonAPIError(f"Respuesta inesperada de la API: {response.status_code}")

    return response.json()["results"]
