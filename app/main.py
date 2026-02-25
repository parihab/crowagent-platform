# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — Sustainability AI Decision Intelligence
# © 2026 Aparajita Parihar. All rights reserved.
#
# Independent research project. Not affiliated with any institution.
# Not licensed for commercial use without written permission of the author.
# CrowAgent™ is an unregistered trademark pending UK IPO Class 42.
#
# Platform Version : v2.1.0 — Production-Grade MVP
# Status           : Working Prototype — See disclaimer
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations
import base64
import os
import sys
import json
import zlib
import uuid
import time

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
from datetime import datetime, timezone

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
from app.visualization_3d import render_campus_3d_map
import app.compliance as compliance
from app.utils import validate_gemini_key

# ─────────────────────────────────────────────────────────────────────────────
# UK EPC / POSTCODE API STUB
# ─────────────────────────────────────────────────────────────────────────────
def fetch_epc_data(postcode: str) -> dict:
    """
    Mock integration for UK Government EPC Register API.
    [REQUIRES CLIENT DEFINITION: Actual EPC API endpoint and auth mechanism (e.g. opendatacommunities.org)]
    
    Args:
        postcode (str): The UK postcode to search.
        
    Returns:
        dict: Parsed mock EPC data representing the building geometry and compliance metadata.
    """
    # Simulate network latency
    time.sleep(0.6)
    
    # Simple deterministic mock based on postcode length/chars
    is_commercial = "W" in postcode.upper() or "E" in postcode.upper()
    
    if is_commercial:
        return {
            "floor_area_m2": 850.0,
            "built_year": 1985,
            "epc_band": "E",
            "u_value_wall": 1.9,
            "u_value_roof": 2.2,
            "u_value_glazing": 3.0,
            "glazing_ratio": 0.40,
            "building_type": "Commercial Office",
            "baseline_energy_mwh": 140.0,
            "occupancy_hours": 2800
        }
    else:
        return {
            "floor_area_m2": 120.0,
            "built_year": 2005,
            "epc_band": "D",
            "u_value_wall": 1.6,
            "u_value_roof": 1.8,
            "u_value_glazing": 2.4,
            "glazing_ratio": 0.20,
            "building_type": "Residential Detached",
            "baseline_energy_mwh": 15.0,
            "occupancy_hours": 5500
        }

# ─────────────────────────────────────────────────────────────────────────────
# BUILDING DATA & SCENARIOS DEFAULTS (Legacy preservation)
# ─────────────────────────────────────────────────────────────────────────────
BUILDINGS: dict[str, dict] = {
    "Greenfield Library": {
        "floor_area_m2":      8500, "height_m": 4.5, "glazing_ratio": 0.35,
        "u_value_wall":       1.8, "u_value_roof": 2.1, "u_value_glazing": 2.8,
        "baseline_energy_mwh": 487, "occupancy_hours": 3500,
        "description":        "Main campus library", "built_year": "Pre-1990",
        "building_type":      "Library / Learning Hub",
    },
    "Greenfield Arts Building": {
        "floor_area_m2":      11200, "height_m": 5.0, "glazing_ratio": 0.28,
        "u_value_wall":       2.1, "u_value_roof": 1.9, "u_value_glazing": 3.1,
        "baseline_energy_mwh": 623, "occupancy_hours": 4000,
        "description":        "Humanities faculty", "built_year": "Pre-1985",
        "building_type":      "Teaching / Lecture",
    },
    "Greenfield Science Block": {
        "floor_area_m2":      6800, "height_m": 4.0, "glazing_ratio": 0.30,
        "u_value_wall":       1.6, "u_value_roof": 1.7, "u_value_glazing": 2.6,
        "baseline_energy_mwh": 391, "occupancy_hours": 3200,
        "description":        "Science laboratories", "built_year": "Pre-1995",
        "building_type":      "Laboratory / Research",
    },
}

SCENARIOS: dict[str, dict] = {
    "Baseline (No Intervention)": {
        "description":         "Current state — no modifications applied.",
        "u_wall_factor":       1.0, "u_roof_factor":    1.0, "u_glazing_factor": 1.0,
        "solar_gain_reduction": 0.0, "infiltration_reduction": 0.0, "renewable_kwh": 0,
        "install_cost_gbp":    0,    "colour": "#4A6FA5", "icon": "🏢",
    },
    "Solar Glass Installation": {
        "description":         "Replace standard glazing with BIPV solar glass.",
        "u_wall_factor":       1.0, "u_roof_factor":    1.0, "u_glazing_factor": 0.55,
        "solar_gain_reduction": 0.15, "infiltration_reduction": 0.05, "renewable_kwh": 42000,
        "install_cost_gbp":    280000, "colour": "#00C2A8", "icon": "☀️",
    },
    "Green Roof Installation": {
        "description":         "Vegetated green roof layer.",
        "u_wall_factor":       1.0, "u_roof_factor":    0.45, "u_glazing_factor": 1.0,
        "solar_gain_reduction": 0.0, "infiltration_reduction": 0.02, "renewable_kwh": 0,
        "install_cost_gbp":    95000,  "colour": "#1DB87A", "icon": "🌱",
    },
    "Enhanced Insulation Upgrade": {
        "description":         "Wall, roof and glazing upgrade.",
        "u_wall_factor":       0.40, "u_roof_factor":    0.35, "u_glazing_factor": 0.70,
        "solar_gain_reduction": 0.0, "infiltration_reduction": 0.20, "renewable_kwh": 0,
        "install_cost_gbp":    520000, "colour": "#0A5C3E", "icon": "🏗️",
    },
    "Combined Package (All Interventions)": {
        "description":         "Solar glass + green roof + enhanced insulation simultaneously.",
        "u_wall_factor":       0.40, "u_roof_factor":    0.35, "u_glazing_factor": 0.55,
        "solar_gain_reduction": 0.15, "infiltration_reduction": 0.22, "renewable_kwh": 42000,
        "install_cost_gbp":    895000, "colour": "#062E1E", "icon": "⚡",
    },
}

def calculate_thermal_load(building: dict, scenario: dict, weather_data: dict) -> dict:
    """Physics-informed thermal load calculation. Returns physics state outputs."""
    b = building
    s = scenario
    temp = weather_data["temperature_c"]

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

    baseline_raw = (b["u_value_wall"] * wall_area_m2 * delta_t * heating_hrs +
                    b["u_value_roof"] * roof_area_m2 * delta_t * heating_hrs +
                    b["u_value_glazing"] * glazing_area_m2 * delta_t * heating_hrs +
                    0.33 * 0.7 * volume_m3 * delta_t * heating_hrs) / 1_000_000.0

    reduction_ratio = max(0.0, 1.0 - (baseline_raw - modelled_mwh) / baseline_raw) if baseline_raw > 0 else 1.0

    is_baseline = (
        float(s.get("u_wall_factor", 1.0)) == 1.0 and float(s.get("u_roof_factor", 1.0)) == 1.0
        and float(s.get("u_glazing_factor", 1.0)) == 1.0 and float(s.get("solar_gain_reduction", 0.0)) == 0.0
        and float(s.get("infiltration_reduction", 0.0)) == 0.0 and int(s.get("renewable_kwh", 0)) == 0
        and int(s.get("install_cost_gbp", 0)) == 0
    )

    if is_baseline:
        adjusted_mwh = b["baseline_energy_mwh"]
        renewable_mwh = 0.0
        final_mwh = adjusted_mwh
    else:
        adjusted_mwh = b["baseline_energy_mwh"] * max(0.35, reduction_ratio)
        renewable_mwh = s.get("renewable_kwh", 0) / 1_000.0
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
        "baseline_energy_mwh": round(b["baseline_energy_mwh"], 1),
        "scenario_energy_mwh": round(final_mwh, 1),
        "energy_saving_mwh": round(b["baseline_energy_mwh"] - final_mwh, 1),
        "energy_saving_pct": round((b["baseline_energy_mwh"] - final_mwh) / max(b["baseline_energy_mwh"], 1.0) * 100.0, 1),
        "baseline_carbon_t": round(baseline_carbon, 1),
        "scenario_carbon_t": round(scenario_carbon, 1),
        "carbon_saving_t": round(baseline_carbon - scenario_carbon, 1),
        "annual_saving_gbp": round(annual_saving, 0),
        "install_cost_gbp": install_cost,
        "payback_years": round(payback, 1) if payback else None,
        "cost_per_tonne_co2": cpt,
        "renewable_mwh": round(renewable_mwh, 1),
        "u_wall": round(u_wall, 2),
        "u_roof": round(u_roof, 2),
        "u_glazing": round(u_glazing, 2),
    }

# ─────────────────────────────────────────────────────────────────────────────
# LOGO LOADER
# ─────────────────────────────────────────────────────────────────────────────
def _load_logo_uri() -> str:
    candidates = [
        os.path.join(os.path.dirname(__file__), "../assets/CrowAgent_Logo_Horizontal_Dark.svg"),
        os.path.join(os.getcwd(), "assets/CrowAgent_Logo_Horizontal_Dark.svg"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "rb") as fh:
                    b64 = base64.b64encode(fh.read()).decode()
                return f"data:image/svg+xml;base64,{b64}"
            except Exception: pass
    return ""

def _load_icon_uri() -> str:
    candidates = [
        os.path.join(os.path.dirname(__file__), "../assets/CrowAgent_Icon_Square.svg"),
        os.path.join(os.getcwd(), "assets/CrowAgent_Icon_Square.svg"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "rb") as fh:
                    b64 = base64.b64encode(fh.read()).decode()
                return f"data:image/svg+xml;base64,{b64}"
            except Exception: pass
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
    initial_sidebar_state = "expanded"
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS BLOCK
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Nunito+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap');
html, body, [class*="css"] { font-family: 'Nunito Sans', sans-serif !important; }
h1,h2,h3,h4 { font-family: 'Rajdhani', sans-serif !important; letter-spacing: 0.3px; }
[data-testid="stAppViewContainer"] > .main { background: #F0F4F8; }
.block-container { padding-top: 0 !important; max-width: 100% !important; }
[data-testid="stSidebar"] { background: #071A2F !important; border-right: 1px solid #1A3A5C !important; }
[data-testid="stSidebar"] * { color: #CBD8E6 !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #00C2A8 !important; }
[data-testid="stSidebar"] .stTextInput input, [data-testid="stSidebar"] .stSelectbox > div > div { background: #0D2640 !important; border: 1px solid #1A3A5C !important; color: #CBD8E6 !important; font-size: 0.82rem !important; }
[data-testid="stSidebar"] hr { border-color: #1A3A5C !important; }
[data-testid="stSidebar"] .stButton button { background: #0D2640 !important; border: 1px solid #00C2A8 !important; color: #00C2A8 !important; font-size: 0.82rem !important; font-weight: 600 !important; padding: 4px 10px !important; }
[data-testid="stSidebar"] .stButton button:hover { background: #00C2A8 !important; color: #071A2F !important; }
.platform-topbar { background: linear-gradient(135deg, #071A2F 0%, #0D2640 60%, #0A2E40 100%); border-bottom: 2px solid #00C2A8; padding: 10px 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.platform-topbar-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.sp { display:inline-flex; align-items:center; gap:5px; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:700; letter-spacing:0.3px; white-space:nowrap; }
.sp-live { background:rgba(29,184,122,.12); color:#1DB87A; border:1px solid rgba(29,184,122,.3); }
.pulse-dot { width:7px; height:7px; border-radius:50%; background:#1DB87A; display:inline-block; animation: blink 2s ease-in-out infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
.stTabs [data-baseweb="tab-list"] { background: #ffffff !important; border-bottom: 2px solid #E0EBF4 !important; gap: 0 !important; padding: 0 !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: #3A576B !important; font-family: 'Rajdhani', sans-serif !important; font-size: 0.88rem !important; font-weight: 600 !important; padding: 10px 20px !important; border-bottom: 3px solid transparent !important; }
.stTabs [aria-selected="true"] { color: #071A2F !important; border-bottom: 3px solid #00C2A8 !important; background: rgba(0,194,168,.04) !important; }
.kpi-card { background: #ffffff; border-radius: 8px; padding: 18px 20px 14px; border: 1px solid #E0EBF4; border-top: 3px solid #00C2A8; box-shadow: 0 2px 8px rgba(7,26,47,.05); height: 100%; transition: transform 0.2s ease, box-shadow 0.2s ease; }
.kpi-card:hover { transform: translateY(-4px); box-shadow: 0 4px 12px rgba(7,26,47,.15); }
.kpi-label { font-family: 'Rajdhani', sans-serif; font-size: 0.78rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: #3A576B; margin-bottom: 6px; }
.kpi-value { font-family: 'Rajdhani', sans-serif; font-size: 2rem; font-weight: 700; color: #071A2F; line-height: 1.1; }
.kpi-unit { font-size: 0.9rem; font-weight: 500; color: #3A576B; margin-left: 2px; }
.kpi-sub { font-size: 0.78rem; color: #5A7A90; margin-top: 2px; }
.sec-hdr { font-family: 'Rajdhani', sans-serif; font-size: 0.84rem; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: #00C2A8; border-bottom: 1px solid rgba(0,194,168,.2); padding-bottom: 6px; margin-bottom: 14px; margin-top: 4px; }
.val-warn { background: rgba(232,76,76,.06); border: 1px solid rgba(232,76,76,.25); border-left: 3px solid #E84C4C; border-radius: 0 4px 4px 0; padding: 7px 12px; font-size: 0.80rem; color: #8B1A1A; }
.gate-container { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 80vh; text-align: center; }
.gate-card { background: #ffffff; padding: 30px; border-radius: 12px; border: 1px solid #E0EBF4; border-top: 4px solid #00C2A8; box-shadow: 0 4px 24px rgba(7,26,47,.08); width: 600px; max-width: 90%; }
.gate-btn { margin-top: 10px; width: 100%; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# STATE INITIALIZATION & ONBOARDING GATE
# ─────────────────────────────────────────────────────────────────────────────
def _get_secret(key: str, default: str = "") -> str:
    try: return st.secrets[key]
    except Exception: return os.getenv(key, default)

_qp = st.query_params

if "gemini_key" not in st.session_state: st.session_state.gemini_key = _get_secret("GEMINI_KEY", "")
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "agent_history" not in st.session_state: st.session_state.agent_history = []
if "wx_city" not in st.session_state: st.session_state.wx_city = "Reading, Berkshire"
if "wx_lat" not in st.session_state: st.session_state.wx_lat = loc.CITIES["Reading, Berkshire"]["lat"]
if "wx_lon" not in st.session_state: st.session_state.wx_lon = loc.CITIES["Reading, Berkshire"]["lon"]
if "wx_location_name" not in st.session_state: st.session_state.wx_location_name = "Reading, Berkshire, UK"

# Restore state from URL query params (F5 Survival)
if "segment" in _qp:
    st.session_state.user_segment = _qp["segment"]
if "p" in _qp:
    try:
        j = zlib.decompress(base64.urlsafe_b64decode(_qp["p"].encode())).decode()
        st.session_state.portfolio = json.loads(j)
    except Exception:
        pass

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

def _save_portfolio_state():
    try:
        j = json.dumps(st.session_state.portfolio)
        c = base64.urlsafe_b64encode(zlib.compress(j.encode())).decode()
        st.query_params["p"] = c
    except Exception as e:
        st.error(f"Failed to save state: {e}")

# The Onboarding Gate
if "user_segment" not in st.session_state:
    st.markdown("<div class='gate-container'><div class='gate-card'>", unsafe_allow_html=True)
    if LOGO_URI:
        st.markdown(f"<img src='{LOGO_URI}' width='250' style='margin-bottom:20px;'/>", unsafe_allow_html=True)
    else:
        st.markdown("<h1 style='color:#00C2A8;'>🌿 CrowAgent™</h1>", unsafe_allow_html=True)
    
    st.markdown("<h3>Select Your Sector to Initialize</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color:#5A7A90;'>Your workspace will be tailored to sector-specific compliance requirements.</p>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    def set_segment(seg):
        st.session_state.user_segment = seg
        st.query_params["segment"] = seg
        # Default load campus for University
        if seg == "university_he" and not st.session_state.portfolio:
            for bname, bdata in BUILDINGS.items():
                st.session_state.portfolio.append({
                    "id": str(uuid.uuid4()), "name": bname, "postcode": "RG6 6UR",
                    "segment": seg, "floor_area_m2": bdata["floor_area_m2"],
                    "built_year": int(bdata["built_year"].split("-")[-1]) if "-" in bdata["built_year"] else 1990,
                    "epc_band": "D", "physics_model_input": bdata
                })
            _save_portfolio_state()
        st.rerun()

    with c1:
        if st.button("🎓 University / Higher Education\n(Campus Portfolio & Net Zero)", use_container_width=True): set_segment("university_he")
        if st.button("🏢 SMB / Commercial Landlord\n(MEES Compliance)", use_container_width=True): set_segment("smb_landlord")
    with c2:
        if st.button("🏭 SMB / Industrial Operator\n(SECR Scope 1 & 2)", use_container_width=True): set_segment("smb_industrial")
        if st.button("🏠 Individual / Self-Build\n(Part L & Future Homes)", use_container_width=True): set_segment("individual_selfbuild")
    
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    if LOGO_URI: st.markdown(f"<div style='text-align:center;'><img src='{LOGO_URI}' width='200'/></div>", unsafe_allow_html=True)
    else: st.markdown("<h2 style='color:#00C2A8;text-align:center;'>🌿 CrowAgent™</h2>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("<div class='sb-section'>👤 Active Segment</div>", unsafe_allow_html=True)
    seg_meta = compliance.SEGMENT_META.get(st.session_state.user_segment, {})
    st.markdown(f"**{seg_meta.get('icon','')} {seg_meta.get('label','')}**")
    if st.button("Change Segment", size="small"):
        del st.session_state.user_segment
        st.query_params.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("<div class='sb-section'>📍 Global Weather Input</div>", unsafe_allow_html=True)
    weather = wx.get_weather(
        lat=st.session_state.wx_lat, lon=st.session_state.wx_lon,
        location_name=st.session_state.wx_location_name,
        provider="open_meteo"
    )
    st.markdown(f"**{weather['temperature_c']}°C** {weather['condition_icon']} ({weather['location_name']})")

    st.markdown("---")
    with st.expander("🔑 API Keys", expanded=False):
        gm_key = st.text_input("Gemini API key", type="password", value=st.session_state.gemini_key)
        if gm_key != st.session_state.gemini_key:
            st.session_state.gemini_key = gm_key
            st.rerun()

# Dynamic Physics Monkeypatching for Map Visualizer Integration
core.physics.BUILDINGS.clear()
for b in st.session_state.portfolio:
    core.physics.BUILDINGS[b["name"]] = b["physics_model_input"]

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
_tab_dash, _tab_fin, _tab_ai, _tab_compliance, _tab_about = st.tabs([
    "📊 Dashboard", "📈 Financial Analysis", "🤖 AI Advisor", "🏛️ UK Compliance Hub", "ℹ️ About & Contact"
])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD (Geo-Physics Hub & Segment KPIs)
# ════════════════════════════════════════════════════════════════════════════
with _tab_dash:
    st.markdown(f"<h2>{seg_meta.get('label','')} Dashboard</h2>", unsafe_allow_html=True)
    
    # KPIs Calculation
    if not st.session_state.portfolio:
        st.info("Your portfolio is empty. Add a building below.")
    else:
        k1, k2, k3, k4 = st.columns(4)
        seg = st.session_state.user_segment
        
        # Aggregate logic
        total_mwh = 0.0
        total_carbon = 0.0
        total_area = 0.0
        total_cost = 0.0
        total_sap_gap = 0.0
        total_upgrade = 0.0
        secr_scope1 = 0.0
        secr_scope2 = 0.0
        
        for b in st.session_state.portfolio:
            r = calculate_thermal_load(b["physics_model_input"], SCENARIOS["Baseline (No Intervention)"], weather)
            total_mwh += r["scenario_energy_mwh"]
            total_carbon += r["scenario_carbon_t"]
            total_area += b["floor_area_m2"]
            total_cost += r["annual_saving_gbp"] # relative to 0
            
            # Sub-calculations per segment
            if seg == "smb_landlord":
                epc = compliance.estimate_epc_rating(b["floor_area_m2"], r["scenario_energy_mwh"]*1000, b["physics_model_input"]["u_value_wall"], b["physics_model_input"]["u_value_roof"], b["physics_model_input"]["u_value_glazing"])
                gap = compliance.mees_gap_analysis(epc["sap_score"], "C")
                total_sap_gap += gap["sap_gap"]
                total_upgrade += gap["total_cost_low"]
            elif seg == "smb_industrial":
                cb = compliance.calculate_carbon_baseline(elec_kwh=r["scenario_energy_mwh"]*1000)
                secr_scope1 += cb["scope1_tco2e"]
                secr_scope2 += cb["scope2_tco2e"]
        
        # Segment KPI Rendering
        if seg == "university_he":
            with k1: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Portfolio MWh</div><div class='kpi-value'>{total_mwh:,.0f}</div></div>", unsafe_allow_html=True)
            with k2: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Carbon Intensity</div><div class='kpi-value'>{(total_carbon*1000)/max(total_area,1):,.1f} <span class='kpi-unit'>kg/m²</span></div></div>", unsafe_allow_html=True)
            with k3: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Cost Exposure</div><div class='kpi-value'>£{(total_mwh*1000*0.28):,.0f}</div></div>", unsafe_allow_html=True)
            with k4: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Net Zero Gap</div><div class='kpi-value'>{total_carbon:,.1f} <span class='kpi-unit'>tCO₂e</span></div></div>", unsafe_allow_html=True)
        elif seg == "smb_landlord":
            with k1: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Avg MEES Gap</div><div class='kpi-value'>{total_sap_gap/len(st.session_state.portfolio):,.1f} <span class='kpi-unit'>pts</span></div></div>", unsafe_allow_html=True)
            with k2: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Est. Upgrade Cost</div><div class='kpi-value'>£{total_upgrade:,.0f}</div></div>", unsafe_allow_html=True)
            with k3: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Portfolio Size</div><div class='kpi-value'>{len(st.session_state.portfolio)} <span class='kpi-unit'>units</span></div></div>", unsafe_allow_html=True)
            with k4: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>ROI Target</div><div class='kpi-value'>~12%</div></div>", unsafe_allow_html=True)
        elif seg == "smb_industrial":
            with k1: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>SECR Scope 1</div><div class='kpi-value'>{secr_scope1:,.1f} <span class='kpi-unit'>t</span></div></div>", unsafe_allow_html=True)
            with k2: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>SECR Scope 2</div><div class='kpi-value'>{secr_scope2:,.1f} <span class='kpi-unit'>t</span></div></div>", unsafe_allow_html=True)
            with k3: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Carbon Liability</div><div class='kpi-value'>£{(secr_scope1+secr_scope2)*50:,.0f}</div></div>", unsafe_allow_html=True)
            with k4: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Abatement Potential</div><div class='kpi-value'>Moderate</div></div>", unsafe_allow_html=True)
        elif seg == "individual_selfbuild":
            if st.session_state.portfolio:
                b = st.session_state.portfolio[-1] # Look at latest
                r = calculate_thermal_load(b["physics_model_input"], SCENARIOS["Baseline (No Intervention)"], weather)
                pl = compliance.part_l_compliance_check(b["physics_model_input"]["u_value_wall"], b["physics_model_input"]["u_value_roof"], b["physics_model_input"]["u_value_glazing"], b["floor_area_m2"], r["scenario_energy_mwh"]*1000)
                with k1: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Part L Primary Energy</div><div class='kpi-value'>{pl['primary_energy_est']:,.1f} <span class='kpi-unit'>kWh/m²/y</span></div></div>", unsafe_allow_html=True)
                with k2: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Compliance Status</div><div class='kpi-value'>{'PASS' if pl['part_l_2021_pass'] else 'FAIL'}</div></div>", unsafe_allow_html=True)
                with k3: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Fabric Avg U-Value</div><div class='kpi-value'>{b['physics_model_input']['u_value_wall']}</div></div>", unsafe_allow_html=True)
                with k4: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Latest Unit</div><div class='kpi-value'>{b['name']}</div></div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    
    # Split Layout: Geo-Physics Map Tagging
    c_left, c_right = st.columns([1, 2])
    
    with c_left:
        st.markdown("### 🏢 Portfolio Array")
        st.caption(f"Used Capacity: {len(st.session_state.portfolio)}/10")
        
        # Display existing
        for idx, b in enumerate(st.session_state.portfolio):
            c_n, c_btn = st.columns([4, 1])
            c_n.markdown(f"**{b['name']}** ({b['floor_area_m2']} m²)")
            if c_btn.button("🗑", key=f"del_{idx}"):
                st.session_state.portfolio.pop(idx)
                _save_portfolio_state()
                st.rerun()
                
        st.markdown("#### ➕ Add Building via EPC")
        if len(st.session_state.portfolio) >= 10:
            st.warning("Maximum portfolio size (10) reached.")
        else:
            with st.form("epc_import_form"):
                postcode = st.text_input("UK Postcode", placeholder="SW1A 1AA")
                b_name = st.text_input("Friendly Name", placeholder="Office Hub")
                submit = st.form_submit_button("Fetch & Map Data")
                
            if submit and postcode and b_name:
                with st.spinner("Querying EPC Register..."):
                    data = fetch_epc_data(postcode)
                    
                    # Transform to Physics Model Input
                    physics_input = {
                        "floor_area_m2": data["floor_area_m2"],
                        "height_m": 3.5, # Default Assumption
                        "glazing_ratio": data["glazing_ratio"],
                        "u_value_wall": data["u_value_wall"],
                        "u_value_roof": data["u_value_roof"],
                        "u_value_glazing": data["u_value_glazing"],
                        "baseline_energy_mwh": data["baseline_energy_mwh"],
                        "occupancy_hours": data["occupancy_hours"],
                        "building_type": data["building_type"]
                    }
                    
                    new_b = {
                        "id": str(uuid.uuid4()),
                        "name": b_name,
                        "postcode": postcode,
                        "segment": st.session_state.user_segment,
                        "floor_area_m2": data["floor_area_m2"],
                        "built_year": data["built_year"],
                        "epc_band": data["epc_band"],
                        "physics_model_input": physics_input
                    }
                    
                    st.session_state.portfolio.append(new_b)
                    
                    # Geocode postcode to update map view
                    geo = loc.geocode_location(postcode)
                    if geo:
                        st.session_state.wx_lat, st.session_state.wx_lon, st.session_state.wx_location_name = geo
                        
                    _save_portfolio_state()
                    st.success("Building Tagged & Added to Physics Array.")
                    st.rerun()

    with c_right:
        # We leverage the existing visualization, wrapped in an error handler
        if st.session_state.portfolio:
            scenarios_to_run = ["Baseline (No Intervention)", "Combined Package (All Interventions)"]
            try:
                render_campus_3d_map(scenarios_to_run, weather)
            except Exception as e:
                st.warning("Map component initialized. Add buildings in the correct campus area to view 3D polygons.")
        else:
            st.info("Map visualizer awaiting portfolio data.")


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — FINANCIAL ANALYSIS (Preserved)
# ════════════════════════════════════════════════════════════════════════════
with _tab_fin:
    st.markdown("<h3>Financial Analysis & Appraisal</h3>", unsafe_allow_html=True)
    if not st.session_state.portfolio:
        st.info("Add buildings to view financial metrics.")
    else:
        results = []
        for b in st.session_state.portfolio:
            r_base = calculate_thermal_load(b["physics_model_input"], SCENARIOS["Baseline (No Intervention)"], weather)
            r_comb = calculate_thermal_load(b["physics_model_input"], SCENARIOS["Combined Package (All Interventions)"], weather)
            
            results.append({
                "Building": b["name"],
                "Install Cost (£)": f"£{r_comb['install_cost_gbp']:,.0f}",
                "Annual Saving (£)": f"£{r_comb['annual_saving_gbp']:,.0f}",
                "Payback (Yrs)": f"{r_comb['payback_years']} yrs" if r_comb['payback_years'] else "N/A"
            })
        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — AI ADVISOR (Preserved)
# ════════════════════════════════════════════════════════════════════════════
with _tab_ai:
    st.markdown("<h3>🤖 CrowAgent™ AI Advisor</h3>", unsafe_allow_html=True)
    _akey = st.session_state.get("gemini_key", "")
    if not _akey:
        st.warning("Activate AI Advisor with a free Gemini API key in the sidebar.")
    else:
        with st.form(key="ai_form", clear_on_submit=True):
            user_q = st.text_input("Ask the AI Advisor:", placeholder="e.g. Which building should we upgrade first?")
            if st.form_submit_button("Send →") and user_q:
                st.session_state.chat_history.append({"role": "user", "content": user_q})
                with st.spinner("🤖 Reasoning..."):
                    # Execute LLM Loop mapping active portfolio
                    dyn_buildings = {b["name"]: b["physics_model_input"] for b in st.session_state.portfolio}
                    res = crow_agent.run_agent(
                        api_key=_akey, user_message=user_q,
                        conversation_history=st.session_state.agent_history,
                        buildings=dyn_buildings, scenarios=SCENARIOS,
                        calculate_fn=calculate_thermal_load,
                        current_context={"temperature_c": weather["temperature_c"]}
                    )
                if res.get("updated_history"):
                    st.session_state.agent_history = res["updated_history"]
                st.session_state.chat_history.append({"role": "assistant", "content": res.get("answer", "")})
                st.rerun()
                
        for msg in st.session_state.chat_history:
            icon = "👤" if msg["role"] == "user" else "🤖"
            st.markdown(f"**{icon} {msg['role'].capitalize()}:** {msg['content']}")


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — UK COMPLIANCE HUB (Preserved)
# ════════════════════════════════════════════════════════════════════════════
with _tab_compliance:
    st.markdown("<h3>🏛️ UK Compliance Hub</h3>", unsafe_allow_html=True)
    st.info(f"Active framework: {seg_meta.get('label','')} - {' · '.join(seg_meta.get('regulations',[]))}")

# ════════════════════════════════════════════════════════════════════════════
# TAB 5 — ABOUT & CONTACT (Preserved)
# ════════════════════════════════════════════════════════════════════════════
with _tab_about:
    st.markdown("<h3>ℹ️ About & Contact</h3>", unsafe_allow_html=True)
    st.write("CrowAgent™ Platform — Sustainability AI Decision Intelligence.")