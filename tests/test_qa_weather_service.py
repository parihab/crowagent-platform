"""
QA Test Suite — services/weather.py
=====================================
Tests for weather provider fallback chain, cache correctness, and offline mode.
Validates actual module API: WMO_CODES dict, validate_temperature, get_weather.

Note: _fetch_open_meteo is decorated with @st.cache_data and propagates exceptions
internally. Fallback handling lives in get_weather(). Tests use get_weather() to
verify the end-to-end fallback behaviour.
"""
from __future__ import annotations

import os
import sys
import pytest

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from services import weather as wx


class TestWMOCodes:
    def test_wmo_codes_is_dict(self):
        assert isinstance(wx.WMO_CODES, dict)
        assert len(wx.WMO_CODES) > 0

    def test_known_code_0_exists(self):
        assert 0 in wx.WMO_CODES

    def test_each_entry_is_tuple_of_two(self):
        for code, val in wx.WMO_CODES.items():
            assert isinstance(val, tuple), f"WMO_CODES[{code}] should be a tuple"
            assert len(val) == 2, f"WMO_CODES[{code}] should have 2 elements (desc, icon)"

    def test_icon_is_non_empty_string(self):
        for code, (desc, icon) in wx.WMO_CODES.items():
            assert isinstance(icon, str) and len(icon) > 0

    def test_description_is_non_empty_string(self):
        for code, (desc, icon) in wx.WMO_CODES.items():
            assert isinstance(desc, str) and len(desc) > 0


class TestModuleConstants:
    def test_default_lat_is_float(self):
        assert isinstance(wx.DEFAULT_LAT, float)
        assert -90 <= wx.DEFAULT_LAT <= 90

    def test_default_lon_is_float(self):
        assert isinstance(wx.DEFAULT_LON, float)
        assert -180 <= wx.DEFAULT_LON <= 180

    def test_default_location_name_is_string(self):
        assert isinstance(wx.DEFAULT_LOCATION_NAME, str)
        assert len(wx.DEFAULT_LOCATION_NAME) > 0

    def test_providers_dict_not_empty(self):
        assert len(wx.PROVIDERS) > 0

    def test_cache_ttl_is_positive(self):
        assert wx.CACHE_TTL_SECONDS > 0


class TestTemperatureValidation:
    @pytest.mark.parametrize("temp,expected_valid", [
        (-30.0, True), (0.0, True), (10.5, True), (40.0, True),
        (-60.0, False), (80.0, False),
    ])
    def test_validate_temperature(self, temp, expected_valid):
        valid, msg = wx.validate_temperature(temp)
        assert valid == expected_valid, (
            f"temp={temp}: expected {expected_valid}, got {valid} ({msg})"
        )

    def test_validation_message_non_empty_on_failure(self):
        valid, msg = wx.validate_temperature(999.0)
        assert not valid
        assert len(msg) > 0

    def test_validation_message_on_success(self):
        valid, msg = wx.validate_temperature(15.0)
        assert valid


class TestGetWeatherFallback:
    """Test that get_weather falls back to manual temperature when all APIs fail."""

    def test_get_weather_fallback_on_all_api_failures(self, monkeypatch):
        """When all APIs raise, get_weather returns manual_temp_c."""
        import requests

        def raise_conn_error(*args, **kwargs):
            raise requests.exceptions.ConnectionError("offline")

        wx._fetch_open_meteo.clear()
        monkeypatch.setattr(requests, "get", raise_conn_error)

        result = wx.get_weather(
            lat=51.4543, lon=-0.9781,
            location_name="Reading",
            provider="open_meteo",
            met_office_key=None, openweathermap_key=None,
            manual_temp_c=15.5,
        )
        # Should fall back to manual temperature
        assert isinstance(result, dict)
        assert "temperature_c" in result
        assert result["temperature_c"] == 15.5
        assert result["is_live"] is False

    def test_get_weather_returns_correct_structure(self, monkeypatch):
        """get_weather must always return a dict with required keys."""
        import requests

        def raise_all(*args, **kwargs):
            raise requests.exceptions.ConnectionError()

        wx._fetch_open_meteo.clear()
        monkeypatch.setattr(requests, "get", raise_all)

        result = wx.get_weather(lat=51.4, lon=-0.9, location_name="Test")
        assert isinstance(result, dict)
        for key in ("temperature_c", "is_live"):
            assert key in result, f"Missing key: {key}"


class TestProviderFallbackChain:
    def test_open_meteo_preferred_when_no_keys(self, monkeypatch):
        called = []

        def mock_open_meteo(lat, lon, location_name):
            called.append("open_meteo")
            return {
                "temperature_c": 10.5, "is_live": True, "condition_icon": "☀️",
                "wind_speed_mph": 5.0, "humidity": 70, "humidity_pct": 70,
                "wind_dir_deg": 0, "feels_like_c": 8.5,
                "condition": "Clear", "location_name": location_name,
                "source": "Open-Meteo", "fetched_utc": "2026-01-01T12:00:00Z",
            }

        wx._fetch_open_meteo.clear()
        monkeypatch.setattr(wx, "_fetch_open_meteo", mock_open_meteo)

        result = wx.get_weather(
            lat=51.4543, lon=-0.9781, location_name="Reading",
            provider="open_meteo", met_office_key=None, openweathermap_key=None,
        )
        assert "open_meteo" in called

    def test_manual_temp_c_parameter_exists(self):
        import inspect
        sig = inspect.signature(wx.get_weather)
        assert "manual_temp_c" in sig.parameters


class TestWindCompass:
    @pytest.mark.parametrize("degrees,expected", [
        (0, "N"), (45, "NE"), (90, "E"), (135, "SE"),
        (180, "S"), (225, "SW"), (270, "W"), (315, "NW"), (360, "N"),
    ])
    def test_compass_points(self, degrees, expected):
        result = wx.wind_compass(degrees)
        assert result == expected, f"degrees={degrees}: expected {expected}, got {result}"
