# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — Session State Management
# © 2026 Aparajita Parihar. All rights reserved.
#
# Single responsibility: own the complete st.session_state initialisation
# contract for the entire application.
#
# Rules:
#   • init_session() is idempotent — call it every run(), it never overwrites
#     existing values (uses setdefault exclusively).
#   • No module outside this file may write a NEW top-level session key
#     without first registering it here.
#   • Reading st.session_state keys from any module is unrestricted.
#   • _get_secret() is the sole secrets access point for the application.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import os

import streamlit as st

from config.constants import DEFAULT_ELECTRICITY_TARIFF_GBP_PER_KWH


# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Maximum number of chat messages retained per session (prevents memory bloat)
MAX_CHAT_HISTORY: int = 100

# Default location — Reading, Berkshire, UK
# Values sourced from services/weather.py DEFAULT_LAT / DEFAULT_LON
_DEFAULT_CITY: str     = "Reading, Berkshire"
_DEFAULT_LAT: float    = 51.4543
_DEFAULT_LON: float    = -0.9781
_DEFAULT_LOC_NAME: str = "Reading, Berkshire, UK"

# Default EPC API endpoint
_DEFAULT_EPC_API_URL: str = "https://epc.opendatacommunities.org/api/v1"


# ─────────────────────────────────────────────────────────────────────────────
# SECRETS ACCESS POINT
# The ONLY function in the application permitted to read st.secrets or os.getenv
# for API credentials.  All callers use _get_secret() — never st.secrets directly.
# ─────────────────────────────────────────────────────────────────────────────

def _get_secret(key: str, default: str = "") -> str:
    """Read a secret from Streamlit Secrets, falling back to environment variable.

    Priority: st.secrets[key]  →  os.getenv(key, default)

    Never raises; returns ``default`` if the key is absent from both sources.
    """
    try:
        return st.secrets[key]
    except (KeyError, AttributeError, FileNotFoundError):
        return os.getenv(key, default)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INITIALISATION
# ─────────────────────────────────────────────────────────────────────────────

def init_session() -> None:
    """Idempotently initialise all application session state keys.

    Uses ``st.session_state.setdefault()`` throughout — existing values are
    never overwritten.  Call this as the first action inside ``run()`` after
    ``st.set_page_config()`` and ``inject_branding()``.

    Session key registry (authoritative):

    Segment & onboarding
    ────────────────────
    user_segment              str | None   Active segment ID; None = onboarding gate
    onboarding_complete       bool         True once segment has been selected

    Portfolio & analysis
    ────────────────────
    portfolio                 list[dict]   All portfolio entries across all segments
    active_analysis_ids       list[str]    UUIDs of entries selected for active analysis
    selected_scenario_names   list[str]    Scenario names currently selected in UI
    building_names            dict         postcode → display name cache

    AI Advisor
    ──────────
    chat_history              list[dict]   UI-visible chat messages
    agent_history             list[dict]   Gemini internal tool-use turn history
    gemini_key                str          User-supplied Gemini API key
    gemini_key_valid          bool         True if key has been validated successfully

    Weather configuration
    ─────────────────────
    wx_city                   str          Selected city/region name
    wx_lat                    float        Latitude
    wx_lon                    float        Longitude
    wx_location_name          str          Display location name with country suffix
    wx_provider               str          Active weather provider ID
    wx_enable_fallback        bool         Enable Open-Meteo fallback on provider failure
    met_office_key            str          Met Office DataPoint API key
    owm_key                   str          OpenWeatherMap API key
    manual_temp               float        Manual temperature override (°C)
    force_weather_refresh     bool         Trigger one-shot cache-busting weather fetch

    Energy & financial
    ──────────────────
    energy_tariff_gbp_per_kwh float        Active electricity tariff (£/kWh)

    EPC integration
    ───────────────
    epc_api_key               str          EPC API authentication key
    epc_api_url               str          EPC API base URL
    """
    ss = st.session_state

    # ── Segment & onboarding ──────────────────────────────────────────────────
    ss.setdefault("user_segment",         None)
    ss.setdefault("onboarding_complete",  False)

    # ── Portfolio & analysis ──────────────────────────────────────────────────
    ss.setdefault("portfolio",              [])
    ss.setdefault("active_analysis_ids",    [])
    ss.setdefault("selected_scenario_names", [])
    ss.setdefault("building_names",          {})

    # ── AI Advisor ────────────────────────────────────────────────────────────
    ss.setdefault("chat_history",    [])
    ss.setdefault("agent_history",   [])
    ss.setdefault("gemini_key",      "")
    ss.setdefault("gemini_key_valid", False)

    # ── Weather configuration ─────────────────────────────────────────────────
    ss.setdefault("wx_city",              _DEFAULT_CITY)
    ss.setdefault("wx_lat",               _DEFAULT_LAT)
    ss.setdefault("wx_lon",               _DEFAULT_LON)
    ss.setdefault("wx_location_name",     _DEFAULT_LOC_NAME)
    ss.setdefault("wx_provider",          "open_meteo")
    ss.setdefault("wx_enable_fallback",   True)
    ss.setdefault("met_office_key",       "")
    ss.setdefault("owm_key",              "")
    ss.setdefault("manual_temp",          10.5)
    ss.setdefault("force_weather_refresh", False)

    # ── Energy & financial ────────────────────────────────────────────────────
    ss.setdefault("energy_tariff_gbp_per_kwh", DEFAULT_ELECTRICITY_TARIFF_GBP_PER_KWH)

    # ── EPC integration ───────────────────────────────────────────────────────
    ss.setdefault("epc_api_key", _get_secret("EPC_API_KEY", ""))
    ss.setdefault(
        "epc_api_url",
        _get_secret("EPC_API_URL", _DEFAULT_EPC_API_URL),
    )
