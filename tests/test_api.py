import httpx
import pytest

from mi_cli import api


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


def test_fetch_pokemon_ok(monkeypatch):
    payload = {"id": 25, "name": "pikachu", "types": []}
    monkeypatch.setattr(
        api.httpx,
        "get",
        lambda url, timeout: FakeResponse(200, payload),
    )

    result = api.fetch_pokemon("pikachu")
    assert result["name"] == "pikachu"


def test_fetch_pokemon_normalizes_name(monkeypatch):
    captured = {}

    def fake_get(url, timeout):
        captured["url"] = url
        return FakeResponse(200, {"id": 25, "name": "pikachu"})

    monkeypatch.setattr(api.httpx, "get", fake_get)
    api.fetch_pokemon("  PIKACHU  ")

    assert captured["url"].endswith("/pokemon/pikachu")


def test_fetch_pokemon_not_found(monkeypatch):
    monkeypatch.setattr(
        api.httpx,
        "get",
        lambda url, timeout: FakeResponse(404),
    )

    with pytest.raises(api.PokemonAPIError, match="no encontrado"):
        api.fetch_pokemon("noexiste")


def test_fetch_pokemon_timeout(monkeypatch):
    def raise_timeout(url, timeout):
        raise httpx.TimeoutException("boom")

    monkeypatch.setattr(api.httpx, "get", raise_timeout)

    with pytest.raises(api.PokemonAPIError, match="Timeout"):
        api.fetch_pokemon("pikachu")


def test_fetch_pokemon_network_error(monkeypatch):
    def raise_request_error(url, timeout):
        raise httpx.RequestError("sin red")

    monkeypatch.setattr(api.httpx, "get", raise_request_error)

    with pytest.raises(api.PokemonAPIError, match="Error de red"):
        api.fetch_pokemon("pikachu")


def test_list_pokemon_names_ok(monkeypatch):
    payload = {
        "results": [
            {"name": "bulbasaur", "url": "https://pokeapi.co/api/v2/pokemon/1/"},
            {"name": "ivysaur", "url": "https://pokeapi.co/api/v2/pokemon/2/"},
        ]
    }
    captured = {}

    def fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse(200, payload)

    monkeypatch.setattr(api.httpx, "get", fake_get)
    results = api.list_pokemon_names(limit=2, offset=0)

    assert captured["url"].endswith("/pokemon")
    assert captured["params"] == {"limit": 2, "offset": 0}
    assert len(results) == 2
    assert results[0]["name"] == "bulbasaur"


def test_list_pokemon_names_error(monkeypatch):
    monkeypatch.setattr(
        api.httpx,
        "get",
        lambda url, params, timeout: FakeResponse(500),
    )

    with pytest.raises(api.PokemonAPIError, match="Respuesta inesperada"):
        api.list_pokemon_names()
