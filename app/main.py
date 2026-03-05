"""
CrowAgent™ Platform — Main Application Orchestrator
=====================================================
Navigation architecture: in-content horizontal button bar
  • After segment selection, run() renders:
      logo → nav bar (6 page buttons) → active page content → footer
  • Navigation is driven by `_current_page` in session state; each button
    sets the key and calls st.rerun() — no st.navigation / URL routing needed.
  • The sidebar panel is permanently hidden; all controls live in-page.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import logging
import os
import sys

import streamlit as st

import app.branding as branding
import app.session as session

# ── set_page_config — MUST be the very first Streamlit call ─────────────────
st.set_page_config(**branding.PAGE_CONFIG)

# ── Remaining imports (after set_page_config) ────────────────────────────────
import app.tabs.dashboard as tab_dashboard
import app.tabs.financial as tab_financial
import app.tabs.compliance_hub as tab_compliance
import app.tabs.settings as tab_settings
import app.tabs.ai_advisor as tab_ai_advisor
import core.about as about_page
import services.weather as weather_service
from app.segments import SEGMENT_IDS, SEGMENT_LABELS, get_segment_handler
from app.session import ensure_portfolio_defaults
from config.scenarios import SCENARIOS
from app.segments.university_he import BUILDINGS
from core.physics import calculate_thermal_load

# Re-export for any legacy caller that does `from app.main import _card`
_card = branding.render_card

# ── Compliance page title map ────────────────────────────────────────────────
_COMPLIANCE_TITLES: dict[str, str] = {
    "university_he":        "SECR & TCFD",
    "smb_landlord":         "MEES & EPC",
    "smb_industrial":       "SECR Carbon",
    "individual_selfbuild": "Part L & FHS",
}


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
      2. render_page_logo() — logo bar.
      3. _render_page_nav() — 6-button horizontal navigation row.
    """
    branding.inject_branding()
    branding.render_page_logo()
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
        tab_ai_advisor.render(handler, weather, portfolio)
    branding.render_footer()


def _page_settings() -> None:
    """⚙️ Settings."""
    _page_setup()
    _, weather, _ = _get_page_context()
    tab_settings.render(weather)
    branding.render_footer()


def _page_about() -> None:
    """ℹ️ About & Contact."""
    _page_setup()
    about_page.render()
    branding.render_footer()



def _render_segment_gate() -> None:
    """In-page segment selector (no sidebar dependency)."""
    st.markdown("## Welcome to CrowAgent™")
    st.caption("Select your profile to configure portfolio defaults and compliance context.")

    cols = st.columns(2)
    items = list(SEGMENT_LABELS.items())
    for idx, (seg_id, label) in enumerate(items):
        with cols[idx % 2]:
            with st.container(border=True):
                st.markdown(f"### {label}")
                if st.button("Select", key=f"seg_{seg_id}", use_container_width=True):
                    st.session_state["user_segment"] = seg_id
                    st.session_state["portfolio"] = []
                    st.rerun()


def _fetch_weather_silently() -> dict:
    """Populate weather context used by pages without sidebar."""
    lat = st.session_state.get("wx_lat", 51.45)
    lon = st.session_state.get("wx_lon", -0.97)
    loc_name = st.session_state.get("wx_location_name", "Reading (Default)")
    provider = st.session_state.get("weather_provider", "open_meteo")
    try:
        return weather_service.get_weather(
            lat, lon, loc_name, provider,
            met_office_key=st.session_state.get("met_office_key"),
            openweathermap_key=st.session_state.get("openweathermap_key"),
        )
    except Exception:
        return {
            "temperature_c": 10.0,
            "condition": "Fallback",
            "description": "Fallback",
            "location_name": loc_name,
            "wind_speed_mph": 0,
            "humidity_pct": 0,
        }

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

    # 4. Ensure portfolio defaults are populated if segment is active
    ensure_portfolio_defaults()

    # 5. URL query-param bootstrap
    _resolve_query_params()

    # 6. Segment gate & context fetching (no sidebar dependency)
    _segment = st.session_state.get("user_segment")
    if not _segment:
        _render_segment_gate()
        return

    st.session_state["_current_weather"] = _fetch_weather_silently()

    # 7. Route to active page — _page_setup() inside each wrapper handles
    # CSS injection, logo bar, and the nav button row.
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
