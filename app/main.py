"""
# Crow Agent Platform - Main Application

This is the primary page for the Crow Agent Platform, serving as the 'Home' tab.

"""

import streamlit as st
from app.branding import add_branding
from app.session import initialize_session_state
from config.scenarios import SCENARIOS

# Initialize session state for application stability.
initialize_session_state()

# --- Page Configuration ---
# Set the page configuration as the first Streamlit command.
st.set_page_config(
    page_title="Crow Agent Platform",
    page_icon="🐦",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.example.com/help',
        'Report a bug': "https://www.example.com/bug",
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)

# --- Main Application UI ---

# Add branding and navigation sidebar.
add_branding()

st.title("Crow Agent Platform")

st.write(
    "Welcome to the Crow Agent Platform. This platform allows for the simulation "
    "and visualization of autonomous agent behavior in complex environments. "
    "Please select a scenario from the dropdown below to begin."
)

# Scenario selection dropdown.
selected_scenario = st.selectbox(
    label="**Select a Scenario**",
    options=list(SCENARIOS.keys()),
    index=st.session_state.get('scenario_index', 0),
    help="Choose one of the pre-defined simulation scenarios."
)

# Update session state on scenario change.
if selected_scenario != st.session_state.get('selected_scenario'):
    st.session_state['selected_scenario'] = selected_scenario
    st.session_state['scenario_index'] = list(SCENARIOS.keys()).index(selected_scenario)
    st.rerun()

st.info(f"You have selected: **{selected_scenario}**")
