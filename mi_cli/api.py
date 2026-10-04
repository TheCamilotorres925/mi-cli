import random
import time
from dataclasses import dataclass

import httpx

BASE_URL = "https://pokeapi.co/api/v2"


class PokemonAPIError(Exception):
    """Error al consumir PokéAPI."""


class TransientAPIError(PokemonAPIError):
    """Error temporal: vale la pena reintentar (timeout, red)."""


class PermanentAPIError(PokemonAPIError):
    """Error permanente: reintentar no ayuda (404)."""


@dataclass
class Pokemon:
    """Datos básicos de un Pokémon.

    Nota: aún no se usa; está prevista para reemplazar los dicts
    que hoy devuelve `PokemonClient.fetch`.
    """

    id: int
    name: str
    height: int
    weight: int
    types: list[str]


class PokemonClient:
    """Cliente para consumir PokéAPI.
    El `httpx.Client` que se pasa debe tener configurada la `base_url`
    (por ejemplo, `https://pokeapi.co/api/v2`) porque este cliente
    usa rutas relativas como `/pokemon/pikachu`.
    """

    def __init__(
        self,
        client: httpx.Client,
        retries: int = 2,
        base_delay_ms: int = 500,
    ) -> None:
        self._client = client
        self.retries = retries
        self.base_delay_ms = base_delay_ms

    def close(self) -> None:
        """Cierra el cliente HTTP subyacente."""
        self._client.close()

    def __enter__(self) -> "PokemonClient":
        """Permite usar PokemonClient como context manager."""
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """Cierra el cliente HTTP al salir del bloque `with`."""
        self.close()

    def fetch(
        self,
        name: str,
        etag: str | None = None,
    ) -> tuple[dict | None, str | None]:
        """Obtiene un Pokémon. Maneja ETag: si no cambió, devuelve (None, etag)."""
        url = f"/pokemon/{name.strip().lower()}"
        headers = {}
        if etag:
            headers["If-None-Match"] = etag

        try:
            response = self._client.get(url, headers=headers)
        except httpx.TimeoutException as exc:
            raise TransientAPIError(f"Timeout al consultar {url}") from exc
        except httpx.RequestError as exc:
            raise TransientAPIError(f"Error de red: {exc}") from exc

        if response.status_code == 304:
            return None, etag
        if response.status_code == 404:
            raise PermanentAPIError(f"Pokémon no encontrado: {name}")
        if response.status_code >= 500:
            raise TransientAPIError(
                f"Error del servidor ({response.status_code}): {url}"
            )
        if response.status_code != 200:
            raise PermanentAPIError(
                f"Respuesta inesperada de la API: {response.status_code}"
            )

        new_etag = response.headers.get("ETag")
        return response.json(), new_etag

    def list_names(self, limit: int = 20, offset: int = 0) -> list[dict]:
        """Devuelve una página de nombres de Pokémon."""
        url = "/pokemon"
        params = {"limit": limit, "offset": offset}

        try:
            response = self._client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise TransientAPIError(f"Timeout al consultar {url}") from exc
        except httpx.RequestError as exc:
            raise TransientAPIError(f"Error de red: {exc}") from exc

        if response.status_code >= 500:
            raise TransientAPIError(
                f"Error del servidor ({response.status_code}): {url}"
            )
        if response.status_code != 200:
            raise PermanentAPIError(
                f"Respuesta inesperada de la API: {response.status_code}"
            )

        return response.json()["results"]

    def fetch_with_retries(
        self, name: str, etag: str | None = None
    ) -> tuple[dict | None, str | None]:
        """Llama a fetch con reintentos y backoff exponencial con jitter."""
        attempt = 0
        while True:
            try:
                return self.fetch(name, etag=etag)
            except PermanentAPIError:
                raise
            except TransientAPIError:
                if attempt >= self.retries:
                    raise
                max_delay_ms = self.base_delay_ms * (2**attempt)
                delay_ms = self._jitter(max_delay_ms)
                time.sleep(delay_ms / 1000)
                attempt += 1

    @staticmethod
    def _jitter(max_ms: int) -> float:
        """Devuelve un delay aleatorio entre 0 y max_ms."""

        return random.uniform(0, max_ms)


class RateLimiter:
    """Ajusta el sleep dinámicamente según cuántos requests llevamos."""

    def __init__(self, base_sleep_ms: int = 0) -> None:
        self.base_sleep_ms = base_sleep_ms
        self.requests_made = 0

    def record_request(self) -> None:
        """Registra que se hizo un request."""
        self.requests_made += 1

    def get_sleep_ms(self) -> int:
        """Devuelve cuántos ms dormir antes del próximo request."""
        base = self.base_sleep_ms

        if self.requests_made > 50:
            base += 200
        if self.requests_made > 100:
            base += 500
        if self.requests_made > 200:
            base += 1000

        return base

    def reset(self) -> None:
        """Reinicia el contador."""
        self.requests_made = 0


def make_default_client(base_url: str = BASE_URL) -> PokemonClient:
    """Crea un PokemonClient con la configuración por defecto."""
    http_client = httpx.Client(
        base_url=base_url,
        timeout=httpx.Timeout(
            connect=3.0,
            read=10.0,
            write=5.0,
            pool=2.0,
        ),
    )
    return PokemonClient(client=http_client)
