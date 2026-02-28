"""
Handles all visual branding, including CSS, logos, and page configuration.
"""
import streamlit as st
import base64
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# ENTERPRISE CSS — Full suite including topbar, pills, cards, chat, footer
# ─────────────────────────────────────────────────────────────────────────────
CROWAGENT_CSS = """
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
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stSelectbox > div > div {
  background: #0D2640 !important; border: 1px solid #1A3A5C !important; color: #CBD8E6 !important;
}
[data-testid="stSidebar"] hr { border-color: #1A3A5C !important; }
[data-testid="stSidebar"] .stButton button {
  background: #0D2640 !important; border: 1px solid #00C2A8 !important; color: #00C2A8 !important;
  font-size: 0.82rem !important; font-weight: 600 !important; padding: 4px 10px !important;
}
[data-testid="stSidebar"] .stButton button:hover { background: #00C2A8 !important; color: #071A2F !important; }

/* ── Platform Topbar ─────────────────────────────────────────────────── */
.platform-topbar {
  background: linear-gradient(135deg, #071A2F 0%, #0D2640 60%, #0A2E40 100%);
  border-bottom: 2px solid #00C2A8; padding: 10px 24px; display: flex;
  align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 16px;
}
.platform-topbar-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

/* ── Status Pills ────────────────────────────────────────────────────── */
.sp { display:inline-flex; align-items:center; gap:5px; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:700; white-space:nowrap; }
.sp-live { background:rgba(29,184,122,.12); color:#1DB87A; border:1px solid rgba(29,184,122,.3); }
.sp-cache { background:rgba(240,180,41,.1); color:#F0B429; border:1px solid rgba(240,180,41,.25); }
.sp-manual { background:rgba(90,122,144,.12); color:#A8C8D8; border:1px solid rgba(90,122,144,.2); }
.sp-warn { background:rgba(232,76,76,.1); color:#E84C4C; border:1px solid rgba(232,76,76,.25); }
.pulse-dot { width:7px; height:7px; border-radius:50%; background:#1DB87A; display:inline-block; animation: blink 2s ease-in-out infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }

/* ── Tabs ────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] { background: #ffffff !important; border-bottom: 2px solid #E0EBF4 !important; gap: 0 !important; padding: 0 !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: #3A576B !important; font-family: 'Rajdhani', sans-serif !important; font-size: 0.88rem !important; font-weight: 600 !important; padding: 10px 20px !important; border-bottom: 3px solid transparent !important; }
.stTabs [aria-selected="true"] { color: #071A2F !important; border-bottom: 3px solid #00C2A8 !important; background: rgba(0,194,168,.04) !important; }

/* ── KPI Cards ───────────────────────────────────────────────────────── */
.kpi-card { background: #ffffff; border-radius: 8px; padding: 18px 20px 14px; border: 1px solid #E0EBF4; border-top: 3px solid #00C2A8; box-shadow: 0 2px 8px rgba(7,26,47,.05); height: 100%; transition: transform 0.2s ease, box-shadow 0.2s ease; }
.kpi-card:hover { transform: translateY(-4px); box-shadow: 0 4px 12px rgba(7,26,47,.15); }
.kpi-card.accent-green { border-top-color: #1DB87A; }
.kpi-card.accent-gold { border-top-color: #F0B429; }
.kpi-card.accent-teal { border-top-color: #00C2A8; }
.kpi-card.accent-navy { border-top-color: #071A2F; }
.kpi-card.accent-red { border-top-color: #E84C4C; }
.kpi-label { font-family: 'Rajdhani', sans-serif; font-size: 0.78rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: #3A576B; margin-bottom: 6px; }
.kpi-value { font-family: 'Rajdhani', sans-serif; font-size: 2rem; font-weight: 700; color: #071A2F; line-height: 1.1; }
.kpi-unit { font-size: 0.9rem; font-weight: 500; color: #3A576B; margin-left: 2px; }
.kpi-delta-pos { color: #1DB87A; font-size: 0.80rem; font-weight: 700; margin-top: 4px; }
.kpi-delta-neg { color: #E84C4C; font-size: 0.80rem; font-weight: 700; margin-top: 4px; }
.kpi-sub { font-size: 0.78rem; color: #5A7A90; margin-top: 2px; }
.kpi-subtext { font-size: 0.78rem; color: #5A7A90; margin-top: 2px; }

/* ── Section Headers & Charts ────────────────────────────────────────── */
.sec-hdr { font-family: 'Rajdhani', sans-serif; font-size: 0.84rem; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #00C2A8; border-bottom: 1px solid rgba(0,194,168,.2); padding-bottom: 6px; margin-bottom: 14px; margin-top: 4px; }
.chart-card { background: #ffffff; border-radius: 8px; border: 1px solid #E0EBF4; padding: 18px 18px 10px; box-shadow: 0 2px 8px rgba(7,26,47,.04); margin-bottom: 16px; }
.chart-title { font-family: 'Rajdhani', sans-serif; font-size: 0.88rem; font-weight: 700; color: #071A2F; margin-bottom: 4px; text-transform: uppercase; }
.chart-caption { font-size: 0.74rem; color: #8AACBF; margin-top: 4px; font-style: italic; }

/* ── Disclaimer Boxes ────────────────────────────────────────────────── */
.disc-prototype { background: rgba(240,180,41,.07); border: 1px solid rgba(240,180,41,.3); border-left: 4px solid #F0B429; padding: 10px 16px; font-size: 0.82rem; color: #6A5010; margin: 10px 0; border-radius: 0 6px 6px 0; }
.disc-ai { background: rgba(0,194,168,.05); border: 1px solid rgba(0,194,168,.2); border-left: 4px solid #00C2A8; padding: 10px 16px; font-size: 0.82rem; color: #1A3A5C; margin: 10px 0; border-radius: 0 6px 6px 0; }
.disc-data { background: rgba(90,122,144,.06); border: 1px solid rgba(90,122,144,.2); border-left: 4px solid #5A7A90; padding: 10px 16px; font-size: 0.82rem; color: #3A5268; margin: 10px 0; border-radius: 0 6px 6px 0; }

/* ── Enterprise Footer ───────────────────────────────────────────────── */
.ent-footer { background: #071A2F; border-top: 2px solid #00C2A8; padding: 16px 24px; margin-top: 32px; text-align: center; display: flex; flex-direction: column; align-items: center; }

/* ── Validation Feedback ─────────────────────────────────────────────── */
.val-err { background: rgba(220,53,69,.08); border-left: 3px solid #DC3545; padding: 7px 12px; font-size: 0.80rem; color: #721C24; }
.val-ok { background: rgba(29,184,122,.08); border-left: 3px solid #1DB87A; padding: 7px 12px; font-size: 0.80rem; color: #0A5030; }
.val-warn { background: rgba(240,180,41,.08); border-left: 3px solid #F0B429; padding: 7px 12px; font-size: 0.80rem; color: #664D03; }

/* ── Sidebar Sections ────────────────────────────────────────────────── */
.sb-section { font-family: 'Rajdhani', sans-serif; font-size: 0.80rem; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #00C2A8 !important; margin: 14px 0 6px 0; }

/* ── Chips / Badges ──────────────────────────────────────────────────── */
.chip { display: inline-block; background: #0D2640; border: 1px solid #1A3A5C; border-radius: 4px; padding: 2px 8px; font-size: 0.78rem; color: #9ABDD0; margin: 2px; }

/* ── AI Chat Bubbles ─────────────────────────────────────────────────── */
.ca-user { background:#071A2F; border-left:3px solid #00C2A8; border-radius:0 8px 8px 8px;
           padding:10px 14px; margin:10px 0 4px; color:#F0F4F8; font-size:0.88rem; line-height:1.5; }
.ca-ai   { background:#ffffff; border:1px solid #E0EBF4; border-left:3px solid #1DB87A;
           border-radius:0 8px 8px 8px; padding:10px 14px; margin:4px 0 10px;
           color:#071A2F; font-size:0.88rem; line-height:1.65; }
.ca-tool { display:inline-block; background:#0D2640; color:#00C2A8; border-radius:4px;
           padding:2px 8px; font-size:0.78rem; font-weight:700; margin:2px 2px 2px 0; letter-spacing:0.3px; }
.ca-meta { font-size:0.78rem; color:#6A92AA; margin-top:4px; }

/* ── Contact Card (About tab) ────────────────────────────────────────── */
.contact-card { background:#ffffff; border:1px solid #E0EBF4; border-radius:8px; padding:20px 22px; box-shadow:0 2px 8px rgba(7,26,47,.05); }
.contact-label { font-family:'Rajdhani',sans-serif; font-size:0.75rem; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:#8AACBF; margin-bottom:3px; }
.contact-val { font-size:0.88rem; color:#071A2F; font-weight:600; margin-bottom:10px; }

/* ── Weather Widget ──────────────────────────────────────────────────── */
.wx-widget { background:#0D2640; border:1px solid #1A3A5C; border-radius:8px; padding:12px 14px; margin-bottom:8px; }
.wx-temp { font-family:'Rajdhani',sans-serif; font-size:2.2rem; font-weight:700; color:#F0F4F8; line-height:1.1; }
.wx-desc { font-size:0.82rem; color:#8FBCCE; margin-bottom:6px; }
.wx-row { font-size:0.79rem; color:#8FBCCE; margin-top:4px; }

/* ── Hide Streamlit Chrome ───────────────────────────────────────────── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
div[data-testid="stToolbar"], div[data-testid="stStatusWidget"] { visibility: hidden; }
header { background: transparent !important; }
"""


def _load_asset_uri(filename: str) -> str:
    """
    Resolves an asset's path across candidate locations and returns a
    base64 encoded data URI.
    """
    candidate_paths = [
        Path("assets") / filename,
        Path("app/assets") / filename,
        Path(".") / filename,
    ]
    for path in candidate_paths:
        if path.is_file():
            with open(path, "rb") as f:
                data = f.read()
            b64_data = base64.b64encode(data).decode("utf-8")
            return f"data:image/svg+xml;base64,{b64_data}"
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
PAGE_CONFIG = {
    "page_title": "CrowAgent™ Platform",
    "page_icon": get_icon_uri() or "🌿",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
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
