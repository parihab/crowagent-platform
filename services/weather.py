# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — Weather Integration Module
# © 2026 Aparajita Parihar. All rights reserved.
#
# Provider hierarchy (configurable via admin panel):
#   1. Met Office DataPoint  — UK only, authoritative, free with registration
#   2. OpenWeatherMap        — Global, free tier 1,000 req/day, key required
#   3. Open-Meteo            — Global, fully free, no key, 10,000 req/day (default)
#   4. Manual override       — Offline fallback; user-set temperature slider
#
# BYOK (Bring Your Own Key) model:
#   API keys are supplied by the user/admin in the sidebar config panel.
#   Keys are stored in st.session_state only (cleared on browser close).
#   Never stored server-side in plaintext.
#
# Caching: st.cache_data TTL=3600 s — ≤24 API calls/day per location.
# Fallback chain: primary provider → Open-Meteo → manual override.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations
import streamlit as st
import requests
from datetime import datetime, timezone
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# MODULE CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_LAT           = 51.4543          # Reading, Berkshire
DEFAULT_LON           = -0.9781
DEFAULT_LOCATION_NAME = "Reading, Berkshire, UK"
MET_OFFICE_LOCATION   = "354230"         # Default Met Office DataPoint site ID
OPEN_METEO_BASE_URL   = "https://api.open-meteo.com/v1/forecast"
OWM_BASE_URL          = "https://api.openweathermap.org/data/2.5/weather"
CACHE_TTL_SECONDS     = 3600            # 1 hour

# Supported provider identifiers
PROVIDERS = {
    "open_meteo":       "Open-Meteo (free, no key)",
    "met_office":       "Met Office DataPoint (UK, free with key)",
    "openweathermap":   "OpenWeatherMap (free tier, key required)",
}

# WMO weather code → (description, emoji)
WMO_CODES: dict[int, tuple[str, str]] = {
    0:  ("Clear sky",         "☀️"),
    1:  ("Mainly clear",      "🌤️"),
    2:  ("Partly cloudy",     "⛅"),
    3:  ("Overcast",          "☁️"),
    45: ("Foggy",             "🌫️"),
    48: ("Icy fog",           "🌫️"),
    51: ("Light drizzle",     "🌦️"),
    53: ("Moderate drizzle",  "🌦️"),
    55: ("Dense drizzle",     "🌧️"),
    61: ("Slight rain",       "🌧️"),
    63: ("Moderate rain",     "🌧️"),
    65: ("Heavy rain",        "🌧️"),
    71: ("Slight snow",       "🌨️"),
    73: ("Moderate snow",     "❄️"),
    75: ("Heavy snow",        "❄️"),
    80: ("Rain showers",      "🌦️"),
    81: ("Moderate showers",  "🌦️"),
    82: ("Heavy showers",     "⛈️"),
    85: ("Snow showers",      "🌨️"),
    95: ("Thunderstorm",      "⛈️"),
    96: ("Thunderstorm+hail", "⛈️"),
    99: ("Thunderstorm+hail", "⛈️"),
}


# ─────────────────────────────────────────────────────────────────────────────
# OPEN-METEO  (primary free source — no API key required)
# Cached per (lat, lon) pair; different locations get independent cache entries.
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _fetch_open_meteo(lat: float, lon: float, location_name: str) -> dict:
    """
    Fetch current conditions from Open-Meteo public API.
    Free tier: 10,000 req/day, ~100/min. No API key required.
    Results are cached per location for up to 1 hour.
    """
    params = {
        "latitude":        lat,
        "longitude":       lon,
        "current": [
            "temperature_2m", "apparent_temperature",
            "wind_speed_10m", "wind_direction_10m",
            "relative_humidity_2m", "precipitation",
            "weather_code", "cloud_cover", "surface_pressure",
        ],
        "wind_speed_unit": "mph",
        "timezone":        "auto",
        "forecast_days":   1,
    }
    resp = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=8)
    resp.raise_for_status()
    c = resp.json()["current"]

    wcode = int(c.get("weather_code", 0))
    desc, icon = WMO_CODES.get(wcode, ("Unknown", "🌡️"))

    return {
        "temperature_c":   round(float(c["temperature_2m"]), 1),
        "feels_like_c":    round(float(c.get("apparent_temperature", c["temperature_2m"])), 1),
        "wind_speed_mph":  round(float(c["wind_speed_10m"]), 1),
        "wind_dir_deg":    int(c.get("wind_direction_10m", 225)),
        "humidity_pct":    int(c.get("relative_humidity_2m", 75)),
        "precip_mm":       round(float(c.get("precipitation", 0.0)), 1),
        "cloud_pct":       int(c.get("cloud_cover", 60)),
        "pressure_hpa":    round(float(c.get("surface_pressure", 1013.0)), 1),
        "condition":       desc,
        "condition_icon":  icon,
        "source":          "Open-Meteo API",
        "source_url":      "https://open-meteo.com",
        "is_live":         True,
        "fetched_utc":     datetime.now(timezone.utc).isoformat(),
        "location_name":   location_name,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MET OFFICE DATAPOINT  (optional — UK sites, authoritative for Part L / HDD)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _fetch_met_office(api_key: str, location_id: str, location_name: str) -> dict:
    """
    Fetch from Met Office DataPoint hourly observation endpoint.
    Free with registration at metoffice.gov.uk/services/data/datapoint.
    Cached for 1 hour per (api_key, location_id) pair.
    """
    url = (
        f"https://datapoint.metoffice.gov.uk/public/data/"
        f"val/wxobs/all/json/{location_id}"
        f"?res=hourly&key={api_key}"
    )
    resp = requests.get(url, timeout=8)
    resp.raise_for_status()
    loc     = resp.json()["SiteRep"]["DV"]["Location"]
    periods = loc["Period"]
    if isinstance(periods, dict):
        periods = [periods]
    reps = periods[-1]["Rep"]
    if isinstance(reps, dict):
        reps = [reps]
    obs = reps[-1]

    temp = float(obs.get("T", 10.5))
    wind = float(obs.get("S", 9.2))

    return {
        "temperature_c":   round(temp, 1),
        "feels_like_c":    round(temp - 1.5, 1),
        "wind_speed_mph":  round(wind, 1),
        "wind_dir_deg":    0,
        "humidity_pct":    int(obs.get("H", 75)),
        "precip_mm":       0.0,
        "cloud_pct":       int(float(obs.get("C", 4)) * 12.5),
        "pressure_hpa":    float(obs.get("P", 1013.0)),
        "condition":       "Met Office observation",
        "condition_icon":  "🌡️",
        "source":          "Met Office DataPoint",
        "source_url":      "https://www.metoffice.gov.uk/services/data/datapoint",
        "is_live":         True,
        "fetched_utc":     datetime.now(timezone.utc).isoformat(),
        "location_name":   location_name,
    }


# ─────────────────────────────────────────────────────────────────────────────
# OPENWEATHERMAP  (global, free tier — 1,000 calls/day; BYOK required)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _fetch_openweathermap(api_key: str, lat: float, lon: float, location_name: str) -> dict:
    """
    Fetch current conditions from OpenWeatherMap Current Weather API v2.5.
    Free tier: 1,000 calls/day. API key required (BYOK model).
    Cached for 1 hour per (api_key, lat, lon) combination.
    """
    params = {
        "lat":   lat,
        "lon":   lon,
        "appid": api_key,
        "units": "metric",
    }
    resp = requests.get(OWM_BASE_URL, params=params, timeout=8)
    resp.raise_for_status()
    d = resp.json()

    main    = d.get("main", {})
    wind    = d.get("wind", {})
    clouds  = d.get("clouds", {})
    weather = d.get("weather", [{}])[0]
    rain    = d.get("rain", {}).get("1h", 0.0)

    # Map OWM icon code to a simple emoji
    owm_id  = weather.get("id", 800)
    icon    = _owm_icon(owm_id)

    # OWM wind speed is in m/s when units=metric — convert to mph
    wind_ms  = float(wind.get("speed", 4.0))
    wind_mph = round(wind_ms * 2.23694, 1)

    return {
        "temperature_c":   round(float(main.get("temp", 10.5)), 1),
        "feels_like_c":    round(float(main.get("feels_like", 9.0)), 1),
        "wind_speed_mph":  wind_mph,
        "wind_dir_deg":    int(wind.get("deg", 225)),
        "humidity_pct":    int(main.get("humidity", 75)),
        "precip_mm":       round(float(rain), 1),
        "cloud_pct":       int(clouds.get("all", 60)),
        "pressure_hpa":    round(float(main.get("pressure", 1013.0)), 1),
        "condition":       weather.get("description", "").capitalize(),
        "condition_icon":  icon,
        "source":          "OpenWeatherMap",
        "source_url":      "https://openweathermap.org",
        "is_live":         True,
        "fetched_utc":     datetime.now(timezone.utc).isoformat(),
        "location_name":   location_name,
    }


def _owm_icon(owm_id: int) -> str:
    """Map OpenWeatherMap condition ID to an emoji."""
    if owm_id == 800:
        return "☀️"
    if owm_id == 801:
        return "🌤️"
    if owm_id in (802, 803):
        return "⛅"
    if owm_id == 804:
        return "☁️"
    if 200 <= owm_id < 300:
        return "⛈️"
    if 300 <= owm_id < 400:
        return "🌦️"
    if 500 <= owm_id < 600:
        return "🌧️"
    if 600 <= owm_id < 700:
        return "❄️"
    if 700 <= owm_id < 800:
        return "🌫️"
    return "🌡️"


# ─────────────────────────────────────────────────────────────────────────────
# KEY VALIDATION HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def test_met_office_key(
    api_key: str,
    location_id: str = MET_OFFICE_LOCATION,
) -> tuple[bool, str]:
    """
    Test a Met Office DataPoint API key by making a lightweight live request.
    Returns (True, message) on success or (False, error_message) on failure.
    """
    if not api_key:
        return False, "No API key provided."
    url = (
        f"https://datapoint.metoffice.gov.uk/public/data/"
        f"val/wxobs/all/json/{location_id}?res=hourly&key={api_key}"
    )
    try:
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            return True, "Valid Met Office DataPoint key."
        if resp.status_code in (401, 403):
            return False, f"API rejected the key (HTTP {resp.status_code})."
        return False, f"Unexpected response (HTTP {resp.status_code})."
    except Exception as exc:
        return False, f"Network error: {exc}"


def test_openweathermap_key(
    api_key: str,
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
) -> tuple[bool, str]:
    """
    Test an OpenWeatherMap API key with a live Current Weather request.
    Returns (True, message) on success or (False, error_message) on failure.
    """
    if not api_key:
        return False, "No API key provided."
    try:
        resp = requests.get(
            OWM_BASE_URL,
            params={"lat": lat, "lon": lon, "appid": api_key, "units": "metric"},
            timeout=6,
        )
        if resp.status_code == 200:
            return True, "Valid OpenWeatherMap key."
        if resp.status_code == 401:
            return False, "Invalid API key (HTTP 401)."
        if resp.status_code == 429:
            return False, "Rate limit exceeded (HTTP 429) — key may be valid."
        return False, f"Unexpected response (HTTP {resp.status_code})."
    except Exception as exc:
        return False, f"Network error: {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────
def get_weather(
    lat:                  float          = DEFAULT_LAT,
    lon:                  float          = DEFAULT_LON,
    location_name:        str            = DEFAULT_LOCATION_NAME,
    provider:             str            = "open_meteo",
    met_office_key:       Optional[str]  = None,
    met_office_location:  str            = MET_OFFICE_LOCATION,
    openweathermap_key:   Optional[str]  = None,
    enable_fallback:      bool           = True,
    manual_temp_c:        float          = 10.5,
    force_refresh:        bool           = False,
) -> dict:
    """
    Return current weather data with smart provider selection and caching.

    Provider chain (automatically determined):
      1. Any BYOK key provided via the admin panel – Met Office DataPoint is
         preferred if present, otherwise OpenWeatherMap is tried.
      2. Open-Meteo public API (zero‑cost, no key) is the default/fallback.

    The optional ``provider`` argument can request a specific service, but a
    valid BYOK key will still be used first when ``enable_fallback`` is True.

    Caching: each underlying fetch function is decorated with
    ``st.cache_data`` (TTL=%d seconds) to limit rate‑limit exposure.

    Parameters
    ----------
    lat / lon           : Site coordinates (decimal degrees)
    location_name       : Human-readable label for display
    provider            : Preferred weather provider ID (see above)
    met_office_key      : Met Office DataPoint API key (BYOK)
    met_office_location : Met Office site ID for the chosen location
    openweathermap_key  : OpenWeatherMap API key (BYOK)
    enable_fallback     : Fall back to next provider or Open-Meteo on failure
    manual_temp_c       : Manual temperature when all APIs unavailable
    force_refresh       : Clear caches and fetch immediately
    """% (CACHE_TTL_SECONDS,)
    if force_refresh:
        _fetch_open_meteo.clear()
        _fetch_met_office.clear()
        _fetch_openweathermap.clear()

    # determine effective provider order
    chain: list[str] = []
    if provider and provider in PROVIDERS and provider != "open_meteo":
        chain.append(provider)
    if met_office_key and met_office_key.strip():
        if "met_office" not in chain:
            chain.append("met_office")
    if openweathermap_key and openweathermap_key.strip():
        if "openweathermap" not in chain:
            chain.append("openweathermap")
    if "open_meteo" not in chain:
        chain.append("open_meteo")

    # iterate providers until one succeeds (or fall back to manual)
    for prov in chain:
        if prov == "met_office":
            try:
                return _fetch_met_office(met_office_key, met_office_location, location_name)
            except Exception as exc:
                if enable_fallback:
                    st.caption(
                        f"ℹ️ Met Office unavailable ({type(exc).__name__}) "
                        f"— falling back to next provider"
                    )
                    continue
                else:
                    raise
        elif prov == "openweathermap":
            try:
                return _fetch_openweathermap(openweathermap_key, lat, lon, location_name)
            except Exception as exc:
                if enable_fallback:
                    st.caption(
                        f"ℹ️ OpenWeatherMap unavailable ({type(exc).__name__}) "
                        f"— falling back to next provider"
                    )
                    continue
                else:
                    raise
        else:  # open_meteo
            try:
                return _fetch_open_meteo(lat, lon, location_name)
            except Exception as exc:
                # failed at final provider; drop through to manual fallback
                st.caption(
                    f"ℹ️ Open-Meteo unavailable ({type(exc).__name__}) "
                    f"— using manual override"
                )
                break

    # ── Manual fallback (offline / all APIs down) ─────────────────────────
    return {
        "temperature_c":   manual_temp_c,
        "feels_like_c":    round(manual_temp_c - 2.0, 1),
        "wind_speed_mph":  9.2,
        "wind_dir_deg":    225,
        "humidity_pct":    75,
        "precip_mm":       0.0,
        "cloud_pct":       60,
        "pressure_hpa":    1013.0,
        "condition":       "Manual override",
        "condition_icon":  "🌡️",
        "source":          f"Manual input ({manual_temp_c}°C)",
        "source_url":      None,
        "is_live":         False,
        "fetched_utc":     datetime.now(timezone.utc).isoformat(),
        "location_name":   f"{location_name} (manual override)",
    }


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def wind_compass(degrees: int) -> str:
    """Convert wind bearing (degrees) to a 16-point compass label."""
    labels = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
              "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return labels[round(degrees / 22.5) % 16]


def minutes_since_fetch(fetched_utc: str) -> int:
    """Return integer minutes elapsed since the ISO-format fetched_utc timestamp."""
    try:
        ts  = datetime.fromisoformat(fetched_utc.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return max(0, int((now - ts).total_seconds() / 60))
    except Exception:
        return 0


def validate_temperature(temp: float) -> tuple[bool, str]:
    """Validate temperature input is within realistic bounds for the thermal model."""
    if temp < -30:
        return False, "Temperature below -30°C is outside model bounds."
    if temp > 45:
        return False, "Temperature above 45°C is outside model bounds."
    return True, ""
