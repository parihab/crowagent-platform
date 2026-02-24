import pytest

from services import weather as wx


def test_provider_chain_prefers_met_then_owm(monkeypatch):
    calls = []

    def fake_met(key, loc, name):
        calls.append("met")
        return {"source": "met"}

    def fake_owm(key, lat, lon, name):
        calls.append("owm")
        return {"source": "owm"}

    def fake_open(lat, lon, name):
        calls.append("open")
        return {"source": "open"}

    monkeypatch.setattr(wx, "_fetch_met_office", fake_met)
    monkeypatch.setattr(wx, "_fetch_openweathermap", fake_owm)
    monkeypatch.setattr(wx, "_fetch_open_meteo", fake_open)

    # when both BYOK keys are present the Met Office fetch should be used first
    result = wx.get_weather(
        lat=0,
        lon=0,
        location_name="test",
        met_office_key="KEY1",
        openweathermap_key="KEY2",
        provider="open_meteo",
        enable_fallback=True,
    )
    assert result["source"] == "met"
    assert calls == ["met"]

    # if Met Office fails, we should fall back to OpenWeatherMap
    def bad_met(*args, **kwargs):
        calls.append("met")
        raise RuntimeError("fail")

    monkeypatch.setattr(wx, "_fetch_met_office", bad_met)
    calls.clear()
    result = wx.get_weather(
        lat=0,
        lon=0,
        location_name="test",
        met_office_key="KEY1",
        openweathermap_key="KEY2",
        provider="open_meteo",
        enable_fallback=True,
    )
    assert result["source"] == "owm"
    assert calls == ["met", "owm"]

    # if both key-backed providers fail, we should hit Open-Meteo
    def bad_owm(*args, **kwargs):
        calls.append("owm")
        raise RuntimeError("oops")

    monkeypatch.setattr(wx, "_fetch_openweathermap", bad_owm)
    calls.clear()
    result = wx.get_weather(
        lat=0,
        lon=0,
        location_name="test",
        met_office_key="KEY1",
        openweathermap_key="KEY2",
        provider="open_meteo",
        enable_fallback=True,
    )
    assert result["source"] == "open"
    assert calls == ["met", "owm", "open"]


# caching is handled by st.cache_data on the individual fetch functions; the
# following smoke test simply exercises that behaviour does not raise an error
# and returns a consistent dictionary for repeated calls.

def test_open_meteo_cached(monkeypatch):
    # patch the underlying network call to a counter
    counter = {"calls": 0}

    def fake(lat, lon, name):
        counter["calls"] += 1
        return {"source": "open", "lat": lat, "lon": lon}

    monkeypatch.setattr(wx, "_fetch_open_meteo", wx.st.cache_data(ttl=wx.CACHE_TTL_SECONDS)(fake))
    wx._fetch_open_meteo.clear()

    a = wx.get_weather(lat=1, lon=2, location_name="foo")
    b = wx.get_weather(lat=1, lon=2, location_name="foo")
    assert a == b
    assert counter["calls"] == 1
