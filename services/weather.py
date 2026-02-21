# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — Smart Weather Integration Module
# © 2026 Aparajita Parihar. All rights reserved.
#
# PRIMARY SOURCE : Open-Meteo API  (free, no key, 10,000 req/day)
# SECONDARY      : Met Office DataPoint API  (free, requires registration)
# CACHE STRATEGY : st.cache_data TTL=3600s — ONE call per hour max
# FALLBACK       : Manual temperature override (no API call)
#
# Register Met Office key free at:
# https://register.metoffice.gov.uk/MyAccountClient/account/create
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations
import streamlit as st
import requests
from datetime import datetime, timezone
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# LOCATION CONSTANTS — Reading, Berkshire, UK
# ─────────────────────────────────────────────────────────────────────────────
READING_LAT          = 51.4543
READING_LON          = -0.9781
MET_OFFICE_LOCATION  = "354230"          # Met Office DataPoint site ID
OPEN_METEO_BASE_URL  = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL_SECONDS    = 3600              # 1 hour — respects free tier limits

# WMO weather code → (description, emoji)
WMO_CODES: dict[int, tuple[str, str]] = {
    0:  ("Clear sky",              "☀️"),
    1:  ("Mainly clear",           "🌤️"),
    2:  ("Partly cloudy",          "⛅"),
    3:  ("Overcast",               "☁️"),
    45: ("Foggy",                  "🌫️"),
    48: ("Icy fog",                "🌫️"),
    51: ("Light drizzle",          "🌦️"),
    53: ("Moderate drizzle",       "🌦️"),
    55: ("Dense drizzle",          "🌧️"),
    61: ("Slight rain",            "🌧️"),
    63: ("Moderate rain",          "🌧️"),
    65: ("Heavy rain",             "🌧️"),
    71: ("Slight snow",            "🌨️"),
    73: ("Moderate snow",          "❄️"),
    75: ("Heavy snow",             "❄️"),
    80: ("Rain showers",           "🌦️"),
    81: ("Moderate showers",       "🌦️"),
    82: ("Heavy showers",          "⛈️"),
    85: ("Snow showers",           "🌨️"),
    95: ("Thunderstorm",           "⛈️"),
    96: ("Thunderstorm + hail",    "⛈️"),
    99: ("Thunderstorm + hail",    "⛈️"),
}


# ─────────────────────────────────────────────────────────────────────────────
# OPEN-METEO FETCH  (primary — completely free, no key needed)
# Cached for 1 hour — maximum ONE API call per hour across ALL sessions
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _fetch_open_meteo() -> dict:
    """
    Fetch current conditions from Open-Meteo.
    Open-Meteo free tier: 10,000 requests/day, ~100/min.
    This function is cached — called at most once per hour.
    """
    params = {
        "latitude":         READING_LAT,
        "longitude":        READING_LON,
        "current":          [
            "temperature_2m", "apparent_temperature",
            "wind_speed_10m", "wind_direction_10m",
            "relative_humidity_2m", "precipitation",
            "weather_code", "cloud_cover", "surface_pressure",
        ],
        "wind_speed_unit":  "mph",
        "timezone":         "Europe/London",
        "forecast_days":    1,
    }
    resp = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=8)
    resp.raise_for_status()
    c = resp.json()["current"]

    wcode = int(c.get("weather_code", 0))
    desc, icon = WMO_CODES.get(wcode, ("Unknown", "🌡️"))

    return {
        "temperature_c":    round(float(c["temperature_2m"]), 1),
        "feels_like_c":     round(float(c.get("apparent_temperature", c["temperature_2m"])), 1),
        "wind_speed_mph":   round(float(c["wind_speed_10m"]), 1),
        "wind_dir_deg":     int(c.get("wind_direction_10m", 225)),
        "humidity_pct":     int(c.get("relative_humidity_2m", 75)),
        "precip_mm":        round(float(c.get("precipitation", 0.0)), 1),
        "cloud_pct":        int(c.get("cloud_cover", 60)),
        "pressure_hpa":     round(float(c.get("surface_pressure", 1013.0)), 1),
        "condition":        desc,
        "condition_icon":   icon,
        "source":           "Open-Meteo API",
        "source_url":       "https://open-meteo.com",
        "is_live":          True,
        "fetched_utc":      datetime.now(timezone.utc).isoformat(),
        "location_name":    "Reading, Berkshire, UK",
    }


# ─────────────────────────────────────────────────────────────────────────────
# MET OFFICE DATAPOINT FETCH  (optional premium source — free with registration)
# Cached for 1 hour.
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _fetch_met_office(api_key: str, location_id: str) -> dict:
    """
    Fetch from Met Office DataPoint hourly observation endpoint.
    Free with registration at metoffice.gov.uk/services/data/datapoint.
    Cached for 1 hour — respects the free tier usage limit.
    """
    url = (
        f"http://datapoint.metoffice.gov.uk/public/data/"
        f"val/wxobs/all/json/{location_id}"
        f"?res=hourly&key={api_key}"
    )
    resp = requests.get(url, timeout=8)
    resp.raise_for_status()
    loc  = resp.json()["SiteRep"]["DV"]["Location"]
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
        "temperature_c":    round(temp, 1),
        "feels_like_c":     round(temp - 1.5, 1),
        "wind_speed_mph":   round(wind, 1),
        "wind_dir_deg":     0,
        "humidity_pct":     int(obs.get("H", 75)),
        "precip_mm":        0.0,
        "cloud_pct":        int(float(obs.get("C", 4)) * 12.5),
        "pressure_hpa":     float(obs.get("P", 1013.0)),
        "condition":        "Met Office observation",
        "condition_icon":   "🌡️",
        "source":           "Met Office DataPoint",
        "source_url":       "https://www.metoffice.gov.uk/services/data/datapoint",
        "is_live":          True,
        "fetched_utc":      datetime.now(timezone.utc).isoformat(),
        "location_name":    f"Reading, Berkshire (DataPoint site {location_id})",
    }


def test_met_office_key(api_key: str, location_id: str = MET_OFFICE_LOCATION) -> tuple[bool, str]:
    """
    Test whether a Met Office DataPoint API key is valid by making a lightweight
    request to the observations endpoint. Returns (True, message) on success
    or (False, error_message) on failure.
    """
    if not api_key:
        return False, "No API key provided."
    url = (
        f"http://datapoint.metoffice.gov.uk/public/data/"
        f"val/wxobs/all/json/{location_id}?res=hourly&key={api_key}"
    )
    try:
        resp = requests.get(url, timeout=6)
        if resp.status_code == 200:
            return True, "Valid Met Office DataPoint key."
        elif resp.status_code in (401, 403):
            return False, f"API rejected the key (status {resp.status_code})."
        else:
            return False, f"Unexpected response from API (status {resp.status_code})."
    except Exception as e:
        return False, f"Network/error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API — call this from app.py
# ─────────────────────────────────────────────────────────────────────────────
def get_weather(
    met_office_key:      Optional[str] = None,
    met_office_location: str           = MET_OFFICE_LOCATION,
    manual_temp_c:       float         = 10.5,
    force_refresh:       bool          = False,
) -> dict:
    """
    Return current weather with smart caching.
    Priority order:
      1. Met Office DataPoint (if key provided) — most authoritative for UK
      2. Open-Meteo (free, always available, no key)
      3. Manual override (user-set temperature slider)

    force_refresh=True clears the cache and fetches immediately.
    Smart control: cache TTL of 3600s means at most 24 API calls/day regardless
    of how many users are viewing the app.
    """
    if force_refresh:
        _fetch_open_meteo.clear()
        _fetch_met_office.clear()

    # ── Attempt Met Office (if key supplied) ───────────────────────────────
    key = (met_office_key or "").strip()
    if key:
        try:
            return _fetch_met_office(key, met_office_location)
        except Exception:
            pass  # fall through gracefully

    # ── Attempt Open-Meteo (primary free source) ──────────────────────────────
    try:
        return _fetch_open_meteo()
    except Exception:
        pass  # fall through gracefully

    # ── Manual fallback (offline / API unavailable) ───────────────────────────
    return {
        "temperature_c":    manual_temp_c,
        "feels_like_c":     round(manual_temp_c - 2.0, 1),
        "wind_speed_mph":   9.2,
        "wind_dir_deg":     225,
        "humidity_pct":     75,
        "precip_mm":        0.0,
        "cloud_pct":        60,
        "pressure_hpa":     1013.0,
        "condition":        "Manual override",
        "condition_icon":   "🌡️",
        "source":           f"Manual input ({manual_temp_c}°C)",
        "source_url":       None,
        "is_live":          False,
        "fetched_utc":      datetime.now(timezone.utc).isoformat(),
        "location_name":    "Reading, Berkshire (manual override)",
    }


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def wind_compass(degrees: int) -> str:
    """Convert wind degrees to 16-point compass label."""
    labels = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
              "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return labels[round(degrees / 22.5) % 16]


def minutes_since_fetch(fetched_utc: str) -> int:
    """Return integer minutes elapsed since the fetched_utc ISO timestamp."""
    try:
        ts  = datetime.fromisoformat(fetched_utc.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return max(0, int((now - ts).total_seconds() / 60))
    except Exception:
        return 0


def validate_temperature(temp: float) -> tuple[bool, str]:
    """Validate temperature input is within realistic bounds."""
    if temp < -30:
        return False, "Temperature below -30°C is outside model bounds."
    if temp > 45:
        return False, "Temperature above 45°C is outside model bounds."
    return True, ""
