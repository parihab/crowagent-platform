import streamlit as st
import html
from app.segments import SEGMENT_LABELS
import services.weather as wx
import services.location as loc
from app.utils import validate_gemini_key

def render_sidebar():
    """
    Renders the sidebar and returns (segment_id, weather_dict, location_name).
    If no segment is selected, renders the onboarding gate and returns (None, None, None).
    """
    # Onboarding Gate
    if not st.session_state.get("user_segment"):
        st.title("Welcome to CrowAgent™")
        st.markdown("### Select your segment to begin:")
        
        cols = st.columns(2)
        for i, (seg_id, label) in enumerate(SEGMENT_LABELS.items()):
            with cols[i % 2]:
                if st.button(label, key=f"btn_{seg_id}", use_container_width=True):
                    st.session_state.user_segment = seg_id
                    st.rerun()
        return None, None, None

    # Normal Sidebar
    with st.sidebar:
        st.header("CrowAgent™")
        st.caption(f"Segment: {SEGMENT_LABELS.get(st.session_state.user_segment)}")
        
        if st.button("Change Segment"):
            st.session_state.user_segment = None
            st.rerun()
            
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
            weather = wx.get_weather(
                lat=st.session_state.get("wx_lat", 51.4543),
                lon=st.session_state.get("wx_lon", -0.9781),
                location_name=st.session_state.get("wx_location_name", "Reading, Berkshire, UK"),
                provider=st.session_state.get("wx_provider", "open_meteo"),
                met_office_key=st.session_state.get("met_office_key"),
                openweathermap_key=st.session_state.get("owm_key")
            )
        except wx.WeatherFetchError as e:
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

        return st.session_state.user_segment, weather, st.session_state.get("wx_location_name")