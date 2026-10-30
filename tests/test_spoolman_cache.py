import requests

from src import spoolman as spoolman_module
from src.spoolman import SpoolmanAPI


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_cache_hit_within_ttl(monkeypatch):
    current = {"value": 100.0}

    def fake_monotonic():
        return current["value"]

    monkeypatch.setattr(spoolman_module.time, "monotonic", fake_monotonic)

    calls = {"count": 0}

    def fake_get(*args, **kwargs):
        calls["count"] += 1
        return FakeResponse(200, [{"id": 1}])

    monkeypatch.setattr(spoolman_module.requests, "get", fake_get)

    api = SpoolmanAPI("http://spool", cache_ttl_seconds=30, error_ttl_seconds=5)

    assert api.get_spool_for_printer("P1") == {"id": 1}
    assert api.get_spool_for_printer("P1") == {"id": 1}
    assert calls["count"] == 1


def test_cache_miss_after_ttl(monkeypatch):
    current = {"value": 200.0}

    def fake_monotonic():
        return current["value"]

    monkeypatch.setattr(spoolman_module.time, "monotonic", fake_monotonic)

    calls = {"count": 0}

    def fake_get(*args, **kwargs):
        calls["count"] += 1
        return FakeResponse(200, [{"id": calls["count"]}])

    monkeypatch.setattr(spoolman_module.requests, "get", fake_get)

    api = SpoolmanAPI("http://spool", cache_ttl_seconds=30, error_ttl_seconds=5)

    first = api.get_spool_for_printer("P1")
    current["value"] = 231.0
    second = api.get_spool_for_printer("P1")

    assert first != second
    assert calls["count"] == 2


def test_error_cache_ttl(monkeypatch):
    current = {"value": 300.0}

    def fake_monotonic():
        return current["value"]

    monkeypatch.setattr(spoolman_module.time, "monotonic", fake_monotonic)

    calls = {"count": 0}

    def fake_get(*args, **kwargs):
        calls["count"] += 1
        raise requests.exceptions.RequestException("boom")

    monkeypatch.setattr(spoolman_module.requests, "get", fake_get)

    api = SpoolmanAPI("http://spool", cache_ttl_seconds=30, error_ttl_seconds=10)

    assert api.get_spool_for_printer("P1") is None
    current["value"] = 305.0
    assert api.get_spool_for_printer("P1") is None
    assert calls["count"] == 1
    current["value"] = 311.0
    assert api.get_spool_for_printer("P1") is None
    assert calls["count"] == 2
