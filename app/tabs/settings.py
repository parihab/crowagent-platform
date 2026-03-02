import streamlit as st
from typing import Dict, Any
from app.segments import SEGMENT_LABELS
try:
    from app.utils import validate_gemini_key
except ImportError:
    # Fallback for local development
    def validate_gemini_key(key: str) -> tuple[bool, str]:
        if not key: return False, "Key is empty"
        if not key.startswith("AIza"): return False, "Key should start with 'AIza'"
        return True, "Valid format"

def render(weather_data: Dict[str, Any]):
    """Renders the Settings tab content."""
    st.header("Platform Configuration & Governance")

    # Section 1 — Environment Settings
    with st.container(border=True):
        st.subheader("Environment Settings")
        c1, c2, c3 = st.columns(3)
        c1.metric("Current Profile", SEGMENT_LABELS.get(st.session_state.get("user_segment"), "Unknown"))
        c2.metric("Weather Provider", st.session_state.get("weather_provider", "Unknown"))
        c3.metric("Portfolio Size", len(st.session_state.get("portfolio", [])))

    # Section 2 — System Configuration
    with st.container(border=True):
        st.subheader("System Configuration")
        st.caption("Energy Costs")
        st.session_state.energy_tariff_gbp_per_kwh = st.number_input(
            "Electricity Tariff (£/kWh)",
            min_value=0.05, max_value=1.00,
            value=float(st.session_state.get("energy_tariff_gbp_per_kwh", 0.28)),
            step=0.01,
            format="%.2f",
            help="Used for financial calculations across all scenarios."
        )

    # Section 3 — AI & API Integration
    with st.container(border=True):
        st.subheader("AI & API Integration")
        
        if st.session_state.get("gemini_key_valid"):
            st.success("🤖 AI Advisor Active", icon="✅")
        else:
            st.caption("🤖 AI Advisor Offline (Key Required)")
            
        st.caption("API Access")
        gem_key = st.text_input("Gemini API Key", value=st.session_state.get("gemini_key", ""), type="password", key="inp_gem_key", help="Required for AI Advisor features.")

        if gem_key != st.session_state.get("gemini_key"):
            st.session_state.gemini_key = gem_key
            is_valid, msg = validate_gemini_key(gem_key)
            st.session_state.gemini_key_valid = is_valid
            if is_valid:
                st.toast("Gemini Key Validated", icon="✅")
            else:
                st.error(f"Invalid Key: {msg}")

    # Section 4 — System Logs
    with st.container(border=True):
        st.subheader("System Logs")
        st.caption("Recent Activity")
        if "audit_log" not in st.session_state:
            st.session_state.audit_log = []

        if not st.session_state.audit_log:
            st.caption("No activity logged.")
        else:
            for entry in reversed(st.session_state.audit_log[-10:]):
                st.text(f"{entry.get('timestamp', '')[-8:]} {entry.get('event', '')}")

    # Section 5 — Data Controls
    st.subheader("Data Controls")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Reset Session", type="secondary", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    with c2:
        if st.button("Clear Portfolio", type="secondary", use_container_width=True):
            st.session_state.portfolio = []
            st.rerun()

    # Section 6 — Collapsible Legal
    with st.expander("Legal & Model Disclosure"):
        st.caption("CrowAgent™ Platform v2.0.0")
        st.caption("Physics: Raissi et al. (2019) J. Comp. Physics")
        st.caption("Weather: Open-Meteo API + Met Office DataPoint")
        st.caption("Carbon: BEIS 2023")
        st.caption("Costs: HESA 2022-23")
        st.caption("AI: Google Gemini 1.5 Pro")
