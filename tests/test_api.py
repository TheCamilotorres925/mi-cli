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
        api.httpx, "get",
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
        api.httpx, "get",
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