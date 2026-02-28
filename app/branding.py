# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — Branding & Visual Identity Module
# © 2026 Aparajita Parihar. All rights reserved.
#
# Single responsibility: produce and inject all visual identity tokens.
#
# Public API:
#   PAGE_CONFIG       dict        — kwargs for st.set_page_config()
#   CROWAGENT_CSS     str         — complete <style> block (Google Fonts + layout)
#   inject_branding() -> None     — call once per run() before any widget renders
#   get_logo_uri()    -> str      — @st.cache_resource — base64 SVG data URI
#   get_icon_uri()    -> str      — @st.cache_resource — base64 SVG data URI
#
# Enforcement rule:
#   No st.markdown(..., unsafe_allow_html=True) call containing <style> tags
#   is permitted outside this module.  Violation = merge-blocking.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import base64
import os

import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# ASSET RESOLVER
# Pure function — no Streamlit dependency, safe to call at module import time.
# ─────────────────────────────────────────────────────────────────────────────

def _load_asset_uri(filename: str) -> str:
    """Resolve a named asset file to a base64 data URI.

    Tries four candidate paths in order (handles both local dev and
    Streamlit Community Cloud working-directory layouts).

    Returns:
        A ``data:image/svg+xml;base64,…`` string on success, or ``""`` on
        any failure (file not found, permission error, etc.).  Callers
        responsible for providing a fallback value.
    """
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "assets", filename),
        os.path.join(os.path.dirname(__file__), "assets", filename),
        os.path.join(os.getcwd(), "assets", filename),
        os.path.join("assets", filename),
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "rb") as fh:
                    b64 = base64.b64encode(fh.read()).decode()
                return f"data:image/svg+xml;base64,{b64}"
            except OSError:
                return ""
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# CACHED UI ASSET GETTERS
# @st.cache_resource ensures SVG files are read from disk only once per
# server lifetime (survives across user sessions / reruns).
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_logo_uri() -> str:
    """Return the CrowAgent horizontal logo as a base64 data URI.

    Falls back to empty string on failure (renders text heading instead).
    """
    uri = _load_asset_uri("CrowAgent_Logo_Horizontal_Dark.svg")
    if not uri:
        st.warning(
            "CrowAgent logo asset not found; falling back to text/emoji branding."
        )
    return uri


@st.cache_resource
def get_icon_uri() -> str:
    """Return the CrowAgent square icon as a base64 data URI.

    Falls back to empty string (caller substitutes emoji favicon).
    """
    uri = _load_asset_uri("CrowAgent_Icon_Square.svg")
    if not uri:
        st.warning(
            "CrowAgent icon asset not found; falling back to emoji favicon."
        )
    return uri


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION
# Computed once at module import time.  main.py calls:
#   st.set_page_config(**branding.PAGE_CONFIG)
# at module level (must be first Streamlit command).
# ─────────────────────────────────────────────────────────────────────────────

PAGE_CONFIG: dict = {
    "page_title": "CrowAgent™ Platform",
    "page_icon": _load_asset_uri("CrowAgent_Icon_Square.svg") or "🌿",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
    "menu_items": {
        "Get Help":     "mailto:crowagent.platform@gmail.com",
        "Report a bug": "https://github.com/WonderApri/crowagent-platform/issues",
        "About": (
            "**CrowAgent™ Platform — Sustainability AI Decision Intelligence**\n\n"
            "© 2026 Aparajita Parihar. All rights reserved.\n\n"
            "⚠️ PROTOTYPE: Results are indicative only and based on simplified "
            "physics models. Not for use as the sole basis for investment decisions.\n\n"
            "CrowAgent™ is an unregistered trademark · UK IPO Class 42 pending"
        ),
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# ENTERPRISE CSS + GOOGLE FONTS
# Verbatim copy from app/main.py — do NOT modify without updating both files
# until Batch 5 removes the duplicate from main.py.
# ─────────────────────────────────────────────────────────────────────────────

CROWAGENT_CSS: str = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Nunito+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap');

html, body, [class*="css"] {
  font-family: 'Nunito Sans', sans-serif !important;
}
h1,h2,h3,h4 {
  font-family: 'Rajdhani', sans-serif !important;
  letter-spacing: 0.3px;
}

[data-testid="stAppViewContainer"] > .main { background: #F0F4F8; }
.block-container { padding-top: 0 !important; max-width: 100% !important; }

[data-testid="stSidebar"] {
  background: #071A2F !important;
  border-right: 1px solid #1A3A5C !important;
}
[data-testid="stSidebar"] * { color: #CBD8E6 !important; }
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 { color: #00C2A8 !important; }
[data-testid="stSidebar"] label, [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] p {
  color: #DCEBF8 !important;
}
[data-testid="stSidebar"] .stTextInput input, [data-testid="stSidebar"] .stSelectbox > div > div {
  background: #0D2640 !important; border: 1px solid #1A3A5C !important; color: #CBD8E6 !important;
}
[data-testid="stSidebar"] hr { border-color: #1A3A5C !important; }
[data-testid="stSidebar"] .stButton button {
  background: #0D2640 !important; border: 1px solid #00C2A8 !important; color: #00C2A8 !important;
  font-size: 0.82rem !important; font-weight: 600 !important; padding: 4px 10px !important;
}
[data-testid="stSidebar"] .stButton button:hover { background: #00C2A8 !important; color: #071A2F !important; }

.platform-topbar {
  background: linear-gradient(135deg, #071A2F 0%, #0D2640 60%, #0A2E40 100%);
  border-bottom: 2px solid #00C2A8; padding: 10px 24px; display: flex;
  align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 16px;
}
.platform-topbar-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

.sp { display:inline-flex; align-items:center; gap:5px; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:700; white-space:nowrap; }
.sp-live { background:rgba(29,184,122,.12); color:#1DB87A; border:1px solid rgba(29,184,122,.3); }
.sp-cache { background:rgba(240,180,41,.1); color:#F0B429; border:1px solid rgba(240,180,41,.25); }
.sp-manual { background:rgba(90,122,144,.12); color:#A8C8D8; border:1px solid rgba(90,122,144,.2); }
.sp-warn { background:rgba(232,76,76,.1); color:#E84C4C; border:1px solid rgba(232,76,76,.25); }
.pulse-dot { width:7px; height:7px; border-radius:50%; background:#1DB87A; display:inline-block; animation: blink 2s ease-in-out infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }

.stTabs [data-baseweb="tab-list"] { background: #ffffff !important; border-bottom: 2px solid #E0EBF4 !important; gap: 0 !important; padding: 0 !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: #3A576B !important; font-family: 'Rajdhani', sans-serif !important; font-size: 0.88rem !important; font-weight: 600 !important; padding: 10px 20px !important; border-bottom: 3px solid transparent !important; }
.stTabs [aria-selected="true"] { color: #071A2F !important; border-bottom: 3px solid #00C2A8 !important; background: rgba(0,194,168,.04) !important; }

.kpi-card { background: #ffffff; border-radius: 8px; padding: 18px 20px 14px; border: 1px solid #E0EBF4; border-top: 3px solid #00C2A8; box-shadow: 0 2px 8px rgba(7,26,47,.05); height: 100%; transition: transform 0.2s ease, box-shadow 0.2s ease; }
.kpi-card:hover { transform: translateY(-4px); box-shadow: 0 4px 12px rgba(7,26,47,.15); }
.kpi-card.accent-green { border-top-color: #1DB87A; }
.kpi-card.accent-gold { border-top-color: #F0B429; }
.kpi-label { font-family: 'Rajdhani', sans-serif; font-size: 0.78rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: #3A576B; margin-bottom: 6px; }
.kpi-value { font-family: 'Rajdhani', sans-serif; font-size: 2rem; font-weight: 700; color: #071A2F; line-height: 1.1; }
.kpi-unit { font-size: 0.9rem; font-weight: 500; color: #3A576B; margin-left: 2px; }
.kpi-delta-pos { color: #1DB87A; font-size: 0.80rem; font-weight: 700; margin-top: 4px; }
.kpi-delta-neg { color: #E84C4C; font-size: 0.80rem; font-weight: 700; margin-top: 4px; }
.kpi-sub { font-size: 0.78rem; color: #5A7A90; margin-top: 2px; }

.sec-hdr { font-family: 'Rajdhani', sans-serif; font-size: 0.84rem; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #00C2A8; border-bottom: 1px solid rgba(0,194,168,.2); padding-bottom: 6px; margin-bottom: 14px; margin-top: 4px; }
.chart-card { background: #ffffff; border-radius: 8px; border: 1px solid #E0EBF4; padding: 18px 18px 10px; box-shadow: 0 2px 8px rgba(7,26,47,.04); margin-bottom: 16px; }
.chart-title { font-family: 'Rajdhani', sans-serif; font-size: 0.88rem; font-weight: 700; color: #071A2F; margin-bottom: 4px; text-transform: uppercase; }

.disc-prototype { background: rgba(240,180,41,.07); border: 1px solid rgba(240,180,41,.3); border-left: 4px solid #F0B429; padding: 10px 16px; font-size: 0.82rem; color: #6A5010; margin: 10px 0; }
.ent-footer { background: #071A2F; border-top: 2px solid #00C2A8; padding: 16px 24px; margin-top: 32px; text-align: center; display: flex; flex-direction: column; align-items: center; }
.val-err { background: rgba(220,53,69,.08); border-left: 3px solid #DC3545; padding: 7px 12px; font-size: 0.80rem; color: #721C24; }
.sb-section { font-family: 'Rajdhani', sans-serif; font-size: 0.80rem; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #00C2A8 !important; margin: 14px 0 6px 0; }
.chip { display: inline-block; background: #0D2640; border: 1px solid #1A3A5C; border-radius: 4px; padding: 2px 8px; font-size: 0.78rem; color: #9ABDD0; margin: 2px; }

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
div[data-testid="stToolbar"], div[data-testid="stStatusWidget"] { visibility: hidden; }
header { background: transparent !important; }
[data-testid="collapsedControl"] {
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
  position: fixed !important;
  top: 0.75rem !important;
  left: 0.75rem !important;
  z-index: 10000 !important;
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# BRANDING INJECTION
# Call once per run(), before any widget is rendered.
# ─────────────────────────────────────────────────────────────────────────────

def inject_branding() -> None:
    """Inject the complete CrowAgent CSS into the current Streamlit page.

    Must be called as the first action inside ``run()`` after
    ``st.set_page_config()``.  Idempotent — calling it multiple times is
    harmless (Streamlit deduplicates identical ``st.markdown`` injections).
    """
    st.markdown(CROWAGENT_CSS, unsafe_allow_html=True)
