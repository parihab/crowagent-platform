"""
Manages the Streamlit session state, including initialization and secrets.
"""

import streamlit as st
import os
from config.constants import ELEC_COST_PER_KWH

# Set a sensible default for the maximum length of the chat history to store
MAX_CHAT_HISTORY = 20

def _get_secret(key: str) -> str:
    """
    Safely retrieves a secret from st.secrets, with a fallback to os.environ
    for local development (e.g., using a .env file).
    """
    if hasattr(st, 'secrets') and key in st.secrets:
        return st.secrets[key]
    return os.environ.get(key, "")

def init_session() -> None:
    """
    Initializes all required session state keys with their default values.
    This function is idempotent, using setdefault to avoid overwriting existing
    state. It should be called at the beginning of every app run.
    """
    # Define all default values for the session state
    defaults = {
        "user_segment": None,
        "portfolio": [],
        "active_analysis_ids": [],
        "chat_history": [],
        "agent_history": [],
        "gemini_key": _get_secret("GEMINI_API_KEY"),
        "gemini_key_valid": False,
        "energy_tariff_gbp_per_kwh": ELEC_COST_PER_KWH,
        "weather_provider": "open_meteo",
        "building_names": {},
        "selected_scenario_names": [],
        "onboarding_complete": False,
        "discount_rate": 5.0,
        "analysis_period_yrs": 10,
    }

    # Use setdefault to initialize any keys that are not already present
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
