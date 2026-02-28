"""
Renders the sidebar for the CrowAgent™ platform.

Handles:
- Segment selection gate (onboarding)
- API key inputs
- Location and weather widgets
- Portfolio management
- AI Advisor chat panel
"""
from __future__ import annotations
import streamlit as st
import pandas as pd

import core.agent
import services.weather as weather_service
import services.epc as epc_service
from app.segments import get_segment_handler, SEGMENT_IDS, SEGMENT_LABELS
from config.scenarios import SCENARIOS


def init_portfolio_entry(postcode: str, segment: str, epc_data: dict | None = None) -> dict:
    """Creates a new portfolio entry dictionary."""
    epc_data = epc_data or {}
    return {
        "id": f"{postcode}-{segment}",
        "postcode": postcode,
        "segment": segment,
        "display_name": epc_data.get("address", postcode),
        "epc_rating": epc_data.get("current-energy-rating", "N/A"),
        "building_data": {
            "floor_area_m2": epc_data.get("total-floor-area", 1000.0),
            "built_year": epc_data.get("construction-age-band", "2000"),
            # ... other fields to be populated from EPC or defaults
        },
        "results": {} # To be hydrated by analysis tabs
    }

def add_to_portfolio(postcode: str, segment: str):
    """Fetches EPC data and adds a new building to the portfolio."""
    with st.spinner(f"Fetching EPC data for {postcode}..."):
        try:
            # Note: In a real app, we'd pass API keys from session state
            epc_data = epc_service.fetch_epc_data(postcode)
            st.success(f"Found EPC data for {epc_data.get('address', postcode)}")
        except epc_service.EPCFetchError as e:
            st.warning(f"Could not fetch EPC data for {postcode}: {e}. Adding with estimated values.")
            epc_data = None

    new_entry = init_portfolio_entry(postcode, segment, epc_data)
    st.session_state.portfolio.append(new_entry)
    st.toast(f"Added '{new_entry['display_name']}' to portfolio.")

def remove_from_portfolio(entry_id: str):
    """Removes a building from the portfolio by its ID."""
    st.session_state.portfolio = [p for p in st.session_state.portfolio if p.get("id") != entry_id]
    st.toast("Removed building from portfolio.")


def _render_segment_gate() -> str | None:
    """Renders the full-screen segment selection UI if no segment is chosen."""
    st.title("Welcome to CrowAgent™")
    st.markdown("#### Please select a customer segment to begin.")

    cols = st.columns(len(SEGMENT_IDS))
    for i, seg_id in enumerate(SEGMENT_IDS):
        with cols[i]:
            label = SEGMENT_LABELS.get(seg_id, seg_id)
            if st.button(label, key=f"segment_select_{seg_id}", use_container_width=True):
                st.session_state.user_segment = seg_id
                st.rerun()
    return None

def _render_api_keys():
    """Renders inputs for API keys."""
    with st.expander("API Keys & Configuration"):
        st.text_input(
            "Gemini API Key",
            key="gemini_key",
            type="password",
            help="Get a free key from Google AI Studio."
        )
        # Add other API key inputs (Met Office, etc.) here if needed

def _render_location_and_weather() -> tuple[dict, str]:
    """Renders location picker and weather widget."""
    from app.visualization_3d import geocode_location

    st.subheader("Location & Weather")
    location_query = st.text_input("Enter Postcode or Location", st.session_state.get("wx_location_name", "London"))
    if st.button("Update Location"):
        with st.spinner(f"Geocoding '{location_query}'..."):
            geo = geocode_location(location_query)
            if geo:
                st.session_state.wx_lat, st.session_state.wx_lon, st.session_state.wx_location_name = geo
                st.rerun()
            else:
                st.warning("Location not found.")

    lat = st.session_state.get("wx_lat", 51.5072)
    lon = st.session_state.get("wx_lon", -0.1276)
    
    with st.spinner("Fetching weather data..."):
        try:
            weather = weather_service.get_weather(lat, lon, st.session_state.get("wx_location_name", "London"))
            st.metric("Current Weather", f"{weather.get('temperature_c', 'N/A')}°C", delta=weather.get('description'))
            return weather, st.session_state.get("wx_location_name", "London")
        except weather_service.WeatherFetchError as e:
            st.warning(f"Could not fetch weather: {e}")
            return {}, "Unknown"

def _render_portfolio_controls(segment: str):
    """Renders UI for adding, removing, and selecting portfolio buildings."""
    st.subheader("Portfolio Management")
    
    with st.form("add_building_form"):
        postcode = st.text_input("Add building by UK Postcode")
        submitted = st.form_submit_button("Add to Portfolio")
        if submitted and postcode:
            add_to_portfolio(postcode, segment)

    segment_portfolio = [p for p in st.session_state.portfolio if p.get("segment") == segment]
    if segment_portfolio:
        st.multiselect(
            "Active Buildings for Analysis",
            options=[p['id'] for p in segment_portfolio],
            format_func=lambda p_id: next((p['display_name'] for p in segment_portfolio if p['id'] == p_id), p_id),
            key="active_analysis_ids"
        )
        
        for entry in segment_portfolio:
            cols = st.columns([0.8, 0.2])
            with cols[0]:
                st.caption(entry['display_name'])
            with cols[1]:
                if st.button("X", key=f"remove_{entry['id']}", help="Remove from portfolio"):
                    remove_from_portfolio(entry['id'])
                    st.rerun()

def _render_ai_advisor_panel(handler: SegmentHandler):
    """Renders the AI Advisor chat interface."""
    st.subheader("🤖 AI Advisor")

    if not st.session_state.get("gemini_key"):
        st.info("Enter a Gemini API key in the 'API Keys' section to enable the AI Advisor.")
        return

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask the AI Advisor..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Thinking..."):
                response = core.agent.run_agent_turn(
                    user_message=prompt,
                    history=st.session_state.agent_history,
                    gemini_key=st.session_state.gemini_key,
                    building_registry=handler.building_registry,
                    scenario_registry=SCENARIOS
                )

                if response.get("error"):
                    st.error(response["error"])
                else:
                    answer = response.get("answer", "I could not find an answer.")
                    message_placeholder.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    st.session_state.agent_history = response.get("updated_history", [])


def render_sidebar() -> tuple[str | None, dict, str]:
    """
    Renders the entire sidebar and returns the selected segment, weather, and location.

    If no segment is selected, this function renders the onboarding gate in the
    main area and returns (None, {}, "").

    Returns:
        A tuple of (segment_id, weather_dict, location_name).
    """
    segment = st.session_state.get("user_segment")

    if not segment:
        _render_segment_gate()
        return None, {}, ""

    with st.sidebar:
        st.title("CrowAgent™")
        st.caption(f"Segment: **{SEGMENT_LABELS.get(segment, 'Unknown')}**")
        if st.button("Change Segment"):
            st.session_state.user_segment = None
            st.rerun()

        st.divider()

        # API Keys
        _render_api_keys()
        st.divider()

        # Location & Weather
        weather, location = _render_location_and_weather()
        st.divider()

        # Portfolio
        _render_portfolio_controls(segment)
        st.divider()

        # AI Advisor
        handler = get_segment_handler(segment)
        _render_ai_advisor_panel(handler)

    return segment, weather, location