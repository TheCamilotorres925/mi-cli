import httpx
import pytest

from mi_cli import api


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: dict | None = None,
        headers: dict | None = None,
    ):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def json(self) -> dict:
        return self._payload


class FakeHTTPClient:
    """Simula un httpx.Client para tests."""

    def __init__(self, handler):
        self.handler = handler

    def get(self, url, headers=None, params=None):
        return self.handler(url, headers, params)

    def close(self):
        pass


def make_client(handler, retries=2):
    """Crea un PokemonClient con un httpx.Client falso inyectado."""
    fake_http = FakeHTTPClient(handler)
    return api.PokemonClient(client=fake_http, retries=retries)


def test_fetch_pokemon_ok():
    payload = {"id": 25, "name": "pikachu", "types": []}

    def handler(url, headers, params):
        return FakeResponse(200, payload, {"ETag": '"abc"'})

    client = make_client(handler)
    data, etag = client.fetch("pikachu")

    assert data["name"] == "pikachu"
    assert etag == '"abc"'


def test_fetch_pokemon_normalizes_name():
    captured = {}

    def handler(url, headers, params):
        captured["url"] = url
        return FakeResponse(200, {"id": 25, "name": "pikachu"})

    client = make_client(handler)
    client.fetch("  PIKACHU  ")

    assert captured["url"].endswith("/pokemon/pikachu")


def test_fetch_pokemon_not_found():
    def handler(url, headers, params):
        return FakeResponse(404)

    client = make_client(handler)

    with pytest.raises(api.PermanentAPIError, match="no encontrado"):
        client.fetch("noexiste")


def test_fetch_pokemon_timeout():
    def handler(url, headers, params):
        raise httpx.TimeoutException("boom")

    client = make_client(handler)

    with pytest.raises(api.TransientAPIError, match="Timeout"):
        client.fetch("pikachu")


def test_fetch_pokemon_network_error():
    def handler(url, headers, params):
        raise httpx.RequestError("sin red")

    client = make_client(handler)

    with pytest.raises(api.TransientAPIError, match="Error de red"):
        client.fetch("pikachu")


def test_list_pokemon_names_ok():
    payload = {
        "results": [
            {"name": "bulbasaur", "url": "..."},
            {"name": "ivysaur", "url": "..."},
        ]
    }
    captured = {}

    def handler(url, headers, params):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse(200, payload)

    client = make_client(handler)
    results = client.list_names(limit=2, offset=0)

    assert captured["url"].endswith("/pokemon")
    assert captured["params"] == {"limit": 2, "offset": 0}
    assert len(results) == 2


def test_list_pokemon_names_server_error():
    def handler(url, headers, params):
        return FakeResponse(500)

    client = make_client(handler)

    with pytest.raises(api.TransientAPIError, match="Error del servidor"):
        client.list_names()


def test_list_pokemon_names_client_error():
    def handler(url, headers, params):
        return FakeResponse(400)

    client = make_client(handler)

    with pytest.raises(api.PermanentAPIError, match="Respuesta inesperada"):
        client.list_names()


def test_list_pokemon_names_timeout():
    def handler(url, headers, params):
        raise httpx.TimeoutException("boom")

    client = make_client(handler)

    with pytest.raises(api.TransientAPIError, match="Timeout"):
        client.list_names()


def test_list_pokemon_names_network_error():
    def handler(url, headers, params):
        raise httpx.RequestError("sin red")

    client = make_client(handler)

    with pytest.raises(api.TransientAPIError, match="Error de red"):
        client.list_names()


def test_fetch_with_retries_succeeds_on_second_attempt(monkeypatch):
    attempts = {"count": 0}

    def handler(url, headers, params):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.TimeoutException("boom")
        return FakeResponse(200, {"id": 25, "name": "pikachu", "types": []})

    client = make_client(handler, retries=2)
    monkeypatch.setattr(api.time, "sleep", lambda _: None)

    data, etag = client.fetch_with_retries("pikachu")
    assert data["name"] == "pikachu"
    assert attempts["count"] == 2


def test_fetch_with_retries_exhausts(monkeypatch):
    def handler(url, headers, params):
        raise httpx.TimeoutException("boom")

    client = make_client(handler, retries=2)
    monkeypatch.setattr(api.time, "sleep", lambda _: None)

    with pytest.raises(api.TransientAPIError, match="Timeout"):
        client.fetch_with_retries("pikachu")


def test_fetch_with_retries_does_not_retry_404(monkeypatch):
    attempts = {"count": 0}

    def handler(url, headers, params):
        attempts["count"] += 1
        return FakeResponse(404)

    client = make_client(handler, retries=2)
    monkeypatch.setattr(api.time, "sleep", lambda _: None)

    with pytest.raises(api.PermanentAPIError, match="no encontrado"):
        client.fetch_with_retries("noexiste")

    assert attempts["count"] == 1


def test_fetch_with_retries_zero_retries(monkeypatch):
    def handler(url, headers, params):
        raise httpx.TimeoutException("boom")

    client = make_client(handler, retries=0)
    monkeypatch.setattr(api.time, "sleep", lambda _: None)

    with pytest.raises(api.TransientAPIError, match="Timeout"):
        client.fetch_with_retries("pikachu")


def test_fetch_pokemon_not_modified():
    def handler(url, headers, params):
        return FakeResponse(304, headers={})

    client = make_client(handler)
    data, etag = client.fetch("pikachu", etag='"abc"')

    assert data is None
    assert etag == '"abc"'


def test_fetch_pokemon_sends_if_none_match():
    captured = {}

    def handler(url, headers, params):
        captured["headers"] = headers
        return FakeResponse(200, {"id": 25, "name": "pikachu", "types": []})

    client = make_client(handler)
    client.fetch("pikachu", etag='"abc"')

    assert captured["headers"]["If-None-Match"] == '"abc"'


def test_pokemon_client_make_default():
    """PokemonClient.make_default devuelve un PokemonClient configurado."""
    client = api.PokemonClient.make_default()
    assert isinstance(client, api.PokemonClient)
    client.close()


def test_rate_limiter_no_sleep_when_user_asks():
    limiter = api.RateLimiter(base_sleep_ms=100)
    assert limiter.get_sleep_ms() == 100


def test_rate_limiter_adds_backoff_after_many_requests():
    limiter = api.RateLimiter(base_sleep_ms=0)
    limiter.requests_made = 51
    assert limiter.get_sleep_ms() == 200


def test_rate_limiter_record_request():
    limiter = api.RateLimiter(base_sleep_ms=0)
    assert limiter.requests_made == 0
    limiter.record_request()
    limiter.record_request()
    assert limiter.requests_made == 2


def test_rate_limiter_reset():
    limiter = api.RateLimiter(base_sleep_ms=0)
    limiter.record_request()
    limiter.reset()
    assert limiter.requests_made == 0
