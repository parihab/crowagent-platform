import streamlit as st
import logging
import re
import html as html_mod
from typing import Tuple, Optional, Dict, Any

# Services
import services.weather as weather_service
import core.agent as agent_service

# App modules
import app.branding as branding
from app.segments import SEGMENT_LABELS
from config.scenarios import SEGMENT_SCENARIOS, SCENARIOS

# Utils
try:
    from app.utils import _extract_uk_postcode, validate_gemini_key
except ImportError:
    def _extract_uk_postcode(text: str) -> str:
        if not text: return ""
        match = re.search(r'([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([A-Za-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9][A-Za-z]?))))\s?[0-9][A-Za-z]{2})', text)
        return match.group(0).upper() if match else ""

    def validate_gemini_key(key: str) -> Tuple[bool, str]:
        if not key: return False, "Key is empty"
        if not key.startswith("AIza"): return False, "Key should start with 'AIza'"
        return True, "Valid format"

logger = logging.getLogger(__name__)


def get_sidebar_context() -> Tuple[Optional[str], Dict[str, Any], str]:
    """
    Returns the essential context that was previously gathered in the sidebar.
    Returns: (segment_id, weather_dict, location_name)
    """
    # 1. Segment Gate (Full Screen if no segment selected)
    if not st.session_state.get("user_segment"):
        _render_segment_gate()
        return None, {}, ""

    segment = st.session_state.user_segment

    # Weather fetched silently; display lives in the Dashboard tab
    weather_data = _fetch_weather_silently()

    return segment, weather_data, weather_data.get("location_name", "Unknown")


def _render_segment_gate():
    """Renders the 4-card segment selection screen."""
    branding.render_html("""
    <div style='text-align: center; padding: 2rem 0 3rem 0;'>
        <h1 style='margin-bottom: 0.5rem;'>Welcome to CrowAgent&#x2122;</h1>
        <p style='font-size: 1.1rem; color: #8AACBF; max-width: 600px; margin: 0 auto;'>
            Select your user profile to configure the platform&#x27;s physics engine and compliance tools for your specific needs.
        </p>
    </div>
    """)

    cols = st.columns(2)

    with cols[0]:
        with st.container(border=True):
            st.markdown("### 🏛️ University / HE")
            st.markdown("Campus estate management, decarbonisation planning, SECR & TCFD reporting.")
            if st.button("Select University Profile", key="btn_seg_uni", use_container_width=True, type="primary"):
                st.session_state.user_segment = "university_he"
                st.rerun()

    with cols[1]:
        with st.container(border=True):
            st.markdown("### 🏢 Commercial Landlord")
            st.markdown("Office blocks, retail parks, mixed-use developments. MEES compliance focus.")
            if st.button("Select Landlord Profile", key="btn_seg_landlord", use_container_width=True, type="primary"):
                st.session_state.user_segment = "smb_landlord"
                st.rerun()

    cols2 = st.columns(2)

    with cols2[0]:
        with st.container(border=True):
            st.markdown("### 🏭 SMB Industrial")
            st.markdown("Manufacturing, logistics, warehousing. Scope 1 & 2 carbon baselining.")
            if st.button("Select Industrial Profile", key="btn_seg_ind", use_container_width=True, type="primary"):
                st.session_state.user_segment = "smb_industrial"
                st.rerun()

    with cols2[1]:
        with st.container(border=True):
            st.markdown("### 🏠 Individual Self-Build")
            st.markdown("Single dwelling retrofit, heat pump sizing, Part L & Future Homes Standard.")
            if st.button("Select Self-Build Profile", key="btn_seg_self", use_container_width=True, type="primary"):
                st.session_state.user_segment = "individual_selfbuild"
                st.rerun()


def _render_scenario_selector(segment: str):
    """Renders checkboxes for scenarios available to the segment."""
    st.subheader("Scenarios")
    available = SEGMENT_SCENARIOS.get(segment, [])
    if "selected_scenario_names" not in st.session_state:
        st.session_state.selected_scenario_names = []
    if not st.session_state.selected_scenario_names and available:
        st.session_state.selected_scenario_names = available[:3]

    selected = []
    for sc_id in available:
        sc_data = SCENARIOS.get(sc_id, {})
        label = sc_data.get("name", sc_id)
        is_checked = sc_id in st.session_state.selected_scenario_names
        if st.checkbox(label, value=is_checked, key=f"chk_sc_{sc_id}"):
            selected.append(sc_id)
    st.session_state.selected_scenario_names = selected


def _fetch_weather_silently() -> Dict[str, Any]:
    """Fetch weather for the current session location without rendering any UI.

    Called from render_sidebar() so that _current_weather is always populated
    for every page.  The weather card and provider selector live in the Dashboard.
    """
    lat = st.session_state.get("wx_lat", 51.45)
    lon = st.session_state.get("wx_lon", -0.97)
    loc_name = st.session_state.get("wx_location_name", "Reading (Default)")
    provider = st.session_state.get("weather_provider", "open_meteo")
    try:
        return weather_service.get_weather(
            lat, lon, loc_name, provider,
            met_office_key=st.session_state.get("met_office_key"),
            openweathermap_key=st.session_state.get("openweathermap_key"),
        )
    except Exception:
        return {
            "temperature_c": 10.0,
            "condition": "Fallback",
            "description": "Fallback",
            "location_name": loc_name,
            "wind_speed_mph": 0,
            "humidity_pct": 0,
        }


def _render_weather_widget() -> Dict[str, Any]:
    """Renders weather provider selection and current weather."""
    st.subheader("Live Weather")
    provider = st.selectbox("Source", ["open_meteo", "met_office", "manual"], index=0, key="sb_wx_prov", label_visibility="collapsed")
    st.session_state.weather_provider = provider

    lat = st.session_state.get("wx_lat", 51.45)
    lon = st.session_state.get("wx_lon", -0.97)
    loc_name = st.session_state.get("wx_location_name", "Reading (Default)")

    try:
        weather = weather_service.get_weather(
            lat, lon, loc_name, provider,
            met_key=st.session_state.get("met_office_key"),
            owm_key=st.session_state.get("openweathermap_key")
        )
    except Exception:
        weather = {"temperature_c": 10.0, "description": "Fallback", "location_name": loc_name}

    # Custom Weather Card — values escaped per security policy
    _temp   = html_mod.escape(f"{weather.get('temperature_c', 0):.1f}")
    _loc    = html_mod.escape(str(weather.get('location_name', 'Unknown')))
    _desc   = html_mod.escape(str(weather.get('description', '-')))
    _wind   = html_mod.escape(str(weather.get('wind_speed_mph', 0)))
    _hum    = html_mod.escape(str(weather.get('humidity_pct', 0)))
    branding.render_html(f"""
    <div role="status" aria-label="Current Weather: {_temp} degrees celsius, {_desc}" style="background: #0D2640; border: 1px solid #1A3A5C; border-radius: 6px; padding: 10px; margin-top: 5px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="font-size: 1.8rem; font-weight: 700; color: #F0F4F8;">{_temp}°C</div>
            <div style="text-align: right;">
                <div style="font-size: 0.75rem; color: #8AACBF;">{_loc}</div>
                <div style="font-size: 0.8rem; color: #CBD8E6;">{_desc}</div>
            </div>
        </div>
        <div style="margin-top: 5px; font-size: 0.7rem; color: #5A7A90; display: flex; gap: 10px;">
            <span>💨 {_wind} mph</span>
            <span>💧 {_hum}%</span>
        </div>
    </div>
    """)

    return weather


def render_ai_advisor(handler, weather_data: Dict[str, Any]):
    """Renders the AI Advisor chat interface."""
    st.subheader("🤖 AI Advisor")

    if not st.session_state.get("gemini_key_valid"):
        st.info("Enter your Gemini API key in Settings to enable the AI Advisor.")
        return

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history — user content is html.escape()d (SEC policy)
    for msg in st.session_state.chat_history:
        role_class = "ca-user" if msg["role"] == "user" else "ca-ai"
        safe_content = html_mod.escape(str(msg["content"]))
        branding.render_html(f"<div class='{role_class}'>{safe_content}</div>")

    # Chat input
    if prompt := st.chat_input("Ask about energy efficiency..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        st.rerun()

    # Handle response generation (if last message is user)
    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        with st.spinner("Analyzing..."):
            try:
                last_prompt = st.session_state.chat_history[-1]["content"]
                result = agent_service.run_agent_turn(
                    last_prompt,
                    st.session_state.get("agent_history", []),
                    st.session_state.gemini_key,
                    handler.building_registry,
                    SCENARIOS
                )
                answer = result.get("answer", "I couldn't generate a response.")
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                if "updated_history" in result:
                    st.session_state.agent_history = result["updated_history"]
                st.rerun()
            except Exception as e:
                st.error(f"AI Error: {str(e)}")


