# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — Sustainability AI Decision Intelligence
# © 2026 Aparajita Parihar. All rights reserved.
#
# Independent research project. Not affiliated with any institution.
# Not licensed for commercial use without written permission of the author.
# CrowAgent™ is an unregistered trademark pending UK IPO Class 42.
#
# Platform Version : v2.0.0 — 21 February 2026
# Status           : Working Prototype — See disclaimer
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations
import base64
import os
import sys
import json
import math

# ensure proper UTF-8 output in environments with non-UTF8 locale
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
# Load .env from project root (parent directory of app/)
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_env_path)

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import requests
import pydeck as pdk
from datetime import datetime, timezone


# ----------------------------------------------------------------------------
# helper functions for user-added definitions (used by sidebar forms and tests)
# ----------------------------------------------------------------------------
def _add_building_from_json(jtext: str) -> tuple[bool, str]:
    try:
        obj = json.loads(jtext)
    except Exception as exc:
        return False, f"JSON parse error: {exc}"
    if "name" not in obj:
        return False, "Missing \"name\" key."
    name = obj.pop("name")
    if not isinstance(name, str) or not name.strip():
        return False, "Invalid building name."
    BUILDINGS[name] = obj
    return True, f"Building '{name}' added." 


def _add_scenario_from_json(jtext: str) -> tuple[bool, str]:
    try:
        obj = json.loads(jtext)
    except Exception as exc:
        return False, f"JSON parse error: {exc}"
    if "name" not in obj:
        return False, "Missing \"name\" key."
    name = obj.pop("name")
    if not isinstance(name, str) or not name.strip():
        return False, "Invalid scenario name."
    SCENARIOS[name] = obj
    return True, f"Scenario '{name}' added."

# ─────────────────────────────────────────────────────────────────────────────
# PATH SETUP — Ensure core and services modules are accessible
# ─────────────────────────────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import services.weather as wx
import services.location as loc
import services.audit as audit
import core.agent as crow_agent
import core.physics as physics

# ─────────────────────────────────────────────────────────────────────────────
# LOGO LOADER
# ─────────────────────────────────────────────────────────────────────────────
def _load_logo_uri() -> str:
    candidates = [
        os.path.join(os.path.dirname(__file__), "../assets/CrowAgent_Logo_Horizontal_Dark.svg"),
        os.path.join(os.path.dirname(__file__), "assets/CrowAgent_Logo_Horizontal_Dark.svg"),
        os.path.join(os.getcwd(), "assets/CrowAgent_Logo_Horizontal_Dark.svg"),
        "assets/CrowAgent_Logo_Horizontal_Dark.svg",
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "rb") as fh:
                    b64 = base64.b64encode(fh.read()).decode()
                return f"data:image/svg+xml;base64,{b64}"
            except Exception as e:
                st.warning(f"Failed to read logo file at {path}: {e}")
                return ""
    st.warning("CrowAgent logo asset not found; falling back to text/emoji branding.")
    return ""

def _load_icon_uri() -> str:
    candidates = [
        os.path.join(os.path.dirname(__file__), "../assets/CrowAgent_Icon_Square.svg"),
        os.path.join(os.path.dirname(__file__), "assets/CrowAgent_Icon_Square.svg"),
        os.path.join(os.getcwd(), "assets/CrowAgent_Icon_Square.svg"),
        "assets/CrowAgent_Icon_Square.svg",
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "rb") as fh:
                    b64 = base64.b64encode(fh.read()).decode()
                return f"data:image/svg+xml;base64,{b64}"
            except Exception as e:
                st.warning(f"Failed to read icon file at {path}: {e}")
                return ""
    st.warning("CrowAgent icon asset not found; falling back to emoji favicon.")
    return ""

LOGO_URI = _load_logo_uri()
ICON_URI = _load_icon_uri()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title   = "CrowAgent™ Platform",
    page_icon    = ICON_URI or "🌿",
    layout       = "wide",
    initial_sidebar_state = "expanded",
    menu_items   = {
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
)

# ─────────────────────────────────────────────────────────────────────────────
# ENTERPRISE CSS + GOOGLE FONTS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Nunito+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap');

/* ── Global resets ─────────────────────────────────────────────────────── */
html, body, [class*="css"] { font-family: 'Nunito Sans', sans-serif !important; }
h1,h2,h3,h4 { font-family: 'Rajdhani', sans-serif !important; letter-spacing: 0.3px; }

/* ── App background ────────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"] > .main { background: #F0F4F8; }
.block-container { padding-top: 0 !important; max-width: 100% !important; }

/* ── Sidebar ───────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] { background: #071A2F !important; border-right: 1px solid #1A3A5C !important; }
[data-testid="stSidebar"] * { color: #CBD8E6 !important; }
[data-testid="stSidebar"] .stMarkdown h1, [data-testid="stSidebar"] .stMarkdown h2, [data-testid="stSidebar"] .stMarkdown h3 { color: #00C2A8 !important; }
[data-testid="stSidebar"] .stTextInput input { background: #0D2640 !important; border: 1px solid #1A3A5C !important; color: #CBD8E6 !important; font-size: 0.82rem !important; }
[data-testid="stSidebar"] .stSelectbox > div > div { background: #0D2640 !important; border: 1px solid #1A3A5C !important; color: #CBD8E6 !important; }
[data-testid="stSidebar"] hr { border-color: #1A3A5C !important; }
[data-testid="stSidebar"] .stCheckbox span { color: #CBD8E6 !important; }
[data-testid="stSidebar"] .stButton button { background: #0D2640 !important; border: 1px solid #00C2A8 !important; color: #00C2A8 !important; font-size: 0.82rem !important; font-weight: 600 !important; padding: 4px 10px !important; }
[data-testid="stSidebar"] .stButton button:hover { background: #00C2A8 !important; color: #071A2F !important; }

/* ── Platform header bar ───────────────────────────────────────────────── */
.platform-topbar { background: linear-gradient(135deg, #071A2F 0%, #0D2640 60%, #0A2E40 100%); border-bottom: 2px solid #00C2A8; padding: 10px 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.platform-topbar-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

/* ── Status pills ──────────────────────────────────────────────────────── */
.sp { display:inline-flex; align-items:center; gap:5px; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:700; letter-spacing:0.3px; white-space:nowrap; }
.sp-live   { background:rgba(29,184,122,.12); color:#1DB87A; border:1px solid rgba(29,184,122,.3); }
.sp-cache  { background:rgba(240,180,41,.1);  color:#F0B429; border:1px solid rgba(240,180,41,.25); }
.sp-manual { background:rgba(90,122,144,.12); color:#A8C8D8; border:1px solid rgba(90,122,144,.2); }
.sp-warn   { background:rgba(232,76,76,.1);   color:#E84C4C; border:1px solid rgba(232,76,76,.25); }
.pulse-dot { width:7px; height:7px; border-radius:50%; background:#1DB87A; display:inline-block; animation: blink 2s ease-in-out infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }

/* ── Tab navigation ────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] { background: #ffffff !important; border-bottom: 2px solid #E0EBF4 !important; gap: 0 !important; padding: 0 !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: #3A576B !important; font-family: 'Rajdhani', sans-serif !important; font-size: 0.88rem !important; font-weight: 600 !important; letter-spacing: 0.5px !important; padding: 10px 20px !important; border-bottom: 3px solid transparent !important; }
.stTabs [aria-selected="true"] { color: #071A2F !important; border-bottom: 3px solid #00C2A8 !important; background: rgba(0,194,168,.04) !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 20px 0 0 0 !important; }

/* ── Section headers ───────────────────────────────────────────────────── */
.sec-hdr { font-family: 'Rajdhani', sans-serif; font-size: 0.84rem; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #00C2A8; border-bottom: 1px solid rgba(0,194,168,.2); padding-bottom: 6px; margin-bottom: 14px; margin-top: 4px; }

/* ── Chart containers ──────────────────────────────────────────────────── */
.chart-card { background: #ffffff; border-radius: 8px; border: 1px solid #E0EBF4; padding: 18px 18px 10px; box-shadow: 0 2px 8px rgba(7,26,47,.04); margin-bottom: 16px; }
.chart-title { font-family: 'Rajdhani', sans-serif; font-size: 0.88rem; font-weight: 700; letter-spacing: 0.5px; color: #071A2F; margin-bottom: 4px; text-transform: uppercase; }
.chart-caption { font-size: 0.77rem; color: #6A92AA; margin-top: 4px; font-style: italic; }

/* ── Disclaimer banners ────────────────────────────────────────────────── */
.disc-prototype { background: rgba(240,180,41,.07); border: 1px solid rgba(240,180,41,.3); border-left: 4px solid #F0B429; border-radius: 0 6px 6px 0; padding: 10px 16px; font-size: 0.82rem; color: #6A5010; line-height: 1.55; margin: 10px 0; }
.disc-ai { background: rgba(0,194,168,.05); border: 1px solid rgba(0,194,168,.2); border-left: 4px solid #00C2A8; border-radius: 0 6px 6px 0; padding: 10px 16px; font-size: 0.82rem; color: #1A5A50; line-height: 1.55; margin: 10px 0; }
.disc-data { background: rgba(7,26,47,.04); border: 1px solid rgba(7,26,47,.12); border-left: 4px solid #071A2F; border-radius: 0 6px 6px 0; padding: 10px 16px; font-size: 0.82rem; color: #3A5268; line-height: 1.55; margin: 10px 0; }

/* ── Weather widget (sidebar) ──────────────────────────────────────────── */
.wx-widget { background: #0D2640; border: 1px solid #1A3A5C; border-radius: 8px; padding: 12px 14px; margin: 6px 0; }
.wx-temp { font-family: 'Rajdhani', sans-serif; font-size: 2rem; font-weight: 700; color: #ffffff; display: inline-block; line-height: 1; }
.wx-desc { font-size: 0.82rem; color: #A8C8D8; margin-top: 2px; }
.wx-row  { font-size: 0.78rem; color: #CBD8E6; margin-top: 5px; }

/* ── Contact cards ─────────────────────────────────────────────────────── */
.contact-card { background: #ffffff; border-radius: 8px; border: 1px solid #E0EBF4; padding: 20px 22px; box-shadow: 0 2px 8px rgba(7,26,47,.05); }
.contact-label { font-family: 'Rajdhani', sans-serif; font-size: 0.80rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: #00C2A8; margin-bottom: 4px; }
.contact-val { font-size: 0.88rem; color: #071A2F; font-weight: 600; }

/* ── Enterprise footer ─────────────────────────────────────────────────── */
.ent-footer { background: #071A2F; border-top: 2px solid #00C2A8; padding: 16px 24px; margin-top: 32px; text-align: center; display: flex; flex-direction: column; align-items: center; }

/* ── Validation messages ───────────────────────────────────────────────── */
.val-warn { background: rgba(232,76,76,.06); border: 1px solid rgba(232,76,76,.25); border-left: 3px solid #E84C4C; border-radius: 0 4px 4px 0; padding: 7px 12px; font-size: 0.80rem; color: #8B1A1A; }
.val-ok { background: rgba(29,184,122,.06); border: 1px solid rgba(29,184,122,.25); border-left: 3px solid #1DB87A; border-radius: 0 4px 4px 0; padding: 7px 12px; font-size: 0.80rem; color: #0A4A28; }
.val-err { background: rgba(220,53,69,.08); border: 1px solid rgba(220,53,69,.3); border-left: 3px solid #DC3545; border-radius: 0 4px 4px 0; padding: 7px 12px; font-size: 0.80rem; color: #721C24; }

/* ── Sidebar section label ─────────────────────────────────────────────── */
.sb-section { font-family: 'Rajdhani', sans-serif; font-size: 0.80rem; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #00C2A8 !important; margin: 14px 0 6px 0; }

/* ── Info chip ─────────────────────────────────────────────────────────── */
.chip { display: inline-block; background: #0D2640; border: 1px solid #1A3A5C; border-radius: 4px; padding: 2px 8px; font-size: 0.78rem; color: #9ABDD0; margin: 2px; }

/* ── Clean up Streamlit defaults ─────────────── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
div[data-testid="stToolbar"], div[data-testid="stStatusWidget"] { visibility: hidden; }
header { background: transparent !important; }
button[data-testid="stSidebarCollapseButton"] { visibility: visible !important; color: #00C2A8 !important; }
button[data-testid="stSidebarCollapseButton"]:hover { color: #009688 !important; }
[data-testid="stSidebar"] { background: #071A2F !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# BUILDING DATA
# ─────────────────────────────────────────────────────────────────────────────
BUILDINGS: dict[str, dict] = {
    "Greenfield Library": {
        "floor_area_m2":      8500, "height_m": 4.5, "glazing_ratio": 0.35,
        "u_value_wall":       1.8, "u_value_roof": 2.1, "u_value_glazing": 2.8,
        "baseline_energy_mwh": 487, "occupancy_hours": 3500,
        "description":        "Main campus library — 8,500 m² · 5 floors · Heavy glazing",
        "built_year":         "Pre-1990", "building_type": "Library / Learning Hub",
    },
    "Greenfield Arts Building": {
        "floor_area_m2":      11200, "height_m": 5.0, "glazing_ratio": 0.28,
        "u_value_wall":       2.1, "u_value_roof": 1.9, "u_value_glazing": 3.1,
        "baseline_energy_mwh": 623, "occupancy_hours": 4000,
        "description":        "Humanities faculty — 11,200 m² · 6 floors · Lecture theatres",
        "built_year":         "Pre-1985", "building_type": "Teaching / Lecture",
    },
    "Greenfield Science Block": {
        "floor_area_m2":      6800, "height_m": 4.0, "glazing_ratio": 0.30,
        "u_value_wall":       1.6, "u_value_roof": 1.7, "u_value_glazing": 2.6,
        "baseline_energy_mwh": 391, "occupancy_hours": 3200,
        "description":        "Science laboratories — 6,800 m² · 4 floors · Lab-heavy usage",
        "built_year":         "Pre-1995", "building_type": "Laboratory / Research",
    },
}

SCENARIOS: dict[str, dict] = {
    "Baseline (No Intervention)": {
        "description": "Current state — no modifications applied.",
        "u_wall_factor": 1.0, "u_roof_factor": 1.0, "u_glazing_factor": 1.0, 
        "solar_gain_reduction": 0.0, "infiltration_reduction": 0.0, "renewable_kwh": 0,
        "install_cost_gbp": 0, "colour": "#4A6FA5", "icon": "🏢",
    },
    "Solar Glass Installation": {
        "description": "Replace standard glazing with BIPV solar glass. U-value improvement ~45%.",
        "u_wall_factor": 1.0, "u_roof_factor": 1.0, "u_glazing_factor": 0.55, 
        "solar_gain_reduction": 0.15, "infiltration_reduction": 0.05, "renewable_kwh": 42000,
        "install_cost_gbp": 280000, "colour": "#00C2A8", "icon": "☀️",
    },
    "Green Roof Installation": {
        "description": "Vegetated green roof layer. Roof U-value improvement ~55%.",
        "u_wall_factor": 1.0, "u_roof_factor": 0.45, "u_glazing_factor": 1.0, 
        "solar_gain_reduction": 0.0, "infiltration_reduction": 0.02, "renewable_kwh": 0,
        "install_cost_gbp": 95000, "colour": "#1DB87A", "icon": "🌱",
    },
    "Enhanced Insulation Upgrade": {
        "description": "Wall, roof and glazing upgrade to near-Passivhaus standard.",
        "u_wall_factor": 0.40, "u_roof_factor": 0.35, "u_glazing_factor": 0.70, 
        "solar_gain_reduction": 0.0, "infiltration_reduction": 0.20, "renewable_kwh": 0,
        "install_cost_gbp": 520000, "colour": "#0A5C3E", "icon": "🏗️",
    },
    "Combined Package (All Interventions)": {
        "description": "Solar glass + green roof + enhanced insulation simultaneously.",
        "u_wall_factor": 0.40, "u_roof_factor": 0.35, "u_glazing_factor": 0.55, 
        "solar_gain_reduction": 0.15, "infiltration_reduction": 0.22, "renewable_kwh": 42000,
        "install_cost_gbp": 895000, "colour": "#062E1E", "icon": "⚡",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# PHYSICS ENGINE — PINN Thermal Model
# ─────────────────────────────────────────────────────────────────────────────
def calculate_thermal_load(building: dict, scenario: dict, weather_data: dict) -> dict:
    b = building; s = scenario; temp = weather_data["temperature_c"]
    valid, msg = wx.validate_temperature(temp)
    if not valid: raise ValueError(f"Physics model validation: {msg}")

    perimeter_m = 4.0 * (b["floor_area_m2"] ** 0.5)
    wall_area_m2 = perimeter_m * b["height_m"] * (1.0 - b["glazing_ratio"])
    glazing_area_m2 = perimeter_m * b["height_m"] * b["glazing_ratio"]
    roof_area_m2 = b["floor_area_m2"]
    volume_m3 = b["floor_area_m2"] * b["height_m"]

    u_wall = b["u_value_wall"] * s["u_wall_factor"]
    u_roof = b["u_value_roof"] * s["u_roof_factor"]
    u_glazing = b["u_value_glazing"] * s["u_glazing_factor"]

    delta_t = max(0.0, 21.0 - temp)
    heating_hrs = 5800.0

    q_wall = u_wall * wall_area_m2 * delta_t * heating_hrs
    q_roof = u_roof * roof_area_m2 * delta_t * heating_hrs
    q_glazing = u_glazing * glazing_area_m2 * delta_t * heating_hrs
    q_trans_mwh = (q_wall + q_roof + q_glazing) / 1_000_000.0

    ach = 0.7 * (1.0 - s["infiltration_reduction"])
    q_inf_mwh = (0.33 * ach * volume_m3 * delta_t * heating_hrs) / 1_000_000.0

    solar_mwh = (950.0 * glazing_area_m2 * 0.6 * (1.0 - s["solar_gain_reduction"])) / 1_000.0
    modelled_mwh = max(0.0, q_trans_mwh + q_inf_mwh - solar_mwh * 0.3)

    baseline_raw = (
        b["u_value_wall"] * wall_area_m2 * delta_t * heating_hrs
      + b["u_value_roof"] * roof_area_m2 * delta_t * heating_hrs
      + b["u_value_glazing"] * glazing_area_m2 * delta_t * heating_hrs
      + 0.33 * 0.7 * volume_m3 * delta_t * heating_hrs
    ) / 1_000_000.0

    reduction_ratio = max(0.0, 1.0 - (baseline_raw - modelled_mwh) / baseline_raw) if baseline_raw > 0 else 1.0
    adjusted_mwh = b["baseline_energy_mwh"] * max(0.35, reduction_ratio)
    renewable_mwh = s["renewable_kwh"] / 1_000.0
    final_mwh = max(0.0, adjusted_mwh - renewable_mwh)

    ci = 0.20482
    baseline_carbon = (b["baseline_energy_mwh"] * 1000.0 * ci) / 1000.0
    scenario_carbon = (final_mwh * 1000.0 * ci) / 1000.0

    unit_cost = 0.28
    annual_saving = (b["baseline_energy_mwh"] - final_mwh) * 1000.0 * unit_cost
    install_cost = float(s["install_cost_gbp"])
    payback = (install_cost / annual_saving) if annual_saving > 0.0 else None
    cpt = round(install_cost / max(baseline_carbon - scenario_carbon, 0.01), 1) if install_cost > 0 else None

    return {
        "baseline_energy_mwh": round(b["baseline_energy_mwh"], 1), "scenario_energy_mwh": round(final_mwh, 1),
        "energy_saving_mwh": round(b["baseline_energy_mwh"] - final_mwh, 1),
        "energy_saving_pct": round((b["baseline_energy_mwh"] - final_mwh) / b["baseline_energy_mwh"] * 100.0, 1),
        "baseline_carbon_t": round(baseline_carbon, 1), "scenario_carbon_t": round(scenario_carbon, 1),
        "carbon_saving_t": round(baseline_carbon - scenario_carbon, 1), "annual_saving_gbp": round(annual_saving, 0),
        "install_cost_gbp": install_cost, "payback_years": round(payback, 1) if payback else None,
        "cost_per_tonne_co2": cpt, "renewable_mwh": round(renewable_mwh, 1),
        "u_wall": round(u_wall, 2), "u_roof": round(u_roof, 2), "u_glazing": round(u_glazing, 2),
    }

# ─────────────────────────────────────────────────────────────────────────────
# CHART THEME
# ─────────────────────────────────────────────────────────────────────────────
CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Nunito Sans, sans-serif", size=11, color="#071A2F"),
    margin=dict(t=20, b=10, l=0, r=0), height=300,
    yaxis=dict(gridcolor="#E8EEF4", zerolinecolor="#D0DAE4", tickfont=dict(size=10)),
    xaxis=dict(tickfont=dict(size=10)), showlegend=False,
)

from app.utils import validate_gemini_key
import app.compliance as compliance

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INITIALISATION
# ─────────────────────────────────────────────────────────────────────────────
def _get_secret(key: str, default: str = "") -> str:
    try: return st.secrets[key]
    except (KeyError, AttributeError, FileNotFoundError): return os.getenv(key, default)

if "user_segment" not in st.session_state: st.session_state.user_segment = "university_he"
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "agent_history" not in st.session_state: st.session_state.agent_history = []
if "gemini_key" not in st.session_state: st.session_state.gemini_key = _get_secret("GEMINI_KEY", "")
if "gemini_key_valid" not in st.session_state: st.session_state.gemini_key_valid = False
if "met_office_key" not in st.session_state: st.session_state.met_office_key = _get_secret("MET_OFFICE_KEY", "")
if "manual_temp" not in st.session_state: st.session_state.manual_temp = 10.5
if "force_weather_refresh" not in st.session_state: st.session_state.force_weather_refresh = False
if "wx_city" not in st.session_state: st.session_state.wx_city = "Reading, Berkshire"
if "wx_lat" not in st.session_state: st.session_state.wx_lat = loc.CITIES["Reading, Berkshire"]["lat"]
if "wx_lon" not in st.session_state: st.session_state.wx_lon = loc.CITIES["Reading, Berkshire"]["lon"]
if "wx_location_name" not in st.session_state: st.session_state.wx_location_name = "Reading, Berkshire, UK"
if "wx_provider" not in st.session_state: st.session_state.wx_provider = "open_meteo"
if "wx_enable_fallback" not in st.session_state: st.session_state.wx_enable_fallback = True
if "owm_key" not in st.session_state: st.session_state.owm_key = _get_secret("OWM_KEY", "")

_qp = st.query_params
if "geo_lat" in _qp and "geo_lon" in _qp:
    try:
        _geo_lat = float(_qp["geo_lat"])
        _geo_lon = float(_qp["geo_lon"])
        _resolved = loc.nearest_city(_geo_lat, _geo_lon)
        st.session_state.wx_city = _resolved
        st.session_state.wx_lat = loc.CITIES[_resolved]["lat"]
        st.session_state.wx_lon = loc.CITIES[_resolved]["lon"]
        st.session_state.wx_location_name = f"{_resolved}, {loc.CITIES[_resolved]['country']}"
        st.session_state.force_weather_refresh = True
        audit.log_event("LOCATION_AUTO_DETECTED", f"Resolved browser location to '{_resolved}'")
        st.query_params.clear()
        st.query_params["city"] = _resolved
    except Exception: pass
elif "city" in _qp:
    _city = _qp.get("city")
    if isinstance(_city, list): _city = _city[0]
    if _city in loc.CITIES:
        _meta = loc.city_meta(_city)
        st.session_state.wx_city = _city
        st.session_state.wx_lat = _meta["lat"]
        st.session_state.wx_lon = _meta["lon"]
        st.session_state.wx_location_name = f"{_city}, {_meta['country']}"
        st.session_state.force_weather_refresh = True
    st.query_params.clear()
elif "lat" in _qp and "lon" in _qp:
    try:
        _lat = float(_qp.get("lat"))
        _lon = float(_qp.get("lon"))
        st.session_state.wx_lat = _lat
        st.session_state.wx_lon = _lon
        st.session_state.wx_city = "" 
        st.session_state.wx_location_name = f"Custom site ({_lat:.4f}, {_lon:.4f})"
        st.session_state.force_weather_refresh = True
    except Exception: pass
    st.query_params.clear()

def _update_location_query_params() -> None:
    params: dict[str, str] = {}
    if st.session_state.wx_city: params["city"] = st.session_state.wx_city
    params["lat"] = str(st.session_state.wx_lat)
    params["lon"] = str(st.session_state.wx_lon)
    st.query_params.clear()
    st.query_params.update(params)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    if LOGO_URI:
        st.markdown(f"<div style='padding:10px 0 4px; text-align:center;'><img src='{LOGO_URI}' width='200' style='max-width:100%; height:auto; display:inline-block;' alt='CrowAgent™ Logo'/></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='font-family:Rajdhani,sans-serif;font-size:1.3rem;font-weight:700;color:#00C2A8;padding:10px 0 4px;'>🌿 CrowAgent™</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.82rem;color:#8FBCCE;margin-bottom:8px;'>Sustainability AI Decision Intelligence Platform</div>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("<div class='sb-section'>👤 User Segment</div>", unsafe_allow_html=True)
    _seg_options = {k: f"{v['icon']} {v['label']}" for k, v in compliance.SEGMENT_META.items()}
    _seg_keys = list(_seg_options.keys())
    _seg_idx = _seg_keys.index(st.session_state.user_segment) if st.session_state.user_segment in _seg_keys else 0
    _sel_segment = st.selectbox("User segment", _seg_keys, index=_seg_idx, format_func=lambda k: _seg_options[k], label_visibility="collapsed", key="segment_selector")
    if _sel_segment != st.session_state.user_segment: st.session_state.user_segment = _sel_segment
    _seg_meta = compliance.SEGMENT_META[st.session_state.user_segment]
    st.markdown(f"<div style='font-size:0.74rem;color:#8FBCCE;line-height:1.5;margin-bottom:4px;'>{_seg_meta['description']}</div>", unsafe_allow_html=True)
    st.markdown("---")

    _seg_buildings = compliance.SEGMENT_BUILDINGS.get(st.session_state.user_segment, {})
    _active_buildings = dict(BUILDINGS)           
    if _seg_buildings: _active_buildings = {**_seg_buildings, **BUILDINGS}  

    st.markdown("<div class='sb-section'>🏢 Building</div>", unsafe_allow_html=True)
    selected_building_name = st.selectbox("Building", list(_active_buildings.keys()), label_visibility="collapsed")
    sb = _active_buildings[selected_building_name]
    st.markdown(f"<div style='font-size:0.76rem;color:#9ABDD0;line-height:1.5;'><span class='chip'>{sb['building_type']}</span> <span class='chip'>{sb['built_year']}</span> <span class='chip'>{sb['floor_area_m2']:,} m²</span></div>", unsafe_allow_html=True)

    with st.expander("➕ Add building", expanded=False):
        st.markdown("<div style='font-size:0.75rem;color:#8FBCCE;'>Enter JSON (must include \"name\")</div>", unsafe_allow_html=True)
        cb = st.text_area("Building JSON", height=120)
        if st.button("Add building", key="add_building_btn"):
            ok, msg = _add_building_from_json(cb)
            if ok: st.success(msg)
            else: st.error(msg)
    st.markdown("---")

    st.markdown("<div class='sb-section'>🔧 Scenarios</div>", unsafe_allow_html=True)
    selected_scenario_names = st.multiselect("Scenarios", list(SCENARIOS.keys()), default=["Baseline (No Intervention)", "Solar Glass Installation", "Enhanced Insulation Upgrade", "Combined Package (All Interventions)"], label_visibility="collapsed")
    
    with st.expander("➕ Add scenario", expanded=False):
        st.markdown("<div style='font-size:0.75rem;color:#8FBCCE;'>Enter JSON (must include \"name\")</div>", unsafe_allow_html=True)
        cs = st.text_area("Scenario JSON", height=120)
        if st.button("Add scenario", key="add_scenario_btn"):
            ok, msg = _add_scenario_from_json(cs)
            if ok: st.success(msg)
            else: st.error(msg)
    if not selected_scenario_names:
        st.markdown("<div class='val-warn'>⚠ Select at least one scenario to continue.</div>", unsafe_allow_html=True)
        st.stop()
    st.markdown("---")

    st.markdown("<div class='sb-section'>📍 Location</div>", unsafe_allow_html=True)
    _city_list = loc.city_options()
    _city_idx = _city_list.index(st.session_state.wx_city) if st.session_state.wx_city in _city_list else 0
    _sel_city = st.selectbox("City / Region", _city_list, index=_city_idx, label_visibility="collapsed")
    if _sel_city != st.session_state.wx_city:
        _meta = loc.city_meta(_sel_city)
        st.session_state.wx_city = _sel_city
        st.session_state.wx_lat = _meta["lat"]
        st.session_state.wx_lon = _meta["lon"]
        st.session_state.wx_location_name = f"{_sel_city}, {_meta['country']}"
        st.session_state.force_weather_refresh = True
        audit.log_event("LOCATION_CHANGED", f"City set to '{_sel_city}'")
        _update_location_query_params()

    with st.expander("⚙ Custom coordinates", expanded=False):
        _col_lat, _col_lon = st.columns(2)
        with _col_lat: _custom_lat = st.number_input("Latitude", value=float(st.session_state.wx_lat), format="%.4f")
        with _col_lon: _custom_lon = st.number_input("Longitude", value=float(st.session_state.wx_lon), format="%.4f")
        if st.button("Apply", key="apply_coords", use_container_width=True):
            st.session_state.wx_lat = _custom_lat
            st.session_state.wx_lon = _custom_lon
            st.session_state.wx_location_name = f"Custom site ({_custom_lat:.4f}, {_custom_lon:.4f})"
            st.session_state.force_weather_refresh = True
            _update_location_query_params()
        
    _geo = loc.render_geo_detect()
    if _geo and isinstance(_geo, dict):
        try:
            _lat = float(_geo.get("lat"))
            _lon = float(_geo.get("lon"))
            _resolved = loc.nearest_city(_lat, _lon)
            st.session_state.wx_city = _resolved
            st.session_state.wx_lat = _lat
            st.session_state.wx_lon = _lon
            st.session_state.wx_location_name = f"{_resolved}, {loc.CITIES[_resolved]['country']}"
            st.session_state.force_weather_refresh = True
            _update_location_query_params()
        except Exception: pass

    st.markdown("---")
    st.markdown("<div class='sb-section'>🌤 Live Weather</div>", unsafe_allow_html=True)
    _force = st.button("↻ Refresh Weather", key="wx_refresh", use_container_width=True)
    if _force: st.session_state.force_weather_refresh = True

    manual_t = st.slider("Manual temperature override (°C)", -10.0, 35.0, st.session_state.manual_temp, 0.5)
    st.session_state.manual_temp = manual_t

    _mo_loc_id = loc.city_meta(st.session_state.wx_city).get("mo_id", wx.MET_OFFICE_LOCATION) if st.session_state.wx_city in loc.CITIES else wx.MET_OFFICE_LOCATION

    with st.spinner("Checking weather…"):
        weather = wx.get_weather(
            lat=st.session_state.wx_lat, lon=st.session_state.wx_lon,
            location_name=st.session_state.wx_location_name, provider=st.session_state.wx_provider,
            met_office_key=st.session_state.met_office_key or None, met_office_location=_mo_loc_id,
            openweathermap_key=st.session_state.owm_key or None, enable_fallback=st.session_state.wx_enable_fallback,
            manual_temp_c=manual_t, force_refresh=st.session_state.force_weather_refresh,
        )
    st.session_state.force_weather_refresh = False

    mins_ago = wx.minutes_since_fetch(weather["fetched_utc"])
    wdir_lbl = wx.wind_compass(weather["wind_dir_deg"])
    status_class = "sp sp-live" if weather["is_live"] else "sp sp-manual"
    status_dot = "<span class='pulse-dot'></span>" if weather["is_live"] else "○"
    status_text = f"Live · {mins_ago}m ago" if weather["is_live"] else "Manual override"

    st.markdown(f"""<div class='wx-widget'><div style='display:flex;justify-content:space-between;align-items:flex-start;'><div><div style='font-size:1.4rem;line-height:1;'>{weather['condition_icon']}</div><div class='wx-temp'>{weather['temperature_c']}°C</div><div class='wx-desc'>{weather['condition']}</div></div><div style='text-align:right;'><div style='font-size:0.76rem;color:#8FBCCE;'>{weather['location_name']}</div></div></div><div class='wx-row'>💨 {weather['wind_speed_mph']} mph {wdir_lbl} &nbsp;|&nbsp; 💧 {weather['humidity_pct']}% &nbsp;|&nbsp; 🌡️ {weather['feels_like_c']}°C feels like</div><div style='margin-top:6px;'><span class='{status_class}'>{status_dot} {status_text}</span></div></div>""", unsafe_allow_html=True)
    st.caption(f"📡 {weather['source']}")
    st.markdown("---")

    with st.expander("🔑 API Keys & Weather Config", expanded=False):
        st.markdown("<div style='background:#FFF3CD;border:1px solid #FFD89B;border-radius:6px;padding:10px;'><div style='font-size:0.75rem;color:#664D03;font-weight:700;margin-bottom:6px;'>🔒 Security Notice</div><div style='font-size:0.78rem;color:#664D03;line-height:1.5;'>• Keys exist in your session only (cleared on browser close)<br/>• Your keys are <strong>never</strong> stored on the server<br/>• Each user enters their own key independently<br/>• Use unique, disposable API keys if sharing this link</div></div><br/>", unsafe_allow_html=True)
        
        _provider_labels = {"open_meteo": "Open-Meteo (free, no key)", "openweathermap": "OpenWeatherMap (key required)", "met_office": "Met Office DataPoint (UK, key required)"}
        _provider_keys = list(_provider_labels.keys())
        _cur_prov_idx = _provider_keys.index(st.session_state.wx_provider) if st.session_state.wx_provider in _provider_keys else 0
        _sel_provider = st.selectbox("Weather provider", _provider_keys, index=_cur_prov_idx, format_func=lambda k: _provider_labels[k])
        if _sel_provider != st.session_state.wx_provider:
            st.session_state.wx_provider = _sel_provider
            st.session_state.force_weather_refresh = True

        _fb = st.checkbox("Fall back to Open-Meteo if primary fails", value=st.session_state.wx_enable_fallback)
        if _fb != st.session_state.wx_enable_fallback: st.session_state.wx_enable_fallback = _fb
        st.markdown("---")

        _show_owm = st.checkbox("Show OWM key", key="show_owm_key", value=False)
        _owm_value = st.session_state.owm_key
        _owm_key = st.text_input("OpenWeatherMap API key", type="default" if _show_owm else "password", value=_owm_value)
        if _owm_key != _owm_value: st.session_state.owm_key = _owm_key

        st.markdown("---")
        _show_mo = st.checkbox("Show Met Office key", key="show_mo_key", value=False)
        _mo_value = st.session_state.met_office_key
        _mo_key = st.text_input("Met Office DataPoint key", type="default" if _show_mo else "password", value=_mo_value)
        if _mo_key != _mo_value: st.session_state.met_office_key = _mo_key

        _show_gm = st.checkbox("Show Gemini key", key="show_gm_key", value=False)
        _gm_value = st.session_state.gemini_key
        _gm_key = st.text_input("Gemini API key (for AI Advisor)", type="default" if _show_gm else "password", value=_gm_value)
        if _gm_key != _gm_value: st.session_state.gemini_key = _gm_key
        if st.session_state.gemini_key:
            if not st.session_state.gemini_key.startswith("AIza"):
                st.markdown("<div class='val-warn'>⚠ Gemini key should start with 'AIza'</div>", unsafe_allow_html=True)
            else:
                valid, message, warn = validate_gemini_key(st.session_state.gemini_key)
                st.markdown(message, unsafe_allow_html=True)
                st.session_state.gemini_key_valid = valid or warn

    st.markdown("---")
    if LOGO_URI:
        _footer_logo = f"<img src='{LOGO_URI}' height='28' style='vertical-align:middle;display:inline-block;height:28px;width:auto;' alt='CrowAgent™ Logo'/>"
    else:
        _footer_logo = "<span style='font-family:Rajdhani,sans-serif;font-size:1.1rem;font-weight:700;color:#00C2A8;'>CrowAgent™</span>"
    st.markdown(f"<div class='ent-footer'>{_footer_logo}<div style='font-size:0.76rem;color:#9ABDD0;line-height:1.6;margin-top:8px;'>© 2026 Aparajita Parihar<br/>CrowAgent™ · All rights reserved<br/>v2.0.0 · Prototype</div></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# COMPUTE ALL SELECTED SCENARIOS
# ─────────────────────────────────────────────────────────────────────────────
results: dict[str, dict] = {}
_compute_errors: list[str] = []
for _sn in selected_scenario_names:
    try: results[_sn] = calculate_thermal_load(_active_buildings[selected_building_name], SCENARIOS[_sn], weather)
    except Exception as _e: _compute_errors.append(f"Scenario '{_sn}': {_e}")

baseline_result = results.get("Baseline (No Intervention)", list(results.values())[0] if results else {})

# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM TOP BAR
# ─────────────────────────────────────────────────────────────────────────────
_weather_pill = f"<span class='sp sp-live'><span class='pulse-dot'></span>Live Weather · {weather['temperature_c']}°C {weather['condition_icon']}</span>" if weather["is_live"] else f"<span class='sp sp-manual'>○ Manual · {weather['temperature_c']}°C</span>"
_logo_html = f"<img src='{LOGO_URI}' height='38' style='vertical-align:middle; display:inline-block; height:38px; width:auto;' alt='CrowAgent™ Logo'/>" if LOGO_URI else "<span style='font-family:Rajdhani,sans-serif;font-size:1.2rem;font-weight:700;color:#00C2A8;'>CrowAgent™</span>"

st.markdown(f"""
<div class='platform-topbar'>
  <div style='display:flex;align-items:center;gap:16px;flex-wrap:wrap;'>
    {_logo_html}
    <div>
      <div style='font-family:Rajdhani,sans-serif;font-size:0.82rem;letter-spacing:1.5px;text-transform:uppercase;color:#8FBCCE;line-height:1;margin-top:2px;'>Sustainability AI Decision Intelligence Platform</div>
    </div>
  </div>
  <div class='platform-topbar-right'>{_weather_pill}<span class='sp sp-cache'>🚧 PROTOTYPE v2.0.0</span><span class='sp sp-cache'>{st.session_state.wx_location_name or st.session_state.wx_city or 'Reading, Berkshire'}</span></div>
</div>
""", unsafe_allow_html=True)

if _compute_errors:
    for _err in _compute_errors: st.error(f"Computation error — {_err}")

st.markdown("<div class='disc-prototype'><strong>⚠️ Working Prototype — Results Are Indicative Only.</strong> This platform uses simplified physics models calibrated against published UK higher education sector averages. Outputs should not be used as the sole basis for capital investment decisions. Consult a qualified energy surveyor before committing to any retrofit programme. Greenfield University is a fictional institution used for demonstration purposes. All data is illustrative.</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN NAVIGATION TABS
# ─────────────────────────────────────────────────────────────────────────────
_tab_dash, _tab_fin, _tab_ai, _tab_compliance, _tab_about = st.tabs(["📊 Dashboard", "📈 Financial Analysis", "🤖 AI Advisor", "🏛️ UK Compliance Hub", "ℹ️ About & Contact"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD (REDESIGNED Phase 1-6)
# ════════════════════════════════════════════════════════════════════════════
with _tab_dash:
    # ── CAMPUS AGGREGATION FOR SCORECARD ──────────────────────────────────────
    campus_area = sum(b.get("floor_area_m2", 0) for b in _active_buildings.values())
    campus_energy = sum(b.get("baseline_energy_mwh", 0) for b in _active_buildings.values())
    campus_carbon = campus_energy * 1000 * 0.20482 / 1000
    campus_cost = campus_energy * 1000 * 0.28
    
    avg_u_wall = sum(b.get("u_value_wall", 0) * b.get("floor_area_m2", 0) for b in _active_buildings.values()) / (campus_area or 1)
    avg_u_roof = sum(b.get("u_value_roof", 0) * b.get("floor_area_m2", 0) for b in _active_buildings.values()) / (campus_area or 1)
    avg_u_glazing = sum(b.get("u_value_glazing", 0) * b.get("floor_area_m2", 0) for b in _active_buildings.values()) / (campus_area or 1)
    avg_glazing_ratio = sum(b.get("glazing_ratio", 0) * b.get("floor_area_m2", 0) for b in _active_buildings.values()) / (campus_area or 1)
    
    campus_epc = compliance.estimate_epc_rating(
        floor_area_m2=campus_area, annual_energy_kwh=campus_energy * 1000,
        u_wall=avg_u_wall, u_roof=avg_u_roof, u_glazing=avg_u_glazing,
        glazing_ratio=avg_glazing_ratio, building_type="commercial"
    )
    
    best_scen_name = "None"
    best_scen_saving_pct = 0
    best_scen_carbon_saved = 0
    best_scen_cost_saved = 0
    best_scen_payback = 0
    
    for sn in selected_scenario_names:
        if sn == "Baseline (No Intervention)": continue
        sc_energy = 0; sc_carbon_saved = 0; sc_cost_saved = 0; sc_install_cost = 0
        for bname, bdata in _active_buildings.items():
            try:
                res = calculate_thermal_load(bdata, SCENARIOS[sn], weather)
                sc_energy += res["scenario_energy_mwh"]
                sc_carbon_saved += res["carbon_saving_t"]
                sc_cost_saved += res["annual_saving_gbp"]
                sc_install_cost += SCENARIOS[sn]["install_cost_gbp"] 
            except Exception: pass
        
        saving_pct = ((campus_energy - sc_energy) / campus_energy * 100) if campus_energy else 0
        if saving_pct > best_scen_saving_pct:
            best_scen_saving_pct = saving_pct
            best_scen_name = sn
            best_scen_carbon_saved = sc_carbon_saved
            best_scen_cost_saved = sc_cost_saved
            best_scen_payback = (sc_install_cost / sc_cost_saved) if sc_cost_saved > 0 else 0

    # ── LAYER 1: CAMPUS SCORECARD HERO ────────────────────────────────────────
    st.markdown(f"""
    <div style='background:#071A2F; border: 2px solid #00C2A8; border-radius: 8px; padding: 20px; color: #CBD8E6; margin-bottom: 24px; box-shadow: 0 4px 12px rgba(7,26,47,0.15);'>
        <h2 style='color:#00C2A8; margin-top:0; margin-bottom:4px; font-family:Rajdhani,sans-serif; font-weight: 700; letter-spacing: 0.5px;'>
            🌍 Greenfield Campus — Sustainability Snapshot
        </h2>
        <div style='font-size:0.85rem; color:#8FBCCE; margin-bottom:16px;'>
            📍 {st.session_state.wx_location_name} &nbsp;·&nbsp; {len(_active_buildings)} buildings &nbsp;·&nbsp; Baseline scenario
        </div>
        
        <div style='display:flex; gap:24px; flex-wrap:wrap; border-top:1px solid #1A3A5C; border-bottom:1px solid #1A3A5C; padding:16px 0; margin-bottom:16px;'>
            <div style='flex:1; min-width:150px;'>
                <div style='font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; color:#8FBCCE;'>Total Energy</div>
                <div style='font-size:1.8rem; font-weight:700; color:#fff; font-family:Rajdhani,sans-serif; line-height: 1.1;'>
                    {campus_energy:,.0f} <span style='font-size:1rem; color:#8FBCCE;'>MWh/yr</span>
                </div>
                <div style='margin-top:6px; display:inline-block; background:{campus_epc["epc_colour"]}; color:#fff; padding:3px 10px; border-radius:4px; font-size:0.85rem; font-weight:bold;'>
                    {campus_epc["epc_band"]}-rated Average
                </div>
            </div>
            <div style='flex:1; min-width:150px;'>
                <div style='font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; color:#8FBCCE;'>Total Carbon</div>
                <div style='font-size:1.8rem; font-weight:700; color:#fff; font-family:Rajdhani,sans-serif; line-height: 1.1;'>
                    {campus_carbon:,.0f} <span style='font-size:1rem; color:#8FBCCE;'>t CO₂e/yr</span>
                </div>
            </div>
            <div style='flex:1; min-width:150px;'>
                <div style='font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; color:#8FBCCE;'>Annual Energy Cost</div>
                <div style='font-size:1.8rem; font-weight:700; color:#fff; font-family:Rajdhani,sans-serif; line-height: 1.1;'>
                    £{campus_cost/1000:,.0f}k <span style='font-size:1rem; color:#8FBCCE;'>/yr</span>
                </div>
                <div style='font-size:0.8rem; color:#A8C8D8; margin-top:4px;'>≈ £{campus_cost/365:,.0f} per day</div>
            </div>
        </div>
        
        <div style='background:#0D2640; border-left:4px solid #1DB87A; padding:12px 16px; border-radius:4px;'>
            <div style='color:#1DB87A; font-weight:700; font-size:0.9rem; margin-bottom:4px; font-family:Rajdhani,sans-serif;'>
                ✨ Best available saving: {best_scen_name.split(' (')[0]}
            </div>
            <div style='font-size:0.85rem; color:#CBD8E6;'>
                Saves <strong>{best_scen_saving_pct:.0f}%</strong> (£{best_scen_cost_saved/1000:,.0f}k/yr) 
                &nbsp;·&nbsp; Payback: <strong>{best_scen_payback:.1f} yrs</strong> 
                &nbsp;·&nbsp; Carbon reduction: <strong>{best_scen_carbon_saved:.0f} tonnes/yr</strong>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── LAYER 2: EPC-STYLE BUILDING CARDS ─────────────────────────────────────
    st.markdown("<div class='sec-hdr'>🏢 Campus Buildings (Select to analyse)</div>", unsafe_allow_html=True)
    
    if "selected_building_detail" not in st.session_state:
        st.session_state.selected_building_detail = list(_active_buildings.keys())[0]

    card_cols = st.columns(len(_active_buildings))
    
    for idx, (bname, bdata) in enumerate(_active_buildings.items()):
        b_energy = bdata["baseline_energy_mwh"]
        b_carbon = b_energy * 1000 * 0.20482 / 1000
        b_cost = b_energy * 1000 * 0.28
        
        b_epc = compliance.estimate_epc_rating(
            floor_area_m2=bdata["floor_area_m2"], annual_energy_kwh=b_energy * 1000,
            u_wall=bdata["u_value_wall"], u_roof=bdata["u_value_roof"], u_glazing=bdata["u_value_glazing"],
            glazing_ratio=bdata["glazing_ratio"], building_type="commercial"
        )
        
        best_fix_name = "None"
        best_fix_pct = 0
        best_fix_payback = 0
        
        for sn in selected_scenario_names:
            if sn == "Baseline (No Intervention)": continue
            try:
                res = calculate_thermal_load(bdata, SCENARIOS[sn], weather)
                pct = res["energy_saving_pct"]
                if pct > best_fix_pct:
                    best_fix_pct = pct
                    best_fix_name = sn.split(" (")[0]
                    best_fix_payback = res.get("payback_years", 0)
            except: pass
            
        icon = "🏢"
        if "Library" in bname: icon = "📚"
        elif "Arts" in bname: icon = "🎨"
        elif "Science" in bname: icon = "🔬"
        
        is_selected = st.session_state.selected_building_detail == bname
        border_col = "#00C2A8" if is_selected else "#E0EBF4"
        bg_col = "#ffffff" if is_selected else "#F8FAFC"
        shadow = "box-shadow: 0 4px 12px rgba(0,194,168,0.15);" if is_selected else "box-shadow: 0 2px 4px rgba(7,26,47,0.05);"
        
        with card_cols[idx]:
            st.markdown(f"""
            <div style='border: 2px solid {border_col}; border-radius: 8px; background: {bg_col}; padding: 18px 16px; {shadow} height: 100%; transition: all 0.2s;'>
                <div style='font-family:Rajdhani,sans-serif; font-size:1.15rem; font-weight:700; color:#071A2F; margin-bottom:12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>
                    {icon} {bname.replace("Greenfield ", "")}
                </div>
                <div style='display:flex; align-items:center; gap:10px; margin-bottom:14px;'>
                    <div style='background:{b_epc["epc_colour"]}; color:white; font-size:1.4rem; font-weight:bold; font-family:Rajdhani,sans-serif; padding:2px 14px; border-radius:4px;'>
                        {b_epc["epc_band"]}
                    </div>
                    <div style='height:8px; flex:1; background:linear-gradient(to right, #00873D 20%, #F0B429 50%, #C0392B 80%); border-radius:4px; opacity:0.4;'></div>
                </div>
                <div style='font-size:0.85rem; color:#3A576B; line-height:1.7; margin-bottom:14px;'>
                    <strong style='color:#071A2F;'>{b_energy:,.0f}</strong> MWh/yr<br>
                    <strong style='color:#071A2F;'>{b_carbon:,.1f}</strong> tonnes CO₂e<br>
                    <strong style='color:#071A2F;'>£{b_cost/1000:,.0f}k</strong>/yr
                </div>
                <div style='background:#F0F4F8; padding:10px 12px; border-radius:6px; font-size:0.8rem; color:#071A2F; border-left: 3px solid #00C2A8;'>
                    <div style='font-weight:700; color:#00C2A8; margin-bottom:2px;'>Best fix: {best_fix_name}</div>
                    Saves {best_fix_pct:.0f}% &nbsp;·&nbsp; {best_fix_payback:.1f}yr payback
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Select {bname.replace('Greenfield ', '')}", key=f"sel_{bname}", use_container_width=True, type="primary" if is_selected else "secondary"):
                st.session_state.selected_building_detail = bname
                st.rerun()

    st.markdown("<hr style='border-color:#E0EBF4; margin:24px 0;'>", unsafe_allow_html=True)

    # ── LAYER 3: INLINE BUILDING DETAIL PANEL ─────────────────────────────────
    selected_bname = st.session_state.selected_building_detail
    if selected_bname and selected_bname in _active_buildings:
        bdata = _active_buildings[selected_bname]
        
        icon = "🏢"
        if "Library" in selected_bname: icon = "📚"
        elif "Arts" in selected_bname: icon = "🎨"
        elif "Science" in selected_bname: icon = "🔬"
        
        b_energy = bdata["baseline_energy_mwh"]
        b_carbon = b_energy * 1000 * 0.20482 / 1000
        b_cost = b_energy * 1000 * 0.28
        b_epc = compliance.estimate_epc_rating(
            floor_area_m2=bdata["floor_area_m2"], annual_energy_kwh=b_energy * 1000,
            u_wall=bdata["u_value_wall"], u_roof=bdata["u_value_roof"], u_glazing=bdata["u_value_glazing"],
            glazing_ratio=bdata["glazing_ratio"], building_type="commercial"
        )
        
        best_scen = None; best_res = None; best_saving_pct = 0
        
        for sn in selected_scenario_names:
            if sn == "Baseline (No Intervention)": continue
            try:
                res = calculate_thermal_load(bdata, SCENARIOS[sn], weather)
                if res["energy_saving_pct"] > best_saving_pct:
                    best_saving_pct = res["energy_saving_pct"]
                    best_scen = sn
                    best_res = res
            except: pass
            
        if best_scen and best_res:
            target_epc = compliance.estimate_epc_rating(
                floor_area_m2=bdata["floor_area_m2"], annual_energy_kwh=best_res["scenario_energy_mwh"] * 1000,
                u_wall=best_res["u_wall"], u_roof=best_res["u_roof"], u_glazing=best_res["u_glazing"],
                glazing_ratio=bdata["glazing_ratio"], building_type="commercial"
            )
            
            cars_removed = int(best_res["carbon_saving_t"] / 2.0) 
            trees_planted = int(best_res["carbon_saving_t"] * 40) 
            scen_name_short = best_scen.split(" (")[0]
            
            st.markdown(f"""
            <div style='background: #ffffff; border: 1px solid #E0EBF4; border-top: 4px solid #00C2A8; border-radius: 8px; padding: 20px; box-shadow: 0 6px 16px rgba(7,26,47,0.08); margin-bottom: 24px;'>
                <div style='display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px; flex-wrap:wrap; gap:10px;'>
                    <div>
                        <h3 style='margin:0; font-family:Rajdhani,sans-serif; color:#071A2F; font-size:1.4rem;'>{icon} {selected_bname}</h3>
                        <div style='color:#5A7A90; font-size:0.85rem; margin-top:4px;'>
                            {bdata['building_type']} &nbsp;·&nbsp; {bdata['floor_area_m2']:,} m² &nbsp;·&nbsp; Built {bdata['built_year']}
                        </div>
                    </div>
                    <div style='text-align:right; font-family:Rajdhani,sans-serif; font-weight:bold; font-size:1.1rem; color:#071A2F;'>
                        <span style='color:{b_epc["epc_colour"]};'>{b_epc["epc_band"]}</span> 
                        <span style='color:#A8C8D8; margin:0 6px;'>→</span> 
                        <span style='color:{target_epc["epc_colour"]};'>{target_epc["epc_band"]} possible</span>
                    </div>
                </div>
                <hr style='border-color:#E0EBF4; margin:16px 0;'/>
                <div style='display:flex; flex-wrap:wrap; gap:20px;'>
                    <div style='flex:1; min-width:250px; background:#F8FAFC; padding:16px; border-radius:6px; border:1px solid #E0EBF4;'>
                        <div style='font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; color:#5A7A90; margin-bottom:12px; font-weight:700;'>CURRENT (Baseline)</div>
                        <div style='line-height:1.8; font-size:0.9rem; color:#071A2F;'>
                            ⚡ <strong>{b_energy:,.0f}</strong> MWh/yr<br/>
                            🌍 <strong>{b_carbon:,.1f}</strong> t CO₂e/yr<br/>
                            💷 <strong>£{b_cost/1000:,.0f}k</strong>/yr
                        </div>
                    </div>
                    <div style='flex:1; min-width:250px; background:rgba(29,184,122,0.05); padding:16px; border-radius:6px; border:1px solid rgba(29,184,122,0.3); border-left:3px solid #1DB87A;'>
                        <div style='font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; color:#1DB87A; margin-bottom:12px; font-weight:700;'>BEST SCENARIO ({scen_name_short})</div>
                        <div style='line-height:1.8; font-size:0.9rem; color:#071A2F;'>
                            ⚡ <strong>{best_res["scenario_energy_mwh"]:,.0f}</strong> MWh/yr 
                               <span style='color:#1DB87A; font-weight:bold; font-size:0.8rem; margin-left:8px;'>↓ {best_res["energy_saving_pct"]:.0f}%</span><br/>
                            🌍 <strong>{best_res["scenario_carbon_t"]:,.1f}</strong> t CO₂e 
                               <span style='color:#1DB87A; font-weight:bold; font-size:0.8rem; margin-left:8px;'>↓ {best_res["carbon_saving_t"]:,.1f} t saved</span><br/>
                            💷 <strong>£{best_res["scenario_energy_mwh"] * 1000 * 0.28 / 1000:,.0f}k</strong>/yr 
                               <span style='color:#1DB87A; font-weight:bold; font-size:0.8rem; margin-left:8px;'>saves £{best_res["annual_saving_gbp"]/1000:,.0f}k/yr</span><br/>
                            🏗️ Install: <strong>£{best_res["install_cost_gbp"]/1000:,.0f}k</strong><br/>
                            ⏱️ Payback: <strong>{best_res["payback_years"]:.1f} years</strong>
                        </div>
                    </div>
                </div>
                <div style='margin-top:16px; background:#F0F4F8; padding:12px 16px; border-radius:6px; font-size:0.9rem; color:#3A576B; display:flex; align-items:center; gap:12px;'>
                    <span style='font-size:1.4rem;'>🚗</span>
                    <div>
                        <strong>Real-world impact:</strong> This carbon saving is equivalent to removing <strong>{cars_removed} cars</strong> from the road, 
                        or planting <strong>{trees_planted:,} trees</strong>.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        else:
            st.info(f"Select an intervention scenario in the sidebar to compare against the baseline for {selected_bname}.")

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # ── LAYER 4: SIMPLIFIED MAP (PHASE 3) ─────────────────────────────────────
    with st.expander("📍 View Campus Map (2D Context)", expanded=False):
        center_lat = st.session_state.wx_lat
        center_lon = st.session_state.wx_lon
        cos_lat = math.cos(math.radians(center_lat))
        
        # Synthetic offsets to place the 3 main buildings
        offsets = {
            "Greenfield Library": (60, -130),
            "Greenfield Arts Building": (170, 110),
            "Greenfield Science Block": (-150, 70),
        }
        
        map_data = []
        for bname, (n_m, e_m) in offsets.items():
            if bname in _active_buildings:
                lat = center_lat + n_m / 111000.0
                lon = center_lon + e_m / (111000.0 * cos_lat)
                
                b_energy = _active_buildings[bname]["baseline_energy_mwh"]
                epc = compliance.estimate_epc_rating(
                    floor_area_m2=_active_buildings[bname]["floor_area_m2"],
                    annual_energy_kwh=b_energy * 1000,
                    u_wall=_active_buildings[bname]["u_value_wall"],
                    u_roof=_active_buildings[bname]["u_value_roof"],
                    u_glazing=_active_buildings[bname]["u_value_glazing"],
                    glazing_ratio=_active_buildings[bname]["glazing_ratio"],
                    building_type="commercial"
                )
                
                # Convert hex to rgb list for pydeck
                hex_col = epc["epc_colour"].lstrip('#')
                rgb = [int(hex_col[i:i+2], 16) for i in (0, 2, 4)] + [200]
                
                map_data.append({
                    "name": bname.replace("Greenfield ", ""),
                    "lat": lat,
                    "lon": lon,
                    "color": rgb,
                    "grade": epc["epc_band"]
                })
        
        if map_data:
            scatter_layer = pdk.Layer(
                "ScatterplotLayer",
                map_data,
                get_position="[lon, lat]",
                get_fill_color="color",
                get_radius=25,
                pickable=True
            )
            text_layer = pdk.Layer(
                "TextLayer",
                map_data,
                get_position="[lon, lat]",
                get_text="name",
                get_color=[50, 50, 50, 255],
                get_size=16,
                get_alignment_baseline="'bottom'",
            )
            
            view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=15.5, pitch=0)
            st.pydeck_chart(pdk.Deck(
                layers=[scatter_layer, text_layer], 
                initial_view_state=view_state, 
                map_style="light", 
                tooltip={"text": "{name}\nEPC Grade: {grade}"}
            ))

    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

    # ── LAYER 5: WHAT-IF SCENARIO PLANNER & EXPORT (PHASE 4, 5, 6) ────────────
    st.markdown("<div class='sec-hdr'>⚡ What If? — Campus-Wide Scenario Planner</div>", unsafe_allow_html=True)
    
    non_baseline_scenarios = [s for s in selected_scenario_names if s != "Baseline (No Intervention)"]
    if not non_baseline_scenarios:
        st.info("Select at least one intervention scenario in the sidebar to use the planner.")
    else:
        target_sn = st.selectbox("Compare Baseline vs:", non_baseline_scenarios, label_visibility="collapsed")
        
        # Calculate Target Campus Totals
        sc_energy = 0
        sc_install = 0
        for bname, bdata in _active_buildings.items():
            try:
                res = calculate_thermal_load(bdata, SCENARIOS[target_sn], weather)
                sc_energy += res["scenario_energy_mwh"]
                sc_install += SCENARIOS[target_sn]["install_cost_gbp"]
            except Exception: pass
            
        sc_carbon = sc_energy * 1000 * 0.20482 / 1000
        sc_cost = sc_energy * 1000 * 0.28
        
        saved_carbon = campus_carbon - sc_carbon
        saved_cost = campus_cost - sc_cost
        payback = sc_install / saved_cost if saved_cost > 0 else 0
        
        cars = int(saved_carbon / 2.0)
        flights = int(saved_carbon / 0.8) # approx 0.8 t per transatlantic economy flight
        
        pct_remaining = (sc_carbon / campus_carbon) * 100 if campus_carbon else 100
        
        st.markdown(f"""
        <div style='background:#ffffff; border:1px solid #E0EBF4; border-radius:8px; padding:20px; box-shadow:0 4px 12px rgba(7,26,47,0.05); margin-bottom:16px;'>
            <h3 style='margin-top:0; color:#071A2F; font-family:Rajdhani,sans-serif;'>Campus Net Zero Pathway</h3>
            <div style='margin-bottom:12px; font-size:0.9rem; color:#5A7A90;'>Carbon Budget Progress</div>
            
            <div style='margin-bottom:6px; display:flex; justify-content:space-between; font-weight:bold; color:#071A2F;'>
                <span>Baseline: {campus_carbon:,.0f} t CO₂e</span>
            </div>
            <div style='background:#E0EBF4; width:100%; height:24px; border-radius:12px; overflow:hidden; margin-bottom:12px;'>
                <div style='background:#E84C4C; width:100%; height:100%;'></div>
            </div>
            
            <div style='margin-bottom:6px; display:flex; justify-content:space-between; font-weight:bold; color:#1DB87A;'>
                <span>{target_sn.split(' (')[0]}: {sc_carbon:,.0f} t CO₂e</span>
                <span>↓ You save {saved_carbon:,.0f} t CO₂e/yr</span>
            </div>
            <div style='background:#E0EBF4; width:100%; height:24px; border-radius:12px; overflow:hidden; margin-bottom:24px;'>
                <div style='background:#1DB87A; width:{pct_remaining}%; height:100%;'></div>
            </div>
            
            <div style='display:flex; flex-wrap:wrap; gap:16px; border-top:1px solid #E0EBF4; padding-top:16px;'>
                <div style='flex:1; min-width:200px;'>
                    <div style='color:#5A7A90; font-size:0.85rem;'>Energy Cost</div>
                    <div style='font-size:1.1rem; font-weight:bold; color:#071A2F;'>£{campus_cost/1000:,.0f}k → £{sc_cost/1000:,.0f}k <span style='color:#1DB87A;'>(save £{saved_cost/1000:,.0f}k/yr)</span></div>
                </div>
                <div style='flex:1; min-width:200px;'>
                    <div style='color:#5A7A90; font-size:0.85rem;'>Investment Required</div>
                    <div style='font-size:1.1rem; font-weight:bold; color:#071A2F;'>£{sc_install/1000:,.0f}k <span style='color:#5A7A90; font-size:0.9rem; font-weight:normal;'>· {payback:.1f} yr payback</span></div>
                </div>
            </div>
            
            <div style='margin-top:16px; background:#F0F4F8; padding:12px 16px; border-radius:6px; font-size:0.9rem; color:#3A576B;'>
                🌍 <strong>Real-world equivalent:</strong> Removing <strong>{cars:,} cars</strong> from the road every year, or avoiding <strong>{flights:,} transatlantic flights</strong>.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # ── EXPORT BUSINESS CASE CSV (PHASE 6) ────────────────────────────────
        csv_lines = [
            "CrowAgent Business Case Summary",
            f"Location,{st.session_state.wx_location_name}",
            f"Scenario,{target_sn}",
            "",
            "Metric,Baseline,Target,Difference",
            f"Energy (MWh/yr),{campus_energy:.1f},{sc_energy:.1f},{-abs(campus_energy-sc_energy):.1f}",
            f"Carbon (t CO2e/yr),{campus_carbon:.1f},{sc_carbon:.1f},{-abs(campus_carbon-sc_carbon):.1f}",
            f"Cost (£/yr),{campus_cost:.2f},{sc_cost:.2f},{-abs(campus_cost-sc_cost):.2f}",
            "",
            "Financials",
            f"Total Investment (£),{sc_install:.2f}",
            f"Annual Savings (£),{saved_cost:.2f}",
            f"Simple Payback (yrs),{payback:.2f}"
        ]
        csv_data = "\n".join(csv_lines)
        
        st.download_button(
            label="📥 Export Campus Business Case (CSV)",
            data=csv_data,
            file_name=f"campus_business_case_{target_sn.replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — FINANCIAL ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
with _tab_fin:
    st.markdown(
        "<h3 style='margin-bottom:4px;'>Financial Analysis & Investment Appraisal</h3>"
        "<div style='font-size:0.78rem;color:#5A7A90;margin-bottom:16px;'>"
        f"{selected_building_name} · {len(selected_scenario_names)} scenario(s) selected</div>",
        unsafe_allow_html=True,
    )

    st.markdown("""
    <div class='disc-prototype'>
      <strong>⚠️ Financial Disclaimer.</strong>
      All financial projections are indicative estimates based on simplified models and
      published sector average costs. They assume constant energy prices and do not account
      for inflation, financing costs, planning permission, disruption costs, or maintenance.
      Do not use as the sole basis for investment decisions — engage a qualified cost consultant
      or energy surveyor.
    </div>
    """, unsafe_allow_html=True)

    paid_scenarios = {n: r for n, r in results.items() if SCENARIOS[n]["install_cost_gbp"] > 0}

    if not paid_scenarios:
        st.info("Select at least one intervention scenario (not Baseline) to view financial analysis.")
    else:
        fc1, fc2 = st.columns(2)
        with fc1:
            st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
            st.markdown("<div class='chart-title'>💰 Annual Cost Savings</div>", unsafe_allow_html=True)
            fig_s = go.Figure()
            for sn, res in paid_scenarios.items():
                sc = SCENARIOS[sn]
                fig_s.add_trace(go.Bar(
                    x=[sn.replace(" (All Interventions)","")], y=[res["annual_saving_gbp"]],
                    marker_color=sc["colour"], text=[f"£{res['annual_saving_gbp']:,.0f}"],
                    textposition="outside", name=sn,
                ))
            fig_s.update_layout(**CHART_LAYOUT, yaxis_title="£ per year")
            st.plotly_chart(fig_s, use_container_width=True, config={"displayModeBar": False})
            st.markdown("<div class='chart-caption'>Electricity at £0.28/kWh · HESA 2022-23 · Assumes constant energy price</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with fc2:
            st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
            st.markdown("<div class='chart-title'>⏱ Simple Payback Period</div>", unsafe_allow_html=True)
            fig_p = go.Figure()
            for sn, res in paid_scenarios.items():
                sc = SCENARIOS[sn]
                if res["payback_years"]:
                    fig_p.add_trace(go.Bar(
                        x=[sn.replace(" (All Interventions)","")], y=[res["payback_years"]],
                        marker_color=sc["colour"], text=[f"{res['payback_years']} yrs"],
                        textposition="outside", name=sn,
                    ))
            fig_p.update_layout(**CHART_LAYOUT, yaxis_title="Years")
            st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar": False})
            st.markdown("<div class='chart-caption'>Install cost ÷ annual saving · Simple (undiscounted) · ⚠️ Excludes finance costs</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='sec-hdr'>10-Year Cumulative Net Cash Flow</div>", unsafe_allow_html=True)
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        st.markdown("<div class='chart-title'>Cumulative Net Savings (£) — Year 0 = Installation Cost</div>", unsafe_allow_html=True)
        fig_ncf = go.Figure()
        years = list(range(0, 11))
        for sn, res in paid_scenarios.items():
            sc = SCENARIOS[sn]
            install = res["install_cost_gbp"]; annual = res["annual_saving_gbp"]
            cashflow = [-install + annual * y for y in years]
            fig_ncf.add_trace(go.Scatter(x=years, y=cashflow, name=sn.replace(" (All Interventions)",""), line=dict(color=sc["colour"], width=2.5), mode="lines+markers"))
        fig_ncf.add_hline(y=0, line=dict(dash="dot", color="#C0C8D0", width=1))
        fig_ncf.update_layout(**{**CHART_LAYOUT, "height": 320, "showlegend": True}, yaxis_title="Cumulative Net Cash Flow (£)", xaxis_title="Year", legend=dict(font=dict(size=10), orientation="h", y=-0.25))
        st.plotly_chart(fig_ncf, use_container_width=True, config={"displayModeBar": False})
        st.markdown("<div class='chart-caption'>⚠️ Indicative projection only · Assumes constant energy price · No inflation, discount rate, or maintenance costs applied</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='sec-hdr'>Investment Comparison Matrix</div>", unsafe_allow_html=True)
        inv_rows = []
        for sn, res in paid_scenarios.items():
            inv_rows.append({
                "Scenario": SCENARIOS[sn]["icon"] + " " + sn, "Install Cost": f"£{res['install_cost_gbp']:,.0f}",
                "Annual Saving (£)": f"£{res['annual_saving_gbp']:,.0f}", "Simple Payback": f"{res['payback_years']} yrs" if res["payback_years"] else "—",
                "CO₂ Saving (t/yr)": res["carbon_saving_t"], "£ per tonne CO₂": f"£{res['cost_per_tonne_co2']:,.0f}" if res["cost_per_tonne_co2"] else "—",
                "5-yr Net Saving": f"£{res['annual_saving_gbp']*5 - res['install_cost_gbp']:,.0f}",
            })
        st.dataframe(pd.DataFrame(inv_rows), use_container_width=True, hide_index=True)
        st.caption("⚠️ 5-yr net saving = (annual saving × 5) − install cost · Undiscounted · Indicative only")

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — AI ADVISOR
# ════════════════════════════════════════════════════════════════════════════
with _tab_ai:
    st.markdown("""<div style='background:linear-gradient(135deg,#071A2F,#0D2640);border-left:4px solid #00C2A8;border-radius:8px;padding:16px 20px;margin-bottom:14px;'><div style='font-family:Rajdhani,sans-serif;font-size:1.05rem;font-weight:700;color:#00C2A8;letter-spacing:0.5px;'>🤖 CrowAgent™ AI Advisor</div><div style='color:#CBD8E6;font-size:0.83rem;margin-top:4px;'>Physics-grounded agentic AI that runs real thermal simulations, compares scenarios and gives evidence-based Net Zero investment recommendations.</div><div style='color:#8FBCCE;font-size:0.78rem;margin-top:4px;'>Powered by Google Gemini · Physics-informed reasoning · © 2026 Aparajita Parihar</div></div>""", unsafe_allow_html=True)
    st.markdown("""<div class='disc-ai'><strong>🤖 AI Accuracy Disclaimer.</strong> The AI Advisor generates responses based on physics tool outputs and large language model reasoning. Like all AI systems, it can make mistakes, misinterpret questions, or produce plausible-sounding but incorrect conclusions. All AI-generated recommendations must be independently verified by a qualified professional before any action is taken. This AI Advisor is not a substitute for professional engineering or financial advice. Results are indicative only.</div>""", unsafe_allow_html=True)

    _akey = st.session_state.get("gemini_key", "")
    st.markdown("""<style>.ca-user{background:#071A2F;border-left:3px solid #00C2A8;border-radius:0 8px 8px 8px;padding:10px 14px;margin:10px 0 4px;color:#F0F4F8;font-size:0.88rem;line-height:1.5;}.ca-ai{background:#ffffff;border:1px solid #E0EBF4;border-left:3px solid #1DB87A;border-radius:0 8px 8px 8px;padding:10px 14px;margin:4px 0 10px;color:#071A2F;font-size:0.88rem;line-height:1.65;}.ca-tool{display:inline-block;background:#0D2640;color:#00C2A8;border-radius:4px;padding:2px 8px;font-size:0.78rem;font-weight:700;margin:2px 2px 2px 0;letter-spacing:0.3px;}.ca-meta{font-size:0.78rem;color:#6A92AA;margin-top:4px;}</style>""", unsafe_allow_html=True)

    if not _akey:
        col_onb, _ = st.columns([2, 1])
        with col_onb:
            st.markdown("""<div style='background:#F0F4F8;border:1px solid #E0EBF4;border-radius:8px;padding:24px;text-align:center;'><div style='font-size:2.5rem;margin-bottom:10px;'>🔑</div><div style='font-family:Rajdhani,sans-serif;font-size:1rem;font-weight:700;color:#071A2F;margin-bottom:12px;'>Activate AI Advisor with a free Gemini API key</div><div style='color:#5A7A90;font-size:0.85rem;line-height:1.8;max-width:380px;margin:0 auto;'>1. Visit <a href='https://aistudio.google.com' target='_blank' style='color:#00C2A8;font-weight:700;'>aistudio.google.com</a><br/>2. Sign in with any Google account<br/>3. Click <strong>Get API key → Create API key</strong><br/>4. Paste it into <strong>API Keys</strong> in the sidebar<br/><br/><span style='color:#8AACBF;font-size:0.76rem;'>Free tier · 1,500 requests/day · No credit card required</span></div></div>""", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("<div style='color:#5A7A90;font-size:0.82rem;margin-bottom:8px;'>Questions you can ask once activated:</div>", unsafe_allow_html=True)
        for _sq in crow_agent.STARTER_QUESTIONS[:6]:
            st.markdown(f"<div style='background:#F0F4F8;border:1px solid #E0EBF4;border-radius:5px;padding:8px 12px;margin:4px 0;color:#5A7A90;font-size:0.82rem;'>💬 {_sq}</div>", unsafe_allow_html=True)
    else:
        if not st.session_state.chat_history:
            st.markdown("<div style='color:#5A7A90;font-size:0.82rem;margin-bottom:8px;'>✨ Click a question to start — the AI will run real simulations:</div>", unsafe_allow_html=True)
            _sq_cols = st.columns(2)
            for _qi, _sq in enumerate(crow_agent.STARTER_QUESTIONS[:6]):
                with _sq_cols[_qi % 2]:
                    if st.button(_sq, key=f"sq_{_qi}", use_container_width=True):
                        st.session_state["_pending"] = _sq
                        st.rerun()

        if "_pending" in st.session_state:
            _pq = st.session_state.pop("_pending")
            st.session_state.chat_history.append({"role": "user", "content": _pq})
            with st.spinner("🤖 Running physics simulations and reasoning…"):
                _res = crow_agent.run_agent(
                    api_key=_akey, user_message=_pq, conversation_history=st.session_state.agent_history,
                    buildings=_active_buildings, scenarios=SCENARIOS, calculate_fn=calculate_thermal_load,
                    current_context={"building": selected_building_name, "scenarios": selected_scenario_names, "temperature_c": weather["temperature_c"]},
                )
            if _res.get("updated_history"): st.session_state.agent_history = _res["updated_history"]
            st.session_state.chat_history.append({"role": "assistant", "content": _res.get("answer", ""), "tool_calls": _res.get("tool_calls", []), "error": _res.get("error"), "loops": _res.get("loops", 1)})

        for _msg in st.session_state.chat_history:
            if _msg["role"] == "user":
                st.markdown(f"<div class='ca-user'><strong style='color:#00C2A8;'>You</strong> <span class='ca-meta'>{datetime.now().strftime('%H:%M')}</span><br/>{_msg['content']}</div>", unsafe_allow_html=True)
            else:
                _tc = _msg.get("tool_calls", [])
                if _tc:
                    _bh = "<div style='margin:4px 0 5px;'>"
                    for _t in _tc: _bh += f"<span class='ca-tool'>⚙ {_t['name']}</span>"
                    _bh += f" <span class='ca-meta'>{_msg.get('loops',1)} reasoning step{'s' if _msg.get('loops',1)!=1 else ''}</span></div>"
                    st.markdown(_bh, unsafe_allow_html=True)
                if _msg.get("error"): st.error(f"⚠️ Error: {_msg['error']}")
                else: st.markdown(f"<div class='ca-ai'><strong style='color:#1DB87A;font-family:Rajdhani,sans-serif;'>AI Advisor</strong><span class='ca-meta' style='margin-left:6px;'>Powered by Gemini 1.5 Flash</span><br/><br/>{_msg['content']}<br/><div style='margin-top:8px;padding-top:6px;border-top:1px solid #E0EBF4;font-size:0.77rem;color:#6A92AA;'>⚠️ AI-generated content. Verify all figures independently before acting.</div></div>", unsafe_allow_html=True)

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        with st.form(key="ca_form", clear_on_submit=True):
            _inp = st.text_input("Ask the AI Advisor:", placeholder="e.g. Which building should we upgrade first for £150,000?", label_visibility="collapsed")
            _c1, _c2 = st.columns([5, 1])
            with _c1: _go = st.form_submit_button("Send →", use_container_width=True, type="primary")
            with _c2: _clr = st.form_submit_button("Clear", use_container_width=True)

        if _go and _inp.strip():
            _clean = _inp.strip()[:500]
            if len(_clean) < 5: st.warning("Please enter a more detailed question (at least 5 characters).")
            else:
                st.session_state.chat_history.append({"role": "user", "content": _clean})
                with st.spinner("🤖 Running simulations and reasoning…"):
                    _res = crow_agent.run_agent(
                        api_key=_akey, user_message=_clean, conversation_history=st.session_state.agent_history,
                        buildings=_active_buildings, scenarios=SCENARIOS, calculate_fn=calculate_thermal_load,
                        current_context={"building": selected_building_name, "scenarios": selected_scenario_names, "temperature_c": weather["temperature_c"]},
                    )
                if _res.get("updated_history"): st.session_state.agent_history = _res["updated_history"]
                st.session_state.chat_history.append({"role": "assistant", "content": _res.get("answer", ""), "tool_calls": _res.get("tool_calls", []), "error": _res.get("error"), "loops": _res.get("loops", 1)})
                st.rerun()

        if _clr:
            st.session_state.chat_history = []
            st.session_state.agent_history = []
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — UK COMPLIANCE HUB
# ════════════════════════════════════════════════════════════════════════════
with _tab_compliance:
    _seg = st.session_state.user_segment
    _smeta = compliance.SEGMENT_META[_seg]

    st.markdown(f"<h3 style='margin-bottom:4px;'>UK Compliance Hub</h3><div style='font-size:0.80rem;color:#5A7A90;margin-bottom:14px;'>{_smeta['icon']} {_smeta['label']} · Relevant regulations: {' · '.join(_smeta['regulations'])}</div>", unsafe_allow_html=True)
    st.markdown("""<div class='disc-prototype'><strong>⚠️ Compliance Disclaimer.</strong> All outputs in this tab are <strong>indicative estimates only</strong> based on simplified proxy calculations. They do not constitute a formal EPC, SAP, SBEM, or SECR assessment. Formal compliance requires assessment by an accredited energy assessor (DEA/NDEA) or qualified carbon accountant. Results should not be relied upon for legal, financial, or planning decisions without independent professional verification.</div>""", unsafe_allow_html=True)

    if _seg == "university_he":
        st.info("**University / Higher Education segment selected.** The compliance tools in this tab are designed for SMB and individual self-build users. University campus analysis is available in the **Dashboard** and **Financial Analysis** tabs. Switch your user segment in the sidebar to access the MEES, SECR, or Part L tools.")
    elif _seg == "individual_selfbuild":
        st.markdown("<div class='sec-hdr'>Part L 2021 & Future Homes Standard Compliance Checker</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.83rem;color:#3A5268;margin-bottom:14px;line-height:1.6;'>New dwellings in England must comply with <strong>Approved Document L1A (2021 edition)</strong>. From 2025/26, the <strong>Future Homes Standard</strong> will tighten this further, requiring ~75–80% reduction in carbon vs. 2013 Part L. Enter your proposed fabric U-values below to check compliance.</div>", unsafe_allow_html=True)

        _pl_c1, _pl_c2 = st.columns(2)
        with _pl_c1:
            _pl_u_wall = st.number_input("Proposed wall U-value (W/m²K)", min_value=0.05, max_value=6.0, value=1.6, step=0.01)
            _pl_u_roof = st.number_input("Proposed roof U-value (W/m²K)", min_value=0.05, max_value=6.0, value=2.0, step=0.01)
            _pl_u_glazing = st.number_input("Proposed glazing U-value (W/m²K)", min_value=0.50, max_value=6.0, value=2.8, step=0.01)
        with _pl_c2:
            _pl_area = st.number_input("Floor area (m²)", min_value=10.0, max_value=2000.0, value=120.0, step=5.0)
            _pl_energy = st.number_input("Estimated annual energy (kWh)", min_value=0.0, max_value=500_000.0, value=18000.0, step=100.0)

        if st.button("Run Part L / FHS Check", type="primary", key="run_partl"):
            try:
                _pl_result = compliance.part_l_compliance_check(u_wall=_pl_u_wall, u_roof=_pl_u_roof, u_glazing=_pl_u_glazing, floor_area_m2=_pl_area, annual_energy_kwh=_pl_energy, building_type="individual_selfbuild")
                _pass_colour = "#1DB87A" if _pl_result["part_l_2021_pass"] else "#E84C4C"
                st.markdown(f"<div style='background:{_pass_colour}18;border-left:4px solid {_pass_colour};border-radius:0 6px 6px 0;padding:12px 16px;margin:10px 0;'><strong style='color:{_pass_colour};'>{_pl_result['overall_verdict']}</strong></div>", unsafe_allow_html=True)

                st.markdown("<div class='sec-hdr'>Fabric Element Check</div>", unsafe_allow_html=True)
                _pl_rows = [{"Element": item["element"], "Proposed (W/m²K)": item["proposed_u"], "Target (W/m²K)": item["target_u"], "Gap (W/m²K)": item["gap"] if not item["pass"] else "—", "Status": "✅ PASS" if item["pass"] else "❌ FAIL"} for item in _pl_result["compliance_items"]]
                st.dataframe(pd.DataFrame(_pl_rows), use_container_width=True, hide_index=True)

                _fhs_colour = "#1DB87A" if _pl_result["fhs_ready"] else "#F0B429"
                st.markdown(f"<div class='kpi-card' style='margin-top:10px;border-top-color:{_fhs_colour};'><div class='kpi-label'>Estimated Primary Energy Intensity</div><div class='kpi-value'>{_pl_result['primary_energy_est']}<span class='kpi-unit'> kWh/m²/yr</span></div><div class='kpi-sub'>FHS indicative threshold: ≤ {_pl_result['fhs_threshold']} kWh/m²/yr · {'✅ FHS-ready' if _pl_result['fhs_ready'] else '⚠️ Improvement needed for FHS'}</div></div>", unsafe_allow_html=True)

                if _pl_result["improvement_actions"]:
                    st.markdown("<div class='sec-hdr'>Required Improvement Actions</div>", unsafe_allow_html=True)
                    for _action in _pl_result["improvement_actions"]: st.markdown(f"<div class='disc-prototype' style='margin:4px 0;'>⚙️ {_action}</div>", unsafe_allow_html=True)
            except ValueError as _e: st.error(f"Validation error: {_e}")

        st.markdown("---")
        st.caption("Part L 2021 targets: wall ≤ 0.18 W/m²K · roof ≤ 0.11 W/m²K · glazing ≤ 1.20 W/m²K (ADL1A, England). Future Homes Standard threshold is indicative — final standard TBC. ⚠️ Formal SAP calculation by an accredited DEA is required for Building Control sign-off.")

    elif _seg == "smb_landlord":
        st.markdown("<div class='sec-hdr'>EPC Rating Estimator & MEES Gap Analysis</div>", unsafe_allow_html=True)
        st.markdown("""<div style='background:#FFF8E1;border:1px solid #FFD89B;border-left:4px solid #F0B429;border-radius:0 6px 6px 0;padding:12px 16px;margin-bottom:14px;font-size:0.82rem;color:#664D03;line-height:1.6;'><strong>MEES Compliance Deadlines (England &amp; Wales):</strong><br/>• <strong>Since April 2023:</strong> Non-domestic properties must have EPC rating E or above to be let.<br/>• <strong>From 2028 (new tenancies):</strong> EPC C minimum — all new leases must meet C.<br/>• <strong>From 2030 (all leases):</strong> EPC C minimum applies to all existing leases.<br/>Landlords with non-compliant properties face civil penalties and inability to let.</div>""", unsafe_allow_html=True)

        _mees_c1, _mees_c2 = st.columns(2)
        with _mees_c1:
            _m_area = st.number_input("Floor area (m²)", min_value=10.0, max_value=50_000.0, value=500.0, step=10.0, key="mees_area")
            _m_energy = st.number_input("Annual energy consumption (kWh)", min_value=0.0, max_value=10_000_000.0, value=72_000.0, step=1000.0, key="mees_energy")
            _m_u_wall = st.number_input("Wall U-value (W/m²K)", min_value=0.05, max_value=6.0, value=1.7, step=0.01, key="mees_uwall")
        with _mees_c2:
            _m_u_roof = st.number_input("Roof U-value (W/m²K)", min_value=0.05, max_value=6.0, value=1.8, step=0.01, key="mees_uroof")
            _m_u_glaz = st.number_input("Glazing U-value (W/m²K)", min_value=0.50, max_value=6.0, value=2.8, step=0.01, key="mees_uglaz")
            _m_glaz_r = st.slider("Glazing ratio (% of facade)", min_value=5, max_value=90, value=35, step=5, key="mees_glazr") / 100.0

        if st.button("Run EPC & MEES Analysis", type="primary", key="run_mees"):
            try:
                _epc = compliance.estimate_epc_rating(floor_area_m2=_m_area, annual_energy_kwh=_m_energy, u_wall=_m_u_wall, u_roof=_m_u_roof, u_glazing=_m_u_glaz, glazing_ratio=_m_glaz_r, building_type="commercial")
                _gap = compliance.mees_gap_analysis(current_sap=_epc["sap_score"], target_band="C")

                st.markdown(f"<div style='display:flex;align-items:center;gap:20px;margin:12px 0;'><div style='background:{_epc['epc_colour']};color:#fff;font-family:Rajdhani,sans-serif;font-size:2.8rem;font-weight:700;width:70px;height:70px;border-radius:8px;display:flex;align-items:center;justify-content:center;'>{_epc['epc_band']}</div><div><div style='font-family:Rajdhani,sans-serif;font-size:1.1rem;font-weight:700;color:#071A2F;'>Estimated EPC Band: {_epc['epc_band']}</div><div style='font-size:0.83rem;color:#5A7A90;margin-top:2px;'>Indicative SAP score: {_epc['sap_score']} · Energy intensity: {_epc['eui_kwh_m2']} kWh/m²/yr</div></div></div>", unsafe_allow_html=True)

                _c_now = "#1DB87A" if _epc["mees_compliant_now"] else "#E84C4C"
                _c_28 = "#1DB87A" if _epc["mees_2028_compliant"] else "#F0B429"
                st.markdown(f"<div style='display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px;'><span class='sp' style='background:{_c_now}18;color:{_c_now};border:1px solid {_c_now}44;'>{'✅' if _epc['mees_compliant_now'] else '❌'} Current MEES (E minimum)</span><span class='sp' style='background:{_c_28}18;color:{_c_28};border:1px solid {_c_28}44;'>{'✅' if _epc['mees_2028_compliant'] else '⚠️'} 2028 MEES Target (C)</span></div>", unsafe_allow_html=True)

                st.markdown(f"<div class='disc-ai'><strong>Assessment:</strong> {_epc['recommendation']}</div>", unsafe_allow_html=True)

                if not _epc["mees_2028_compliant"] and _gap["recommended_measures"]:
                    st.markdown("<div class='sec-hdr'>Recommended Improvement Measures</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size:0.82rem;color:#5A7A90;margin-bottom:8px;'>SAP gap to band C: <strong>{_gap['sap_gap']:.1f} points</strong>. Indicative total cost: <strong>£{_gap['total_cost_low']:,} – £{_gap['total_cost_high']:,}</strong></div>", unsafe_allow_html=True)
                    _m_rows = [{"Measure": _m["name"], "SAP Lift": f"+{_m['sap_lift']} pts", "Cost Estimate": f"£{_m['cost_low']:,} – £{_m['cost_high']:,}", "Regulation Ref": _m["regulation"]} for _m in _gap["recommended_measures"]]
                    st.dataframe(pd.DataFrame(_m_rows), use_container_width=True, hide_index=True)
                    if not _gap["achievable"]: st.warning("The measures listed above may not be sufficient to reach EPC C. A formal SBEM/SAP assessment and deeper retrofit will be required.")
            except ValueError as _e: st.error(f"Validation error: {_e}")

        st.markdown("---")
        st.caption("EPC estimation uses a proxy SAP 10.2 methodology based on energy intensity and fabric U-values. ⚠️ A formal SBEM assessment by an accredited Non-Domestic Energy Assessor (NDEA) is required for a legally valid EPC.")

    elif _seg == "smb_industrial":
        st.markdown("<div class='sec-hdr'>SECR Carbon Baseline Calculator (Scope 1 & 2)</div>", unsafe_allow_html=True)
        st.markdown("""<div style='background:#EBF5FB;border:1px solid #AED6F1;border-left:4px solid #2980B9;border-radius:0 6px 6px 0;padding:12px 16px;margin-bottom:14px;font-size:0.82rem;color:#1A4A6B;line-height:1.6;'><strong>SECR — Streamlined Energy &amp; Carbon Reporting:</strong><br/>Mandatory for large UK companies. SMBs below this threshold are not legally required to report but face increasing supply-chain pressure. Use this tool to calculate your Scope 1 and Scope 2 carbon baseline.</div>""", unsafe_allow_html=True)

        _secr_c1, _secr_c2 = st.columns(2)
        with _secr_c1:
            st.markdown("<div style='font-size:0.80rem;font-weight:700;color:#3A576B;margin-bottom:4px;'>Scope 2 — Purchased Electricity</div>", unsafe_allow_html=True)
            _s_elec = st.number_input("Annual electricity (kWh)", min_value=0.0, max_value=100_000_000.0, value=120_000.0, step=1000.0, key="secr_elec")
            st.markdown("<div style='font-size:0.80rem;font-weight:700;color:#3A576B;margin:8px 0 4px;'>Scope 1 — Fuel Combustion</div>", unsafe_allow_html=True)
            _s_gas = st.number_input("Natural gas (kWh)", min_value=0.0, max_value=100_000_000.0, value=85_000.0, step=1000.0, key="secr_gas")
            _s_oil = st.number_input("Gas oil / diesel (kWh)", min_value=0.0, max_value=100_000_000.0, value=0.0, step=1000.0, key="secr_oil")
        with _secr_c2:
            _s_lpg = st.number_input("LPG (kWh)", min_value=0.0, max_value=100_000_000.0, value=0.0, step=1000.0, key="secr_lpg")
            st.markdown("<div style='font-size:0.80rem;font-weight:700;color:#3A576B;margin:8px 0 4px;'>Scope 1 — Fleet</div>", unsafe_allow_html=True)
            _s_miles = st.number_input("Business fleet miles (per year)", min_value=0.0, max_value=10_000_000.0, value=0.0, step=1000.0, key="secr_miles")
            st.markdown("<div style='font-size:0.80rem;font-weight:700;color:#3A576B;margin:8px 0 4px;'>Intensity Metric</div>", unsafe_allow_html=True)
            _s_area = st.number_input("Floor area for intensity (m²) — optional", min_value=0.0, max_value=1_000_000.0, value=2_000.0, step=100.0, key="secr_area")

        if st.button("Calculate Carbon Baseline", type="primary", key="run_secr"):
            try:
                _floor = _s_area if _s_area > 0 else None
                _cb = compliance.calculate_carbon_baseline(elec_kwh=_s_elec, gas_kwh=_s_gas, oil_kwh=_s_oil, lpg_kwh=_s_lpg, fleet_miles=_s_miles, floor_area_m2=_floor)

                _sk1, _sk2, _sk3, _sk4 = st.columns(4)
                with _sk1: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Total Emissions</div><div class='kpi-value'>{_cb['total_tco2e']:,.1f}<span class='kpi-unit'> tCO₂e</span></div><div class='kpi-sub'>Scope 1 + 2 combined</div></div>", unsafe_allow_html=True)
                with _sk2: st.markdown(f"<div class='kpi-card accent-green'><div class='kpi-label'>Scope 1 (Direct)</div><div class='kpi-value'>{_cb['scope1_tco2e']:,.1f}<span class='kpi-unit'> tCO₂e</span></div><div class='kpi-sub'>Gas · Oil · LPG · Fleet</div></div>", unsafe_allow_html=True)
                with _sk3: st.markdown(f"<div class='kpi-card' style='border-top-color:#00C2A8'><div class='kpi-label'>Scope 2 (Electricity)</div><div class='kpi-value'>{_cb['scope2_tco2e']:,.1f}<span class='kpi-unit'> tCO₂e</span></div><div class='kpi-sub'>Grid: 0.20482 kgCO₂e/kWh</div></div>", unsafe_allow_html=True)
                with _sk4:
                    _int_disp = f"{_cb['intensity_kgco2_m2']} kgCO₂e/m²" if _cb["intensity_kgco2_m2"] is not None else "N/A"
                    st.markdown(f"<div class='kpi-card accent-gold'><div class='kpi-label'>Carbon Intensity</div><div class='kpi-value' style='font-size:1.4rem;'>{_int_disp}</div><div class='kpi-sub'>Per m² floor area</div></div>", unsafe_allow_html=True)

                st.markdown("<div class='sec-hdr'>Emissions Breakdown by Source</div>", unsafe_allow_html=True)
                _bk = _cb["breakdown"]
                _bk_labels = ["Electricity (Scope 2)", "Natural Gas (Scope 1)", "Oil (Scope 1)", "LPG (Scope 1)", "Fleet (Scope 1)"]
                _bk_values = [_bk["electricity_scope2_tco2e"], _bk["gas_scope1_tco2e"], _bk["oil_scope1_tco2e"], _bk["lpg_scope1_tco2e"], _bk["fleet_scope1_tco2e"]]
                _bk_filtered = [(l, v) for l, v in zip(_bk_labels, _bk_values) if v > 0]
                if _bk_filtered:
                    _bk_fig = go.Figure(go.Pie(labels=[x[0] for x in _bk_filtered], values=[x[1] for x in _bk_filtered], marker_colors=["#00C2A8", "#1DB87A", "#F0B429", "#E84C4C", "#4A6FA5"], textinfo="label+percent", hole=0.40))
                    _bk_fig.update_layout(**{**CHART_LAYOUT, "height": 280, "showlegend": False}, margin=dict(t=10, b=10, l=0, r=0))
                    st.plotly_chart(_bk_fig, use_container_width=True, config={"displayModeBar": False})

                _secr_info = _cb["secr_threshold_check"]
                _sc_col = "#F0B429" if _secr_info["supply_chain_pressure"] else "#1DB87A"
                st.markdown(f"<div style='background:{_sc_col}10;border-left:3px solid {_sc_col};border-radius:0 6px 6px 0;padding:10px 14px;margin-top:8px;font-size:0.82rem;color:#3A5268;line-height:1.6;'><strong>SECR Context:</strong> {_secr_info['note']}<br/>{'⚠️ At this emissions level, supply-chain buyers are likely to request carbon data.' if _secr_info['supply_chain_pressure'] else '✅ Emissions level is low — supply-chain pressure unlikely in the near term.'}{'<br/>✅ PAS 2060 carbon neutrality declaration is a feasible target.' if _secr_info['pas2060_candidacy'] else ''}</div>", unsafe_allow_html=True)
            except ValueError as _e: st.error(f"Validation error: {_e}")

        st.markdown("---")
        st.caption("⚠️ SECR reporting requires methodology disclosure; this tool is a screening calculator only.")

# ════════════════════════════════════════════════════════════════════════════
# TAB 5 — ABOUT & CONTACT
# ════════════════════════════════════════════════════════════════════════════
with _tab_about:
    _about_c1, _about_c2 = st.columns([2, 1])

    with _about_c1:
        st.markdown("<h3 style='margin-bottom:4px;'>About CrowAgent™ Platform</h3>", unsafe_allow_html=True)
        if LOGO_URI: st.markdown(f"<img src='{LOGO_URI}' width='300' style='margin-bottom:12px;' alt='CrowAgent™ Logo'/><br/>", unsafe_allow_html=True)
        st.markdown("""<div style='font-size:0.88rem;color:#3A5268;line-height:1.7;margin-bottom:16px;'>CrowAgent™ Platform is a physics-informed campus thermal intelligence system designed to help university estate managers and sustainability professionals make evidence-based, cost-effective decisions for achieving Net Zero targets.</div>""", unsafe_allow_html=True)
        
        st.markdown("<div class='sec-hdr'>⚠️ Full Platform Disclaimer</div>", unsafe_allow_html=True)
        st.markdown("""<div class='disc-prototype' style='margin-bottom:10px;'><strong>Working Prototype — Indicative Results Only</strong><br/><br/>Results <strong>must not</strong> be used as the sole basis for any capital investment, procurement, or planning decision.</div>""", unsafe_allow_html=True)

        st.markdown("<div class='sec-hdr'>Intellectual Property</div>", unsafe_allow_html=True)
        st.markdown("""<div style='font-size:0.82rem;color:#3A5268;line-height:1.7;background:#F0F4F8;border:1px solid #E0EBF4;border-radius:6px;padding:14px 16px;'>CrowAgent™ Platform is the original work of <strong>Aparajita Parihar</strong> and is protected by copyright.</div>""", unsafe_allow_html=True)

    with _about_c2:
        st.markdown("""<div class='contact-card'><div style='font-family:Rajdhani,sans-serif;font-size:1rem;font-weight:700;color:#071A2F;margin-bottom:14px;border-bottom:2px solid #00C2A8;padding-bottom:8px;'>📬 Contact & Enquiries</div><div style='margin-bottom:14px;'><div class='contact-label'>Project Lead</div><div class='contact-val'>Aparajita Parihar</div></div></div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='background:#071A2F;border:1px solid #1A3A5C;border-radius:8px;padding:14px 16px;'><div style='font-family:Rajdhani,sans-serif;font-size:0.78rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#00C2A8;margin-bottom:8px;'>Build Information</div><div style='font-size:0.78rem;color:#9ABDD0;line-height:1.8;'><strong style='color:#CBD8E6;'>Version:</strong> v2.0.0</div></div>", unsafe_allow_html=True)