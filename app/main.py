"""
CrowAgent™ Platform — Main Application Orchestrator
=====================================================
Navigation architecture: in-content horizontal button bar
  • After segment selection, run() renders:
      logo+toggle → nav bar (6 page buttons) → active page content → footer
  • Navigation is driven by `_current_page` in session state; each button
    sets the key and calls st.rerun() — no st.navigation / URL routing needed.
  • Sidebar is reserved exclusively for operational controls (segment,
    scenarios, portfolio, weather).

Sidebar toggle:
  • `sidebar_visible` session-state key (bool, default True).
  • When False: CSS `display:none` on stSidebar — content area expands.
  • `initial_sidebar_state: "auto"` auto-collapses on mobile viewports.
"""
from __future__ import annotations

import logging
import os
import sys

import streamlit as st

# ── Project root on sys.path ─────────────────────────────────────────────────
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import app.branding as branding
import app.session as session

# ── set_page_config — MUST be the very first Streamlit call ─────────────────
st.set_page_config(**branding.PAGE_CONFIG)

# ── Remaining imports (after set_page_config) ────────────────────────────────
import app.sidebar as sidebar
import app.tabs.dashboard as tab_dashboard
import app.tabs.financial as tab_financial
import app.tabs.compliance_hub as tab_compliance
import core.about as about_page
from app.segments import SEGMENT_IDS, get_segment_handler

# Re-export for any legacy caller that does `from app.main import _card`
_card = branding.render_card

# ── Compliance page title map ────────────────────────────────────────────────
_COMPLIANCE_TITLES: dict[str, str] = {
    "university_he":        "SECR & TCFD",
    "smb_landlord":         "MEES & EPC",
    "smb_industrial":       "SECR Carbon",
    "individual_selfbuild": "Part L & FHS",
}


# ── Sidebar visibility CSS ───────────────────────────────────────────────────

def _inject_sidebar_css() -> None:
    """Hides the sidebar via CSS when sidebar_visible is False.

    When the sidebar is display:none Streamlit's flexbox layout naturally
    reclaims that space for the main content column.  The native hamburger
    button in Streamlit's top chrome is also hidden so it does not re-appear
    as a confusing orphan control.
    """
    if not st.session_state.get("sidebar_visible", True):
        branding.render_html(
            "<style>"
            "[data-testid='stSidebar'],"
            "[data-testid='stSidebarCollapsedControl']"
            "{ display: none !important; }"
            "</style>"
        )


# ── Logo + sidebar toggle bar ────────────────────────────────────────────────

def _render_logo_and_toggle() -> None:
    """Renders the CrowAgent™ logo on the left and the sidebar toggle on the right.

    Replaces the old branding.render_page_logo() call.  The toggle uses a
    fixed widget key (`_sbt`) which is safe because st.navigation with
    callable-based pages only ever executes ONE page wrapper per script run.
    """
    logo_uri = branding.get_logo_uri()
    visible = st.session_state.get("sidebar_visible", True)

    col_logo, col_btn = st.columns([11, 1])

    with col_logo:
        if logo_uri:
            branding.render_html(
                '<div class="page-logo-bar" role="banner">'
                f'<img src="{logo_uri}" style="height:34px; opacity:0.92;" '
                'alt="CrowAgent™ Platform — Sustainability AI Decision Intelligence">'
                "</div>"
            )

    with col_btn:
        icon = "✕" if visible else "☰"
        tip = "Hide sidebar controls" if visible else "Show sidebar controls"
        if st.button(
            icon,
            key="_sbt",
            help=tip,
            use_container_width=True,
        ):
            st.session_state.sidebar_visible = not visible
            st.rerun()


# ── Shared page setup ────────────────────────────────────────────────────────

def _render_page_nav() -> None:
    """Horizontal in-content navigation bar with one button per page.

    Uses session-state key `_current_page` for routing; the active page
    button is rendered as type="primary", others as type="secondary".
    Compliance title is resolved dynamically from the current segment.
    """
    segment = st.session_state.get("user_segment", "")
    compliance_label = _COMPLIANCE_TITLES.get(segment, "Compliance")
    current = st.session_state.get("_current_page", "dashboard")

    _NAV_ITEMS = [
        ("dashboard",  "📊", "Dashboard"),
        ("financial",  "📈", "Financial Analysis"),
        ("compliance", "🏛️", compliance_label),
        ("ai_advisor", "🤖", "AI Advisor"),
        ("settings",   "⚙️", "Settings"),
        ("about",      "ℹ️", "About & Contact"),
    ]

    cols = st.columns(len(_NAV_ITEMS))
    for col, (key, icon, label) in zip(cols, _NAV_ITEMS):
        with col:
            if st.button(
                f"{icon} {label}",
                key=f"_nav_{key}",
                use_container_width=True,
                type="primary" if current == key else "secondary",
            ):
                st.session_state["_current_page"] = key
                st.rerun()


def _page_setup() -> None:
    """Single DRY call placed at the top of every page wrapper.

    Order matters:
      1. inject_branding() — CSS must arrive before any rendered element.
      2. _inject_sidebar_css() — conditional hide rule (no-op when visible).
      3. _render_logo_and_toggle() — logo bar + toggle button.
      4. _render_page_nav() — 6-button horizontal navigation row.
    """
    branding.inject_branding()
    _inject_sidebar_css()
    _render_logo_and_toggle()
    _render_page_nav()


# ── Shared context helper ────────────────────────────────────────────────────

def _get_page_context():
    """Returns (handler, weather, portfolio) from session state."""
    segment = st.session_state.get("user_segment")
    handler = get_segment_handler(segment) if segment else None
    weather = st.session_state.get("_current_weather", {})
    portfolio = st.session_state.get("portfolio", [])
    return handler, weather, portfolio


# ── URL query-param bootstrap ────────────────────────────────────────────────

def _resolve_query_params() -> None:
    """Apply ?segment= URL param to session state on first load (F5 durability)."""
    if st.session_state.get("user_segment") is None:
        raw = st.query_params.get("segment")
        if raw and raw in SEGMENT_IDS:
            st.session_state.user_segment = raw


# ── Page wrappers ────────────────────────────────────────────────────────────
# Each wrapper: _page_setup() → render content → render_footer().
# No code is shared between wrappers beyond these three steps — all
# page-specific logic lives in the renderer modules under app/tabs/ and core/.

def _page_dashboard() -> None:
    """📊 Dashboard."""
    _page_setup()
    handler, weather, portfolio = _get_page_context()
    if handler:
        tab_dashboard.render(handler, weather, portfolio)
    branding.render_footer()


def _page_financial() -> None:
    """📈 Financial Analysis."""
    _page_setup()
    handler, weather, portfolio = _get_page_context()
    if handler:
        tab_financial.render(handler, portfolio)
    branding.render_footer()


def _page_compliance() -> None:
    """🏛️ Compliance Hub (title resolved dynamically at nav-build time)."""
    _page_setup()
    handler, weather, portfolio = _get_page_context()
    if handler:
        tab_compliance.render(handler, portfolio)
    branding.render_footer()


def _page_ai_advisor() -> None:
    """🤖 AI Advisor."""
    _page_setup()
    handler, weather, portfolio = _get_page_context()
    if handler:
        sidebar.render_ai_advisor(handler, weather)
    branding.render_footer()


def _page_settings() -> None:
    """⚙️ Settings."""
    _page_setup()
    _, weather, _ = _get_page_context()
    sidebar.render_settings_tab(weather)
    branding.render_footer()


def _page_about() -> None:
    """ℹ️ About & Contact."""
    _page_setup()
    about_page.render()
    branding.render_footer()


# ── Main orchestrator ────────────────────────────────────────────────────────

def run() -> None:
    """Entry point called by streamlit_app.py on every script re-run."""

    # 1. Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # 2. Global CSS (before any Streamlit element is rendered)
    branding.inject_branding()

    # 3. Session state — idempotent, safe to call on every rerun
    session.init_session()

    # 4. URL query-param bootstrap
    _resolve_query_params()

    # 5. Segment gate ─────────────────────────────────────────────────────────
    # render_sidebar() shows the full-screen 4-card onboarding when no segment
    # is selected and returns (None, {}, "").  We must not build st.navigation
    # in that state, so we return early here.
    if not st.session_state.get("user_segment"):
        sidebar.render_sidebar()
        return

    # 6. Sidebar controls (segment label, scenarios, portfolio, weather)
    _segment, _weather, _location = sidebar.render_sidebar()
    st.session_state["_current_weather"] = _weather

    # 7. Route to active page — _page_setup() inside each wrapper handles
    # CSS injection, logo bar, sidebar CSS, and the nav button row.
    _ROUTE = {
        "dashboard":  _page_dashboard,
        "financial":  _page_financial,
        "compliance": _page_compliance,
        "ai_advisor": _page_ai_advisor,
        "settings":   _page_settings,
        "about":      _page_about,
    }
    _current = st.session_state.get("_current_page", "dashboard")
    _ROUTE.get(_current, _page_dashboard)()


if __name__ == "__main__":
    run()
