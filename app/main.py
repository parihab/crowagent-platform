# app/main.py
import streamlit as st
import sys
import os
from dotenv import load_dotenv  # Standard enterprise tool for secret loading
 
# --- ENTERPRISE PATH & SECRETS CHECK ---
# 1. Load your local .env file (ignored by Git for security)
load_dotenv()
 
# 2. Ensure the 'app' folder can see 'core' and 'services'
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
 
# 3. Import your modular logic after the path check
import services.weather as wx
import core.agent as crow_agent
import core.physics as physics
 
# Auto-load secrets if available (Streamlit Cloud deployment)
def _get_secret(key: str, default: str = "") -> str:
    """Safely read a Streamlit secret — returns default if not found."""
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

if not st.session_state.get("gemini_key"):
    st.session_state.gemini_key = _get_secret("GEMINI_KEY", "")
if not st.session_state.get("met_office_key"):
    st.session_state.met_office_key = _get_secret("MET_OFFICE_KEY", "")