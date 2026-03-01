"""
CrowAgent™ Platform — Main Application Orchestrator
=====================================================
Implements Streamlit's native multipage architecture (st.navigation / st.Page)
replacing the previous st.tabs routing that suffered from an unclickable CSS
overlay bug.

Architecture Overview
---------------------
* st.set_page_config() is called at MODULE LEVEL — it must be the very first
  Streamlit command executed, which happens here when streamlit_app.py imports
  this module.

* run() is the top-level entry point called by streamlit_app.py on every
  Streamlit script re-run.  It:
    1. Injects global CSS branding.
    2. Initialises / restores session state.
    3. Resolves URL query-param segment shortcuts.
    4. Displays the CrowAgent™ logo in the sidebar via st.logo().
    5. If no user_segment is set → delegates to sidebar.render_sidebar() which
       shows the full-screen onboarding gate; returns early (no navigation).
    6. Otherwise: renders sidebar controls (scenarios, portfolio, weather),
       computes the dynamic compliance page title, builds the st.navigation
       menu, and calls nav.run() to invoke the active page wrapper.

* Six page wrapper functions (_page_*) wrap the underlying renderer modules.
  Each wrapper:
    - Re-injects CSS (belt-and-suspenders — ensures styles survive page
      transitions).
    - Renders the CrowAgent™ logo at the top of the main content area.
    - Retrieves handler / weather / portfolio from session state.
    - Calls the appropriate renderer.
    - Renders the enterprise footer.

Session-State Contracts
-----------------------
Key                    Written by          Read by
─────────────────────────────────────────────────────
user_segment           sidebar / gate      main, all pages
portfolio              sidebar             all pages
_current_weather       run()               _page_dashboard, _page_ai_advisor,
                                          _page_settings
gemini_key_valid       sidebar             _page_ai_advisor (gated)
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import streamlit as st

# ── Ensure project root is importable ───────────────────────────────────────
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import app.branding as branding
import app.session as session

# ── Page config — MUST be the very first Streamlit call (module level) ──────
st.set_page_config(**branding.PAGE_CONFIG)

# Re-export render_card at module level for backward-compatibility with any
# external caller that does `from app.main import _card`.
_card = branding.render_card

# ── Remaining imports (after set_page_config) ────────────────────────────────
import app.sidebar as sidebar
import app.tabs.dashboard as tab_dashboard
import app.tabs.financial as tab_financial
import app.tabs.compliance_hub as tab_compliance
import core.about as about_page
from app.segments import SEGMENT_IDS, get_segment_handler

# ── Compliance page title map ────────────────────────────────────────────────
_COMPLIANCE_TITLES: dict[str, str] = {
    "university_he":      "SECR & TCFD",
    "smb_landlord":       "MEES & EPC",
    "smb_industrial":     "SECR Carbon",
    "individual_selfbuild": "Part L & FHS",
}

# ── Query-param → session-state bootstrap ───────────────────────────────────

def _resolve_query_params() -> None:
    """Apply ?segment= URL param to session state on first load (F5 durability)."""
    if st.session_state.get("user_segment") is None:
        raw = st.query_params.get("segment")
        if raw and raw in SEGMENT_IDS:
            st.session_state.user_segment = raw


# ── Shared context helper ────────────────────────────────────────────────────

def _get_page_context():
    """Return (handler, weather, portfolio) from session state.

    Called at the top of every page wrapper.  Re-instantiating the handler
    on each call is intentional — handlers are lightweight config objects and
    this pattern avoids stale state after a segment switch.
    """
    segment = st.session_state.get("user_segment")
    handler = get_segment_handler(segment) if segment else None
    weather = st.session_state.get("_current_weather", {})
    portfolio = st.session_state.get("portfolio", [])
    return handler, weather, portfolio


# ── Page wrapper functions ───────────────────────────────────────────────────
# Each wrapper is passed as a callable to st.Page().  Streamlit calls it when
# the corresponding page is active.  Every wrapper must:
#   (a) inject_branding()        → CSS present on every page
#   (b) render_page_logo()       → logo visible at top of every page layout
#   (c) render its content
#   (d) render_footer()          → footer present on every page

def _page_dashboard() -> None:
    """📊 Dashboard page."""
    branding.inject_branding()
    branding.render_page_logo()
    handler, weather, portfolio = _get_page_context()
    if handler:
        tab_dashboard.render(handler, weather, portfolio)
    branding.render_footer()


def _page_financial() -> None:
    """📈 Financial Analysis page."""
    branding.inject_branding()
    branding.render_page_logo()
    handler, weather, portfolio = _get_page_context()
    if handler:
        tab_financial.render(handler, portfolio)
    branding.render_footer()


def _page_compliance() -> None:
    """🏛️ Compliance Hub page (dynamic title resolved at nav-build time)."""
    branding.inject_branding()
    branding.render_page_logo()
    handler, weather, portfolio = _get_page_context()
    if handler:
        tab_compliance.render(handler, portfolio)
    branding.render_footer()


def _page_ai_advisor() -> None:
    """🤖 AI Advisor page."""
    branding.inject_branding()
    branding.render_page_logo()
    handler, weather, portfolio = _get_page_context()
    if handler:
        sidebar.render_ai_advisor(handler, weather)
    branding.render_footer()


def _page_settings() -> None:
    """⚙️ Settings page."""
    branding.inject_branding()
    branding.render_page_logo()
    _, weather, _ = _get_page_context()
    sidebar.render_settings_tab(weather)
    branding.render_footer()


def _page_about() -> None:
    """ℹ️ About & Contact page."""
    branding.inject_branding()
    branding.render_page_logo()
    about_page.render()
    branding.render_footer()


# ── Main orchestrator ────────────────────────────────────────────────────────

def run() -> None:
    """Top-level entry point called by streamlit_app.py on every script re-run."""

    # ── 1. Logging ───────────────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # ── 2. Global CSS (runs before anything is rendered) ────────────────────
    branding.inject_branding()

    # ── 3. Session state (idempotent — safe to call on every rerun) ──────────
    session.init_session()

    # ── 4. URL query-param bootstrap ─────────────────────────────────────────
    _resolve_query_params()

    # ── 5. Sidebar logo via st.logo() ────────────────────────────────────────
    # st.logo() renders the brand mark above the navigation items in the sidebar.
    # We attempt the SVG file path first (native rendering); fall back to the
    # base64 data URI if the file is not accessible at runtime working dir.
    _logo_path = Path(__file__).parent.parent / "assets" / "CrowAgent_Logo_Horizontal_Dark.svg"
    if _logo_path.exists():
        st.logo(str(_logo_path))
    else:
        # Fallback: inject logo into sidebar via HTML if file path fails
        _logo_uri = branding.get_logo_uri()
        if _logo_uri:
            with st.sidebar:
                st.markdown(
                    f'<div style="padding:10px 0 6px 0; border-bottom:1px solid #1A3A5C;">'
                    f'<img src="{_logo_uri}" style="height:38px; width:auto;" '
                    f'alt="CrowAgent™"></div>',
                    unsafe_allow_html=True,
                )

    # ── 6. Segment gate ───────────────────────────────────────────────────────
    # If no segment is selected render_sidebar() shows the full-screen
    # onboarding cards and returns (None, {}, "").  We must not build the
    # navigation in that state — hide it by returning early.
    if not st.session_state.get("user_segment"):
        sidebar.render_sidebar()   # renders onboarding gate to main area
        return

    # ── 7. Sidebar controls (scenarios, portfolio, weather) ───────────────────
    # render_sidebar() populates the sidebar with all operational controls and
    # returns live weather data.  We cache weather in session_state so that
    # page wrappers can retrieve it without re-fetching.
    _segment, _weather, _location = sidebar.render_sidebar()
    st.session_state["_current_weather"] = _weather

    # ── 8. Dynamic compliance page title ─────────────────────────────────────
    # Rebuilt on every rerun → automatically reflects segment switches without
    # any additional wiring.
    _compliance_title = _COMPLIANCE_TITLES.get(
        st.session_state.user_segment, "Compliance"
    )

    # ── 9. Build navigation ───────────────────────────────────────────────────
    # Six pages per specification.  st.Page() with callables keeps all state in
    # the single process — no page-reload / session-reset on navigation.
    _pages = [
        st.Page(_page_dashboard,  title="Dashboard",           icon="📊", default=True),
        st.Page(_page_financial,  title="Financial Analysis",  icon="📈"),
        st.Page(_page_compliance, title=_compliance_title,     icon="🏛️"),
        st.Page(_page_ai_advisor, title="AI Advisor",          icon="🤖"),
        st.Page(_page_settings,   title="Settings",            icon="⚙️"),
        st.Page(_page_about,      title="About & Contact",     icon="ℹ️"),
    ]

    _nav = st.navigation(_pages)

    # ── 10. Execute active page ───────────────────────────────────────────────
    _nav.run()


if __name__ == "__main__":
    run()
# Verified Stable Baseline — multipage st.navigation refactor
