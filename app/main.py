"""
Main application orchestrator for the CrowAgent™ platform.
This file initializes the app, sets up the page, and routes rendering
to the appropriate sidebar and tab modules.
"""
from __future__ import annotations
import streamlit as st
import sys
import os
import html

# Ensure project root is in sys.path for absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import app.branding as branding
import app.session as session

# ── Page config (must be first Streamlit call at module level) ──────────────
st.set_page_config(**branding.PAGE_CONFIG)

# ── KPI card component — defined BEFORE tab imports to prevent circular import
def _card(label: str, value: str, subtext: str, accent_class: str = "") -> None:
    """Renders a compact KPI card. Imported by tab modules as per spec."""
    st.markdown(
        f"""
        <div class="kpi-card {accent_class}">
            <div class="kpi-label">{html.escape(label)}</div>
            <div class="kpi-value">{html.escape(value)}</div>
            <div class="kpi-subtext">{html.escape(subtext)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

import app.sidebar as sidebar
from app.segments import get_segment_handler
import app.tabs.dashboard as tab_dashboard
import app.tabs.financial as tab_financial
import app.tabs.compliance_hub as tab_compliance

# ── Query param persistence (F5 durability) ─────────────────────────────────
def _resolve_query_params() -> None:
    """Apply ?segment= URL param to session state on first load."""
    if "user_segment" not in st.session_state or st.session_state.user_segment is None:
        if "segment" in st.query_params:
            # Basic validation to ensure the param is a known segment
            from app.segments import SEGMENT_IDS
            query_segment = st.query_params.get("segment")
            if query_segment in SEGMENT_IDS:
                st.session_state.user_segment = query_segment

# ── Main orchestrator ────────────────────────────────────────────────────────
def run() -> None:
    branding.inject_branding()
    session.init_session()
    _resolve_query_params()

    segment, weather, location = sidebar.render_sidebar()

    if not segment:
        return  # Onboarding gate is showing; stop here.

    handler = get_segment_handler(segment)
    portfolio = st.session_state.portfolio

    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📈 Financial Analysis", "🏛️ UK Compliance Hub"])
    with tab1:
        tab_dashboard.render(handler, weather, portfolio)
    with tab2:
        tab_financial.render(handler, portfolio)
    with tab3:
        tab_compliance.render(handler, portfolio)

if __name__ == "__main__":
    run()
