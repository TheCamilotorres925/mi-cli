import time

import httpx

BASE_URL = "https://pokeapi.co/api/v2"


def get_client() -> httpx.Client:
    """Crea un cliente httpx con configuración común."""
    return httpx.Client(
        base_url=BASE_URL,
        timeout=10.0,
    )


class PokemonAPIError(Exception):
    """Error al consumir PokéAPI."""


class TransientAPIError(PokemonAPIError):
    """Error temporal: vale la pena reintentar (timeout, red)."""


class PermanentAPIError(PokemonAPIError):
    """Error permanente: reintentar no ayuda (404)."""


def fetch_pokemon(
    name: str,
    etag: str | None = None,
    client: httpx.Client | None = None,
) -> tuple[dict | None, str | None]:
    """Obtiene un Pokémon desde PokéAPI.

    Devuelve (data, etag):
    - Si hay datos nuevos: (dict, "nuevo-etag").
    - Si el servidor responde 304: (None, etag-anterior).
    """
    url = f"/pokemon/{name.strip().lower()}"
    headers = {}
    if etag:
        headers["If-None-Match"] = etag

    own_client = client is None
    active_client: httpx.Client = client if client is not None else get_client()

    try:
        response = active_client.get(url, headers=headers)
    except httpx.TimeoutException as exc:
        raise TransientAPIError(f"Timeout al consultar {url}") from exc
    except httpx.RequestError as exc:
        raise TransientAPIError(f"Error de red: {exc}") from exc
    finally:
        if own_client:
            active_client.close()

    if response.status_code == 304:
        return None, etag

    if response.status_code == 404:
        raise PermanentAPIError(f"Pokémon no encontrado: {name}")
    if response.status_code >= 500:
        raise TransientAPIError(f"Error del servidor ({response.status_code}): {url}")
    if response.status_code != 200:
        raise PermanentAPIError(
            f"Respuesta inesperada de la API: {response.status_code}"
        )

    new_etag = response.headers.get("ETag")
    return response.json(), new_etag


def list_pokemon_names(
    limit: int = 20,
    offset: int = 0,
    client: httpx.Client | None = None,
) -> list[dict]:
    """Devuelve una página de nombres de Pokémon desde PokéAPI."""
    url = "/pokemon"
    params = {"limit": limit, "offset": offset}

    own_client = client is None
    active_client: httpx.Client = client if client is not None else get_client()

    try:
        response = active_client.get(url, params=params)
    except httpx.TimeoutException as exc:
        raise TransientAPIError(f"Timeout al consultar {url}") from exc
    except httpx.RequestError as exc:
        raise TransientAPIError(f"Error de red: {exc}") from exc
    finally:
        if own_client:
            active_client.close()

    if response.status_code >= 500:
        raise TransientAPIError(f"Error del servidor ({response.status_code}): {url}")
    if response.status_code != 200:
        raise PermanentAPIError(
            f"Respuesta inesperada de la API: {response.status_code}"
        )

    return response.json()["results"]


def fetch_pokemon_with_retries(
    name: str,
    retries: int = 2,
    base_delay_ms: int = 500,
    etag: str | None = None,
    client: httpx.Client | None = None,
) -> tuple[dict | None, str | None]:
    """Llama a fetch_pokemon con reintentos y backoff exponencial."""
    attempt = 0
    while True:
        try:
            return fetch_pokemon(name, etag=etag, client=client)
        except PermanentAPIError:
            raise
        except TransientAPIError:
            if attempt >= retries:
                raise
            delay = (base_delay_ms * (2**attempt)) / 1000
            time.sleep(delay)
            attempt += 1
