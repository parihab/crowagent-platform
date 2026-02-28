"""
Handles all visual branding, including CSS, logos, and page configuration.
"""
import streamlit as st
import base64
from pathlib import Path

CROWAGENT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;700&family=Rajdhani:wght@600&display=swap');

html, body, [class*="st-"] {
    font-family: 'Nunito Sans', sans-serif;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 600;
}

/* Main background */
body {
    background-color: #F0F4F8;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #071A2F;
    color: #CBD8E6;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4 {
    color: #00C2A8;
}
[data-testid="stSidebar"] a:link, [data-testid="stSidebar"] a:visited {
    color: #00C2A8;
}
[data-testid="stSidebar"] a:hover, [data-testid="stSidebar"] a:active {
    color: #00FFD1;
}

/* KPI Card Styles */
.kpi-card {
    background-color: #ffffff;
    border: 1px solid #e6e6e6;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    box-shadow: 0px 4px 6px rgba(0,0,0,0.04);
}
.kpi-value {
    font-size: 2.5rem;
    font-weight: 600;
    font-family: 'Rajdhani', sans-serif;
    color: #071A2F;
}
.kpi-label {
    font-size: 1rem;
    color: #555;
}
.kpi-card.accent-green .kpi-value { color: #008060; }
.kpi-card.accent-red .kpi-value { color: #B92100; }

/* Tab Styles */
button[data-baseweb="tab"] {
    font-size: 1.1rem;
    font-family: 'Rajdhani', sans-serif;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background-color: transparent;
    border-bottom: 2px solid #00C2A8;
    color: #071A2F;
}

/* Button Styles */
div[data-testid="stButton"] > button {
    background-color: #00C2A8;
    color: #071A2F;
    border-color: #00C2A8;
    border-radius: 5px;
    font-weight: bold;
}
div[data-testid="stButton"] > button:hover {
    background-color: #00A38A;
    border-color: #00A38A;
    color: #071A2F;
}
div[data-testid="stButton"] > button:focus {
    box-shadow: 0 0 0 2px #071A2F, 0 0 0 4px #00FFD1;
}


/* Footer Style - default streamlit footer is hidden */
footer {
    visibility: hidden;
}
"""

def _load_asset_uri(filename: str) -> str:
    """
    Resolves an asset's path across candidate locations and returns a
    base64 encoded data URI.
    """
    candidate_paths = [
        Path("assets") / filename,
        Path("app/assets") / filename, # Common alternative
        Path(".") / filename
    ]
    for path in candidate_paths:
        if path.is_file():
            with open(path, "rb") as f:
                data = f.read()
            b64_data = base64.b64encode(data).decode("utf-8")
            return f"data:image/svg+xml;base64,{b64_data}"

    st.warning(f"Asset not found: {filename}")
    return ""

@st.cache_resource
def get_logo_uri() -> str:
    """Returns the data URI for the horizontal logo."""
    return _load_asset_uri("CrowAgent_Logo_Horizontal_Dark.svg")

@st.cache_resource
def get_icon_uri() -> str:
    """Returns the data URI for the square icon."""
    return _load_asset_uri("CrowAgent_Icon_Square.svg")

def inject_branding():
    """Injects custom CSS via a st.markdown call."""
    st.markdown(f"<style>{CROWAGENT_CSS}</style>", unsafe_allow_html=True)

# This dict is imported by main.py and passed to st.set_page_config()
# The icon URI is resolved once at startup and cached.
PAGE_CONFIG = {
    "page_title": "CrowAgent™",
    "page_icon": get_icon_uri(),
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}
