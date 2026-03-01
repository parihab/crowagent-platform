"""
Main application orchestrator for the CrowAgent™ platform.
This file initializes the app, sets up the page, and routes rendering
to the appropriate sidebar and tab modules.
"""
from __future__ import annotations
import streamlit as st
import sys
import os
import logging

# Ensure project root is in sys.path for absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import app.branding as branding
import app.session as session

# ── Page config (must be first Streamlit call at module level) ──────────────
st.set_page_config(**branding.PAGE_CONFIG)

# Re-export render_card as _card for compatibility if needed
_card = branding.render_card

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
    # Configure logging (CQ-004)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    branding.inject_branding()
    session.init_session()
    _resolve_query_params()

    segment, weather, location = sidebar.render_sidebar()

    if not segment:
        return  # Onboarding gate is showing; stop here.

    handler = get_segment_handler(segment)
    portfolio = st.session_state.portfolio

    # Dynamic tab label for Compliance based on segment
    compliance_label = {
        "university_he": "🏛️ SECR & TCFD",
        "smb_landlord": "🏛️ MEES & EPC",
        "smb_industrial": "🏛️ SECR Carbon",
        "individual_selfbuild": "🏛️ Part L & FHS",
    }.get(segment, "🏛️ UK Compliance Hub")

    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📈 Financial Analysis", compliance_label])
    with tab1:
        tab_dashboard.render(handler, weather, portfolio)
    with tab2:
        tab_financial.render(handler, portfolio)
    with tab3:
        tab_compliance.render(handler, portfolio)

    # ── Footer ───────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="ent-footer">
            <img src="{branding.get_logo_uri()}" style="height: 28px; margin-bottom: 14px; opacity: 0.85;">
            <div style="color: #CBD8E6; font-size: 0.9rem; font-weight: 600; margin-bottom: 10px; letter-spacing: 0.5px;">
                CrowAgent™ Sustainability AI Decision Intelligence Platform v2.0.0 · Working Prototype
            </div>
            <div style="color: #8AACBF; font-size: 0.8rem; margin-bottom: 16px; max-width: 700px; line-height: 1.6;">
                ⚠️ <strong>Results Are Indicative Only.</strong> This platform uses simplified physics models calibrated against published UK higher education sector averages. 
                Outputs should not be used as the sole basis for capital investment decisions. Consult a qualified energy surveyor before committing to any retrofit programme. 
                Greenfield University is a fictional institution used for demonstration purposes. All data is illustrative.
            </div>
            <div style="color: #5A7A90; font-size: 0.75rem; margin-bottom: 8px;">
                © 2026 Aparajita Parihar · All rights reserved · Independent research project · CrowAgent™ is an unregistered trademark (UK IPO Class 42, registration pending) · Not licensed for commercial use without written permission
            </div>
            <div style="color: #3A5268; font-size: 0.7rem; font-family: monospace; letter-spacing: -0.2px;">
                Physics: Raissi et al. (2019) J. Comp. Physics · doi:10.1016/j.jcp.2018.10.045 · Weather: Open-Meteo API + Met Office DataPoint · Carbon: BEIS 2023 · Costs: HESA 2022-23 · AI: Google Gemini 1.5 Pro
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    run()
