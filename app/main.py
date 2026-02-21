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
 
# --- AUTO-LOAD SECRETS ---
# This logic prioritizes Environment Variables (Local) or st.secrets (Cloud)
if "gemini_key" not in st.session_state:
    st.session_state.gemini_key = _get_secret("GEMINI_KEY", "")

if "met_office_key" not in st.session_state:
    st.session_state.met_office_key = os.getenv("MET_OFFICE_KEY") or st.secrets.get("MET_OFFICE_KEY", "")