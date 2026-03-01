import streamlit as st
import html
import app.branding as branding
from app.segments import SEGMENT_LABELS
from config.scenarios import SCENARIOS
import services.weather as wx
import services.location as loc
import services.epc as epc
import core.agent as agent
from app.utils import validate_gemini_key

def render_sidebar():
    """
    Renders the sidebar and returns (segment_id, weather_dict, location_name).
    If no segment is selected, renders the onboarding gate and returns (None, None, None).
    """
    # Onboarding Gate
    if not st.session_state.get("user_segment"):
        if branding.get_logo_uri():
            _, c, _ = st.columns([1, 2, 1])
            with c:
                st.image(branding.get_logo_uri(), use_container_width=True)
        else:
            st.title("Welcome to CrowAgent™")
        
        st.markdown("<h3 style='text-align: center; margin-bottom: 2rem;'>Select your segment to begin:</h3>", unsafe_allow_html=True)
        
        cols = st.columns(2)
        for i, (seg_id, label) in enumerate(SEGMENT_LABELS.items()):
            with cols[i % 2]:
                if st.button(label, key=f"btn_{seg_id}", use_container_width=True):
                    st.session_state.user_segment = seg_id
                    st.rerun()
        return None, None, None

    # Normal Sidebar
    with st.sidebar:
        if branding.get_logo_uri():
            st.image(branding.get_logo_uri(), use_container_width=True)
        else:
            st.header("CrowAgent™")
        st.caption(f"Segment: {SEGMENT_LABELS.get(st.session_state.user_segment)}")
        
        if st.button("Change Segment"):
            st.session_state.user_segment = None
            st.rerun()
            
        st.divider()
        
        # ── Portfolio Management ─────────────────────────────────────────────
        st.subheader("🏢 Asset Portfolio")
        
        # Add Building
        with st.expander("Add Building", expanded=False):
            postcode_input = st.text_input("Postcode", placeholder="SW1A 1AA", key="sb_pc_input", max_chars=10).strip()
            if st.button("Search EPC", key="sb_epc_btn", disabled=not postcode_input):
                try:
                    with st.spinner("Fetching EPC data..."):
                        epc_data = epc.fetch_epc_data(postcode_input, api_key=st.session_state.get("epc_key"))
                        
                    # Calculate baseline energy using EPC current consumption if available, else estimate
                    baseline_mwh = epc_data.get("floor_area_m2", 100.0) * 0.15 # Fallback estimate
                    if "energy_consumption_current" in epc_data:
                        try:
                            baseline_mwh = epc_data.get("floor_area_m2", 100.0) * float(epc_data["energy_consumption_current"]) / 1000.0
                        except (ValueError, TypeError):
                            pass

                    # Create new portfolio entry
                    new_building = {
                        "id": f"bld_{len(st.session_state.portfolio) + 1}",
                        "name": f"Building at {postcode_input.upper()}",
                        "postcode": postcode_input.upper(),
                        "segment": st.session_state.user_segment,
                        "floor_area_m2": epc_data.get("floor_area_m2", 100.0),
                        "built_year": epc_data.get("built_year", 1990),
                        "epc_band": epc_data.get("epc_band", "D"),
                        # Default physics params
                        "height_m": 12.0,
                        "glazing_ratio": 0.4,
                        "u_value_wall": 0.45,
                        "u_value_roof": 0.30,
                        "u_value_glazing": 2.8,
                        "baseline_energy_mwh": baseline_mwh,
                        "occupancy_hours": 3000,
                        "building_type": "Office",
                    }
                    st.session_state.portfolio.append(new_building)
                    st.success(f"Added {new_building['name']}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add building: {e}")

        # Active Assets
        segment_assets = [b for b in st.session_state.portfolio if b.get("segment") == st.session_state.user_segment]
        if segment_assets:
            asset_names = [b["name"] for b in segment_assets]
            selected = st.multiselect(
                "Active Analysis Assets",
                options=asset_names,
                default=asset_names[:3], # Select first 3 by default
                key="sb_active_assets"
            )
            # Update active IDs based on selection
            st.session_state.active_analysis_ids = [
                b["id"] for b in segment_assets if b["name"] in selected
            ]
            
            if st.button("Clear Portfolio", key="sb_clear_port"):
                st.session_state.portfolio = [b for b in st.session_state.portfolio if b.get("segment") != st.session_state.user_segment]
                st.session_state.active_analysis_ids = []
                st.rerun()
        else:
            st.info("No assets in portfolio. Add one above.")

        st.divider()
        st.subheader("📍 Location")
        
        # Location Selector
        current_loc = st.session_state.get("wx_location_name", "Reading, Berkshire, UK")
        selected_city = st.selectbox(
            "Select City", 
            options=loc.city_options(),
            index=loc.city_options().index(current_loc) if current_loc in loc.city_options() else 0,
            label_visibility="collapsed"
        )
        
        if selected_city != current_loc:
            meta = loc.city_meta(selected_city)
            st.session_state.wx_location_name = selected_city
            st.session_state.wx_lat = meta["lat"]
            st.session_state.wx_lon = meta["lon"]
            st.rerun()

        # Weather Service Integration
        try:
            # Safely handle potential missing exception class during refactor
            WeatherError = getattr(wx, "WeatherFetchError", Exception)
            weather = wx.get_weather(
                lat=st.session_state.get("wx_lat", 51.4543),
                lon=st.session_state.get("wx_lon", -0.9781),
                location_name=st.session_state.get("wx_location_name", "Reading, Berkshire, UK"),
                provider=st.session_state.get("wx_provider", "open_meteo"),
                met_office_key=st.session_state.get("met_office_key"),
                openweathermap_key=st.session_state.get("owm_key")
            )
        except WeatherError as e:
            st.warning(f"Weather unavailable: {e}")
            weather = {
                "temperature_c": 10.0, 
                "condition": "Unavailable", 
                "condition_icon": "⚠️",
                "description": "Data unavailable"
            }

        # Weather Widget
        condition_safe = html.escape(weather.get('condition', ''))
        st.markdown(
            f"""
            <div class="wx-widget">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div class="wx-temp">{weather.get('temperature_c')}°C</div>
                    <div style="font-size:2rem;">{weather.get('condition_icon')}</div>
                </div>
                <div class="wx-desc">{condition_safe}</div>
                <div class="wx-row">💨 {weather.get('wind_speed_mph', 0)} mph &nbsp; 💧 {weather.get('humidity_pct', 0)}%</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        with st.expander("🔑 API Keys & Config"):
            gemini_input = st.text_input(
                "Gemini API Key",
                value=st.session_state.get("gemini_key", ""),
                type="password",
                help="Required for AI Advisor"
            )
            if gemini_input != st.session_state.get("gemini_key", ""):
                valid, msg = validate_gemini_key(gemini_input)
                if valid:
                    st.session_state.gemini_key = gemini_input
                    st.success("Key updated")
                else:
                    st.error(msg)

            st.session_state.met_office_key = st.text_input(
                "Met Office Key (Optional)",
                value=st.session_state.get("met_office_key", ""),
                type="password"
            )
            
            st.session_state.owm_key = st.text_input(
                "OpenWeatherMap Key (Optional)",
                value=st.session_state.get("owm_key", ""),
                type="password"
            )
            
            st.session_state.epc_key = st.text_input(
                "EPC OpenData Key (Optional)",
                value=st.session_state.get("epc_key", ""),
                type="password"
            )


        # ── AI Advisor ───────────────────────────────────────────────────────
        st.subheader("🤖 AI Advisor")
        
        # Chat History Display
        for msg in st.session_state.chat_history:
            role = "user" if msg["role"] == "user" else "assistant"
            with st.chat_message(role):
                st.markdown(msg["content"])

        # Chat Input
        if prompt := st.chat_input("Ask about your portfolio..."):
            if not st.session_state.get("gemini_key"):
                st.error("Please enter a Gemini API Key above to use the AI Advisor.")
            else:
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        # Prepare context from active buildings
                        active_buildings = {b["name"]: b for b in segment_assets if b["id"] in st.session_state.active_analysis_ids}
                        # Call agent
                        response = agent.run_agent_turn(
                            prompt, 
                            st.session_state.chat_history, 
                            st.session_state.gemini_key, 
                            active_buildings, 
                            SCENARIOS,
                            tariff=st.session_state.get("energy_tariff_gbp_per_kwh", 0.28)
                        )
                        st.markdown(response)
                        st.session_state.chat_history.append({"role": "assistant", "content": response})

        return st.session_state.user_segment, weather, st.session_state.get("wx_location_name")