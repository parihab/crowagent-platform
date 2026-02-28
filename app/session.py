"""
Manages the Streamlit session state, including initialization and secrets.
"""

import streamlit as st
import os
from config.constants import ELEC_COST_PER_KWH

MAX_CHAT_HISTORY = 20


def _get_secret(key: str, default: str = "") -> str:
    """
    Safely retrieves a secret from st.secrets, with a fallback to os.environ
    for local development (e.g., using a .env file).
    """
    if hasattr(st, "secrets") and key in st.secrets:
        return st.secrets[key]
    return os.environ.get(key, default)


def init_session() -> None:
    """
    Initializes all required session state keys with their default values.
    This function is idempotent, using setdefault to avoid overwriting existing
    state. It should be called at the beginning of every app run.
    """
    # Restore segment + scenarios from URL query params on first load
    qp = st.query_params
    if "segment" in qp and "user_segment" not in st.session_state:
        st.session_state["user_segment"] = qp.get("segment")
    if "scenarios" in qp and "selected_scenario_names" not in st.session_state:
        _qp_sc = [s.strip() for s in str(qp.get("scenarios", "")).split(",") if s.strip()]
        if _qp_sc:
            st.session_state["selected_scenario_names"] = _qp_sc

    defaults = {
        # Onboarding / segment
        "user_segment": None,
        "onboarding_complete": False,

        # Portfolio
        "portfolio": [],
        "active_analysis_ids": [],

        # AI Advisor
        "chat_history": [],
        "agent_history": [],

        # API keys
        "gemini_key": _get_secret("GEMINI_API_KEY") or _get_secret("GEMINI_KEY"),
        "gemini_key_valid": False,
        "owm_key": _get_secret("OWM_KEY"),
        "met_office_key": _get_secret("MET_OFFICE_KEY"),

        # Financial analysis parameters
        "energy_tariff_gbp_per_kwh": ELEC_COST_PER_KWH,
        "discount_rate": 5.0,
        "analysis_period_yrs": 10,

        # Scenarios
        "selected_scenario_names": [],

        # Building selection
        "selected_building_name": None,
        "building_names": {},

        # Location / weather
        "wx_city": "Reading, Berkshire",
        "wx_lat": 51.4543,
        "wx_lon": -0.9781,
        "wx_location_name": "Reading, Berkshire, UK",
        "wx_provider": "open_meteo",
        "wx_enable_fallback": True,
        "manual_temp": 10.5,
        "force_weather_refresh": False,
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
