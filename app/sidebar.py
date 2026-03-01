import streamlit as st
import logging
import re
import uuid
from typing import Tuple, Optional, Dict, Any

# Services
import services.weather as weather_service
import services.epc as epc_service
import core.agent as agent_service

# App modules
from app.segments import SEGMENT_LABELS
from config.scenarios import SEGMENT_SCENARIOS, SCENARIOS

# Utils
try:
    from app.utils import _extract_uk_postcode, validate_gemini_key
except ImportError:
    # Fallback if utils not fully migrated
    def _extract_uk_postcode(text: str) -> str:
        if not text: return ""
        match = re.search(r'([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([A-Za-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9][A-Za-z]?))))\s?[0-9][A-Za-z]{2})', text)
        return match.group(0).upper() if match else ""
    
    def validate_gemini_key(key: str) -> Tuple[bool, str]:
        if not key: return False, "Key is empty"
        if not key.startswith("AIza"): return False, "Key should start with 'AIza'"
        return True, "Valid format"

logger = logging.getLogger(__name__)

def render_sidebar() -> Tuple[Optional[str], Dict[str, Any], str]:
    """
    Renders the full sidebar and returns the current context.
    Returns: (segment_id, weather_dict, location_name)
    """
    # 1. Segment Gate (Full Screen if no segment selected)
    if not st.session_state.get("user_segment"):
        _render_segment_gate()
        return None, {}, ""

    segment = st.session_state.user_segment
    
    # 2. Sidebar Content
    with st.sidebar:
        # Advanced Settings
        with st.expander("⚙️ Advanced Settings"):
            st.session_state.energy_tariff_gbp_per_kwh = st.number_input(
                "Electricity Tariff (£/kWh)",
                min_value=0.05, max_value=1.00,
                value=float(st.session_state.get("energy_tariff_gbp_per_kwh", 0.28)),
                step=0.01,
                format="%.2f"
            )

        # Active Segment Display
        st.info(f"**Active Segment:**\n{SEGMENT_LABELS.get(segment, segment)}")
        if st.button("Change Segment", key="btn_change_seg", use_container_width=True):
            st.session_state.user_segment = None
            st.rerun()
            
        st.markdown("---")

        # Scenarios
        st.subheader("Scenarios")
        _render_scenario_selector(segment)
        
        st.markdown("---")

        # Portfolio Controls
        _render_portfolio_controls(segment)
        
        st.markdown("---")

        # Weather
        weather_data = _render_weather_widget()
        
        st.markdown("---")

        # API Keys
        _render_api_keys()
        
        st.markdown("---")
        
        # AI Advisor
        _render_ai_advisor_panel()
        
        # Footer / Audit
        with st.expander("📜 Config Audit Log"):
            if "audit_log" not in st.session_state:
                st.session_state.audit_log = []
            for entry in st.session_state.audit_log[-5:]:
                st.text(f"{entry.get('timestamp', '')} {entry.get('event', '')}")

    return segment, weather_data, weather_data.get("location_name", "Unknown")

def _render_segment_gate():
    """Renders the 4-card segment selection screen."""
    st.markdown("## Select Your Segment")
    st.markdown("Choose the profile that best matches your use case.")
    
    cols = st.columns(2)
    
    with cols[0]:
        with st.container(border=True):
            st.markdown("### 🏛️ University / HE")
            st.markdown("Campus estate management, decarbonisation planning.")
            if st.button("Select University", key="btn_seg_uni", use_container_width=True):
                st.session_state.user_segment = "university_he"
                st.rerun()

    with cols[1]:
        with st.container(border=True):
            st.markdown("### 🏢 Commercial Landlord")
            st.markdown("Office blocks, retail parks, mixed-use developments.")
            if st.button("Select Landlord", key="btn_seg_landlord", use_container_width=True):
                st.session_state.user_segment = "smb_landlord"
                st.rerun()
                
    cols2 = st.columns(2)
    
    with cols2[0]:
        with st.container(border=True):
            st.markdown("### 🏭 SMB Industrial")
            st.markdown("Manufacturing, logistics, warehousing. SECR reporting.")
            if st.button("Select Industrial", key="btn_seg_ind", use_container_width=True):
                st.session_state.user_segment = "smb_industrial"
                st.rerun()

    with cols2[1]:
        with st.container(border=True):
            st.markdown("### 🏠 Individual Self-Build")
            st.markdown("Single dwelling retrofit, heat pump sizing.")
            if st.button("Select Self-Build", key="btn_seg_self", use_container_width=True):
                st.session_state.user_segment = "individual_selfbuild"
                st.rerun()

def _render_scenario_selector(segment: str):
    """Renders checkboxes for scenarios available to the segment."""
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

def _render_portfolio_controls(segment: str):
    """Renders Add/Remove building controls."""
    st.subheader("Asset Portfolio")
    with st.expander("➕ Add Building", expanded=False):
        postcode_input = st.text_input("Postcode", key="inp_add_pc").upper()
        if st.button("Search & Add", key="btn_add_bldg"):
            clean_pc = _extract_uk_postcode(postcode_input)
            if clean_pc:
                with st.spinner("Fetching EPC data..."):
                    add_to_portfolio(clean_pc, segment)
            else:
                st.error("Invalid UK Postcode")

    portfolio = st.session_state.get("portfolio", [])
    seg_portfolio = [p for p in portfolio if p.get("segment") == segment]
    
    if not seg_portfolio:
        st.info("No buildings in portfolio.")
        return

    options = {p["id"]: p.get("display_name", p["id"]) for p in seg_portfolio}
    if "active_analysis_ids" not in st.session_state:
        st.session_state.active_analysis_ids = list(options.keys())[:5]
        
    selected_ids = st.multiselect(
        "Active Analysis Assets",
        options=list(options.keys()),
        format_func=lambda x: options[x],
        default=[x for x in st.session_state.active_analysis_ids if x in options],
        key="ms_active_assets"
    )
    st.session_state.active_analysis_ids = selected_ids
    
    if st.button("Clear Portfolio", key="btn_clear_port"):
        st.session_state.portfolio = [p for p in portfolio if p.get("segment") != segment]
        st.session_state.active_analysis_ids = []
        st.rerun()

def _render_weather_widget() -> Dict[str, Any]:
    """Renders weather provider selection and current weather."""
    st.subheader("Live Weather")
    provider = st.selectbox("Provider", ["open_meteo", "met_office", "manual"], index=0, key="sb_wx_prov")
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
    except Exception as e:
        st.warning(f"Weather fetch failed: {e}")
        weather = {"temperature_c": 10.0, "description": "Fallback", "location_name": loc_name}

    c1, c2 = st.columns([1, 2])
    c1.metric("Temp", f"{weather.get('temperature_c', 0):.1f}°C")
    c2.caption(f"📍 {weather.get('location_name', 'Unknown')}\n☁️ {weather.get('description', '-')}")
    return weather

def _render_api_keys():
    with st.expander("🔑 API Keys (optional)"):
        gem_key = st.text_input("Gemini API key", value=st.session_state.get("gemini_key", ""), type="password", key="inp_gem_key")
        if gem_key != st.session_state.get("gemini_key"):
            st.session_state.gemini_key = gem_key
            is_valid, msg = validate_gemini_key(gem_key)
            st.session_state.gemini_key_valid = is_valid
        
        # Auto-validate if key exists (e.g. from secrets) but validity not set
        if st.session_state.get("gemini_key") and not st.session_state.get("gemini_key_valid"):
            is_valid, msg = validate_gemini_key(st.session_state.gemini_key)
            st.session_state.gemini_key_valid = is_valid

def _render_ai_advisor_panel():
    st.subheader("🤖 AI Advisor")
    st.caption("Chat available in AI Advisor tab.")

def add_to_portfolio(postcode: str, segment: str):
    api_key = st.session_state.get("epc_api_key", "")
    try:
        epc_data = epc_service.fetch_epc_data(postcode, api_key=api_key)
    except Exception:
        epc_data = {"postcode": postcode, "address": f"Unknown ({postcode})"}
    
    entry = init_portfolio_entry(epc_data, segment)
    if "portfolio" not in st.session_state: st.session_state.portfolio = []
    st.session_state.portfolio.append(entry)
    st.success(f"Added {entry['display_name']}")

def remove_from_portfolio(building_id: str):
    if "portfolio" in st.session_state:
        st.session_state.portfolio = [p for p in st.session_state.portfolio if p["id"] != building_id]

def init_portfolio_entry(epc_data: dict, segment: str) -> dict:
    return {
        "id": str(uuid.uuid4())[:8],
        "segment": segment,
        "postcode": epc_data.get("postcode"),
        "display_name": epc_data.get("address", "Unknown Building"),
        "floor_area_m2": float(epc_data.get("total-floor-area", 100.0)),
        "epc_rating": epc_data.get("current-energy-rating", "E"),
        "latitude": 51.45, "longitude": -0.97
    }

def render_ai_advisor(handler, weather_data: Dict[str, Any]):
    """Renders the AI Advisor chat interface."""
    st.subheader("🤖 AI Advisor")
    
    if not st.session_state.get("gemini_key_valid"):
        st.warning("Please enter a valid Gemini API key in the sidebar to use the AI Advisor.")
        return

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask about energy efficiency..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    result = agent_service.run_agent_turn(
                        prompt,
                        st.session_state.get("agent_history", []),
                        st.session_state.gemini_key,
                        handler.building_registry,
                        SCENARIOS
                    )
                    answer = result.get("answer", "I couldn't generate a response.")
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    if "updated_history" in result:
                        st.session_state.agent_history = result["updated_history"]
                except Exception as e:
                    st.error(f"AI Error: {str(e)}")

def render_settings_tab(weather_data: Dict[str, Any]):
    """Renders the Settings tab content."""
    st.header("⚙️ Settings")
    st.info("Most settings are configured in the sidebar.")
    
    st.subheader("System Status")
    st.json({
        "segment": st.session_state.get("user_segment"),
        "weather_location": weather_data.get("location_name"),
        "weather_provider": st.session_state.get("weather_provider"),
        "portfolio_size": len(st.session_state.get("portfolio", [])),
        "gemini_active": st.session_state.get("gemini_key_valid", False)
    })