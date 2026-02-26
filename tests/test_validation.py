import pytest
import requests

from app.utils import validate_gemini_key


class DummyResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_validate_success(monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: DummyResponse(200))
    valid, msg, warn = validate_gemini_key("AI" + "za" + "ValidKey")
    assert valid is True
    assert "ready" in msg
    assert warn is False


def test_validate_invalid_format():
    valid, msg, warn = validate_gemini_key("BadKey")
    assert valid is False
    assert "Invalid key format" in msg
    assert warn is False


def test_validate_401(monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: DummyResponse(401))
    valid, msg, warn = validate_gemini_key("AI" + "za" + "Whatever")
    assert valid is False
    assert "Invalid API key" in msg


def test_validate_timeout(monkeypatch):
    def raiser(*args, **kwargs):
        raise requests.exceptions.Timeout()
    monkeypatch.setattr(requests, "post", raiser)
    valid, msg, warn = validate_gemini_key("AI" + "za" + "Whatever")
    assert valid is True
    assert warn is True
    assert "timed out" in msg


def test_validate_connection_error(monkeypatch):
    def raiser(*args, **kwargs):
        raise requests.exceptions.ConnectionError()
    monkeypatch.setattr(requests, "post", raiser)
    valid, msg, warn = validate_gemini_key("AI" + "za" + "Whatever")
    assert valid is True
    assert warn is True
    assert "No internet" in msg
