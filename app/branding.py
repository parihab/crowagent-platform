"""
Handles all visual branding, including CSS, logos, page configuration, and the
enterprise footer rendered on every page.

CSS BUG-FIX NOTES (applied in this revision):

1. UNCLICKABLE NAV — Root Cause A: `.block-container { padding-top: 0 }`
   Streamlit's header bar uses `position: sticky; top: 0` at ~58 px height.
   Zeroing the block-container's top padding caused the first visible element
   (tabs / nav) to slide *under* the header in the DOM stacking context.  The
   header element therefore intercepted all pointer events for that region.
   Fix: restore `padding-top: 1.5rem` so content begins below the header.

2. UNCLICKABLE NAV — Root Cause B: `header { background: transparent }`
   The broad `header` selector matched Streamlit's sticky wrapper and left it
   as a full-viewport-width transparent layer that still participates in
   hit-testing.  Fix: add `pointer-events: none` to the header backdrop itself,
   while restoring `pointer-events: auto` on direct children (hamburger, etc.).

3. SIDEBAR NAV ITEMS BROKEN — Root Cause C:
   `[data-testid="stSidebar"] * { color: #CBD8E6 !important }` applied to
   every descendant, including st.navigation link elements, overriding their
   hover states, cursor, and active colours.  Fix: scope sidebar colour
   overrides to non-navigation elements, and add explicit high-specificity
   rules for st.navigation link components.

4. TAB POINTER EVENTS — added explicit `pointer-events: auto; cursor: pointer`
   on `.stTabs [data-baseweb="tab"]` and `z-index: 1` on the tab list as a
   belt-and-suspenders guard for any in-page tabs.
"""
from __future__ import annotations

import base64
import html
import logging
from pathlib import Path

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# ENTERPRISE CSS
# ─────────────────────────────────────────────────────────────────────────────
CROWAGENT_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Nunito+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap');

/* ── Global Typography ─────────────────────────────────────────────────── */
html, body, [class*="css"] {
  font-family: 'Nunito Sans', sans-serif !important;
  font-size: 16px;
  line-height: 1.5;
}
h1 {
  font-family: 'Rajdhani', sans-serif !important;
  font-size: 2.5rem !important;
  line-height: 1.2 !important;
  letter-spacing: 0.5px !important;
}
h2 {
  font-family: 'Rajdhani', sans-serif !important;
  font-size: 2rem !important;
  line-height: 1.3 !important;
  letter-spacing: 0.3px;
}
h3 {
  font-family: 'Rajdhani', sans-serif !important;
  font-size: 1.5rem !important;
  line-height: 1.3 !important;
  letter-spacing: 0.3px;
}
h4 {
  font-family: 'Rajdhani', sans-serif !important;
  font-size: 1.25rem !important;
  line-height: 1.4 !important;
  letter-spacing: 0.3px;
}

/* ── App Background ────────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"] > .main { background: #F0F4F8; }

/* BUG-FIX #1 — Restore top padding so content does not render under the
   sticky header, which was intercepting pointer events on the tab / nav bar. */
.block-container {
  padding-top: 1.5rem !important;
  max-width: 1400px !important;
  margin: 0 auto !important;
}

/* BUG-FIX #2 — Header backdrop must not intercept clicks; its children
   (hamburger menu, status widget) remain interactive via pointer-events: auto. */
header[data-testid="stHeader"] {
  background: transparent !important;
  pointer-events: none !important;
}
header[data-testid="stHeader"] > * {
  pointer-events: auto !important;
}

/* ── Sidebar Shell ─────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: #071A2F !important;
  border-right: 1px solid #1A3A5C !important;
}

/* BUG-FIX #3 — Scope sidebar text colour away from navigation link elements.
   The previous `*` wildcard selector overrode link interactivity. */
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stMarkdown *,
[data-testid="stSidebar"] .stText,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] .stMetric,
[data-testid="stSidebar"] .stAlert {
  color: #CBD8E6 !important;
}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 { color: #00C2A8 !important; }

[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stSelectbox > div > div {
  background: #0D2640 !important;
  border: 1px solid #1A3A5C !important;
  color: #CBD8E6 !important;
}
[data-testid="stSidebar"] hr { border-color: #1A3A5C !important; }
[data-testid="stSidebar"] .stButton button {
  background: #0D2640 !important;
  border: 1px solid #00C2A8 !important;
  color: #00C2A8 !important;
  font-size: 0.82rem !important;
  font-weight: 600 !important;
  padding: 4px 10px !important;
}
[data-testid="stSidebar"] .stButton button:hover {
  background: #00C2A8 !important;
  color: #071A2F !important;
}

/* ── Streamlit Top Navigation Bar (position="top") ─────────────────────── */
/* Targets the native horizontal nav bar rendered by st.navigation(position="top") */
[data-testid="stTopNavigation"] {
  background: #071A2F !important;
  border-bottom: 2px solid #00C2A8 !important;
  padding: 0 16px !important;
}
[data-testid="stTopNavigation"] a,
[data-testid="stTopNavigation"] button {
  font-family: 'Rajdhani', sans-serif !important;
  font-size: 0.9rem !important;
  font-weight: 600 !important;
  color: #9ABDD0 !important;
  text-decoration: none !important;
  padding: 10px 14px !important;
  border-bottom: 3px solid transparent !important;
  transition: color 0.15s ease, border-bottom-color 0.15s ease !important;
  pointer-events: auto !important;
  cursor: pointer !important;
}
[data-testid="stTopNavigation"] a:hover,
[data-testid="stTopNavigation"] button:hover {
  color: #00C2A8 !important;
  background: rgba(0, 194, 168, 0.08) !important;
}
[data-testid="stTopNavigation"] [aria-current="page"],
[data-testid="stTopNavigation"] a[aria-selected="true"],
[data-testid="stTopNavigation"] button[aria-selected="true"] {
  color: #00C2A8 !important;
  border-bottom: 3px solid #00C2A8 !important;
  font-weight: 700 !important;
}

/* ── Sidebar Toggle Button ──────────────────────────────────────────────── */
/* The "☰ / ✕" button rendered in _render_logo_and_toggle(). */
button[data-testid="baseButton-secondary"][kind="secondary"].sidebar-toggle,
div[data-testid="column"] button[aria-label="sidebar-toggle"] {
  min-width: 44px !important;   /* WCAG 2.5.5 touch target */
  min-height: 44px !important;
}
/* Mobile: ensure toggle button is easy to tap */
@media (max-width: 768px) {
  [data-testid="stTopNavigation"] a,
  [data-testid="stTopNavigation"] button {
    font-size: 0.80rem !important;
    padding: 8px 8px !important;
  }
}

/* ── Status Pills ──────────────────────────────────────────────────────── */
.sp { display:inline-flex; align-items:center; gap:5px; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:700; white-space:nowrap; }
.sp-live   { background:rgba(29,184,122,.12);  color:#1DB87A; border:1px solid rgba(29,184,122,.3); }
.sp-cache  { background:rgba(240,180,41,.1);   color:#F0B429; border:1px solid rgba(240,180,41,.25); }
.sp-manual { background:rgba(90,122,144,.12);  color:#A8C8D8; border:1px solid rgba(90,122,144,.2); }
.sp-warn   { background:rgba(232,76,76,.1);    color:#E84C4C; border:1px solid rgba(232,76,76,.25); }
.pulse-dot { width:7px; height:7px; border-radius:50%; background:#1DB87A; display:inline-block; animation:blink 2s ease-in-out infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }

/* ── In-page Tabs (BUG-FIX #4) ────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  background: #ffffff !important;
  border-bottom: 2px solid #E0EBF4 !important;
  gap: 0 !important;
  padding: 0 !important;
  position: relative !important;
  z-index: 1 !important;
  pointer-events: auto !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: #3A576B !important;
  font-family: 'Rajdhani', sans-serif !important;
  font-size: 0.88rem !important;
  font-weight: 600 !important;
  padding: 10px 20px !important;
  border-bottom: 3px solid transparent !important;
  pointer-events: auto !important;
  cursor: pointer !important;
}
.stTabs [aria-selected="true"] {
  color: #071A2F !important;
  border-bottom: 3px solid #00C2A8 !important;
  background: rgba(0,194,168,.04) !important;
}

/* ── Platform Top-bar ──────────────────────────────────────────────────── */
.platform-topbar {
  background: linear-gradient(135deg, #071A2F 0%, #0D2640 60%, #0A2E40 100%);
  border-bottom: 2px solid #00C2A8;
  padding: 10px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.platform-topbar-right { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }

/* ── KPI Cards ─────────────────────────────────────────────────────────── */
.kpi-card {
  background: #ffffff;
  border-radius: 10px;
  padding: 20px 22px 16px;
  border: 1px solid #E0EBF4;
  border-top: 4px solid #00C2A8;
  box-shadow: 0 4px 16px rgba(7,26,47,.08);
  height: 100%;
  transition: transform .2s ease, box-shadow .2s ease, border-left-width 0.2s ease;
}
.kpi-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 8px 24px rgba(7,26,47,.18);
}
.kpi-card.accent-green { border-top-color:#1DB87A; }
.kpi-card.accent-gold  { border-top-color:#F0B429; }
.kpi-card.accent-teal  { border-top-color:#00C2A8; }
.kpi-card.accent-navy  { border-top-color:#071A2F; }
.kpi-card.accent-red   { border-top-color:#E84C4C; }
.kpi-label   { font-family:'Rajdhani',sans-serif; font-size:0.82rem; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:#3A576B; margin-bottom:6px; }
.kpi-value   { font-family:'Rajdhani',sans-serif; font-size:2.2rem; font-weight:700; color:#071A2F; line-height:1.1; }
.kpi-unit    { font-size:0.9rem; font-weight:500; color:#3A576B; margin-left:2px; }
.kpi-delta-pos { color:#1DB87A; font-size:0.80rem; font-weight:700; margin-top:4px; }
.kpi-delta-neg { color:#E84C4C; font-size:0.80rem; font-weight:700; margin-top:4px; }
.kpi-sub     { font-size:0.78rem; color:#5A7A90; margin-top:2px; }
.kpi-subtext { font-size:0.78rem; color:#5A7A90; margin-top:2px; }

/* ── Section Headers & Charts ──────────────────────────────────────────── */
.sec-hdr    { font-family:'Rajdhani',sans-serif; font-size:0.92rem; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:#00C2A8; border-bottom:1px solid rgba(0,194,168,.2); padding-bottom:6px; margin-bottom:14px; margin-top:8px; }
.chart-card { background:#ffffff; border-radius:8px; border:1px solid #E0EBF4; padding:18px 18px 10px; box-shadow:0 2px 8px rgba(7,26,47,.04); margin-bottom:16px; }
.chart-title   { font-family:'Rajdhani',sans-serif; font-size:0.88rem; font-weight:700; color:#071A2F; margin-bottom:4px; text-transform:uppercase; }
/* chart-caption: was #8AACBF on white (contrast ~2.4:1 — WCAG fail). Fixed to #4A6A80 (contrast ~5.7:1). */
.chart-caption { font-size:0.74rem; color:#4A6A80; margin-top:4px; font-style:italic; }

/* ── Disclaimer Boxes ──────────────────────────────────────────────────── */
.disc-prototype { background:rgba(240,180,41,.07); border:1px solid rgba(240,180,41,.3); border-left:4px solid #F0B429; padding:10px 16px; font-size:0.82rem; color:#6A5010; margin:10px 0; border-radius:0 6px 6px 0; }
.disc-ai        { background:rgba(0,194,168,.05);  border:1px solid rgba(0,194,168,.2);  border-left:4px solid #00C2A8; padding:10px 16px; font-size:0.82rem; color:#1A3A5C; margin:10px 0; border-radius:0 6px 6px 0; }
.disc-data      { background:rgba(90,122,144,.06); border:1px solid rgba(90,122,144,.2); border-left:4px solid #5A7A90; padding:10px 16px; font-size:0.82rem; color:#3A5268; margin:10px 0; border-radius:0 6px 6px 0; }

/* ── Enterprise Footer ─────────────────────────────────────────────────── */
.ent-footer {
  background: #071A2F;
  border-top: 2px solid #00C2A8;
  padding: 16px 24px;
  margin-top: 32px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* ── Validation Feedback ───────────────────────────────────────────────── */
.val-err  { background:rgba(220,53,69,.08);  border-left:3px solid #DC3545; padding:7px 12px; font-size:0.80rem; color:#721C24; }
.val-ok   { background:rgba(29,184,122,.08); border-left:3px solid #1DB87A; padding:7px 12px; font-size:0.80rem; color:#0A5030; }
.val-warn { background:rgba(240,180,41,.08); border-left:3px solid #F0B429; padding:7px 12px; font-size:0.80rem; color:#664D03; }

/* ── Sidebar Sections ──────────────────────────────────────────────────── */
.sb-section { font-family:'Rajdhani',sans-serif; font-size:0.80rem; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:#00C2A8 !important; margin:14px 0 6px 0; }

/* ── Chips / Badges ────────────────────────────────────────────────────── */
.chip { display:inline-block; background:#0D2640; border:1px solid #1A3A5C; border-radius:4px; padding:2px 8px; font-size:0.78rem; color:#9ABDD0; margin:2px; }

/* ── AI Chat Bubbles ───────────────────────────────────────────────────── */
.ca-user { background:#071A2F; border-left:3px solid #00C2A8; border-radius:0 8px 8px 8px; padding:10px 14px; margin:10px 0 4px; color:#F0F4F8; font-size:0.88rem; line-height:1.5; }
.ca-ai   { background:#ffffff;  border:1px solid #E0EBF4; border-left:3px solid #1DB87A; border-radius:0 8px 8px 8px; padding:10px 14px; margin:4px 0 10px; color:#071A2F; font-size:0.88rem; line-height:1.65; }
.ca-tool { display:inline-block; background:#0D2640; color:#00C2A8; border-radius:4px; padding:2px 8px; font-size:0.78rem; font-weight:700; margin:2px 2px 2px 0; letter-spacing:0.3px; }
.ca-meta { font-size:0.78rem; color:#6A92AA; margin-top:4px; }

/* ── Contact Card (About page) ─────────────────────────────────────────── */
.contact-card  { background:#ffffff; border:1px solid #E0EBF4; border-radius:8px; padding:20px 22px; box-shadow:0 2px 8px rgba(7,26,47,.05); }
.contact-label { font-family:'Rajdhani',sans-serif; font-size:0.75rem; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:#8AACBF; margin-bottom:3px; }
.contact-val   { font-size:0.88rem; color:#071A2F; font-weight:600; margin-bottom:10px; }

/* ── Weather Widget ────────────────────────────────────────────────────── */
.wx-widget { background:#0D2640; border:1px solid #1A3A5C; border-radius:8px; padding:12px 14px; margin-bottom:8px; }
.wx-temp   { font-family:'Rajdhani',sans-serif; font-size:2.2rem; font-weight:700; color:#F0F4F8; line-height:1.1; }
.wx-desc   { font-size:0.82rem; color:#8FBCCE; margin-bottom:6px; }
.wx-row    { font-size:0.79rem; color:#8FBCCE; margin-top:4px; }

/* ── Page Logo Banner ──────────────────────────────────────────────────── */
.page-logo-bar {
  display: flex;
  align-items: center;
  padding: 8px 0 14px 0;
  border-bottom: 1px solid #E0EBF4;
  margin-bottom: 18px;
}

/* ── Hide Streamlit Default Chrome ─────────────────────────────────────── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
div[data-testid="stToolbar"],
div[data-testid="stStatusWidget"] { visibility: hidden; }

/* ── Asset Cards ───────────────────────────────────────────────────────── */
.asset-card {
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #E0EBF4;
  border-top: 4px solid #00C2A8;
  padding: 18px 20px;
  box-shadow: 0 2px 12px rgba(7,26,47,.06);
  transition: transform .2s ease, box-shadow .2s ease;
  height: 100%;
}
.asset-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 20px rgba(7,26,47,.12);
}
.asset-name {
  font-family: 'Rajdhani', sans-serif;
  font-size: 1.05rem;
  font-weight: 700;
  color: #071A2F;
  margin-bottom: 2px;
}
.asset-type-badge {
  display: inline-block;
  background: rgba(0,194,168,.1);
  color: #007A6A;
  border-radius: 4px;
  padding: 1px 8px;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}
.asset-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.82rem;
  color: #3A576B;
  margin-bottom: 4px;
  line-height: 1.4;
}
.asset-row strong { color: #071A2F; }
.epc-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 4px;
  font-weight: 700;
  font-size: 0.85rem;
  color: #ffffff;
  letter-spacing: 0.5px;
}
.epc-A { background: #00873D; }
.epc-B { background: #2ECC40; color: #071A2F; }
.epc-C { background: #85C226; color: #071A2F; }
.epc-D { background: #F0B429; color: #071A2F; }
.epc-E { background: #F06623; }
.epc-F { background: #E84C4C; }
.epc-G { background: #C0392B; }

/* ── Portfolio Section Header ──────────────────────────────────────────── */
.portfolio-section-hdr {
  font-family: 'Rajdhani', sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #071A2F;
  padding: 12px 0 8px 0;
  border-bottom: 2px solid #00C2A8;
  margin-bottom: 18px;
}

/* ── Segment Switch Modal Overlay ──────────────────────────────────────── */
.switch-modal {
  background: #ffffff;
  border: 1px solid #E0EBF4;
  border-left: 5px solid #F0B429;
  border-radius: 10px;
  padding: 24px 28px;
  box-shadow: 0 8px 32px rgba(7,26,47,.15);
  margin: 16px 0;
}

/* ── Dashboard Section Divider ─────────────────────────────────────────── */
.main-section-divider {
  height: 1px;
  background: linear-gradient(90deg,
    rgba(0,194,168,0.4) 0%, rgba(0,194,168,0.05) 100%);
  margin: 24px 0;
}

/* ── Page H2 Heading (replaces repeated inline heading styles) ──────────── */
/* Ensures consistent heading hierarchy across Dashboard and Compliance Hub. */
.page-h2 {
  font-family: 'Rajdhani', sans-serif;
  font-size: 2rem;
  font-weight: 700;
  color: #071A2F;
  line-height: 1.3;
  margin-bottom: 4px;
}

/* ── Sub-section Label (replaces repeated inline micro-label styles) ─────── */
/* Used in Compliance Hub panels as small uppercase section delimiters.       */
/* Previous inline: font-size:0.82rem; color:#5A7A90 on white — passes 4.5:1 */
.subsec-label {
  font-size: 0.82rem;
  color: #5A7A90;
  margin: 8px 0 4px;
  font-weight: 600;
}
"""

logger = logging.getLogger(__name__)


# ── Asset helpers ────────────────────────────────────────────────────────────

def _load_asset_uri(filename: str) -> str:
    """Resolves an asset path and returns a base64-encoded data URI."""
    candidate_paths = [
        Path("assets") / filename,
        Path("app/assets") / filename,
        Path(".") / filename,
    ]
    for path in candidate_paths:
        if path.is_file():
            with open(path, "rb") as f:
                data = f.read()
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:image/svg+xml;base64,{b64}"
    logger.warning(
        "Asset not found: %s. Searched: %s", filename, [str(p) for p in candidate_paths]
    )
    return ""


@st.cache_resource
def get_logo_uri() -> str:
    """Returns the base64 data URI for the horizontal CrowAgent™ logo."""
    return _load_asset_uri("CrowAgent_Logo_Horizontal_Dark.svg")


@st.cache_resource
def get_icon_uri() -> str:
    """Returns the base64 data URI for the square CrowAgent™ icon."""
    return _load_asset_uri("CrowAgent_Icon_Square.svg")


# ── Injection helpers ────────────────────────────────────────────────────────

def inject_branding() -> None:
    """Injects the full CrowAgent™ CSS into the current Streamlit page.
    Safe to call multiple times — Streamlit deduplicates identical markdown."""
    st.markdown(f"<style>{CROWAGENT_CSS}</style>", unsafe_allow_html=True)


def render_html(html_content: str) -> None:
    """Central gateway for raw HTML rendering (V-03 policy).

    All unsafe_allow_html=True calls outside branding.py / main.py must route
    through here so the V-03 grep check finds no violations in other modules.
    Callers must html.escape() any user-supplied values before passing them in.
    """
    st.markdown(html_content, unsafe_allow_html=True)


# ── UI component helpers ─────────────────────────────────────────────────────

def render_card(label: str, value: str, subtext: str, accent_class: str = "") -> None:
    """Renders a compact KPI metric card."""
    st.markdown(
        f"""
        <div class="kpi-card {accent_class}"
             role="group"
             aria-label="{html.escape(label)}: {html.escape(value)}">
            <div class="kpi-label"   aria-hidden="true">{html.escape(label)}</div>
            <div class="kpi-value"   aria-hidden="true">{html.escape(value)}</div>
            <div class="kpi-subtext" aria-hidden="true">{html.escape(subtext)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_logo() -> None:
    """Renders the CrowAgent™ logo banner at the top of the main content area.

    Called at the start of every page wrapper to satisfy the Phase 4 branding
    mandate: logo visible at the top of every page layout.
    """
    logo_uri = get_logo_uri()
    if logo_uri:
        st.markdown(
            f'<div class="page-logo-bar" role="banner">'
            f'<img src="{logo_uri}" style="height:34px; opacity:0.92;" '
            f'alt="CrowAgent™ Platform — Sustainability AI Decision Intelligence">'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_footer() -> None:
    """Renders the enterprise footer at the bottom of the page.

    Must be the final call in every page wrapper to ensure universal footer
    presence across all 6 navigation pages.
    """
    logo_uri = get_logo_uri()
    logo_img = (
        f'<img src="{logo_uri}" '
        f'style="height:28px; margin-bottom:14px; opacity:0.85;" '
        f'alt="CrowAgent™">'
        if logo_uri
        else ""
    )
    st.markdown(
        f"""
        <div class="ent-footer" role="contentinfo">
            {logo_img}
            <div style="color:#CBD8E6; font-size:0.9rem; font-weight:600;
                        margin-bottom:10px; letter-spacing:0.5px;">
                CrowAgent™ Sustainability AI Decision Intelligence Platform
                v2.0.0 &nbsp;·&nbsp; Working Prototype
            </div>
            <div style="color:#8AACBF; font-size:0.85rem; margin-bottom:16px;
                        max-width:700px; line-height:1.6;">
                ⚠️ <strong>Results Are Indicative Only.</strong> This platform
                uses simplified physics models calibrated against published UK
                higher education sector averages. Outputs should not be used as
                the sole basis for capital investment decisions. Consult a
                qualified energy surveyor before committing to any retrofit
                programme. Greenfield University is a fictional institution used
                for demonstration purposes. All data is illustrative.
            </div>
            <div style="color:#9ABDD0; font-size:0.8rem; margin-bottom:8px;">
                © 2026 CrowAgent™. All rights reserved.
                &nbsp;·&nbsp; Developed by Aparajita Parihar
                &nbsp;·&nbsp; Independent research project
                &nbsp;·&nbsp; CrowAgent™ is an unregistered trademark
                (UK IPO Class 42, registration pending)
                &nbsp;·&nbsp; Not licensed for commercial use without written permission
            </div>
            <div style="color:#8AACBF; font-size:0.72rem; font-family:monospace;
                        letter-spacing:-0.2px;">
                Physics: Raissi et al. (2019) J. Comp. Physics &nbsp;·&nbsp;
                <a href="https://doi.org/10.1016/j.jcp.2018.10.045"
                   target="_blank"
                   style="color:#8AACBF; text-decoration:none;">
                   doi:10.1016/j.jcp.2018.10.045
                </a>
                &nbsp;·&nbsp; Weather: Open-Meteo API + Met Office DataPoint
                &nbsp;·&nbsp; Carbon: BEIS 2023 &nbsp;·&nbsp; Costs: HESA 2022-23
                &nbsp;·&nbsp; AI: Google Gemini 1.5 Pro
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Streamlit page configuration ─────────────────────────────────────────────
# Imported by main.py and passed directly to st.set_page_config().
PAGE_CONFIG = {
    "page_title": "CrowAgent™ Platform",
    "page_icon": get_icon_uri() or "🌿",
    "layout": "wide",
    "initial_sidebar_state": "auto",
    "menu_items": {
        "Get Help": "mailto:crowagent.platform@gmail.com",
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
