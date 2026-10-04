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


class FakeClient:
    """Cliente falso que delega en una función."""

    def __init__(self, handler):
        self.handler = handler

    def get(self, url, headers=None, params=None):
        return self.handler(url, headers, params)

    def close(self):
        pass


def test_fetch_pokemon_ok(monkeypatch):
    payload = {"id": 25, "name": "pikachu", "types": []}

    def handler(url, headers, params):
        return FakeResponse(200, payload, {"ETag": '"abc"'})

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))

    data, etag = api.fetch_pokemon("pikachu")
    assert data["name"] == "pikachu"
    assert etag == '"abc"'


def test_fetch_pokemon_normalizes_name(monkeypatch):
    captured = {}

    def handler(url, headers, params):
        captured["url"] = url
        return FakeResponse(200, {"id": 25, "name": "pikachu"})

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))
    api.fetch_pokemon("  PIKACHU  ")

    assert captured["url"].endswith("/pokemon/pikachu")


def test_fetch_pokemon_not_found(monkeypatch):
    def handler(url, headers, params):
        return FakeResponse(404)

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))

    with pytest.raises(api.PokemonAPIError, match="no encontrado"):
        api.fetch_pokemon("noexiste")


def test_fetch_pokemon_timeout(monkeypatch):
    def handler(url, headers, params):
        raise httpx.TimeoutException("boom")

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))

    with pytest.raises(api.PokemonAPIError, match="Timeout"):
        api.fetch_pokemon("pikachu")


def test_fetch_pokemon_network_error(monkeypatch):
    def handler(url, headers, params):
        raise httpx.RequestError("sin red")

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))

    with pytest.raises(api.PokemonAPIError, match="Error de red"):
        api.fetch_pokemon("pikachu")


def test_list_pokemon_names_ok(monkeypatch):
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

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))
    results = api.list_pokemon_names(limit=2, offset=0)

    assert captured["url"].endswith("/pokemon")
    assert captured["params"] == {"limit": 2, "offset": 0}
    assert len(results) == 2


def test_list_pokemon_names_server_error(monkeypatch):
    def handler(url, headers, params):
        return FakeResponse(500)

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))

    with pytest.raises(api.TransientAPIError, match="Error del servidor"):
        api.list_pokemon_names()


def test_fetch_with_retries_succeeds_on_second_attempt(monkeypatch):
    attempts = {"count": 0}

    def handler(url, headers, params):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.TimeoutException("boom")
        return FakeResponse(200, {"id": 25, "name": "pikachu", "types": []})

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))
    monkeypatch.setattr(api.time, "sleep", lambda _: None)

    data, etag = api.fetch_pokemon_with_retries("pikachu", retries=2)
    assert data["name"] == "pikachu"
    assert attempts["count"] == 2


def test_fetch_with_retries_exhausts(monkeypatch):
    def handler(url, headers, params):
        raise httpx.TimeoutException("boom")

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))
    monkeypatch.setattr(api.time, "sleep", lambda _: None)

    with pytest.raises(api.TransientAPIError, match="Timeout"):
        api.fetch_pokemon_with_retries("pikachu", retries=2)


def test_fetch_with_retries_does_not_retry_404(monkeypatch):
    attempts = {"count": 0}

    def handler(url, headers, params):
        attempts["count"] += 1
        return FakeResponse(404)

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))
    monkeypatch.setattr(api.time, "sleep", lambda _: None)

    with pytest.raises(api.PermanentAPIError, match="no encontrado"):
        api.fetch_pokemon_with_retries("noexiste", retries=2)

    assert attempts["count"] == 1


def test_list_pokemon_names_client_error(monkeypatch):
    def handler(url, headers, params):
        return FakeResponse(400)

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))

    with pytest.raises(api.PermanentAPIError, match="Respuesta inesperada"):
        api.list_pokemon_names()


def test_list_pokemon_names_timeout(monkeypatch):
    def handler(url, headers, params):
        raise httpx.TimeoutException("boom")

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))

    with pytest.raises(api.TransientAPIError, match="Timeout"):
        api.list_pokemon_names()


def test_list_pokemon_names_network_error(monkeypatch):
    def handler(url, headers, params):
        raise httpx.RequestError("sin red")

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))

    with pytest.raises(api.TransientAPIError, match="Error de red"):
        api.list_pokemon_names()


def test_fetch_with_retries_zero_retries(monkeypatch):
    def handler(url, headers, params):
        raise httpx.TimeoutException("boom")

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))
    monkeypatch.setattr(api.time, "sleep", lambda _: None)

    with pytest.raises(api.TransientAPIError, match="Timeout"):
        api.fetch_pokemon_with_retries("pikachu", retries=0)


def test_fetch_pokemon_not_modified(monkeypatch):
    def handler(url, headers, params):
        return FakeResponse(304, headers={})

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))

    data, etag = api.fetch_pokemon("pikachu", etag='"abc"')
    assert data is None
    assert etag == '"abc"'


def test_fetch_pokemon_sends_if_none_match(monkeypatch):
    captured = {}

    def handler(url, headers, params):
        captured["headers"] = headers
        return FakeResponse(200, {"id": 25, "name": "pikachu", "types": []})

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))
    api.fetch_pokemon("pikachu", etag='"abc"')

    assert captured["headers"]["If-None-Match"] == '"abc"'


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


def test_fetch_with_retries_uses_jitter(monkeypatch):
    """El delay real debe estar entre 0 y el máximo calculado."""
    captured = {"delays": []}

    def handler(url, headers, params):
        raise httpx.TimeoutException("boom")

    def fake_sleep(seconds):
        captured["delays"].append(seconds)

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))
    monkeypatch.setattr(api.time, "sleep", fake_sleep)

    with pytest.raises(api.TransientAPIError):
        api.fetch_pokemon_with_retries("pikachu", retries=2, base_delay_ms=500)

    # Se llamó dos veces (retries=2)
    assert len(captured["delays"]) == 2

    # El primer delay es entre 0 y 0.5 segundos
    assert 0 <= captured["delays"][0] <= 0.5

    # El segundo delay es entre 0 y 1.0 segundos
    assert 0 <= captured["delays"][1] <= 1.0


def test_fetch_with_retries_jitter_is_not_constant(monkeypatch):
    """Con jitter, el delay no debería ser siempre el mismo."""
    captured = {"delays": []}

    def handler(url, headers, params):
        raise httpx.TimeoutException("boom")

    def fake_sleep(seconds):
        captured["delays"].append(seconds)

    monkeypatch.setattr(api, "get_client", lambda: FakeClient(handler))
    monkeypatch.setattr(api.time, "sleep", fake_sleep)

    # Corremos varias veces acumulando delays
    for _ in range(10):
        with pytest.raises(api.TransientAPIError):
            api.fetch_pokemon_with_retries("pikachu", retries=1)

    # Con jitter, los 10 delays no deberían ser todos iguales.
    # Con 10 valores aleatorios uniformes, la probabilidad de
    # que todos coincidan es prácticamente nula.
    rounded = {round(d, 3) for d in captured["delays"]}
    assert len(rounded) > 1


def test_get_client_has_phase_timeouts():
    client = api.get_client()
    timeout = client.timeout

    assert timeout.connect == 3.0
    assert timeout.read == 10.0
    assert timeout.write == 5.0
    assert timeout.pool == 2.0

    client.close()
