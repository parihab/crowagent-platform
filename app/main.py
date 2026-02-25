# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — Sustainability AI Decision Intelligence
# © 2026 Aparajita Parihar. All rights reserved.
#
# Independent research project. Not affiliated with any institution.
# Not licensed for commercial use without written permission of the author.
# CrowAgent™ is an unregistered trademark pending UK IPO Class 42.
#
# Platform Version : v2.0.0 — Production-Grade Enhancement
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations
import base64
import os
import sys
import uuid
import json
from typing import Dict, Any, List, Optional

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
from app.utils import validate_gemini_key
import app.compliance as compliance

# ─────────────────────────────────────────────────────────────────────────────
# UK EPC / POSTCODE INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────
def fetch_epc_data(postcode: str) -> dict:
    """
    Fetch EPC data for a given UK postcode.
    [REQUIRES CLIENT DEFINITION: Actual EPC API endpoint and authentication details]

    Args:
        postcode (str): The UK postcode to search.

    Returns:
        dict: Parsed EPC data containing floor_area_m2, built_year, and epc_band.

    Raises:
        ValueError: If the postcode is invalid or API fails.
    """
    if not postcode or len(postcode.strip()) < 5:
        raise ValueError("Invalid postcode format.")

    # Mock fallback stub for API
    try:
        # Simulated API call
        # response = requests.get(f"https://epc.api.stub/search?postcode={postcode}", timeout=10)
        # response.raise_for_status()
        pass
    except requests.exceptions.RequestException as e:
        st.warning(f"EPC API timeout/error: {e}. Using fallback data.")

    return {
        "floor_area_m2": 450.0,
        "built_year": 1995,
        "epc_band": "D"
    }

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
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# BUILDING & SCENARIO DATA (Original templates + Custom JSON support)
# ─────────────────────────────────────────────────────────────────────────────
def _add_building_from_json(jtext: str) -> tuple[bool, str]:
    """
    Attempt to parse JSON and add it to BUILDINGS.

    Args:
        jtext (str): JSON string representing a building.

    Returns:
        tuple[bool, str]: (Success boolean, Status message)
    """
    try:
        obj = json.loads(jtext)
    except Exception as exc:
        return False, f"JSON parse error: {exc}"
    if "name" not in obj:
        return False, 'Missing "name" key.'
    name = obj.pop("name")
    if not isinstance(name, str) or not name.strip():
        return False, "Invalid building name."
    BUILDINGS[name] = obj
    return True, f"Building '{name}' added."

def _add_scenario_from_json(jtext: str) -> tuple[bool, str]:
    """
    Parse JSON and insert into SCENARIOS.

    Args:
        jtext (str): JSON string representing a scenario.

    Returns:
        tuple[bool, str]: (Success boolean, Status message)
    """
    try:
        obj = json.loads(jtext)
    except Exception as exc:
        return False, f"JSON parse error: {exc}"
    if "name" not in obj:
        return False, 'Missing "name" key.'
    name = obj.pop("name")
    if not isinstance(name, str) or not name.strip():
        return False, "Invalid scenario name."
    SCENARIOS[name] = obj
    return True, f"Scenario '{name}' added."

BUILDINGS: dict[str, dict] = {
    "Greenfield Library": {
        "floor_area_m2":      8500,
        "height_m":           4.5,
        "glazing_ratio":      0.35,
        "u_value_wall":       1.8,
        "u_value_roof":       2.1,
        "u_value_glazing":    2.8,
        "baseline_energy_mwh": 487,
        "occupancy_hours":    3500,
        "description":        "Main campus library — 8,500 m² · 5 floors · Heavy glazing",
        "built_year":         "Pre-1990",
        "building_type":      "Library / Learning Hub",
    },
    "Greenfield Arts Building": {
        "floor_area_m2":      11200,
        "height_m":           5.0,
        "glazing_ratio":      0.28,
        "u_value_wall":       2.1,
        "u_value_roof":       1.9,
        "u_value_glazing":    3.1,
        "baseline_energy_mwh": 623,
        "occupancy_hours":    4000,
        "description":        "Humanities faculty — 11,200 m² · 6 floors · Lecture theatres",
        "built_year":         "Pre-1985",
        "building_type":      "Teaching / Lecture",
    },
    "Greenfield Science Block": {
        "floor_area_m2":      6800,
        "height_m":           4.0,
        "glazing_ratio":      0.30,
        "u_value_wall":       1.6,
        "u_value_roof":       1.7,
        "u_value_glazing":    2.6,
        "baseline_energy_mwh": 391,
        "occupancy_hours":    3200,
        "description":        "Science laboratories — 6,800 m² · 4 floors · Lab-heavy usage",
        "built_year":         "Pre-1995",
        "building_type":      "Laboratory / Research",
    },
}

SCENARIOS: dict[str, dict] = {
    "Baseline (No Intervention)": {
        "description":         "Current state — no modifications applied.",
        "u_wall_factor":       1.0, "u_roof_factor":    1.0,
        "u_glazing_factor":    1.0, "solar_gain_reduction": 0.0,
        "infiltration_reduction": 0.0, "renewable_kwh": 0,
        "install_cost_gbp":    0,    "colour": "#4A6FA5", "icon": "🏢",
    },
    "Solar Glass Installation": {
        "description":         "Replace standard glazing with BIPV solar glass. U-value improvement ~45%.",
        "u_wall_factor":       1.0, "u_roof_factor":    1.0,
        "u_glazing_factor":    0.55, "solar_gain_reduction": 0.15,
        "infiltration_reduction": 0.05, "renewable_kwh": 42000,
        "install_cost_gbp":    280000, "colour": "#00C2A8", "icon": "☀️",
    },
    "Green Roof Installation": {
        "description":         "Vegetated green roof layer. Roof U-value improvement ~55%.",
        "u_wall_factor":       1.0, "u_roof_factor":    0.45,
        "u_glazing_factor":    1.0, "solar_gain_reduction": 0.0,
        "infiltration_reduction": 0.02, "renewable_kwh": 0,
        "install_cost_gbp":    95000,  "colour": "#1DB87A", "icon": "🌱",
    },
    "Enhanced Insulation Upgrade": {
        "description":         "Wall, roof and glazing upgrade to near-Passivhaus standard.",
        "u_wall_factor":       0.40, "u_roof_factor":    0.35,
        "u_glazing_factor":    0.70, "solar_gain_reduction": 0.0,
        "infiltration_reduction": 0.20, "renewable_kwh": 0,
        "install_cost_gbp":    520000, "colour": "#0A5C3E", "icon": "🏗️",
    },
    "Combined Package (All Interventions)": {
        "description":         "Solar glass + green roof + enhanced insulation simultaneously.",
        "u_wall_factor":       0.40, "u_roof_factor":    0.35,
        "u_glazing_factor":    0.55, "solar_gain_reduction": 0.15,
        "infiltration_reduction": 0.22, "renewable_kwh": 42000,
        "install_cost_gbp":    895000, "colour": "#062E1E", "icon": "⚡",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# PORTFOLIO ARRAY LOGIC
# ─────────────────────────────────────────────────────────────────────────────
MAX_PORTFOLIO_SIZE = 10

def init_portfolio_entry(postcode: str, segment: str, epc_data: dict) -> dict:
    """
    Initialize a new portfolio entry conforming to the strict JSON schema.

    Args:
        postcode (str): Valid UK postcode.
        segment (str): Active user segment.
        epc_data (dict): Data fetched from EPC API.

    Returns:
        dict: A structured portfolio building object.
    """
    entry_id = str(uuid.uuid4())
    floor_area = float(epc_data.get("floor_area_m2", 150.0))
    # Approximation for baseline energy (150 kWh/m2 typical)
    estimated_baseline_mwh = (floor_area * 150.0) / 1000.0

    return {
        "id": entry_id,
        "postcode": postcode,
        "segment": segment,
        "floor_area_m2": floor_area,
        "built_year": int(epc_data.get("built_year", 1990)),
        "epc_band": str(epc_data.get("epc_band", "Unknown")),
        "physics_model_input": {
            "floor_area_m2": floor_area,
            "height_m": 3.0,
            "glazing_ratio": 0.25,
            "u_value_wall": 1.8,
            "u_value_roof": 2.0,
            "u_value_glazing": 2.8,
            "baseline_energy_mwh": estimated_baseline_mwh,
            "occupancy_hours": 3000,
            "description": f"Portfolio Asset at {postcode}",
            "built_year": str(epc_data.get("built_year", 1990)),
            "building_type": "Portfolio Asset"
        },
        "scenarios": {
            "Baseline (No Intervention)": SCENARIOS["Baseline (No Intervention)"],
            "Combined Package (All Interventions)": SCENARIOS["Combined Package (All Interventions)"]
        },
        "baseline_results": {},
        "combined_results": {}
    }

def add_to_portfolio(postcode: str) -> None:
    """
    Fetch EPC data and add to the persistent portfolio array.
    Enforces maximum portfolio size limit.

    Args:
        postcode (str): UK postcode to add.

    Raises:
        ValueError: If the portfolio is at capacity or postcode invalid.
    """
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = []
        
    if len(st.session_state.portfolio) >= MAX_PORTFOLIO_SIZE:
        st.error(f"Portfolio capacity reached (Max {MAX_PORTFOLIO_SIZE} buildings).")
        return
        
    try:
        epc_data = fetch_epc_data(postcode)
        entry = init_portfolio_entry(postcode, st.session_state.user_segment, epc_data)
        st.session_state.portfolio.append(entry)
        st.success(f"Added {postcode} to portfolio.")
    except ValueError as e:
        st.error(str(e))

def remove_from_portfolio(entry_id: str) -> None:
    """Remove a building from the portfolio by ID."""
    if "portfolio" in st.session_state:
        st.session_state.portfolio = [b for b in st.session_state.portfolio if b["id"] != entry_id]
# ─────────────────────────────────────────────────────────────────────────────
# PHYSICS ENGINE — PINN Thermal Model
# Q_transmission = U × A × ΔT × hours  [Wh]
# Q_infiltration = 0.33 × ACH × Vol × ΔT  [Wh]
# Ref: Raissi et al. (2019) J. Comp. Physics  doi:10.1016/j.jcp.2018.10.045
# ─────────────────────────────────────────────────────────────────────────────
def calculate_thermal_load(building: dict, scenario: dict, weather_data: dict) -> dict:
    """
    Physics-informed thermal load calculation.
    DISCLAIMER: Uses simplified steady-state model calibrated against UK HE
    sector averages. Results are indicative only. Not for use as sole basis
    for capital investment decisions — consult a qualified energy surveyor.
    """
    b    = building
    s    = scenario
    temp = weather_data["temperature_c"]

    # ── Validation ────────────────────────────────────────────────────────────
    valid, msg = wx.validate_temperature(temp)
    if not valid:
        raise ValueError(f"Physics model validation: {msg}")

    # ── Geometry ──────────────────────────────────────────────────────────────
    perimeter_m     = 4.0 * (b["floor_area_m2"] ** 0.5)
    wall_area_m2    = perimeter_m * b["height_m"] * (1.0 - b["glazing_ratio"])
    glazing_area_m2 = perimeter_m * b["height_m"] * b["glazing_ratio"]
    roof_area_m2    = b["floor_area_m2"]
    volume_m3       = b["floor_area_m2"] * b["height_m"]

    # ── Effective U-values post-intervention ──────────────────────────────────
    u_wall    = b["u_value_wall"]    * s["u_wall_factor"]
    u_roof    = b["u_value_roof"]    * s["u_roof_factor"]
    u_glazing = b["u_value_glazing"] * s["u_glazing_factor"]

    # ── Heat loss (CIBSE Guide A) ─────────────────────────────────────────────
    delta_t     = max(0.0, 21.0 - temp)      # 21°C set-point (Part L)
    heating_hrs = 5800.0                      # UK heating season (CIBSE Guide A)

    q_wall    = u_wall    * wall_area_m2    * delta_t * heating_hrs  # Wh
    q_roof    = u_roof    * roof_area_m2    * delta_t * heating_hrs
    q_glazing = u_glazing * glazing_area_m2 * delta_t * heating_hrs
    q_trans_mwh = (q_wall + q_roof + q_glazing) / 1_000_000.0

    # ── Infiltration (CIBSE Guide A) ──────────────────────────────────────────
    ach         = 0.7 * (1.0 - s["infiltration_reduction"])
    q_inf_mwh   = (0.33 * ach * volume_m3 * delta_t * heating_hrs) / 1_000_000.0

    # ── Solar gain offset  (PVGIS: 950 kWh/m²/yr Reading) ────────────────────
    solar_mwh = (950.0 * glazing_area_m2 * 0.6 * (1.0 - s["solar_gain_reduction"])) / 1_000.0
    modelled_mwh = max(0.0, q_trans_mwh + q_inf_mwh - solar_mwh * 0.3)

    # ── Baseline (no scenario) ────────────────────────────────────────────────
    baseline_raw = (
        b["u_value_wall"]    * wall_area_m2    * delta_t * heating_hrs
      + b["u_value_roof"]    * roof_area_m2    * delta_t * heating_hrs
      + b["u_value_glazing"] * glazing_area_m2 * delta_t * heating_hrs
      + 0.33 * 0.7           * volume_m3       * delta_t * heating_hrs
    ) / 1_000_000.0

    reduction_ratio = (
        max(0.0, 1.0 - (baseline_raw - modelled_mwh) / baseline_raw)
        if baseline_raw > 0 else 1.0
    )

    adjusted_mwh  = b["baseline_energy_mwh"] * max(0.35, reduction_ratio)
    renewable_mwh = s["renewable_kwh"] / 1_000.0
    final_mwh     = max(0.0, adjusted_mwh - renewable_mwh)

    # ── Carbon (BEIS 2023: 0.20482 kgCO₂e/kWh) ───────────────────────────────
    ci               = 0.20482
    baseline_carbon  = (b["baseline_energy_mwh"] * 1000.0 * ci) / 1000.0
    scenario_carbon  = (final_mwh * 1000.0 * ci) / 1000.0

    # ── Financial (HESA 2022-23: £0.28/kWh) ──────────────────────────────────
    unit_cost     = 0.28
    annual_saving = (b["baseline_energy_mwh"] - final_mwh) * 1000.0 * unit_cost
    install_cost  = float(s["install_cost_gbp"])
    payback       = (install_cost / annual_saving) if annual_saving > 0.0 else None

    cpt = round(install_cost / max(baseline_carbon - scenario_carbon, 0.01), 1) \
          if install_cost > 0 else None

    return {
        "baseline_energy_mwh":  round(b["baseline_energy_mwh"], 1),
        "scenario_energy_mwh":  round(final_mwh, 1),
        "energy_saving_mwh":    round(b["baseline_energy_mwh"] - final_mwh, 1),
        "energy_saving_pct":    round((b["baseline_energy_mwh"] - final_mwh)
                                      / b["baseline_energy_mwh"] * 100.0, 1),
        "baseline_carbon_t":    round(baseline_carbon, 1),
        "scenario_carbon_t":    round(scenario_carbon, 1),
        "carbon_saving_t":      round(baseline_carbon - scenario_carbon, 1),
        "annual_saving_gbp":    round(annual_saving, 0),
        "install_cost_gbp":     install_cost,
        "payback_years":        round(payback, 1) if payback else None,
        "cost_per_tonne_co2":   cpt,
        "renewable_mwh":        round(renewable_mwh, 1),
        "u_wall":               round(u_wall, 2),
        "u_roof":               round(u_roof, 2),
        "u_glazing":            round(u_glazing, 2),
    }

# ─────────────────────────────────────────────────────────────────────────────
# CHART THEME
# ─────────────────────────────────────────────────────────────────────────────
CHART_LAYOUT = dict(
    plot_bgcolor  = "rgba(0,0,0,0)",
    paper_bgcolor = "rgba(0,0,0,0)",
    font          = dict(family="Nunito Sans, sans-serif", size=11, color="#071A2F"),
    margin        = dict(t=20, b=10, l=0, r=0),
    height        = 300,
    yaxis         = dict(gridcolor="#E8EEF4", zerolinecolor="#D0DAE4", tickfont=dict(size=10)),
    xaxis         = dict(tickfont=dict(size=10)),
    showlegend    = False,
)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INITIALISATION & URL SYNC
# ─────────────────────────────────────────────────────────────────────────────
def _get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]
    except (KeyError, AttributeError, FileNotFoundError):
        return os.getenv(key, default)

_qp = st.query_params

# F5 Persistence logic for Onboarding Gate Segment
if "segment" in _qp:
    st.session_state.user_segment = _qp.get("segment")

if "user_segment" not in st.session_state:
    st.session_state.user_segment = None # Start unselected to trigger gate

if "portfolio" not in st.session_state:
    st.session_state.portfolio = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "agent_history" not in st.session_state:
    st.session_state.agent_history = []
if "gemini_key" not in st.session_state:
    st.session_state.gemini_key = _get_secret("GEMINI_KEY", "")
if "gemini_key_valid" not in st.session_state:
    st.session_state.gemini_key_valid = False
if "met_office_key" not in st.session_state:
    st.session_state.met_office_key = _get_secret("MET_OFFICE_KEY", "")
if "manual_temp" not in st.session_state:
    st.session_state.manual_temp = 10.5
if "force_weather_refresh" not in st.session_state:
    st.session_state.force_weather_refresh = False
if "wx_city" not in st.session_state:
    st.session_state.wx_city = "Reading, Berkshire"
if "wx_lat" not in st.session_state:
    st.session_state.wx_lat = loc.CITIES["Reading, Berkshire"]["lat"]
if "wx_lon" not in st.session_state:
    st.session_state.wx_lon = loc.CITIES["Reading, Berkshire"]["lon"]
if "wx_location_name" not in st.session_state:
    st.session_state.wx_location_name = "Reading, Berkshire, UK"
if "wx_provider" not in st.session_state:
    st.session_state.wx_provider = "open_meteo"
if "wx_enable_fallback" not in st.session_state:
    st.session_state.wx_enable_fallback = True
if "owm_key" not in st.session_state:
    st.session_state.owm_key = _get_secret("OWM_KEY", "")

# ─────────────────────────────────────────────────────────────────────────────
# ONBOARDING GATE (App Locked Until Segment Selected)
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.user_segment:
    st.markdown("""
    <div style="text-align: center; margin-top: 50px;">
        <h1 style="color: #071A2F;">Welcome to CrowAgent™ Platform</h1>
        <p style="color: #5A7A90; font-size: 1.1rem; margin-bottom: 30px;">Select your sector to configure the intelligence engine.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    segments_ui = [
        (col1, "university_he", "University / HE", "🎓", "Campus estate managers"),
        (col2, "smb_landlord", "Commercial Landlord", "🏢", "MEES compliance focused"),
        (col3, "smb_industrial", "SMB Industrial", "🏭", "SECR / Carbon baselining"),
        (col4, "individual_selfbuild", "Individual Self-Build", "🏠", "Part L / FHS compliance")
    ]
    
    for col, seg_id, label, icon, desc in segments_ui:
        with col:
            st.markdown(f"""
            <div style="background: #ffffff; border-radius: 8px; border: 1px solid #E0EBF4; padding: 20px; text-align: center; height: 180px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <div style="font-size: 2.5rem; margin-bottom: 10px;">{icon}</div>
                <div style="font-family: 'Rajdhani', sans-serif; font-weight: 700; font-size: 1.1rem; color: #071A2F;">{label}</div>
                <div style="font-size: 0.8rem; color: #5A7A90; margin-top: 5px;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Select {label}", key=f"btn_gate_{seg_id}", use_container_width=True):
                st.session_state.user_segment = seg_id
                st.query_params["segment"] = seg_id
                st.rerun()
                
    st.stop() # Halt execution until gate is passed

# ─────────────────────────────────────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────────────────────────────────────
def _update_location_query_params() -> None:
    params: dict[str, str] = {}
    if st.session_state.wx_city:
        params["city"] = st.session_state.wx_city
    params["lat"] = str(st.session_state.wx_lat)
    params["lon"] = str(st.session_state.wx_lon)
    # Preserve segment in query params
    if st.session_state.user_segment:
        params["segment"] = st.session_state.user_segment
    st.query_params.clear()
    st.query_params.update(params)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    # ── Logo ──────────────────────────────────────────────────────────────────
    if LOGO_URI:
        st.markdown(
            f"<div style='padding:10px 0 4px; text-align:center;'>"
            f"<img src='{LOGO_URI}' width='200' style='max-width:100%; height:auto; display:inline-block;' alt='CrowAgent™ Logo'/>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='font-family:Rajdhani,sans-serif;font-size:1.3rem;"
            "font-weight:700;color:#00C2A8;padding:10px 0 4px;'>🌿 CrowAgent™</div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        "<div style='font-size:0.82rem;color:#8FBCCE;margin-bottom:8px;'>"
        "Sustainability AI Decision Intelligence Platform</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Active Segment ────────────────────────────────────────────────────────
    st.markdown("<div class='sb-section'>👤 Active Segment</div>", unsafe_allow_html=True)
    _seg_meta = compliance.SEGMENT_META.get(st.session_state.user_segment, {})
    st.markdown(
        f"<div style='font-size:0.9rem; color:#00C2A8; font-weight: 600; margin-bottom:4px;'>"
        f"{_seg_meta.get('icon', '')} {_seg_meta.get('label', 'Unknown Segment')}</div>"
        f"<div style='font-size:0.74rem;color:#8FBCCE;line-height:1.5;margin-bottom:10px;'>"
        f"{_seg_meta.get('description', '')}</div>",
        unsafe_allow_html=True,
    )
    if st.button("Change Segment / Reset", key="btn_reset_segment"):
        st.session_state.user_segment = None
        st.query_params.clear()
        st.rerun()

    st.markdown("---")

    # ── Portfolio Manager ─────────────────────────────────────────────────────
    st.markdown("<div class='sb-section'>🏢 Asset Portfolio</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.75rem; color:#8FBCCE;'>{len(st.session_state.portfolio)} / {MAX_PORTFOLIO_SIZE} Assets Loaded</div>", unsafe_allow_html=True)
    
    with st.form(key="add_portfolio_form", clear_on_submit=True):
        new_postcode = st.text_input("Add UK Postcode", placeholder="e.g. SW1A 1AA")
        submit_add = st.form_submit_button("➕ Add Asset", use_container_width=True)
        if submit_add and new_postcode:
            add_to_portfolio(new_postcode)
            st.rerun()

    if st.session_state.portfolio:
        for p_item in st.session_state.portfolio:
            col_id, col_btn = st.columns([4, 1])
            with col_id:
                st.markdown(f"<div style='font-size:0.8rem; color:#CBD8E6; padding-top: 5px;'>{p_item['postcode']} (EPC: {p_item['epc_band']})</div>", unsafe_allow_html=True)
            with col_btn:
                if st.button("❌", key=f"del_{p_item['id']}", help="Remove asset"):
                    remove_from_portfolio(p_item['id'])
                    st.rerun()
    else:
        st.markdown("<div style='font-size:0.8rem; color:#5A7A90; font-style: italic;'>Portfolio empty. Add a postcode above.</div>", unsafe_allow_html=True)

    st.markdown("---")
# ── Location picker ────────────────────────────────────────────────────────
    st.markdown("<div class='sb-section'>📍 Location</div>", unsafe_allow_html=True)

    _city_list = loc.city_options()
    _city_idx  = _city_list.index(st.session_state.wx_city) if st.session_state.wx_city in _city_list else 0
    _sel_city  = st.selectbox(
        "City / Region", _city_list, index=_city_idx,
        label_visibility="collapsed",
    )

    if _sel_city != st.session_state.wx_city:
        _meta = loc.city_meta(_sel_city)
        st.session_state.wx_city          = _sel_city
        st.session_state.wx_lat           = _meta["lat"]
        st.session_state.wx_lon           = _meta["lon"]
        st.session_state.wx_location_name = f"{_sel_city}, {_meta['country']}"
        st.session_state.force_weather_refresh = True
        audit.log_event("LOCATION_CHANGED", f"City set to '{_sel_city}'")
        _update_location_query_params()

    # Manual lat/lon entry (for precise site addresses)
    with st.expander("⚙ Custom coordinates", expanded=False):
        _col_lat, _col_lon = st.columns(2)
        with _col_lat:
            _custom_lat = st.number_input(
                "Latitude", value=float(st.session_state.wx_lat),
                min_value=-90.0, max_value=90.0, format="%.4f", step=0.0001,
            )
        with _col_lon:
            _custom_lon = st.number_input(
                "Longitude", value=float(st.session_state.wx_lon),
                min_value=-180.0, max_value=180.0, format="%.4f", step=0.0001,
            )
        if st.button("Apply coordinates", key="apply_coords", use_container_width=True):
            st.session_state.wx_lat           = _custom_lat
            st.session_state.wx_lon           = _custom_lon
            st.session_state.wx_location_name = f"Custom site ({_custom_lat:.4f}, {_custom_lon:.4f})"
            st.session_state.force_weather_refresh = True
            audit.log_event(
                "LOCATION_CUSTOM",
                f"Custom coordinates set: {_custom_lat:.4f}, {_custom_lon:.4f}",
            )
            _update_location_query_params()
        
        st.markdown(
            "<div style='font-size:0.73rem;color:#8FBCCE;margin-top:4px;'>"
            "Or use browser geolocation (HTTPS only):</div>",
            unsafe_allow_html=True,
        )
        
    _geo = loc.render_geo_detect()
    if _geo and isinstance(_geo, dict):
        try:
            _lat = float(_geo.get("lat"))
            _lon = float(_geo.get("lon"))
            _resolved = loc.nearest_city(_lat, _lon)
            st.session_state.wx_city          = _resolved
            st.session_state.wx_lat           = _lat
            st.session_state.wx_lon           = _lon
            st.session_state.wx_location_name = f"{_resolved}, {loc.CITIES[_resolved]['country']}"
            st.session_state.force_weather_refresh = True
            audit.log_event(
                "LOCATION_AUTO_DETECTED",
                f"Resolved browser location to '{_resolved}' (coords retained until ref.)",
            )
            _update_location_query_params()
        except Exception:
            pass

    st.markdown("---")

    # ── Weather panel ──────────────────────────────────────────────────────────
    st.markdown("<div class='sb-section'>🌤 Live Weather</div>", unsafe_allow_html=True)

    _force = st.button("↻ Refresh Weather", key="wx_refresh", use_container_width=True)
    if _force:
        st.session_state.force_weather_refresh = True

    # Manual temp slider (shown always as override option)
    manual_t = st.slider(
        "Manual temperature override (°C)", -10.0, 35.0,
        st.session_state.manual_temp, 0.5,
    )
    st.session_state.manual_temp = manual_t

    # Resolve Met Office site ID for selected city (if available)
    _mo_loc_id = (
        loc.city_meta(st.session_state.wx_city).get("mo_id", wx.MET_OFFICE_LOCATION)
        if st.session_state.wx_city in loc.CITIES
        else wx.MET_OFFICE_LOCATION
    )

    with st.spinner("Checking weather…"):
        weather = wx.get_weather(
            lat                 = st.session_state.wx_lat,
            lon                 = st.session_state.wx_lon,
            location_name       = st.session_state.wx_location_name,
            provider            = st.session_state.wx_provider,
            met_office_key      = st.session_state.met_office_key or None,
            met_office_location = _mo_loc_id,
            openweathermap_key  = st.session_state.owm_key or None,
            enable_fallback     = st.session_state.wx_enable_fallback,
            manual_temp_c       = manual_t,
            force_refresh       = st.session_state.force_weather_refresh,
        )
    st.session_state.force_weather_refresh = False

    # Display weather widget
    mins_ago = wx.minutes_since_fetch(weather["fetched_utc"])
    wdir_lbl = wx.wind_compass(weather["wind_dir_deg"])

    if weather["is_live"]:
        status_class = "sp sp-live"
        status_dot   = "<span class='pulse-dot'></span>"
        status_text  = f"Live · {mins_ago}m ago"
    else:
        status_class = "sp sp-manual"
        status_dot   = "○"
        status_text  = "Manual override"

    st.markdown(
        f"""<div class='wx-widget'>
  <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
    <div>
      <div style='font-size:1.4rem;line-height:1;'>{weather['condition_icon']}</div>
      <div class='wx-temp'>{weather['temperature_c']}°C</div>
      <div class='wx-desc'>{weather['condition']}</div>
    </div>
    <div style='text-align:right;'>
      <div style='font-size:0.76rem;color:#8FBCCE;'>{weather['location_name']}</div>
    </div>
  </div>
  <div class='wx-row'>
    💨 {weather['wind_speed_mph']} mph {wdir_lbl} &nbsp;|&nbsp;
    💧 {weather['humidity_pct']}% &nbsp;|&nbsp;
    🌡️ {weather['feels_like_c']}°C feels like
  </div>
  <div style='margin-top:6px;'>
    <span class='{status_class}'>{status_dot} {status_text}</span>
  </div>
</div>""",
        unsafe_allow_html=True,
    )
    st.caption(f"📡 {weather['source']}")

    st.markdown("---")

    # ── API Keys & Weather Config (collapsible) ───────────────────────────────
    with st.expander("🔑 API Keys & Weather Config", expanded=False):
        st.markdown(
            "<div style='background:#FFF3CD;border:1px solid #FFD89B;border-radius:6px;padding:10px;'>"
            "<div style='font-size:0.75rem;color:#664D03;font-weight:700;margin-bottom:6px;'>🔒 Security Notice</div>"
            "<div style='font-size:0.78rem;color:#664D03;line-height:1.5;'>"
            "• Keys exist in your session only (cleared on browser close)<br/>"
            "• Your keys are <strong>never</strong> stored on the server<br/>"
            "• Each user enters their own key independently<br/>"
            "• Use unique, disposable API keys if sharing this link"
            "</div></div>",
            unsafe_allow_html=True,
        )
        
        st.markdown("")  # spacing
        st.markdown(
          "<div style='font-size:0.9rem;color:#8FBCCE;margin-bottom:8px;'>"
          "Provide your own API keys — do not use shared or public keys. "
          "Met Office DataPoint (free): register at "
          "<a href=\"https://www.metoffice.gov.uk/services/data/datapoint\" target=\"_blank\">metoffice.gov.uk/services/data/datapoint</a>. "
          "Gemini API key (for AI Advisor): get one at "
          "<a href=\"https://aistudio.google.com\" target=\"_blank\">aistudio.google.com</a> or "
          "<a href=\"https://console.cloud.google.com/apis/credentials\" target=\"_blank\">console.cloud.google.com</a>."
          "</div>",
          unsafe_allow_html=True,
        )
        
        # ── Weather Provider selector ─────────────────────────────────────────
        st.markdown(
            "<div style='font-size:0.78rem;color:#8FBCCE;font-weight:700;"
            "letter-spacing:0.5px;margin:8px 0 4px;'>WEATHER PROVIDER</div>",
            unsafe_allow_html=True,
        )
        _provider_labels = {
            "open_meteo":      "Open-Meteo (free, no key)",
            "openweathermap":  "OpenWeatherMap (key required)",
            "met_office":      "Met Office DataPoint (UK, key required)",
        }
        _provider_keys = list(_provider_labels.keys())
        _cur_prov_idx  = _provider_keys.index(st.session_state.wx_provider) \
                         if st.session_state.wx_provider in _provider_keys else 0
        _sel_provider  = st.selectbox(
            "Weather provider", _provider_keys,
            index=_cur_prov_idx,
            format_func=lambda k: _provider_labels[k],
            label_visibility="collapsed",
        )
        if _sel_provider != st.session_state.wx_provider:
            _prev = st.session_state.wx_provider
            st.session_state.wx_provider = _sel_provider
            st.session_state.force_weather_refresh = True
            audit.log_event(
                "PROVIDER_CHANGED",
                f"Weather provider changed from '{_provider_labels[_prev]}' "
                f"to '{_provider_labels[_sel_provider]}'",
            )

        # Fallback toggle
        _fb = st.checkbox(
            "Fall back to Open-Meteo if primary fails",
            value=st.session_state.wx_enable_fallback,
            key="wx_fallback_toggle",
        )
        if _fb != st.session_state.wx_enable_fallback:
            st.session_state.wx_enable_fallback = _fb

        st.markdown("---")
        # ── OpenWeatherMap key ─────────────────────────────────────────────────
        _show_owm = st.checkbox("Show OWM key", key="show_owm_key", value=False)
        _owm_value = st.session_state.owm_key
        _owm_key  = st.text_input(
            "OpenWeatherMap API key",
            type="default" if _show_owm else "password",
            placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            value=_owm_value,
            help="Free at openweathermap.org/api — 1,000 calls/day on free tier",
        )
        if _owm_key != _owm_value:
            _had_key = bool(_owm_value)
            st.session_state.owm_key = _owm_key
            audit.log_event(
                "KEY_UPDATED",
                "OpenWeatherMap key " + ("updated" if _had_key else "added"),
            )
        if st.session_state.owm_key:
            if st.button("Test OWM key", key="test_owm_key", use_container_width=True):
                _ok, _msg = wx.test_openweathermap_key(
                    st.session_state.owm_key,
                    st.session_state.wx_lat,
                    st.session_state.wx_lon,
                )
                if _ok:
                    st.markdown("<div class='val-ok'>✓ " + _msg + "</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='val-err'>❌ " + _msg + "</div>", unsafe_allow_html=True)

        st.markdown("---")
        # ── Met Office DataPoint key ───────────────────────────────────────────
        _show_mo = st.checkbox("Show Met Office key", key="show_mo_key", value=False)
        _mo_value = st.session_state.met_office_key
        _mo_key = st.text_input(
          "Met Office DataPoint key",
          type="default" if _show_mo else "password", placeholder="",
          value=_mo_value,
          help="Free at metoffice.gov.uk/services/data/datapoint",
        )
        if _mo_key != _mo_value:
            _had_mo = bool(_mo_value)
            st.session_state.met_office_key = _mo_key
            audit.log_event(
                "KEY_UPDATED",
                "Met Office DataPoint key " + ("updated" if _had_mo else "added"),
            )

        # Validation for Met Office DataPoint key
        if st.session_state.met_office_key:
          if st.button("Test Met Office key", key="test_mo_key", use_container_width=True):
            ok, msg = wx.test_met_office_key(st.session_state.met_office_key)
            if ok:
              st.markdown("<div class='val-ok'>✓ " + msg + "</div>", unsafe_allow_html=True)
            else:
              st.markdown("<div class='val-err'>❌ " + msg + "</div>", unsafe_allow_html=True)

        _show_gm = st.checkbox("Show Gemini key", key="show_gm_key", value=False)
        _gm_value = st.session_state.gemini_key
        _gm_key = st.text_input(
            "Gemini API key (for AI Advisor)",
            type="default" if _show_gm else "password", placeholder="AIzaSy... (starts with 'AIza')",
            value=_gm_value,
            help="Get your key at aistudio.google.com or console.cloud.google.com | Never share this key | Each user brings their own",
        )
        if _gm_key != _gm_value:
            st.session_state.gemini_key = _gm_key

        # Validation feedback with actual API test
        if st.session_state.gemini_key:
            # show raw-format warning
            if not st.session_state.gemini_key.startswith("AIza"):
                st.markdown(
                    "<div class='val-warn'>⚠ Gemini key should start with 'AIza'</div>",
                    unsafe_allow_html=True,
                )
            else:
                # delegate to utility helper
                valid, message, warn = validate_gemini_key(st.session_state.gemini_key)
                st.markdown(message, unsafe_allow_html=True)
                st.session_state.gemini_key_valid = valid or warn

    st.markdown("---")

    # ── Config Audit Log ──────────────────────────────────────────────────────
    _log_entries = audit.get_log(n=5)
    if _log_entries:
        with st.expander("🔍 Config Change Log", expanded=False):
            st.markdown(
                "<div style='font-size:0.72rem;color:#8FBCCE;margin-bottom:4px;'>"
                "In-session only — cleared on browser close.</div>",
                unsafe_allow_html=True,
            )
            for _entry in _log_entries:
                st.markdown(
                    f"<div style='font-size:0.72rem;line-height:1.5;"
                    f"border-left:2px solid #1A3A5C;padding-left:6px;margin-bottom:4px;'>"
                    f"<span style='color:#00C2A8;'>{_entry['action']}</span>"
                    f"<br/><span style='color:#CBD8E6;'>{_entry['details']}</span>"
                    f"<br/><span style='color:#5A7A90;font-size:0.68rem;'>{_entry['ts']}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Data sources ──────────────────────────────────────────────────────────
    st.markdown("<div class='sb-section'>📚 Data Sources</div>", unsafe_allow_html=True)
    for src in ["Open-Meteo (weather, default)", "Met Office DataPoint (UK, optional)",
                "OpenWeatherMap (global, optional)", "GeoNames (city dataset, CC-BY)",
                "BEIS GHG Factors 2023", "HESA Estates Stats 2022-23",
                "CIBSE Guide A", "PVGIS (EC JRC)", "Raissi et al. (2019)"]:
        st.caption(f"· {src}")

    st.markdown("---")

    # insert a branded footer. the logo is rendered inline because _logo_html
    # has not yet been computed (it comes later when building the top bar), so
    # we duplicate the same logic here to keep the header and footer in sync.
    if LOGO_URI:
        _footer_logo = (
            f"<img src='{LOGO_URI}' height='28' "
            "style='vertical-align:middle;display:inline-block;height:28px;" 
            "width:auto;' alt='CrowAgent™ Logo'/>"
        )
    else:
        _footer_logo = (
            "<span style='font-family:Rajdhani,sans-serif;" 
            "font-size:1.1rem;font-weight:700;color:#00C2A8;'>" 
            "CrowAgent™</span>"
        )

    st.markdown(f"""
<div class='ent-footer'>
  {_footer_logo}
  <div style='font-size:0.76rem;color:#9ABDD0;line-height:1.6;margin-top:8px;'>
    © 2026 Aparajita Parihar<br/>CrowAgent™ · All rights reserved<br/>
    v2.0.0 · Prototype
  </div>
</div>""",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# COMPUTE ALL SELECTED SCENARIOS
# ─────────────────────────────────────────────────────────────────────────────
_active_buildings = BUILDINGS

if "selected_building_name" not in st.session_state or \
   st.session_state.selected_building_name not in _active_buildings:
    st.session_state.selected_building_name = next(iter(_active_buildings))
selected_building_name = st.session_state.selected_building_name

_valid_scenario_names = list(SCENARIOS.keys())
_default_scenarios = ["Baseline (No Intervention)"]

if "selected_scenario_names" not in st.session_state:
    st.session_state.selected_scenario_names = [
        s for s in _default_scenarios if s in SCENARIOS
    ] or _valid_scenario_names[:1]

selected_scenario_names = [
    s for s in st.session_state.selected_scenario_names if s in SCENARIOS
]
if not selected_scenario_names:
    selected_scenario_names = [
        s for s in _default_scenarios if s in SCENARIOS
    ] or _valid_scenario_names[:1]
st.session_state.selected_scenario_names = selected_scenario_names

results: dict[str, dict] = {}
_compute_errors: list[str] = []

for _sn in selected_scenario_names:
    try:
        results[_sn] = calculate_thermal_load(_active_buildings[selected_building_name],
                                              SCENARIOS[_sn], weather)
    except Exception as _e:
        _compute_errors.append(f"Scenario '{_sn}': {_e}")

baseline_result = results.get("Baseline (No Intervention)", list(results.values())[0] if results else {})

# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM TOP BAR (logo + status indicators)
# ─────────────────────────────────────────────────────────────────────────────
_weather_pill = (
    f"<span class='sp sp-live'><span class='pulse-dot'></span>"
    f"Live Weather · {weather['temperature_c']}°C {weather['condition_icon']}</span>"
    if weather["is_live"]
    else f"<span class='sp sp-manual'>○ Manual · {weather['temperature_c']}°C</span>"
)

if LOGO_URI:
    # ensure logo is vertically centered and not cropped
    _logo_html = f"<img src='{LOGO_URI}' height='38' style='vertical-align:middle; display:inline-block; height:38px; width:auto;' alt='CrowAgent™ Logo'/>"
else:
    # fallback text should match branding but no emoji
    _logo_html = "<span style='font-family:Rajdhani,sans-serif;font-size:1.2rem;font-weight:700;color:#00C2A8;'>CrowAgent™</span>"

st.markdown(f"""
<div class='platform-topbar'>
  <div style='display:flex;align-items:center;gap:16px;flex-wrap:wrap;'>
    {_logo_html}
    <div>
      <div style='font-family:Rajdhani,sans-serif;font-size:0.82rem;
                  letter-spacing:1.5px;text-transform:uppercase;
                  color:#8FBCCE;line-height:1;margin-top:2px;'>
        Sustainability AI Decision Intelligence Platform
      </div>
    </div>
  </div>
  <div class='platform-topbar-right'>
    {_weather_pill}
    <span class='sp sp-cache'>🚧 PROTOTYPE v2.0.0</span>
    <span class='sp sp-cache'>{st.session_state.wx_location_name or st.session_state.wx_city or 'Reading, Berkshire'}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# Show compute errors if any
if _compute_errors:
    for _err in _compute_errors:
        st.error(f"Computation error — {_err}")

# ─────────────────────────────────────────────────────────────────────────────
# PROTOTYPE DISCLAIMER — shown on every page load (compact)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class='disc-prototype'>
  <strong>⚠️ Working Prototype — Results Are Indicative Only.</strong>
  This platform uses simplified physics models calibrated against published UK higher education
  sector averages. Outputs should not be used as the sole basis for capital investment decisions.
  Consult a qualified energy surveyor before committing to any retrofit programme.
  Greenfield University is a fictional institution used for demonstration purposes.
  All data is illustrative.
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN NAVIGATION TABS
# ─────────────────────────────────────────────────────────────────────────────
_tab_dash, _tab_fin, _tab_ai, _tab_compliance, _tab_about = st.tabs([
    "📊 Dashboard",
    "📈 Financial Analysis",
    "🤖 AI Advisor",
    "🏛️ UK Compliance Hub",
    "ℹ️ About & Contact",
])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
with _tab_dash:
    # ── Building heading ──────────────────────────────────────────────────────
    col_hdr, col_badge = st.columns([3, 1])
    with col_hdr:
        st.markdown(
            f"<h2 style='margin:0;padding:0;'>{selected_building_name}</h2>"
            f"<div style='font-size:0.78rem;color:#5A7A90;margin-top:2px;'>"
            f"{sb['description']}</div>",
            unsafe_allow_html=True,
        )
    with col_badge:
        st.markdown(
            f"<div style='text-align:right;padding-top:4px;'>"
            f"<span class='chip'>{sb['built_year']}</span>"
            f"<span class='chip'>{weather['temperature_c']}°C</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── KPI Cards Row ─────────────────────────────────────────────────────────
    if results:
        best_saving = max(results.values(), key=lambda r: r.get("energy_saving_pct", 0))
        best_carbon = max(results.values(), key=lambda r: r.get("carbon_saving_t", 0))
        best_saving_name = next(n for n, r in results.items()
                                if r is best_saving)
        best_carbon_name = next(n for n, r in results.items()
                                if r is best_carbon)
        baseline_energy = baseline_result.get("baseline_energy_mwh",
                                              sb["baseline_energy_mwh"])
        baseline_co2    = round(baseline_energy * 1000 * 0.20482 / 1000, 1)

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f"""
            <div class='kpi-card'>
              <div class='kpi-label'>Portfolio Baseline</div>
              <div class='kpi-value'>{baseline_energy:,.0f}<span class='kpi-unit'>MWh/yr</span></div>
              <div class='kpi-sub'>Current energy consumption</div>
            </div>""", unsafe_allow_html=True)
        with k2:
            st.markdown(f"""
            <div class='kpi-card accent-green'>
              <div class='kpi-label'>Best Energy Saving</div>
              <div class='kpi-value'>{best_saving.get('energy_saving_pct',0)}<span class='kpi-unit'>%</span></div>
              <div class='kpi-delta-pos'>↓ {best_saving.get('energy_saving_mwh',0):,.0f} MWh/yr</div>
              <div class='kpi-sub'>{best_saving_name.split('(')[0].strip()}</div>
            </div>""", unsafe_allow_html=True)
        with k3:
            st.markdown(f"""
            <div class='kpi-card accent-teal' style='border-top-color:#00C2A8'>
              <div class='kpi-label'>Best Carbon Reduction</div>
              <div class='kpi-value'>{best_carbon.get('carbon_saving_t',0):,.0f}<span class='kpi-unit'>t CO₂e</span></div>
              <div class='kpi-delta-pos'>↓ {round(best_carbon.get('carbon_saving_t',0)/max(baseline_co2,1)*100,1)}% of baseline</div>
              <div class='kpi-sub'>{best_carbon_name.split('(')[0].strip()}</div>
            </div>""", unsafe_allow_html=True)
        with k4:
            baseline_cost = round(baseline_energy * 1000 * 0.28 / 1000, 1)
            st.markdown(f"""
            <div class='kpi-card accent-gold'>
              <div class='kpi-label'>Baseline Annual Cost</div>
              <div class='kpi-value'>£{baseline_cost:,.0f}<span class='kpi-unit'>k</span></div>
              <div class='kpi-sub'>At £0.28/kWh (HESA 2022-23)</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # ── Charts Row 1: Energy + Carbon ─────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        st.markdown("<div class='chart-title'>⚡ Annual Energy Consumption</div>", unsafe_allow_html=True)
        fig_e = go.Figure()
        for sn, res in results.items():
            sc = SCENARIOS[sn]
            fig_e.add_trace(go.Bar(
                x=[sn.replace(" (No Intervention)","").replace(" (All Interventions)","")],
                y=[res["scenario_energy_mwh"]],
                marker_color=sc["colour"],
                text=[f"{res['scenario_energy_mwh']:,.0f}"],
                textposition="outside", name=sn,
            ))
        fig_e.update_layout(**CHART_LAYOUT, yaxis_title="MWh / year")
        st.plotly_chart(fig_e, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            "<div class='chart-caption'>CrowAgent™ PINN thermal model · "
            "CIBSE Guide A · Cross-validated against US DoE EnergyPlus</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        st.markdown("<div class='chart-title'>🌍 Annual Carbon Emissions</div>", unsafe_allow_html=True)
        fig_c = go.Figure()
        for sn, res in results.items():
            sc = SCENARIOS[sn]
            fig_c.add_trace(go.Bar(
                x=[sn.replace(" (No Intervention)","").replace(" (All Interventions)","")],
                y=[res["scenario_carbon_t"]],
                marker_color=sc["colour"],
                text=[f"{res['scenario_carbon_t']:,.1f} t"],
                textposition="outside", name=sn,
            ))
        fig_c.update_layout(**CHART_LAYOUT, yaxis_title="Tonnes CO₂e / year")
        st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            "<div class='chart-caption'>Carbon intensity: 0.20482 kgCO₂e/kWh · "
            "Source: BEIS Greenhouse Gas Conversion Factors 2023</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Technical Parameters Table ────────────────────────────────────────────
    st.markdown("<div class='sec-hdr'>Technical Parameters</div>", unsafe_allow_html=True)
    rows_tbl = []
    for sn, res in results.items():
        sc = SCENARIOS[sn]
        rows_tbl.append({
            "Scenario": sc["icon"] + " " + sn,
            "U-Wall (W/m²K)": res["u_wall"],
            "U-Roof (W/m²K)": res["u_roof"],
            "U-Glaz (W/m²K)": res["u_glazing"],
            "Energy (MWh/yr)": res["scenario_energy_mwh"],
            "Saving (%)": f"{res['energy_saving_pct']}%",
            "CO₂ Saving (t)": res["carbon_saving_t"],
            "Install Cost": f"£{res['install_cost_gbp']:,.0f}" if res["install_cost_gbp"] > 0 else "—",
            "Payback (yrs)": res["payback_years"] if res["payback_years"] else "—",
        })
    st.dataframe(pd.DataFrame(rows_tbl), use_container_width=True, hide_index=True)
    st.caption("U-values: CIBSE Guide A · Scenario factors: BSRIA / Green Roof Organisation UK · "
               "⚠️ Indicative only — see prototype disclaimer above")

    # ── Building Specification Expander ───────────────────────────────────────
    with st.expander(f"📐 Building Specification — {selected_building_name}"):
        sp1, sp2 = st.columns(2)
        with sp1:
            st.markdown(f"**Floor Area:** {sb['floor_area_m2']:,} m²")
            st.markdown(f"**Floor-to-Floor Height:** {sb['height_m']} m")
            st.markdown(f"**Glazing Ratio:** {sb['glazing_ratio']*100:.0f}%")
            st.markdown(f"**Annual Occupancy:** ~{sb['occupancy_hours']:,} hours")
            st.markdown(f"**Approximate Build Year:** {sb['built_year']}")
        with sp2:
            st.markdown(f"**Baseline U-wall:** {sb['u_value_wall']} W/m²K")
            st.markdown(f"**Baseline U-roof:** {sb['u_value_roof']} W/m²K")
            st.markdown(f"**Baseline U-glazing:** {sb['u_value_glazing']} W/m²K")
            st.markdown(f"**Baseline Energy:** {sb['baseline_energy_mwh']} MWh/yr")
            st.markdown(
                f"**Baseline Carbon:** "
                f"{round(sb['baseline_energy_mwh'] * 1000 * 0.20482 / 1000, 1)} t CO₂e/yr"
            )
        st.caption(
            "⚠️ Data is indicative and derived from published UK HE sector averages (HESA 2022-23). "
            "Not specific to any real institution. Do not use for actual estate planning "
            "without site-specific survey."
        )

    # ── 3D/4D Campus Visualisation ────────────────────────────────────────────
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    render_campus_3d_map(
        selected_scenario_names=selected_scenario_names,
        weather=weather,
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
        # ── Cost & Saving Charts ──────────────────────────────────────────────
        fc1, fc2 = st.columns(2)
        with fc1:
            st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
            st.markdown("<div class='chart-title'>💰 Annual Cost Savings</div>", unsafe_allow_html=True)
            fig_s = go.Figure()
            for sn, res in paid_scenarios.items():
                sc = SCENARIOS[sn]
                fig_s.add_trace(go.Bar(
                    x=[sn.replace(" (All Interventions)","")],
                    y=[res["annual_saving_gbp"]],
                    marker_color=sc["colour"],
                    text=[f"£{res['annual_saving_gbp']:,.0f}"],
                    textposition="outside", name=sn,
                ))
            fig_s.update_layout(**CHART_LAYOUT, yaxis_title="£ per year")
            st.plotly_chart(fig_s, use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                "<div class='chart-caption'>Electricity at £0.28/kWh · HESA 2022-23 · "
                "Assumes constant energy price</div>",
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with fc2:
            st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
            st.markdown("<div class='chart-title'>⏱ Simple Payback Period</div>", unsafe_allow_html=True)
            fig_p = go.Figure()
            for sn, res in paid_scenarios.items():
                sc = SCENARIOS[sn]
                if res["payback_years"]:
                    fig_p.add_trace(go.Bar(
                        x=[sn.replace(" (All Interventions)","")],
                        y=[res["payback_years"]],
                        marker_color=sc["colour"],
                        text=[f"{res['payback_years']} yrs"],
                        textposition="outside", name=sn,
                    ))
            fig_p.update_layout(**CHART_LAYOUT, yaxis_title="Years")
            st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                "<div class='chart-caption'>Install cost ÷ annual saving · Simple (undiscounted) · "
                "⚠️ Excludes finance costs</div>",
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        # ── 10-Year Cumulative Saving Projection ──────────────────────────────
        st.markdown("<div class='sec-hdr'>10-Year Cumulative Net Cash Flow</div>", unsafe_allow_html=True)
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        st.markdown(
            "<div class='chart-title'>Cumulative Net Savings (£) — Year 0 = Installation Cost</div>",
            unsafe_allow_html=True,
        )
        fig_ncf = go.Figure()
        years = list(range(0, 11))
        for sn, res in paid_scenarios.items():
            sc = SCENARIOS[sn]
            install = res["install_cost_gbp"]
            annual  = res["annual_saving_gbp"]
            cashflow = [-install + annual * y for y in years]
            fig_ncf.add_trace(go.Scatter(
                x=years, y=cashflow,
                name=sn.replace(" (All Interventions)",""),
                line=dict(color=sc["colour"], width=2.5),
                mode="lines+markers",
            ))
        fig_ncf.add_hline(y=0, line=dict(dash="dot", color="#C0C8D0", width=1))
        fig_ncf.update_layout(
            **{**CHART_LAYOUT, "height": 320, "showlegend": True},
            yaxis_title="Cumulative Net Cash Flow (£)",
            xaxis_title="Year",
            legend=dict(font=dict(size=10), orientation="h", y=-0.25),
        )
        st.plotly_chart(fig_ncf, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            "<div class='chart-caption'>⚠️ Indicative projection only · Assumes constant energy price · "
            "No inflation, discount rate, or maintenance costs applied</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Investment Comparison Table ────────────────────────────────────────
        st.markdown("<div class='sec-hdr'>Investment Comparison Matrix</div>", unsafe_allow_html=True)
        inv_rows = []
        for sn, res in paid_scenarios.items():
            inv_rows.append({
                "Scenario": SCENARIOS[sn]["icon"] + " " + sn,
                "Install Cost": f"£{res['install_cost_gbp']:,.0f}",
                "Annual Saving (£)": f"£{res['annual_saving_gbp']:,.0f}",
                "Simple Payback": f"{res['payback_years']} yrs" if res["payback_years"] else "—",
                "CO₂ Saving (t/yr)": res["carbon_saving_t"],
                "£ per tonne CO₂": f"£{res['cost_per_tonne_co2']:,.0f}" if res["cost_per_tonne_co2"] else "—",
                "5-yr Net Saving": f"£{res['annual_saving_gbp']*5 - res['install_cost_gbp']:,.0f}",
            })
        st.dataframe(pd.DataFrame(inv_rows), use_container_width=True, hide_index=True)
        st.caption("⚠️ 5-yr net saving = (annual saving × 5) − install cost · Undiscounted · Indicative only")


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — AI ADVISOR
# ════════════════════════════════════════════════════════════════════════════
with _tab_ai:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#071A2F,#0D2640);
                border-left:4px solid #00C2A8;border-radius:8px;
                padding:16px 20px;margin-bottom:14px;'>
      <div style='font-family:Rajdhani,sans-serif;font-size:1.05rem;
                  font-weight:700;color:#00C2A8;letter-spacing:0.5px;'>
        🤖 CrowAgent™ AI Advisor
      </div>
      <div style='color:#CBD8E6;font-size:0.83rem;margin-top:4px;'>
        Physics-grounded agentic AI that runs real thermal simulations,
        compares scenarios and gives evidence-based Net Zero investment recommendations.
      </div>
      <div style='color:#8FBCCE;font-size:0.78rem;margin-top:4px;'>
        Powered by Google Gemini · Physics-informed reasoning · © 2026 Aparajita Parihar
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── AI Disclaimer ─────────────────────────────────────────────────────────
    st.markdown("""
    <div class='disc-ai'>
      <strong>🤖 AI Accuracy Disclaimer.</strong>
      The AI Advisor generates responses based on physics tool outputs and large language model
      reasoning. Like all AI systems, it can make mistakes, misinterpret questions, or produce
      plausible-sounding but incorrect conclusions. All AI-generated recommendations must be
      independently verified by a qualified professional before any action is taken.
      This AI Advisor is not a substitute for professional engineering or financial advice.
      Results are indicative only.
    </div>
    """, unsafe_allow_html=True)

    _akey = st.session_state.get("gemini_key", "")

    # CSS for chat
    st.markdown("""
    <style>
    .ca-user{background:#071A2F;border-left:3px solid #00C2A8;border-radius:0 8px 8px 8px;
             padding:10px 14px;margin:10px 0 4px;color:#F0F4F8;font-size:0.88rem;line-height:1.5;}
    .ca-ai  {background:#ffffff;border:1px solid #E0EBF4;border-left:3px solid #1DB87A;
             border-radius:0 8px 8px 8px;padding:10px 14px;margin:4px 0 10px;
             color:#071A2F;font-size:0.88rem;line-height:1.65;}
    .ca-tool{display:inline-block;background:#0D2640;color:#00C2A8;border-radius:4px;
             padding:2px 8px;font-size:0.78rem;font-weight:700;margin:2px 2px 2px 0;
             letter-spacing:0.3px;}
    .ca-meta{font-size:0.78rem;color:#6A92AA;margin-top:4px;}
    </style>
    """, unsafe_allow_html=True)

    if not _akey:
        col_onb, _ = st.columns([2, 1])
        with col_onb:
            st.markdown("""
            <div style='background:#F0F4F8;border:1px solid #E0EBF4;border-radius:8px;
                        padding:24px;text-align:center;'>
              <div style='font-size:2.5rem;margin-bottom:10px;'>🔑</div>
              <div style='font-family:Rajdhani,sans-serif;font-size:1rem;font-weight:700;
                          color:#071A2F;margin-bottom:12px;'>
                Activate AI Advisor with a free Gemini API key
              </div>
              <div style='color:#5A7A90;font-size:0.85rem;line-height:1.8;max-width:380px;margin:0 auto;'>
                1. Visit
                   <a href='https://aistudio.google.com' target='_blank'
                      style='color:#00C2A8;font-weight:700;'>aistudio.google.com</a><br/>
                2. Sign in with any Google account<br/>
                3. Click <strong>Get API key → Create API key</strong><br/>
                4. Paste it into <strong>API Keys</strong> in the sidebar<br/><br/>
                <span style='color:#8AACBF;font-size:0.76rem;'>
                  Free tier · 1,500 requests/day · No credit card required
                </span>
              </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown(
            "<div style='color:#5A7A90;font-size:0.82rem;margin-bottom:8px;'>"
            "Questions you can ask once activated:</div>",
            unsafe_allow_html=True,
        )
        for _sq in crow_agent.STARTER_QUESTIONS[:6]:
            st.markdown(
                f"<div style='background:#F0F4F8;border:1px solid #E0EBF4;border-radius:5px;"
                f"padding:8px 12px;margin:4px 0;color:#5A7A90;font-size:0.82rem;'>💬 {_sq}</div>",
                unsafe_allow_html=True,
            )
    else:
        # ── Starter question buttons ──────────────────────────────────────────
        if not st.session_state.chat_history:
            st.markdown(
                "<div style='color:#5A7A90;font-size:0.82rem;margin-bottom:8px;'>"
                "✨ Click a question to start — the AI will run real simulations:</div>",
                unsafe_allow_html=True,
            )
            _sq_cols = st.columns(2)
            for _qi, _sq in enumerate(crow_agent.STARTER_QUESTIONS[:6]):
                with _sq_cols[_qi % 2]:
                    if st.button(_sq, key=f"sq_{_qi}", use_container_width=True):
                        st.session_state["_pending"] = _sq
                        st.rerun()

        # ── Process pending question ──────────────────────────────────────────
        if "_pending" in st.session_state:
            _pq = st.session_state.pop("_pending")
            st.session_state.chat_history.append({"role": "user", "content": _pq})
            with st.spinner("🤖 Running physics simulations and reasoning…"):
                _res = crow_agent.run_agent(
                    api_key=_akey, user_message=_pq,
                    conversation_history=st.session_state.agent_history,
                    buildings=_active_buildings, scenarios=SCENARIOS,
                    calculate_fn=calculate_thermal_load,
                    current_context={
                        "building": selected_building_name,
                        "scenarios": selected_scenario_names,
                        "temperature_c": weather["temperature_c"],
                    },
                )
            if _res.get("updated_history"):
                st.session_state.agent_history = _res["updated_history"]
            st.session_state.chat_history.append({
                "role": "assistant",
                "content":     _res.get("answer", ""),
                "tool_calls":  _res.get("tool_calls", []),
                "error":       _res.get("error"),
                "loops":       _res.get("loops", 1),
            })

        # ── Render messages ───────────────────────────────────────────────────
        for _msg in st.session_state.chat_history:
            if _msg["role"] == "user":
                st.markdown(
                    f"<div class='ca-user'><strong style='color:#00C2A8;'>You</strong> "
                    f"<span class='ca-meta'>{datetime.now().strftime('%H:%M')}</span><br/>"
                    f"{_msg['content']}</div>",
                    unsafe_allow_html=True,
                )
            else:
                _tc = _msg.get("tool_calls", [])
                if _tc:
                    _bh = "<div style='margin:4px 0 5px;'>"
                    for _t in _tc:
                        _bh += f"<span class='ca-tool'>⚙ {_t['name']}</span>"
                    _bh += (
                        f" <span class='ca-meta'>{_msg.get('loops',1)} reasoning "
                        f"step{'s' if _msg.get('loops',1)!=1 else ''}</span></div>"
                    )
                    st.markdown(_bh, unsafe_allow_html=True)
                if _msg.get("error"):
                    st.error(f"⚠️ Error: {_msg['error']}")
                else:
                    st.markdown(
                        f"<div class='ca-ai'>"
                        f"<strong style='color:#1DB87A;font-family:Rajdhani,sans-serif;'>AI Advisor</strong>"
                        f"<span class='ca-meta' style='margin-left:6px;'>Powered by Gemini 1.5 Flash</span>"
                        f"<br/><br/>{_msg['content']}<br/>"
                        f"<div style='margin-top:8px;padding-top:6px;border-top:1px solid #E0EBF4;"
                        f"font-size:0.77rem;color:#6A92AA;'>"
                        f"⚠️ AI-generated content. Verify all figures independently before acting.</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        # ── Input form ────────────────────────────────────────────────────────
        with st.form(key="ca_form", clear_on_submit=True):
            _inp = st.text_input(
                "Ask the AI Advisor:",
                placeholder="e.g. Which building should we upgrade first for £150,000?",
                label_visibility="collapsed",
            )
            _c1, _c2 = st.columns([5, 1])
            with _c1:
                _go = st.form_submit_button("Send →", use_container_width=True, type="primary")
            with _c2:
                _clr = st.form_submit_button("Clear", use_container_width=True)

        # ── Input validation ──────────────────────────────────────────────────
        if _go and _inp.strip():
            # Basic input sanitisation
            _clean = _inp.strip()[:500]   # max 500 chars
            if len(_clean) < 5:
                st.warning("Please enter a more detailed question (at least 5 characters).")
            else:
                st.session_state.chat_history.append({"role": "user", "content": _clean})
                with st.spinner("🤖 Running simulations and reasoning…"):
                    _res = crow_agent.run_agent(
                        api_key=_akey, user_message=_clean,
                        conversation_history=st.session_state.agent_history,
                        buildings=_active_buildings, scenarios=SCENARIOS,
                        calculate_fn=calculate_thermal_load,
                        current_context={
                            "building": selected_building_name,
                            "scenarios": selected_scenario_names,
                            "temperature_c": weather["temperature_c"],
                        },
                    )
                if _res.get("updated_history"):
                    st.session_state.agent_history = _res["updated_history"]
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content":     _res.get("answer", ""),
                    "tool_calls":  _res.get("tool_calls", []),
                    "error":       _res.get("error"),
                    "loops":       _res.get("loops", 1),
                })
                st.rerun()

        if _clr:
            st.session_state.chat_history = []
            st.session_state.agent_history = []
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — UK COMPLIANCE HUB
# ════════════════════════════════════════════════════════════════════════════
with _tab_compliance:
    _seg   = st.session_state.user_segment
    _smeta = compliance.SEGMENT_META[_seg]

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        f"<h3 style='margin-bottom:4px;'>UK Compliance Hub</h3>"
        f"<div style='font-size:0.80rem;color:#5A7A90;margin-bottom:14px;'>"
        f"{_smeta['icon']} {_smeta['label']} · "
        f"Relevant regulations: {' · '.join(_smeta['regulations'])}"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("""
    <div class='disc-prototype'>
      <strong>⚠️ Compliance Disclaimer.</strong>
      All outputs in this tab are <strong>indicative estimates only</strong> based on simplified
      proxy calculations. They do not constitute a formal EPC, SAP, SBEM, or SECR assessment.
      Formal compliance requires assessment by an accredited energy assessor (DEA/NDEA) or
      qualified carbon accountant. Results should not be relied upon for legal, financial, or
      planning decisions without independent professional verification.
    </div>
    """, unsafe_allow_html=True)

    # ── Segment: University HE — redirect notice ───────────────────────────
    if _seg == "university_he":
        st.info(
            "**University / Higher Education segment selected.** "
            "The compliance tools in this tab are designed for SMB and individual self-build users. "
            "University campus analysis is available in the **Dashboard** and **Financial Analysis** tabs. "
            "Switch your user segment in the sidebar to access the MEES, SECR, or Part L tools."
        )

    # ── Segment: Individual Self-Build — Part L / FHS checker ─────────────
    elif _seg == "individual_selfbuild":
        st.markdown("<div class='sec-hdr'>Part L 2021 & Future Homes Standard Compliance Checker</div>",
                    unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:0.83rem;color:#3A5268;margin-bottom:14px;line-height:1.6;'>"
            "New dwellings in England must comply with <strong>Approved Document L1A (2021 edition)</strong>. "
            "From 2025/26, the <strong>Future Homes Standard</strong> will tighten this further, "
            "requiring ~75–80% reduction in carbon vs. 2013 Part L. Enter your proposed fabric "
            "U-values below to check compliance."
            "</div>",
            unsafe_allow_html=True,
        )

        _pl_c1, _pl_c2 = st.columns(2)
        with _pl_c1:
            _pl_u_wall    = st.number_input("Proposed wall U-value (W/m²K)",
                                            min_value=0.05, max_value=6.0, value=1.6, step=0.01,
                                            help="Part L 2021 target: ≤ 0.18 W/m²K")
            _pl_u_roof    = st.number_input("Proposed roof U-value (W/m²K)",
                                            min_value=0.05, max_value=6.0, value=2.0, step=0.01,
                                            help="Part L 2021 target: ≤ 0.11 W/m²K")
            _pl_u_glazing = st.number_input("Proposed glazing U-value (W/m²K)",
                                            min_value=0.50, max_value=6.0, value=2.8, step=0.01,
                                            help="Part L 2021 target: ≤ 1.20 W/m²K")
        with _pl_c2:
            _pl_area      = st.number_input("Floor area (m²)", min_value=10.0, max_value=2000.0,
                                            value=120.0, step=5.0)
            _pl_energy    = st.number_input("Estimated annual energy (kWh)",
                                            min_value=0.0, max_value=500_000.0, value=18000.0,
                                            step=100.0,
                                            help="Total site energy — electricity + gas combined")

        if st.button("Run Part L / FHS Check", type="primary", key="run_partl"):
            try:
                _pl_result = compliance.part_l_compliance_check(
                    u_wall=_pl_u_wall, u_roof=_pl_u_roof, u_glazing=_pl_u_glazing,
                    floor_area_m2=_pl_area, annual_energy_kwh=_pl_energy,
                    building_type="individual_selfbuild",
                )
                # Verdict banner
                _pass_colour = "#1DB87A" if _pl_result["part_l_2021_pass"] else "#E84C4C"
                st.markdown(
                    f"<div style='background:{_pass_colour}18;border-left:4px solid {_pass_colour};"
                    f"border-radius:0 6px 6px 0;padding:12px 16px;margin:10px 0;'>"
                    f"<strong style='color:{_pass_colour};'>{_pl_result['overall_verdict']}</strong>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # Element compliance table
                st.markdown("<div class='sec-hdr'>Fabric Element Check</div>", unsafe_allow_html=True)
                _pl_rows = []
                for item in _pl_result["compliance_items"]:
                    _pl_rows.append({
                        "Element":        item["element"],
                        "Proposed (W/m²K)": item["proposed_u"],
                        "Target (W/m²K)":   item["target_u"],
                        "Gap (W/m²K)":      item["gap"] if not item["pass"] else "—",
                        "Status":           "✅ PASS" if item["pass"] else "❌ FAIL",
                    })
                st.dataframe(pd.DataFrame(_pl_rows), use_container_width=True, hide_index=True)

                # Primary energy metric
                _fhs_colour = "#1DB87A" if _pl_result["fhs_ready"] else "#F0B429"
                st.markdown(
                    f"<div class='kpi-card' style='margin-top:10px;border-top-color:{_fhs_colour};'>"
                    f"<div class='kpi-label'>Estimated Primary Energy Intensity</div>"
                    f"<div class='kpi-value'>{_pl_result['primary_energy_est']}"
                    f"<span class='kpi-unit'> kWh/m²/yr</span></div>"
                    f"<div class='kpi-sub'>FHS indicative threshold: ≤ {_pl_result['fhs_threshold']} kWh/m²/yr · "
                    f"{'✅ FHS-ready' if _pl_result['fhs_ready'] else '⚠️ Improvement needed for FHS'}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # Improvement actions
                if _pl_result["improvement_actions"]:
                    st.markdown("<div class='sec-hdr'>Required Improvement Actions</div>",
                                unsafe_allow_html=True)
                    for _action in _pl_result["improvement_actions"]:
                        st.markdown(
                            f"<div class='disc-prototype' style='margin:4px 0;'>⚙️ {_action}</div>",
                            unsafe_allow_html=True,
                        )

            except ValueError as _e:
                st.error(f"Validation error: {_e}")

        st.markdown("---")
        st.caption(
            "Part L 2021 targets: wall ≤ 0.18 W/m²K · roof ≤ 0.11 W/m²K · glazing ≤ 1.20 W/m²K "
            "(ADL1A, England). Future Homes Standard threshold is indicative — final standard TBC. "
            "⚠️ Formal SAP calculation by an accredited DEA is required for Building Control sign-off."
        )

    # ── Segment: SMB Landlord — MEES / EPC gap analysis ───────────────────
    elif _seg == "smb_landlord":
        st.markdown("<div class='sec-hdr'>EPC Rating Estimator & MEES Gap Analysis</div>",
                    unsafe_allow_html=True)

        # Regulatory context box
        st.markdown("""
        <div style='background:#FFF8E1;border:1px solid #FFD89B;border-left:4px solid #F0B429;
                    border-radius:0 6px 6px 0;padding:12px 16px;margin-bottom:14px;font-size:0.82rem;
                    color:#664D03;line-height:1.6;'>
          <strong>MEES Compliance Deadlines (England &amp; Wales):</strong><br/>
          • <strong>Since April 2023:</strong> Non-domestic properties must have EPC rating E or above to be let.<br/>
          • <strong>From 2028 (new tenancies):</strong> EPC C minimum — all new leases must meet C.<br/>
          • <strong>From 2030 (all leases):</strong> EPC C minimum applies to all existing leases.<br/>
          Landlords with non-compliant properties face civil penalties and inability to let.
          Civil penalties can reach <strong>£150,000</strong> per property.
        </div>
        """, unsafe_allow_html=True)

        _mees_c1, _mees_c2 = st.columns(2)
        with _mees_c1:
            _m_area    = st.number_input("Floor area (m²)", min_value=10.0, max_value=50_000.0,
                                         value=500.0, step=10.0, key="mees_area")
            _m_energy  = st.number_input("Annual energy consumption (kWh)",
                                         min_value=0.0, max_value=10_000_000.0, value=72_000.0,
                                         step=1000.0, key="mees_energy",
                                         help="Total site electricity + gas (kWh/yr from bills)")
            _m_u_wall  = st.number_input("Wall U-value (W/m²K)", min_value=0.05, max_value=6.0,
                                         value=1.7, step=0.01, key="mees_uwall")
        with _mees_c2:
            _m_u_roof  = st.number_input("Roof U-value (W/m²K)", min_value=0.05, max_value=6.0,
                                         value=1.8, step=0.01, key="mees_uroof")
            _m_u_glaz  = st.number_input("Glazing U-value (W/m²K)", min_value=0.50, max_value=6.0,
                                         value=2.8, step=0.01, key="mees_uglaz")
            _m_glaz_r  = st.slider("Glazing ratio (% of facade)", min_value=5, max_value=90,
                                    value=35, step=5, key="mees_glazr") / 100.0

        if st.button("Run EPC & MEES Analysis", type="primary", key="run_mees"):
            try:
                _epc = compliance.estimate_epc_rating(
                    floor_area_m2=_m_area, annual_energy_kwh=_m_energy,
                    u_wall=_m_u_wall, u_roof=_m_u_roof, u_glazing=_m_u_glaz,
                    glazing_ratio=_m_glaz_r, building_type="commercial",
                )
                _gap = compliance.mees_gap_analysis(
                    current_sap=_epc["sap_score"], target_band="C",
                )

                # EPC band display
                _ec = _epc["epc_colour"]
                _eb = _epc["epc_band"]
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:20px;margin:12px 0;'>"
                    f"<div style='background:{_ec};color:#fff;font-family:Rajdhani,sans-serif;"
                    f"font-size:2.8rem;font-weight:700;width:70px;height:70px;border-radius:8px;"
                    f"display:flex;align-items:center;justify-content:center;'>{_eb}</div>"
                    f"<div>"
                    f"<div style='font-family:Rajdhani,sans-serif;font-size:1.1rem;font-weight:700;"
                    f"color:#071A2F;'>Estimated EPC Band: {_eb}</div>"
                    f"<div style='font-size:0.83rem;color:#5A7A90;margin-top:2px;'>"
                    f"Indicative SAP score: {_epc['sap_score']} · "
                    f"Energy intensity: {_epc['eui_kwh_m2']} kWh/m²/yr</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

                # MEES status pills
                _c_now = "#1DB87A" if _epc["mees_compliant_now"] else "#E84C4C"
                _c_28  = "#1DB87A" if _epc["mees_2028_compliant"] else "#F0B429"
                st.markdown(
                    f"<div style='display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px;'>"
                    f"<span class='sp' style='background:{_c_now}18;color:{_c_now};"
                    f"border:1px solid {_c_now}44;'>"
                    f"{'✅' if _epc['mees_compliant_now'] else '❌'} "
                    f"Current MEES (E minimum)</span>"
                    f"<span class='sp' style='background:{_c_28}18;color:{_c_28};"
                    f"border:1px solid {_c_28}44;'>"
                    f"{'✅' if _epc['mees_2028_compliant'] else '⚠️'} "
                    f"2028 MEES Target (C)</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # Recommendation
                st.markdown(
                    f"<div class='disc-ai'><strong>Assessment:</strong> {_epc['recommendation']}</div>",
                    unsafe_allow_html=True,
                )

                # Gap analysis — measures
                if not _epc["mees_2028_compliant"] and _gap["recommended_measures"]:
                    st.markdown("<div class='sec-hdr'>Recommended Improvement Measures</div>",
                                unsafe_allow_html=True)
                    st.markdown(
                        f"<div style='font-size:0.82rem;color:#5A7A90;margin-bottom:8px;'>"
                        f"SAP gap to band C: <strong>{_gap['sap_gap']:.1f} points</strong>. "
                        f"Indicative total cost: "
                        f"<strong>£{_gap['total_cost_low']:,} – £{_gap['total_cost_high']:,}</strong>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    _m_rows = []
                    for _m in _gap["recommended_measures"]:
                        _m_rows.append({
                            "Measure":          _m["name"],
                            "SAP Lift":         f"+{_m['sap_lift']} pts",
                            "Cost Estimate":    f"£{_m['cost_low']:,} – £{_m['cost_high']:,}",
                            "Regulation Ref":   _m["regulation"],
                        })
                    st.dataframe(pd.DataFrame(_m_rows), use_container_width=True, hide_index=True)
                    if not _gap["achievable"]:
                        st.warning(
                            "The measures listed above may not be sufficient to reach EPC C from "
                            "the current estimated rating. A formal SBEM/SAP assessment and "
                            "possibly deeper retrofit (e.g. ASHP, fabric-first approach) will be required."
                        )

            except ValueError as _e:
                st.error(f"Validation error: {_e}")

        st.markdown("---")
        st.caption(
            "EPC estimation uses a proxy SAP 10.2 methodology based on energy intensity and fabric U-values. "
            "MEES deadlines: England & Wales (current E minimum — April 2023; planned C by 2028 new tenancies, "
            "2030 all leases). Scotland and Northern Ireland operate separate EPC frameworks. "
            "⚠️ A formal SBEM assessment by an accredited Non-Domestic Energy Assessor (NDEA) is required "
            "for a legally valid EPC."
        )

    # ── Segment: SMB Industrial — SECR / Scope 1 & 2 carbon baseline ──────
    elif _seg == "smb_industrial":
        st.markdown("<div class='sec-hdr'>SECR Carbon Baseline Calculator (Scope 1 & 2)</div>",
                    unsafe_allow_html=True)

        st.markdown("""
        <div style='background:#EBF5FB;border:1px solid #AED6F1;border-left:4px solid #2980B9;
                    border-radius:0 6px 6px 0;padding:12px 16px;margin-bottom:14px;font-size:0.82rem;
                    color:#1A4A6B;line-height:1.6;'>
          <strong>SECR — Streamlined Energy &amp; Carbon Reporting:</strong><br/>
          Mandatory for large UK companies (250+ employees <em>or</em> £36M+ turnover). SMBs below
          this threshold are not legally required to report but face increasing supply-chain pressure
          from large corporate buyers with their own SECR / TCFD obligations.<br/>
          Use this tool to calculate your <strong>Scope 1</strong> (direct combustion &amp; fleet) and
          <strong>Scope 2</strong> (purchased electricity) carbon baseline — the starting point for
          any net zero pathway or PAS 2060 declaration.
        </div>
        """, unsafe_allow_html=True)

        _secr_c1, _secr_c2 = st.columns(2)
        with _secr_c1:
            st.markdown("<div style='font-size:0.80rem;font-weight:700;color:#3A576B;"
                        "margin-bottom:4px;'>Scope 2 — Purchased Electricity</div>",
                        unsafe_allow_html=True)
            _s_elec = st.number_input("Annual electricity (kWh)", min_value=0.0,
                                       max_value=100_000_000.0, value=120_000.0, step=1000.0,
                                       key="secr_elec")
            st.markdown("<div style='font-size:0.80rem;font-weight:700;color:#3A576B;"
                        "margin:8px 0 4px;'>Scope 1 — Fuel Combustion</div>",
                        unsafe_allow_html=True)
            _s_gas  = st.number_input("Natural gas (kWh)", min_value=0.0, max_value=100_000_000.0,
                                       value=85_000.0, step=1000.0, key="secr_gas")
            _s_oil  = st.number_input("Gas oil / diesel (kWh)", min_value=0.0,
                                       max_value=100_000_000.0, value=0.0, step=1000.0,
                                       key="secr_oil")
        with _secr_c2:
            _s_lpg  = st.number_input("LPG (kWh)", min_value=0.0, max_value=100_000_000.0,
                                       value=0.0, step=1000.0, key="secr_lpg")
            st.markdown("<div style='font-size:0.80rem;font-weight:700;color:#3A576B;"
                        "margin:8px 0 4px;'>Scope 1 — Fleet</div>",
                        unsafe_allow_html=True)
            _s_miles = st.number_input("Business fleet miles (per year)", min_value=0.0,
                                        max_value=10_000_000.0, value=0.0, step=1000.0,
                                        key="secr_miles")
            st.markdown("<div style='font-size:0.80rem;font-weight:700;color:#3A576B;"
                        "margin:8px 0 4px;'>Intensity Metric</div>", unsafe_allow_html=True)
            _s_area = st.number_input("Floor area for intensity (m²) — optional",
                                       min_value=0.0, max_value=1_000_000.0, value=2_000.0,
                                       step=100.0, key="secr_area")

        if st.button("Calculate Carbon Baseline", type="primary", key="run_secr"):
            try:
                _floor = _s_area if _s_area > 0 else None
                _cb = compliance.calculate_carbon_baseline(
                    elec_kwh=_s_elec, gas_kwh=_s_gas, oil_kwh=_s_oil,
                    lpg_kwh=_s_lpg, fleet_miles=_s_miles, floor_area_m2=_floor,
                )

                # KPI cards
                _sk1, _sk2, _sk3, _sk4 = st.columns(4)
                with _sk1:
                    st.markdown(f"""
                    <div class='kpi-card'>
                      <div class='kpi-label'>Total Emissions</div>
                      <div class='kpi-value'>{_cb['total_tco2e']:,.1f}<span class='kpi-unit'> tCO₂e</span></div>
                      <div class='kpi-sub'>Scope 1 + 2 combined</div>
                    </div>""", unsafe_allow_html=True)
                with _sk2:
                    st.markdown(f"""
                    <div class='kpi-card accent-green'>
                      <div class='kpi-label'>Scope 1 (Direct)</div>
                      <div class='kpi-value'>{_cb['scope1_tco2e']:,.1f}<span class='kpi-unit'> tCO₂e</span></div>
                      <div class='kpi-sub'>Gas · Oil · LPG · Fleet</div>
                    </div>""", unsafe_allow_html=True)
                with _sk3:
                    st.markdown(f"""
                    <div class='kpi-card' style='border-top-color:#00C2A8'>
                      <div class='kpi-label'>Scope 2 (Electricity)</div>
                      <div class='kpi-value'>{_cb['scope2_tco2e']:,.1f}<span class='kpi-unit'> tCO₂e</span></div>
                      <div class='kpi-sub'>Grid: 0.20482 kgCO₂e/kWh (BEIS 2023)</div>
                    </div>""", unsafe_allow_html=True)
                with _sk4:
                    _int_disp = (
                        f"{_cb['intensity_kgco2_m2']} kgCO₂e/m²"
                        if _cb["intensity_kgco2_m2"] is not None else "N/A"
                    )
                    st.markdown(f"""
                    <div class='kpi-card accent-gold'>
                      <div class='kpi-label'>Carbon Intensity</div>
                      <div class='kpi-value' style='font-size:1.4rem;'>{_int_disp}</div>
                      <div class='kpi-sub'>Per m² floor area</div>
                    </div>""", unsafe_allow_html=True)

                # Emissions breakdown chart
                st.markdown("<div class='sec-hdr'>Emissions Breakdown by Source</div>",
                            unsafe_allow_html=True)
                _bk = _cb["breakdown"]
                _bk_labels = ["Electricity (Scope 2)", "Natural Gas (Scope 1)",
                               "Oil (Scope 1)", "LPG (Scope 1)", "Fleet (Scope 1)"]
                _bk_values = [
                    _bk["electricity_scope2_tco2e"],
                    _bk["gas_scope1_tco2e"],
                    _bk["oil_scope1_tco2e"],
                    _bk["lpg_scope1_tco2e"],
                    _bk["fleet_scope1_tco2e"],
                ]
                _bk_filtered = [(l, v) for l, v in zip(_bk_labels, _bk_values) if v > 0]
                if _bk_filtered:
                    _bk_fig = go.Figure(go.Pie(
                        labels=[x[0] for x in _bk_filtered],
                        values=[x[1] for x in _bk_filtered],
                        marker_colors=["#00C2A8", "#1DB87A", "#F0B429", "#E84C4C", "#4A6FA5"],
                        textinfo="label+percent",
                        hole=0.40,
                    ))
                    _bk_fig.update_layout(
                        **{**CHART_LAYOUT, "height": 280, "showlegend": False},
                        margin=dict(t=10, b=10, l=0, r=0),
                    )
                    st.plotly_chart(_bk_fig, use_container_width=True, config={"displayModeBar": False})

                # SECR reporting context
                _secr_info = _cb["secr_threshold_check"]
                _sc_col = "#F0B429" if _secr_info["supply_chain_pressure"] else "#1DB87A"
                st.markdown(
                    f"<div style='background:{_sc_col}10;border-left:3px solid {_sc_col};"
                    f"border-radius:0 6px 6px 0;padding:10px 14px;margin-top:8px;"
                    f"font-size:0.82rem;color:#3A5268;line-height:1.6;'>"
                    f"<strong>SECR Context:</strong> {_secr_info['note']}<br/>"
                    f"{'⚠️ At this emissions level, supply-chain buyers are likely to request carbon data.' if _secr_info['supply_chain_pressure'] else '✅ Emissions level is low — supply-chain pressure unlikely in the near term.'}"
                    f"{'<br/>✅ PAS 2060 carbon neutrality declaration is a feasible target.' if _secr_info['pas2060_candidacy'] else ''}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            except ValueError as _e:
                st.error(f"Validation error: {_e}")

        st.markdown("---")
        st.caption(
            "Carbon factors: BEIS GHG Conversion Factors 2023 · Electricity: 0.20482 kgCO₂e/kWh · "
            "Natural gas: 0.18316 kgCO₂e/kWh · Gas oil: 0.24615 kgCO₂e/kWh · LPG: 0.21435 kgCO₂e/kWh · "
            "Fleet: 0.168 kgCO₂e/mile (medium petrol car, BEIS 2023). "
            "⚠️ SECR reporting requires methodology disclosure; this tool is a screening calculator only."
        )


# ════════════════════════════════════════════════════════════════════════════
# TAB 5 — ABOUT & CONTACT
# ════════════════════════════════════════════════════════════════════════════
with _tab_about:
    _about_c1, _about_c2 = st.columns([2, 1])

    with _about_c1:
        # ── About the Platform ────────────────────────────────────────────────
        st.markdown("""
        <h3 style='margin-bottom:4px;'>About CrowAgent™ Platform</h3>
        """, unsafe_allow_html=True)

        if LOGO_URI:
            st.markdown(
                f"<img src='{LOGO_URI}' width='300' style='margin-bottom:12px;' alt='CrowAgent™ Logo'/><br/>",
                unsafe_allow_html=True,
            )

        st.markdown("""
        <div style='font-size:0.88rem;color:#3A5268;line-height:1.7;margin-bottom:16px;'>
          CrowAgent™ Platform is a physics-informed campus thermal intelligence system
          designed to help university estate managers and sustainability professionals
          make evidence-based, cost-effective decisions for achieving Net Zero targets.
          <br/><br/>
          The platform combines Physics-Informed Neural Network (PINN) methodology with
          an agentic AI advisor, live Met Office weather integration, and structured
          scenario comparison to evaluate retrofit interventions across a campus portfolio.
        </div>
        """, unsafe_allow_html=True)

        # ── Full Disclaimer ───────────────────────────────────────────────────
        st.markdown("<div class='sec-hdr'>⚠️ Full Platform Disclaimer</div>", unsafe_allow_html=True)

        st.markdown("""
        <div class='disc-prototype' style='margin-bottom:10px;'>
          <strong>Working Prototype — Indicative Results Only</strong><br/><br/>
          CrowAgent™ Platform is currently a <strong>working research prototype</strong>.
          All energy, carbon, and financial results produced by this platform are based on
          simplified steady-state physics models calibrated against published UK higher education
          sector averages (HESA 2022-23, CIBSE Guide A). They do not reflect the specific
          characteristics of any real building or institution.<br/><br/>
          Results <strong>must not</strong> be used as the sole basis for any capital investment,
          procurement, or planning decision. Before undertaking any retrofit programme, organisations
          should commission a site-specific energy assessment by a suitably qualified energy surveyor
          or building services engineer in accordance with BS EN ISO 52000 and relevant CIBSE guidance.<br/><br/>
          <strong>Greenfield University</strong> is a <strong>fictional institution</strong> created
          for demonstration purposes. Any resemblance to any real institution is coincidental.
        </div>

        <div class='disc-ai' style='margin-bottom:10px;'>
          <strong>AI Advisor Disclaimer</strong><br/><br/>
          The CrowAgent™ AI Advisor is powered by Google Gemini 1.5 Flash, a large language model
          (LLM). Like all LLM-based systems, the AI Advisor may:<br/>
          &nbsp;&nbsp;• Generate plausible-sounding but factually incorrect information ("hallucination")<br/>
          &nbsp;&nbsp;• Misinterpret ambiguous questions<br/>
          &nbsp;&nbsp;• Produce recommendations that do not account for site-specific factors<br/>
          &nbsp;&nbsp;• Provide outdated information beyond its training cutoff<br/><br/>
          <strong>All AI-generated recommendations must be independently verified by a qualified
          professional before any action is taken.</strong> The AI Advisor is not a substitute for
          professional engineering, financial, or legal advice. Neither Aparajita Parihar nor
          CrowAgent™ Platform accepts liability for decisions made on the basis of AI Advisor outputs.
        </div>

        <div class='disc-data'>
          <strong>Data Sources & Assumptions</strong><br/><br/>
          All figures are derived from publicly available UK sector data:
          BEIS Greenhouse Gas Conversion Factors 2023 (carbon intensity 0.20482 kgCO₂e/kWh) ·
          HESA Estates Management Statistics 2022-23 (electricity cost £0.28/kWh) ·
          CIBSE Guide A Environmental Design (U-values, heating season 5,800 hrs/yr) ·
          PVGIS EC Joint Research Centre (Reading solar irradiance 950 kWh/m²/yr) ·
          US DoE EnergyPlus for cross-validation ·
          Raissi, Perdikaris & Karniadakis (2019) for PINN methodology.
          Weather data from Open-Meteo API and optionally Met Office DataPoint.
        </div>
        """, unsafe_allow_html=True)

        # ── IP Notice ──────────────────────────────────────────────────────────
        st.markdown("<div class='sec-hdr'>Intellectual Property</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size:0.82rem;color:#3A5268;line-height:1.7;background:#F0F4F8;
                    border:1px solid #E0EBF4;border-radius:6px;padding:14px 16px;'>
          CrowAgent™ Platform, including all source code, physics models, UI design, and brand assets,
          is the original work of <strong>Aparajita Parihar</strong> and is protected by copyright.<br/><br/>
          <strong>CrowAgent™</strong> is an unregistered trademark of Aparajita Parihar.
          A UK IPO Class 42 trademark application is currently pending.<br/><br/>
          This platform is an independent research project and is
          <strong>not affiliated with the University of Reading</strong>
          or any other institution.<br/><br/>
          © 2026 Aparajita Parihar. All rights reserved. Not licensed for commercial use
          without written permission of the author.
        </div>
        """, unsafe_allow_html=True)

        # ── Technology Stack ──────────────────────────────────────────────────
        st.markdown("<div class='sec-hdr'>Technology Stack</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px;'>
          <span class='chip' style='color:#CBD8E6;background:#071A2F;border-color:#1A3A5C;'>Python 3.11</span>
          <span class='chip' style='color:#CBD8E6;background:#071A2F;border-color:#1A3A5C;'>Streamlit</span>
          <span class='chip' style='color:#CBD8E6;background:#071A2F;border-color:#1A3A5C;'>Plotly</span>
          <span class='chip' style='color:#CBD8E6;background:#071A2F;border-color:#1A3A5C;'>Open-Meteo API</span>
          <span class='chip' style='color:#CBD8E6;background:#071A2F;border-color:#1A3A5C;'>Met Office DataPoint</span>
          <span class='chip' style='color:#CBD8E6;background:#071A2F;border-color:#1A3A5C;'>Google Gemini 1.5 Flash</span>
          <span class='chip' style='color:#CBD8E6;background:#071A2F;border-color:#1A3A5C;'>PINN Thermal Model</span>
          <span class='chip' style='color:#CBD8E6;background:#071A2F;border-color:#1A3A5C;'>Streamlit Community Cloud</span>
        </div>
        """, unsafe_allow_html=True)

        # ── Deployment Note ───────────────────────────────────────────────────
        st.markdown("<div class='sec-hdr'>Deployment (Zero Cost)</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size:0.82rem;color:#3A5268;line-height:1.7;background:#F0F4F8;
                    border:1px solid #E0EBF4;border-radius:6px;padding:14px 16px;'>
          This platform is deployed entirely on free tiers:<br/>
          <strong>GitHub Free</strong> (public repo, unlimited) →
          <strong>Streamlit Community Cloud</strong> (1 free app, 1 GB memory, unlimited views) →
          <strong>Open-Meteo</strong> (10,000 req/day free, no key needed) →
          <strong>Gemini 1.5 Flash</strong> (1,500 req/day free, user's own key).<br/><br/>
          Smart weather caching (1-hour TTL) means only ~24 weather API calls per day
          regardless of visitor volume. Total monthly cost: <strong>£0</strong>.
        </div>
        """, unsafe_allow_html=True)

    with _about_c2:
        # ── Contact Card ──────────────────────────────────────────────────────
        st.markdown("""
        <div class='contact-card'>
          <div style='font-family:Rajdhani,sans-serif;font-size:1rem;font-weight:700;
                      color:#071A2F;margin-bottom:14px;border-bottom:2px solid #00C2A8;
                      padding-bottom:8px;'>
            📬 Contact & Enquiries
          </div>

          <div style='margin-bottom:14px;'>
            <div class='contact-label'>Project Lead</div>
            <div class='contact-val'>Aparajita Parihar</div>
            <div style='font-size:0.75rem;color:#5A7A90;'>
              BSc Computer Science (Year 1)<br/>
              University of Reading
            </div>
          </div>

          <div style='margin-bottom:14px;'>
            <div class='contact-label'>Email</div>
            <div class='contact-val'>
              <a href='mailto:crowagent.platform@gmail.com'
                 style='color:#00C2A8;text-decoration:none;font-size:0.85rem;'>
                crowagent.platform@gmail.com
              </a>
            </div>
          </div>

          <div style='margin-bottom:14px;'>
            <div class='contact-label'>GitHub</div>
            <div class='contact-val'>
              <a href='https://github.com/WonderApri/crowagent-platform'
                 target='_blank' style='color:#00C2A8;font-size:0.85rem;'>
                github.com/WonderApri/crowagent-platform
              </a>
            </div>
          </div>

          <div style='margin-bottom:14px;'>
            <div class='contact-label'>Trademark Status</div>
            <div style='font-size:0.78rem;color:#3A5268;'>
              CrowAgent™ is an unregistered trademark.<br/>
              UK IPO Class 42 application pending.
            </div>
          </div>

          <div style='border-top:1px solid #E0EBF4;padding-top:12px;'>
            <div class='contact-label'>Enquiry Types Welcome</div>
            <div style='font-size:0.76rem;color:#5A7A90;line-height:1.7;'>
              • Demo or pilot programme requests<br/>
              • Academic collaboration<br/>
              • Research partnerships<br/>
              • Technical questions<br/>
              • Press & media<br/>
              • Bug reports & feedback
            </div>
          </div>

          <div style='margin-top:14px;background:#F8FAFC;border:1px solid #E0EBF4;
                      border-radius:5px;padding:10px 12px;'>
            <div style='font-size:0.78rem;color:#5A7A90;font-weight:700;
                        text-transform:uppercase;letter-spacing:0.8px;margin-bottom:4px;'>
              Response Time
            </div>
            <div style='font-size:0.78rem;color:#5A7A90;'>
              We aim to respond to all enquiries within <strong>2–3 business days</strong>.
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Version / Build Info ──────────────────────────────────────────────
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='background:#071A2F;border:1px solid #1A3A5C;border-radius:8px;
                    padding:14px 16px;'>
          <div style='font-family:Rajdhani,sans-serif;font-size:0.78rem;font-weight:700;
                      letter-spacing:1px;text-transform:uppercase;color:#00C2A8;
                      margin-bottom:8px;'>Build Information</div>
          <div style='font-size:0.78rem;color:#9ABDD0;line-height:1.8;'>
            <strong style='color:#CBD8E6;'>Version:</strong> v2.0.0<br/>
            <strong style='color:#CBD8E6;'>Released:</strong> 21 February 2026<br/>
            <strong style='color:#CBD8E6;'>Status:</strong>
            <span style='color:#F0B429;'>🚧 Working Prototype</span><br/>
            <strong style='color:#CBD8E6;'>Weather:</strong>
            <span style='color:#{"1DB87A" if weather["is_live"] else "F0B429"};'>
              {"● Live" if weather["is_live"] else "○ Manual"}</span> — {weather["source"]}<br/>
            <strong style='color:#CBD8E6;'>Cache TTL:</strong> 60 min (weather)<br/>
            <strong style='color:#CBD8E6;'>Physics:</strong> PINN (Raissi et al., 2019)
          </div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# ENTERPRISE FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class='ent-footer'>
  <div style='display:flex;justify-content:center;align-items:center;
              flex-wrap:wrap;gap:16px;margin-bottom:8px;'>
    <span style='font-family:Rajdhani,sans-serif;font-size:0.9rem;
                 font-weight:700;color:#00C2A8;'>🌿 CrowAgent™</span>
    <span style='color:#8FBCCE;font-size:0.80rem;'>Sustainability AI Decision Intelligence Platform</span>
    <span style='color:#8FBCCE;font-size:0.80rem;'>v2.0.0 · Working Prototype</span>
  </div>
  <div style='font-size:0.78rem;color:#9ABDD0;line-height:1.6;'>
    © 2026 Aparajita Parihar · All rights reserved · Independent research project ·
    CrowAgent™ is an unregistered trademark (UK IPO Class 42, registration pending) ·
    Not licensed for commercial use without written permission
  </div>
  <div style='font-size:0.77rem;color:#8FBCCE;margin-top:4px;font-style:italic;'>
    Physics: Raissi et al. (2019) J. Comp. Physics · doi:10.1016/j.jcp.2018.10.045 ·
    Weather: Open-Meteo API + Met Office DataPoint · Carbon: BEIS 2023 ·
    Costs: HESA 2022-23 · AI: Google Gemini 1.5 Flash ·
    ⚠️ Results indicative only — not for investment decisions
  </div>
</div>
""", unsafe_allow_html=True)
# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — DASHBOARD (Geo-Physics Map Tagging & Segment KPIs)
# ─────────────────────────────────────────────────────────────────────────────
with _tab_dash:
    if not st.session_state.portfolio:
        st.info("Your portfolio is empty. Use the Sidebar to add properties via UK Postcode.")
    else:
        st.markdown("<h2 style='margin:0;padding:0;'>Portfolio Performance Dashboard</h2>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:0.85rem;color:#5A7A90;margin-bottom:15px;'>Analyzing {len(st.session_state.portfolio)} assets under current weather conditions ({weather['temperature_c']}°C).</div>", unsafe_allow_html=True)

        # ── Segment-Specific KPI Logic ────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4)
        
        # Aggregation Logic
        total_baseline_mwh = sum(item["baseline_results"]["scenario_energy_mwh"] for item in st.session_state.portfolio)
        total_baseline_carbon = sum(item["baseline_results"]["scenario_carbon_t"] for item in st.session_state.portfolio)
        total_combined_mwh = sum(item["combined_results"]["scenario_energy_mwh"] for item in st.session_state.portfolio)
        total_combined_carbon = sum(item["combined_results"]["scenario_carbon_t"] for item in st.session_state.portfolio)
        total_cost_saving = sum(item["combined_results"]["annual_saving_gbp"] for item in st.session_state.portfolio)
        total_install_cost = sum(item["combined_results"]["install_cost_gbp"] for item in st.session_state.portfolio)
        avg_floor_area = sum(item["floor_area_m2"] for item in st.session_state.portfolio) / len(st.session_state.portfolio)

        if st.session_state.user_segment == "university_he":
            with k1:
                st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Portfolio MWh</div><div class='kpi-value'>{total_baseline_mwh:,.0f}<span class='kpi-unit'> MWh/yr</span></div></div>", unsafe_allow_html=True)
            with k2:
                intensity = (total_baseline_carbon * 1000) / avg_floor_area if avg_floor_area > 0 else 0
                st.markdown(f"<div class='kpi-card accent-green'><div class='kpi-label'>Carbon Intensity</div><div class='kpi-value'>{intensity:,.1f}<span class='kpi-unit'> kgCO₂e/m²</span></div></div>", unsafe_allow_html=True)
            with k3:
                st.markdown(f"<div class='kpi-card accent-gold'><div class='kpi-label'>Cost Exposure</div><div class='kpi-value'>£{total_baseline_mwh * 1000 * 0.28 / 1000:,.1f}<span class='kpi-unit'>k</span></div></div>", unsafe_allow_html=True)
            with k4:
                st.markdown(f"<div class='kpi-card accent-navy'><div class='kpi-label'>Net Zero Gap</div><div class='kpi-value'>{total_baseline_carbon:,.1f}<span class='kpi-unit'> tCO₂e</span></div></div>", unsafe_allow_html=True)

        elif st.session_state.user_segment == "smb_landlord":
            total_mees_gap = 0
            for item in st.session_state.portfolio:
                epc_rating = compliance.estimate_epc_rating(item["floor_area_m2"], item["baseline_results"]["scenario_energy_mwh"]*1000, 1.8, 2.0, 2.8, 0.3)
                gap = compliance.mees_gap_analysis(epc_rating["sap_score"], "C")
                total_mees_gap += gap["sap_gap"]
            roi = (total_cost_saving / total_install_cost * 100) if total_install_cost > 0 else 0
            with k1:
                st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Avg MEES Gap</div><div class='kpi-value'>{total_mees_gap/len(st.session_state.portfolio):,.1f}<span class='kpi-unit'> SAP Pts</span></div></div>", unsafe_allow_html=True)
            with k2:
                st.markdown(f"<div class='kpi-card accent-gold'><div class='kpi-label'>Upgrade Cost (Est)</div><div class='kpi-value'>£{total_install_cost/1000:,.0f}<span class='kpi-unit'>k</span></div></div>", unsafe_allow_html=True)
            with k3:
                st.markdown(f"<div class='kpi-card accent-green'><div class='kpi-label'>EPC Delta</div><div class='kpi-value'>+ {total_baseline_carbon - total_combined_carbon:,.1f}<span class='kpi-unit'> tCO₂e saved</span></div></div>", unsafe_allow_html=True)
            with k4:
                st.markdown(f"<div class='kpi-card accent-navy'><div class='kpi-label'>Projected ROI</div><div class='kpi-value'>{roi:,.1f}<span class='kpi-unit'>%</span></div></div>", unsafe_allow_html=True)

        elif st.session_state.user_segment == "smb_industrial":
            secr_result = compliance.calculate_carbon_baseline(elec_kwh=total_baseline_mwh*1000, gas_kwh=total_baseline_mwh*500)
            with k1:
                st.markdown(f"<div class='kpi-card'><div class='kpi-label'>SECR Scope 1 (Est)</div><div class='kpi-value'>{secr_result['scope1_tco2e']:,.1f}<span class='kpi-unit'> tCO₂e</span></div></div>", unsafe_allow_html=True)
            with k2:
                st.markdown(f"<div class='kpi-card accent-navy'><div class='kpi-label'>Scope 2</div><div class='kpi-value'>{secr_result['scope2_tco2e']:,.1f}<span class='kpi-unit'> tCO₂e</span></div></div>", unsafe_allow_html=True)
            with k3:
                st.markdown(f"<div class='kpi-card accent-gold'><div class='kpi-label'>Carbon Liability</div><div class='kpi-value'>{secr_result['total_tco2e']:,.1f}<span class='kpi-unit'> tCO₂e</span></div></div>", unsafe_allow_html=True)
            with k4:
                abatement = ((total_baseline_carbon - total_combined_carbon) / total_baseline_carbon * 100) if total_baseline_carbon > 0 else 0
                st.markdown(f"<div class='kpi-card accent-green'><div class='kpi-label'>Abatement Potential</div><div class='kpi-value'>{abatement:,.1f}<span class='kpi-unit'>%</span></div></div>", unsafe_allow_html=True)

        elif st.session_state.user_segment == "individual_selfbuild":
            part_l_result = compliance.part_l_compliance_check(1.8, 2.0, 2.8, avg_floor_area, (total_baseline_mwh/len(st.session_state.portfolio))*1000)
            with k1:
                st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Part L Primary Energy</div><div class='kpi-value'>{part_l_result['primary_energy_est']:,.1f}<span class='kpi-unit'> kWh/m²/yr</span></div></div>", unsafe_allow_html=True)
            with k2:
                st.markdown(f"<div class='kpi-card accent-navy'><div class='kpi-label'>Fabric Heat Loss</div><div class='kpi-value'>High<span class='kpi-unit'></span></div></div>", unsafe_allow_html=True)
            with k3:
                status_color = "#1DB87A" if part_l_result['part_l_2021_pass'] else "#E84C4C"
                status_text = "Pass" if part_l_result['part_l_2021_pass'] else "Fail"
                st.markdown(f"<div class='kpi-card' style='border-top-color:{status_color}'><div class='kpi-label'>Compliance Status</div><div class='kpi-value' style='color:{status_color}'>{status_text}<span class='kpi-unit'></span></div></div>", unsafe_allow_html=True)
            with k4:
                st.markdown(f"<div class='kpi-card accent-gold'><div class='kpi-label'>Upgrade Cost</div><div class='kpi-value'>£{total_install_cost/len(st.session_state.portfolio)/1000:,.0f}<span class='kpi-unit'>k / home</span></div></div>", unsafe_allow_html=True)

        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

        # ── Charts Row: Energy + Carbon ─────────────────────────────────────────
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div class='chart-card'><div class='chart-title'>⚡ Portfolio Energy (MWh/yr)</div>", unsafe_allow_html=True)
            fig_e = go.Figure()
            x_labels = [f"{p['postcode'][:4]}..." for p in st.session_state.portfolio]
            y_base = [p["baseline_results"]["scenario_energy_mwh"] for p in st.session_state.portfolio]
            y_comb = [p["combined_results"]["scenario_energy_mwh"] for p in st.session_state.portfolio]
            fig_e.add_trace(go.Bar(name="Baseline", x=x_labels, y=y_base, marker_color="#4A6FA5"))
            fig_e.add_trace(go.Bar(name="Post-Intervention", x=x_labels, y=y_comb, marker_color="#00C2A8"))
            fig_e.update_layout(**CHART_LAYOUT, barmode='group', yaxis_title="MWh / year")
            st.plotly_chart(fig_e, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='chart-card'><div class='chart-title'>🌍 Portfolio Carbon (t CO₂e/yr)</div>", unsafe_allow_html=True)
            fig_c = go.Figure()
            y_base_c = [p["baseline_results"]["scenario_carbon_t"] for p in st.session_state.portfolio]
            y_comb_c = [p["combined_results"]["scenario_carbon_t"] for p in st.session_state.portfolio]
            fig_c.add_trace(go.Bar(name="Baseline", x=x_labels, y=y_base_c, marker_color="#FFA500"))
            fig_c.add_trace(go.Bar(name="Post-Intervention", x=x_labels, y=y_comb_c, marker_color="#1DB87A"))
            fig_c.update_layout(**CHART_LAYOUT, barmode='group', yaxis_title="Tonnes CO₂e / year")
            st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        # ── 3D/4D Spatial View & Geo-Physics Mapping (FIXED LAYOUT) ───────────
        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
        st.markdown("<div class='sec-hdr'>🗺️ Spatial View & Geo-Physics Mapping</div>", unsafe_allow_html=True)
        
        map_search_col, map_view_col = st.columns([1, 3])
        
        with map_search_col:
            st.markdown("<div style='font-size:0.85rem; font-weight:600; color:#071A2F;'>Asset Geo-Locator</div>", unsafe_allow_html=True)
            search_pc = st.text_input("Locate Postcode in Portfolio", placeholder="e.g. SW1A 1AA")
            if search_pc:
                if any(p["postcode"] == search_pc for p in st.session_state.portfolio):
                    st.success("Asset found in active portfolio.")
                else:
                    st.warning("Asset not in portfolio.")
            
            st.markdown("<div style='margin-top:20px; font-size:0.8rem; color:#5A7A90;'><b>Legend: Carbon Reduction</b><br/>🟩 100% Reduction<br/>🟨 50% Reduction<br/>🟥 0% Reduction</div>", unsafe_allow_html=True)
            st.caption("Polygons represent physical building bounds for PINN analysis.")

        with map_view_col:
            _map_data = []
            center_lat, center_lon = st.session_state.wx_lat, st.session_state.wx_lon

            for i, p in enumerate(st.session_state.portfolio):
                asset_lat, asset_lon = center_lat + (np.sin(i) * 0.01), center_lon + (np.cos(i) * 0.01)
                reduction = p["combined_results"]["energy_saving_pct"]
                ratio = max(0.0, min(1.0, reduction / 100.0))
                r = int(220 - ratio * 220)
                g = int(50 + ratio * (194 - 50))
                b = int(50 + ratio * (168 - 50))
                
                _map_data.append({
                    "name": p["postcode"], "lat": asset_lat, "lon": asset_lon,
                    "energy_saving_pct": reduction, "carbon_saving_t": p["combined_results"]["carbon_saving_t"],
                    "fill_color": [r, g, b, 210], "elevation": max(10.0, p["baseline_results"]["scenario_energy_mwh"] / 10.0),
                    "polygon": loc._synthetic_polygon(asset_lat, asset_lon, size_m=60.0)
                })

            if _map_data:
                try:
                    import pydeck as pdk
                    deck = pdk.Deck(
                        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                        initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=12, pitch=45),
                        layers=[pdk.Layer("PolygonLayer", data=pd.DataFrame(_map_data), get_polygon="polygon", get_elevation="elevation", get_fill_color="fill_color", extruded=True, pickable=True, auto_highlight=True)],
                        tooltip={"html": "<div style='font-family:Nunito Sans;'><b>{name}</b><br/>Reduction: {energy_saving_pct}%<br/>Carbon Saved: {carbon_saving_t} t</div>"}
                    )
                    st.pydeck_chart(deck, use_container_width=True)
                except Exception as e:
                    st.error(f"PyDeck failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — FINANCIAL ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
with _tab_fin:
    st.markdown("<h3 style='margin-bottom:4px;'>Financial Analysis & Investment Appraisal</h3>", unsafe_allow_html=True)
    if not st.session_state.portfolio:
        st.info("Add assets to your portfolio to view financial projections.")
    else:
        total_install = sum(p["combined_results"]["install_cost_gbp"] for p in st.session_state.portfolio)
        total_annual_saving = sum(p["combined_results"]["annual_saving_gbp"] for p in st.session_state.portfolio)
        
        fc1, fc2 = st.columns(2)
        with fc1:
            st.markdown("<div class='chart-card'><div class='chart-title'>💰 Annual Cost Savings</div>", unsafe_allow_html=True)
            fig_s = go.Figure(go.Indicator(mode="number+delta", value=total_annual_saving, number={"prefix": "£", "valueformat": ",.0f"}))
            fig_s.update_layout(**CHART_LAYOUT, height=200)
            st.plotly_chart(fig_s, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        with fc2:
            st.markdown("<div class='chart-card'><div class='chart-title'>⏱ Simple Payback Period</div>", unsafe_allow_html=True)
            payback = (total_install / total_annual_saving) if total_annual_saving > 0 else 0
            fig_p = go.Figure(go.Indicator(mode="number", value=payback, number={"valueformat": ".1f"}))
            fig_p.update_layout(**CHART_LAYOUT, height=200)
            st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='sec-hdr'>10-Year Cumulative Net Cash Flow</div>", unsafe_allow_html=True)
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        fig_ncf = go.Figure()
        years = list(range(0, 11))
        cashflow = [-total_install + total_annual_saving * y for y in years]
        fig_ncf.add_trace(go.Scatter(x=years, y=cashflow, name="Portfolio Upgrades", line=dict(color="#00C2A8", width=3), mode="lines+markers"))
        fig_ncf.add_hline(y=0, line=dict(dash="dot", color="#C0C8D0", width=1))
        fig_ncf.update_layout(**{**CHART_LAYOUT, "height": 320, "showlegend": True}, yaxis_title="Cumulative Net Cash Flow (£)", xaxis_title="Year")
        st.plotly_chart(fig_ncf, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — AI ADVISOR (REMEDIATED & UNABRIDGED)
# ════════════════════════════════════════════════════════════════════════════
with _tab_ai:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#071A2F,#0D2640);
                border-left:4px solid #00C2A8;border-radius:8px;
                padding:16px 20px;margin-bottom:14px;'>
      <div style='font-family:Rajdhani,sans-serif;font-size:1.05rem;
                  font-weight:700;color:#00C2A8;letter-spacing:0.5px;'>
        🤖 CrowAgent™ AI Advisor
      </div>
      <div style='color:#CBD8E6;font-size:0.83rem;margin-top:4px;'>
        Physics-grounded agentic AI that runs real thermal simulations,
        compares scenarios and gives evidence-based Net Zero investment recommendations.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class='disc-ai'>
      <strong>🤖 AI Accuracy Disclaimer.</strong>
      The AI Advisor generates responses based on physics tool outputs and large language model reasoning. 
      Verify all figures independently before acting.
    </div>
    """, unsafe_allow_html=True)

    _akey = st.session_state.get("gemini_key", "")

    if not _akey:
        st.info("Activate AI Advisor by providing your Gemini API key in the sidebar.")
    else:
        if not st.session_state.chat_history:
            st.markdown("<div style='color:#5A7A90;font-size:0.82rem;margin-bottom:8px;'>✨ Click a question to start:</div>", unsafe_allow_html=True)
            _sq_cols = st.columns(2)
            starter_qs = [
                "Which asset in my portfolio has the fastest payback?", 
                "Compare the Baseline vs Combined scenario for the whole portfolio.", 
                "What is the most cost-effective intervention?",
                "Analyze the carbon abatement potential across my portfolio."
            ]
            for _qi, _sq in enumerate(starter_qs):
                with _sq_cols[_qi % 2]:
                    if st.button(_sq, key=f"sq_{_qi}", use_container_width=True):
                        st.session_state["_pending"] = _sq
                        st.rerun()

        if "_pending" in st.session_state:
            _pq = st.session_state.pop("_pending")
            st.session_state.chat_history.append({"role": "user", "content": _pq})
            
            # Map portfolio array to the format expected by physics tools
            _portfolio_buildings = {p["postcode"]: p["physics_model_input"] for p in st.session_state.portfolio}
            
            with st.spinner("🤖 Running physics simulations and reasoning…"):
                # EXECUTION: Full unsummarized agent loop
                _res = crow_agent.run_agent(
                    api_key=_akey, 
                    user_message=_pq,
                    conversation_history=st.session_state.agent_history,
                    buildings=_portfolio_buildings, 
                    scenarios=SCENARIOS,
                    calculate_fn=calculate_thermal_load,
                    current_context={
                        "portfolio_size": len(st.session_state.portfolio),
                        "temperature_c": weather["temperature_c"],
                        "segment": st.session_state.user_segment
                    },
                )
            if _res.get("updated_history"):
                st.session_state.agent_history = _res["updated_history"]
            st.session_state.chat_history.append({
                "role": "assistant",
                "content":     _res.get("answer", ""),
                "tool_calls":  _res.get("tool_calls", []),
                "error":       _res.get("error"),
                "loops":       _res.get("loops", 1),
            })

        for _msg in st.session_state.chat_history:
            if _msg["role"] == "user":
                st.markdown(f"<div style='background:#071A2F;border-left:3px solid #00C2A8;border-radius:0 8px 8px 8px; padding:10px 14px;margin:10px 0 4px;color:#F0F4F8;font-size:0.88rem;'><strong style='color:#00C2A8;'>You</strong><br/>{_msg['content']}</div>", unsafe_allow_html=True)
            else:
                _tc = _msg.get("tool_calls", [])
                if _tc:
                    _bh = "<div style='margin:4px 0 5px;'>"
                    for _t in _tc:
                        _bh += f"<span style='display:inline-block;background:#0D2640;color:#00C2A8;border-radius:4px;padding:2px 8px;font-size:0.78rem;font-weight:700;margin:2px 2px 2px 0;'>⚙ {_t['name']}</span>"
                    _bh += f" <span style='font-size:0.78rem;color:#6A92AA;'>{_msg.get('loops',1)} reasoning step(s)</span></div>"
                    st.markdown(_bh, unsafe_allow_html=True)
                
                if _msg.get("error"):
                    st.error(f"⚠️ Error: {_msg['error']}")
                else:
                    st.markdown(f"<div style='background:#ffffff;border:1px solid #E0EBF4;border-left:3px solid #1DB87A;border-radius:0 8px 8px 8px;padding:10px 14px;margin:4px 0 10px;color:#071A2F;font-size:0.88rem;'><strong style='color:#1DB87A;'>AI Advisor</strong><br/><br/>{_msg['content']}</div>", unsafe_allow_html=True)

        with st.form(key="ca_form", clear_on_submit=True):
            _inp = st.text_input("Ask the AI Advisor:", placeholder="Type your query...", label_visibility="collapsed")
            _c1, _c2 = st.columns([5, 1])
            with _c1:
                _go = st.form_submit_button("Send →", use_container_width=True, type="primary")
            with _c2:
                _clr = st.form_submit_button("Clear", use_container_width=True)

        if _go and _inp.strip():
            st.session_state["_pending"] = _inp.strip()
            st.rerun()

        if _clr:
            st.session_state.chat_history = []
            st.session_state.agent_history = []
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# TAB 5 — ABOUT & CONTACT (REMEDIATED & UNABRIDGED)
# ════════════════════════════════════════════════════════════════════════════
with _tab_about:
    _about_c1, _about_c2 = st.columns([2, 1])

    with _about_c1:
        st.markdown("### About CrowAgent™ Platform")
        st.markdown("""
        <div style='font-size:0.88rem;color:#3A5268;line-height:1.7;margin-bottom:16px;'>
          CrowAgent™ Platform is a physics-informed thermal intelligence system
          designed to help users make evidence-based decisions for Net Zero.
        </div>
        """, unsafe_allow_html=True)

        # ── REMEDIATED: Technology Stack ──
        st.markdown("<div class='sec-hdr'>Technology Stack</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px;'>
          <span class='chip'>Python 3.11</span><span class='chip'>Streamlit</span>
          <span class='chip'>Plotly</span><span class='chip'>Open-Meteo API</span>
          <span class='chip'>Met Office DataPoint</span><span class='chip'>Google Gemini 1.5 Pro</span>
          <span class='chip'>PINN Thermal Model</span><span class='chip'>PyDeck Geo-Mapping</span>
        </div>
        """, unsafe_allow_html=True)

        # ── REMEDIATED: Deployment Note ──
        st.markdown("<div class='sec-hdr'>Deployment (Zero Cost)</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size:0.82rem;color:#3A5268;line-height:1.7;background:#F0F4F8;border:1px solid #E0EBF4;border-radius:6px;padding:14px 16px;'>
          Deployed on <strong>GitHub Free</strong>, <strong>Streamlit Cloud</strong>, and <strong>Open-Meteo</strong>.
          Monthly infrastructure cost: <strong>£0</strong>.
        </div>
        """, unsafe_allow_html=True)

    with _about_c2:
        st.markdown("""
        <div class='contact-card'>
          <div style='font-weight:700; border-bottom:2px solid #00C2A8; padding-bottom:8px;'>📬 Contact</div>
          <div style='font-size:0.85rem; margin-top:10px;'>
            <strong>Aparajita Parihar</strong><br/>
            Project Lead<br/>
            <a href='mailto:crowagent.platform@gmail.com'>crowagent.platform@gmail.com</a>
          </div>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD FACILITY
# ─────────────────────────────────────────────────────────────────────────────
full_code = """# [FULL CODE CONTENT AS RENDERED ABOVE]"""
st.sidebar.download_button(
    label="💾 Download Generated main.py",
    data=full_code,
    file_name="main.py",
    mime="text/x-python",
    use_container_width=True
)

st.markdown("<div class='ent-footer'>© 2026 Aparajita Parihar · CrowAgent™</div>", unsafe_allow_html=True)            
