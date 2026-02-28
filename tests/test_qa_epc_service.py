"""
QA Test Suite — services/epc.py
================================
Tests for DEF-008 regression (silent stub fallback) and EPC service correctness.
"""
from __future__ import annotations

import os
import sys
import pytest

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from services.epc import fetch_epc_data, search_addresses


# ─────────────────────────────────────────────────────────────────────────────
# DEF-008 REGRESSION: _is_stub flag
# ─────────────────────────────────────────────────────────────────────────────

class TestEpcStubFlag:
    """Verify that _is_stub is always present and True when no API configured."""

    def test_stub_flag_present_when_no_api_configured(self, monkeypatch):
        monkeypatch.delenv("EPC_API_URL", raising=False)
        monkeypatch.delenv("EPC_API_KEY", raising=False)
        result = fetch_epc_data("RG1 1AA")
        assert "_is_stub" in result, "Response missing _is_stub flag"
        assert result["_is_stub"] is True

    def test_stub_flag_false_on_successful_api_call(self, monkeypatch):
        """When API returns 200 JSON, _is_stub should be False."""
        import requests

        class MockGoodResp:
            status_code = 200
            content = b'{"floor_area_m2": 300, "built_year": 2005, "epc_band": "B"}'
            def raise_for_status(self): pass
            def json(self):
                return {"floor_area_m2": 300, "built_year": 2005, "epc_band": "B"}

        monkeypatch.setenv("EPC_API_URL", "https://fake-epc.test/api")
        monkeypatch.setenv("EPC_API_KEY", "testkey")
        monkeypatch.setattr(requests, "get", lambda *a, **kw: MockGoodResp())

        result = fetch_epc_data("SW1A 2AA")
        assert result["_is_stub"] is False
        assert result["floor_area_m2"] == 300.0
        assert result["epc_band"] == "B"

    def test_stub_flag_true_on_api_failure(self, monkeypatch):
        """When API raises an exception, fallback stub sets _is_stub=True."""
        import requests

        monkeypatch.setenv("EPC_API_URL", "https://fake-epc.test/api")
        monkeypatch.setattr(
            requests, "get",
            lambda *a, **kw: (_ for _ in ()).throw(requests.exceptions.ConnectionError())
        )

        result = fetch_epc_data("SW1A 2AA")
        assert result["_is_stub"] is True


class TestEpcStubData:
    def test_stub_has_required_keys(self, monkeypatch):
        monkeypatch.delenv("EPC_API_URL", raising=False)
        monkeypatch.delenv("EPC_API_KEY", raising=False)
        result = fetch_epc_data("SW1A 1AA")
        for key in ("floor_area_m2", "built_year", "epc_band", "_is_stub"):
            assert key in result, f"Missing key: {key}"

    def test_stub_floor_area_is_positive(self, monkeypatch):
        monkeypatch.delenv("EPC_API_URL", raising=False)
        monkeypatch.delenv("EPC_API_KEY", raising=False)
        result = fetch_epc_data("M1 1AA")
        assert result["floor_area_m2"] > 0

    def test_stub_epc_band_is_string(self, monkeypatch):
        monkeypatch.delenv("EPC_API_URL", raising=False)
        monkeypatch.delenv("EPC_API_KEY", raising=False)
        result = fetch_epc_data("E1 6RF")
        assert isinstance(result["epc_band"], str)
        assert result["epc_band"] in ("A", "B", "C", "D", "E", "F", "G")

    def test_invalid_postcode_raises(self, monkeypatch):
        monkeypatch.delenv("EPC_API_URL", raising=False)
        monkeypatch.delenv("EPC_API_KEY", raising=False)
        with pytest.raises(ValueError):
            fetch_epc_data("X")

    def test_short_postcode_raises(self, monkeypatch):
        monkeypatch.delenv("EPC_API_URL", raising=False)
        monkeypatch.delenv("EPC_API_KEY", raising=False)
        with pytest.raises(ValueError):
            fetch_epc_data("AB1")

    def test_valid_postcode_formats_accepted(self, monkeypatch):
        monkeypatch.delenv("EPC_API_URL", raising=False)
        monkeypatch.delenv("EPC_API_KEY", raising=False)
        # Various UK postcode formats
        for pc in ("SW1A 2AA", "EC1A 1BB", "W1A 0AX", "M1 1AE", "B1 1BB"):
            result = fetch_epc_data(pc)
            assert "_is_stub" in result

    def test_returns_dict(self, monkeypatch):
        monkeypatch.delenv("EPC_API_URL", raising=False)
        monkeypatch.delenv("EPC_API_KEY", raising=False)
        result = fetch_epc_data("LS1 1BA")
        assert isinstance(result, dict)

def test_search_addresses_uses_epc_api_rows(monkeypatch):
    import requests

    class MockResp:
        status_code = 200
        content = b"1"

        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    calls = []

    def mock_get(url, *args, **kwargs):
        calls.append(url)
        if "epc.opendatacommunities.org" in url and "domestic/search" in url:
            return MockResp(
                {
                    "rows": [
                        {
                            "address1": "1 Test Street",
                            "address2": "Reading",
                            "postcode": "RG1 1AA",
                            "latitude": "51.454",
                            "longitude": "-0.973",
                        }
                    ]
                }
            )
        if "epc.opendatacommunities.org" in url and "non-domestic/search" in url:
            return MockResp({"rows": []})
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setenv("EPC_API_KEY", "abc123")
    monkeypatch.setattr(requests, "get", mock_get)

    result = search_addresses("rg11aa", limit=3)
    assert result
    assert result[0]["postcode"] == "RG1 1AA"
    assert "1 Test Street" in result[0]["label"]
    assert any("domestic/search" in c for c in calls)


def test_search_addresses_falls_back_to_findthatpostcode(monkeypatch):
    import requests

    class MockResp:
        status_code = 200
        content = b"1"

        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    def mock_get(url, *args, **kwargs):
        if "findthatpostcode.uk" in url:
            return MockResp({"data": {"postcode": "SW1A 2AA", "lat": 51.501, "lon": -0.141}})
        raise requests.exceptions.ConnectionError()

    monkeypatch.delenv("EPC_API_KEY", raising=False)
    monkeypatch.setattr(requests, "get", mock_get)

    result = search_addresses("SW1A2AA", limit=5)
    assert result == [
        {"label": "SW1A 2AA, UK", "lat": 51.501, "lon": -0.141, "postcode": "SW1A 2AA"}
    ]


def test_search_addresses_rejects_non_postcode_query():
    assert search_addresses("this is not a postcode", limit=5) == []
