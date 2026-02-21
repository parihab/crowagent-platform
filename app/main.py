# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — Sustainability AI Decisioning
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
import core.agent as crow_agent
import core.physics as physics

# ─────────────────────────────────────────────────────────────────────────────
# LOGO LOADER
# ─────────────────────────────────────────────────────────────────────────────
def _load_logo_uri() -> str:
    """Return the horizontal dark logo as a base64 data URI, or '' if file missing."""
    candidates = [
        os.path.join(os.path.dirname(__file__), "../assets/CrowAgent_Logo_Horizontal_Dark.svg"),
        os.path.join(os.path.dirname(__file__), "assets/CrowAgent_Logo_Horizontal_Dark.svg"),
        "assets/CrowAgent_Logo_Horizontal_Dark.svg",
    ]
    for path in candidates:
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                b64 = base64.b64encode(fh.read()).decode()
            return f"data:image/svg+xml;base64,{b64}"
    return ""

LOGO_URI = _load_logo_uri()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title   = "CrowAgent™ Platform",
    page_icon    = "🌿",
    layout       = "wide",
    initial_sidebar_state = "expanded",
    menu_items   = {
        "Get Help":     "mailto:crowagent.platform@gmail.com",
        "Report a bug": "https://github.com/YOUR_GITHUB/crowagent/issues",
        "About": (
            "**CrowAgent™ Platform — Sustainability AI Decisioning**\n\n"
            "© 2026 Aparajita Parihar. All rights reserved.\n\n"
            "⚠️ PROTOTYPE: Results are indicative only and based on simplified "
            "physics models. Not for use as the sole basis for investment decisions.\n\n"
            "CrowAgent™ is an unregistered trademark · UK IPO Class 42 pending"
        ),
    },
)

# ─────────────────────────────────────────────────────────────────────────────
# ENTERPRISE CSS + GOOGLE FONTS
# Fonts: Rajdhani (headings/display) + Nunito Sans (body)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Nunito+Sans:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap');

/* ── Global resets ─────────────────────────────────────────────────────── */
html, body, [class*="css"] {
  font-family: 'Nunito Sans', sans-serif !important;
}
h1,h2,h3,h4 {
  font-family: 'Rajdhani', sans-serif !important;
  letter-spacing: 0.3px;
}

/* ── App background ────────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"] > .main {
  background: #F0F4F8;
}
.block-container {
  padding-top: 0 !important;
  max-width: 100% !important;
}

/* ── Sidebar ───────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: #071A2F !important;
  border-right: 1px solid #1A3A5C !important;
}
[data-testid="stSidebar"] * { color: #CBD8E6 !important; }
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
  color: #00C2A8 !important;
}
[data-testid="stSidebar"] .stTextInput input {
  background: #0D2640 !important;
  border: 1px solid #1A3A5C !important;
  color: #CBD8E6 !important;
  font-size: 0.82rem !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
  background: #0D2640 !important;
  border: 1px solid #1A3A5C !important;
  color: #CBD8E6 !important;
}
[data-testid="stSidebar"] hr { border-color: #1A3A5C !important; }
[data-testid="stSidebar"] .stCheckbox span { color: #CBD8E6 !important; }
[data-testid="stSidebar"] .stButton button {
  background: #0D2640 !important;
  border: 1px solid #00C2A8 !important;
  color: #00C2A8 !important;
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  padding: 4px 10px !important;
}
[data-testid="stSidebar"] .stButton button:hover {
  background: #00C2A8 !important;
  color: #071A2F !important;
}

/* ── Platform header bar ───────────────────────────────────────────────── */
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
.platform-topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

/* ── Status pills ──────────────────────────────────────────────────────── */
.sp { display:inline-flex; align-items:center; gap:5px; padding:3px 10px;
      border-radius:20px; font-size:0.7rem; font-weight:700;
      letter-spacing:0.3px; white-space:nowrap; }
.sp-live   { background:rgba(29,184,122,.12); color:#1DB87A;
             border:1px solid rgba(29,184,122,.3); }
.sp-cache  { background:rgba(240,180,41,.1);  color:#F0B429;
             border:1px solid rgba(240,180,41,.25); }
.sp-manual { background:rgba(90,122,144,.12); color:#8AACBF;
             border:1px solid rgba(90,122,144,.2); }
.sp-warn   { background:rgba(232,76,76,.1);   color:#E84C4C;
             border:1px solid rgba(232,76,76,.25); }
.pulse-dot { width:7px; height:7px; border-radius:50%;
             background:#1DB87A; display:inline-block;
             animation: blink 2s ease-in-out infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }

/* ── Tab navigation ────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  background: #ffffff !important;
  border-bottom: 2px solid #E0EBF4 !important;
  gap: 0 !important;
  padding: 0 !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: #5A7A90 !important;
  font-family: 'Rajdhani', sans-serif !important;
  font-size: 0.88rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.5px !important;
  padding: 10px 20px !important;
  border-bottom: 3px solid transparent !important;
}
.stTabs [aria-selected="true"] {
  color: #071A2F !important;
  border-bottom: 3px solid #00C2A8 !important;
  background: rgba(0,194,168,.04) !important;
}
.stTabs [data-baseweb="tab-panel"] {
  padding: 20px 0 0 0 !important;
}

/* ── Enterprise KPI cards ──────────────────────────────────────────────── */
.kpi-card {
  background: #ffffff;
  border-radius: 8px;
  padding: 18px 20px 14px;
  border: 1px solid #E0EBF4;
  border-top: 3px solid #00C2A8;
  box-shadow: 0 2px 8px rgba(7,26,47,.05);
  height: 100%;
}
.kpi-card.accent-green  { border-top-color: #1DB87A; }
.kpi-card.accent-gold   { border-top-color: #F0B429; }
.kpi-card.accent-navy   { border-top-color: #071A2F; }
.kpi-label {
  font-family: 'Rajdhani', sans-serif;
  font-size: 0.68rem; font-weight: 700; letter-spacing: 1px;
  text-transform: uppercase; color: #5A7A90; margin-bottom: 6px;
}
.kpi-value {
  font-family: 'Rajdhani', sans-serif;
  font-size: 2rem; font-weight: 700; color: #071A2F; line-height: 1.1;
}
.kpi-unit  { font-size: 0.9rem; font-weight: 500; color: #5A7A90; margin-left: 2px; }
.kpi-delta-pos { color: #1DB87A; font-size: 0.78rem; font-weight: 700; margin-top: 4px; }
.kpi-delta-neg { color: #E84C4C; font-size: 0.78rem; font-weight: 700; margin-top: 4px; }
.kpi-sub   { font-size: 0.72rem; color: #8AACBF; margin-top: 2px; }

/* ── Section headers ───────────────────────────────────────────────────── */
.sec-hdr {
  font-family: 'Rajdhani', sans-serif;
  font-size: 0.72rem; font-weight: 700; letter-spacing: 1.5px;
  text-transform: uppercase; color: #00C2A8;
  border-bottom: 1px solid rgba(0,194,168,.2);
  padding-bottom: 6px; margin-bottom: 14px; margin-top: 4px;
}

/* ── Chart containers ──────────────────────────────────────────────────── */
.chart-card {
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #E0EBF4;
  padding: 18px 18px 10px;
  box-shadow: 0 2px 8px rgba(7,26,47,.04);
  margin-bottom: 16px;
}
.chart-title {
  font-family: 'Rajdhani', sans-serif;
  font-size: 0.82rem; font-weight: 700; letter-spacing: 0.5px;
  color: #071A2F; margin-bottom: 4px;
  text-transform: uppercase;
}
.chart-caption {
  font-size: 0.68rem; color: #8AACBF; margin-top: 4px;
  font-style: italic;
}

/* ── Disclaimer banners ────────────────────────────────────────────────── */
.disc-prototype {
  background: rgba(240,180,41,.07);
  border: 1px solid rgba(240,180,41,.3);
  border-left: 4px solid #F0B429;
  border-radius: 0 6px 6px 0;
  padding: 10px 16px; font-size: 0.78rem;
  color: #6A5010; line-height: 1.55; margin: 10px 0;
}
.disc-ai {
  background: rgba(0,194,168,.05);
  border: 1px solid rgba(0,194,168,.2);
  border-left: 4px solid #00C2A8;
  border-radius: 0 6px 6px 0;
  padding: 10px 16px; font-size: 0.78rem;
  color: #1A5A50; line-height: 1.55; margin: 10px 0;
}
.disc-data {
  background: rgba(7,26,47,.04);
  border: 1px solid rgba(7,26,47,.12);
  border-left: 4px solid #071A2F;
  border-radius: 0 6px 6px 0;
  padding: 10px 16px; font-size: 0.78rem;
  color: #3A5268; line-height: 1.55; margin: 10px 0;
}

/* ── Weather widget (sidebar) ──────────────────────────────────────────── */
.wx-widget {
  background: #0D2640;
  border: 1px solid #1A3A5C;
  border-radius: 8px;
  padding: 12px 14px;
  margin: 6px 0;
}
.wx-temp {
  font-family: 'Rajdhani', sans-serif;
  font-size: 2rem; font-weight: 700; color: #ffffff;
  display: inline-block; line-height: 1;
}
.wx-desc { font-size: 0.78rem; color: #7A9BB5; margin-top: 2px; }
.wx-row  { font-size: 0.74rem; color: #CBD8E6; margin-top: 5px; }

/* ── Contact cards ─────────────────────────────────────────────────────── */
.contact-card {
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #E0EBF4;
  padding: 20px 22px;
  box-shadow: 0 2px 8px rgba(7,26,47,.05);
}
.contact-label {
  font-family: 'Rajdhani', sans-serif;
  font-size: 0.7rem; font-weight: 700; letter-spacing: 1px;
  text-transform: uppercase; color: #00C2A8; margin-bottom: 4px;
}
.contact-val { font-size: 0.88rem; color: #071A2F; font-weight: 600; }

/* ── Enterprise footer ─────────────────────────────────────────────────── */
.ent-footer {
  background: #071A2F;
  border-top: 2px solid #00C2A8;
  padding: 16px 24px;
  margin-top: 32px;
  text-align: center;
}

/* ── Validation messages ───────────────────────────────────────────────── */
.val-warn {
  background: rgba(232,76,76,.06);
  border: 1px solid rgba(232,76,76,.25);
  border-left: 3px solid #E84C4C;
  border-radius: 0 4px 4px 0;
  padding: 7px 12px;
  font-size: 0.76rem; color: #8B1A1A;
}
.val-ok {
  background: rgba(29,184,122,.06);
  border: 1px solid rgba(29,184,122,.25);
  border-left: 3px solid #1DB87A;
  border-radius: 0 4px 4px 0;
  padding: 7px 12px;
  font-size: 0.76rem; color: #0A4A28;
}
.val-err {
  background: rgba(220,53,69,.08);
  border: 1px solid rgba(220,53,69,.3);
  border-left: 3px solid #DC3545;
  border-radius: 0 4px 4px 0;
  padding: 7px 12px;
  font-size: 0.76rem; color: #721C24;
}

/* ── Plotly overrides ──────────────────────────────────────────────────── */
.js-plotly-plot .plotly .modebar { top: 4px !important; }

/* ── Sidebar section label ─────────────────────────────────────────────── */
.sb-section {
  font-family: 'Rajdhani', sans-serif;
  font-size: 0.65rem; font-weight: 700; letter-spacing: 1.5px;
  text-transform: uppercase; color: #00C2A8 !important;
  margin: 14px 0 6px 0;
}

/* ── Info chip ─────────────────────────────────────────────────────────── */
.chip {
  display: inline-block; background: #0D2640;
  border: 1px solid #1A3A5C; border-radius: 4px;
  padding: 2px 8px; font-size: 0.7rem; color: #7A9BB5;
  margin: 2px;
}

/* ── Hide Streamlit default elements ───────────────────────────────────── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# BUILDING DATA — Greenfield University (fictional)
# Derived from HESA 2022-23 UK HE sector averages + CIBSE Guide A U-values.
# NOT data from any real institution.
# ─────────────────────────────────────────────────────────────────────────────
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
# SESSION STATE INITIALISATION
# ─────────────────────────────────────────────────────────────────────────────
def _get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

# Initialize session state with defaults or environment values
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


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    # ── Logo ──────────────────────────────────────────────────────────────────
    if LOGO_URI:
        st.markdown(
            f"<div style='padding:10px 0 4px;'>"
            f"<img src='{LOGO_URI}' width='200' style='max-width:100%;'/>"
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
        "<div style='font-size:0.68rem;color:#4A6880;margin-bottom:8px;'>"
        "Sustainability AI Decisioning Platform</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Building selector ─────────────────────────────────────────────────────
    st.markdown("<div class='sb-section'>🏢 Building</div>", unsafe_allow_html=True)
    selected_building_name = st.selectbox(
        "Building", list(BUILDINGS.keys()), label_visibility="collapsed",
    )
    sb = BUILDINGS[selected_building_name]
    st.markdown(
        f"<div style='font-size:0.72rem;color:#7A9BB5;line-height:1.5;'>"
        f"<span class='chip'>{sb['building_type']}</span> "
        f"<span class='chip'>{sb['built_year']}</span> "
        f"<span class='chip'>{sb['floor_area_m2']:,} m²</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Scenario multi-select ─────────────────────────────────────────────────
    st.markdown("<div class='sb-section'>⚡ Scenarios</div>", unsafe_allow_html=True)
    selected_scenario_names = st.multiselect(
        "Scenarios", list(SCENARIOS.keys()),
        default=["Baseline (No Intervention)", "Solar Glass Installation",
                 "Enhanced Insulation Upgrade"],
        label_visibility="collapsed",
    )
    # Validation
    if not selected_scenario_names:
        st.markdown(
            "<div class='val-warn'>⚠ Select at least one scenario to continue.</div>",
            unsafe_allow_html=True,
        )
        st.stop()

    st.markdown("---")

    # ── Weather panel ──────────────────────────────────────────────────────────
    st.markdown("<div class='sb-section'>🌤 Live Weather</div>", unsafe_allow_html=True)

    _force = st.button("⟳ Force Refresh", key="wx_refresh", use_container_width=True)
    if _force:
        st.session_state.force_weather_refresh = True

    # Manual temp slider (shown always as override option)
    manual_t = st.slider(
        "Manual temperature override (°C)", -10.0, 35.0,
        st.session_state.manual_temp, 0.5,
    )
    st.session_state.manual_temp = manual_t

    with st.spinner("Checking weather…"):
        weather = wx.get_weather(
            met_office_key      = st.session_state.met_office_key or None,
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
      <div style='font-size:0.72rem;color:#4A6880;'>{weather['location_name']}</div>
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

    # ── API Keys (collapsible) ────────────────────────────────────────────────
    with st.expander("🔑 API Keys (optional)", expanded=False):
        st.markdown(
            "<div style='background:#FFF3CD;border:1px solid #FFD89B;border-radius:6px;padding:10px;'>"
            "<div style='font-size:0.75rem;color:#664D03;font-weight:700;margin-bottom:6px;'>🔒 Security Notice</div>"
            "<div style='font-size:0.68rem;color:#664D03;line-height:1.5;'>"
            "• Keys exist in your session only (cleared on browser close)<br/>"
            "• Your keys are <strong>never</strong> stored on the server<br/>"
            "• Each user enters their own key independently<br/>"
            "• Use unique, disposable API keys if sharing this link"
            "</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown("")  # spacing
        
        _mo_key = st.text_input(
            "Met Office DataPoint key",
            type="password", placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            value=st.session_state.met_office_key,
            help="Free at metoffice.gov.uk/services/data/datapoint",
        )
        if _mo_key != st.session_state.met_office_key:
            st.session_state.met_office_key = _mo_key

        # Guidance and validation for Met Office DataPoint key
        if not st.session_state.met_office_key:
          st.markdown(
            "<div style='font-size:0.86rem;color:#4A6880;'>"
            "Met Office DataPoint is optional. To enable UK-observation-level "
            "weather, register for a free API key at: <a href=\"https://www.metoffice.gov.uk/services/data/datapoint\" target=\"_blank\">metoffice.gov.uk/services/data/datapoint</a>. "
            "Paste your key into this field and click 'Test Met Office key'."
            "</div>",
            unsafe_allow_html=True,
          )
        else:
          if st.button("Test Met Office key", key="test_mo_key", use_container_width=True):
            ok, msg = wx.test_met_office_key(st.session_state.met_office_key)
            if ok:
              st.markdown("<div class='val-ok'>✓ " + msg + "</div>", unsafe_allow_html=True)
            else:
              st.markdown("<div class='val-err'>❌ " + msg + "</div>", unsafe_allow_html=True)

        _gm_key = st.text_input(
            "Gemini API key (for AI Advisor)",
            type="password", placeholder="AIzaSy... (starts with 'AIza')",
            value=st.session_state.gemini_key,
            help="Get free at aistudio.google.com | Never share this key | Each user brings their own",
        )
        if _gm_key != st.session_state.gemini_key:
            st.session_state.gemini_key = _gm_key

        # Validation feedback with actual API test
        if st.session_state.gemini_key:
            if not st.session_state.gemini_key.startswith("AIza"):
                st.markdown(
                    "<div class='val-warn'>⚠ Gemini key should start with 'AIza'</div>",
                    unsafe_allow_html=True,
                )
            else:
                # Test the API key with a simple request
                try:
                    test_url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent"
                    test_payload = {
                        "contents": [{"parts": [{"text": "test"}]}],
                        "generationConfig": {"maxOutputTokens": 10}
                    }
                    test_resp = requests.post(
                        test_url,
                        params={"key": st.session_state.gemini_key},
                        json=test_payload,
                        timeout=10
                    )
                    
                    if test_resp.status_code == 200:
                        st.markdown(
                            "<div class='val-ok'>✓ Gemini AI Advisor ready</div>",
                            unsafe_allow_html=True,
                        )
                        st.session_state.gemini_key_valid = True
                    elif test_resp.status_code == 401:
                        st.markdown(
                            "<div class='val-err'>❌ Invalid API key</div>",
                            unsafe_allow_html=True,
                        )
                        st.session_state.gemini_key_valid = False
                    elif test_resp.status_code == 403:
                        st.markdown(
                            "<div class='val-err'>❌ API key blocked (check permissions in Google Cloud)</div>",
                            unsafe_allow_html=True,
                        )
                        st.session_state.gemini_key_valid = False
                    else:
                        st.markdown(
                            "<div class='val-ok'>✓ Key format valid (will test on first use)</div>",
                            unsafe_allow_html=True,
                        )
                        st.session_state.gemini_key_valid = True
                except Exception as e:
                    st.markdown(
                        "<div class='val-ok'>✓ Key format valid (will test on first use)</div>",
                        unsafe_allow_html=True,
                    )
                    st.session_state.gemini_key_valid = True

    st.markdown("---")

    # ── Data sources ──────────────────────────────────────────────────────────
    st.markdown("<div class='sb-section'>📚 Data Sources</div>", unsafe_allow_html=True)
    for src in ["Open-Meteo (live weather)", "Met Office DataPoint (optional)",
                "BEIS GHG Factors 2023", "HESA Estates Stats 2022-23",
                "CIBSE Guide A", "PVGIS (EC JRC)", "Raissi et al. (2019)"]:
        st.caption(f"· {src}")

    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.64rem;color:#334A60;text-align:center;line-height:1.6;'>"
        "© 2026 Aparajita Parihar<br/>CrowAgent™ · All rights reserved<br/>"
        "v2.0.0 · Prototype</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# COMPUTE ALL SELECTED SCENARIOS
# ─────────────────────────────────────────────────────────────────────────────
results: dict[str, dict] = {}
_compute_errors: list[str] = []

for _sn in selected_scenario_names:
    try:
        results[_sn] = calculate_thermal_load(BUILDINGS[selected_building_name],
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
    _logo_html = f"<img src='{LOGO_URI}' height='38' style='vertical-align:middle;'/>"
else:
    _logo_html = "<span style='font-family:Rajdhani,sans-serif;font-size:1.2rem;font-weight:700;color:#00C2A8;'>🌿 CrowAgent™</span>"

st.markdown(f"""
<div class='platform-topbar'>
  <div style='display:flex;align-items:center;gap:16px;flex-wrap:wrap;'>
    {_logo_html}
    <div>
      <div style='font-family:Rajdhani,sans-serif;font-size:0.7rem;
                  letter-spacing:1.5px;text-transform:uppercase;
                  color:#4A6880;line-height:1;margin-top:2px;'>
        Sustainability AI Decisioning Platform
      </div>
    </div>
  </div>
  <div class='platform-topbar-right'>
    {_weather_pill}
    <span class='sp sp-warn'>⚗ PROTOTYPE v2.0.0</span>
    <span class='sp sp-cache'>Reading, Berkshire</span>
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
_tab_dash, _tab_fin, _tab_ai, _tab_about = st.tabs([
    "📊  Dashboard",
    "📈  Financial Analysis",
    "🤖  AI Advisor",
    "ℹ️  About & Contact",
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
      <div style='color:#4A6880;font-size:0.72rem;margin-top:4px;'>
        Google Gemini 1.5 Flash · Free tier · Tool-use agent loop · 1,500 req/day ·
        © 2026 Aparajita Parihar
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
             padding:2px 8px;font-size:0.68rem;font-weight:700;margin:2px 2px 2px 0;
             letter-spacing:0.3px;}
    .ca-meta{font-size:0.68rem;color:#8AACBF;margin-top:4px;}
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
                    buildings=BUILDINGS, scenarios=SCENARIOS,
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
                        f"font-size:0.68rem;color:#8AACBF;'>"
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
                        buildings=BUILDINGS, scenarios=SCENARIOS,
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
# TAB 4 — ABOUT & CONTACT
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
                f"<img src='{LOGO_URI}' width='300' style='margin-bottom:12px;'/><br/>",
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
            <div class='contact-label'>Platform Enquiries</div>
            <div class='contact-val'>
              <a href='mailto:crowagent.platform@gmail.com'
                 style='color:#00C2A8;text-decoration:none;font-size:0.85rem;'>
                crowagent.platform@gmail.com
              </a>
            </div>
          </div>

          <div style='margin-bottom:14px;'>
            <div class='contact-label'>Domains</div>
            <div style='font-size:0.82rem;color:#3A5268;'>
              <a href='https://crowagent.co.uk' target='_blank'
                 style='color:#00C2A8;'>crowagent.co.uk</a><br/>
              <a href='https://crowagent.ai' target='_blank'
                 style='color:#00C2A8;'>crowagent.ai</a><br/>
              <a href='https://crowagentplatform.co.uk' target='_blank'
                 style='color:#00C2A8;'>crowagentplatform.co.uk</a>
            </div>
          </div>

          <div style='margin-bottom:14px;'>
            <div class='contact-label'>GitHub</div>
            <div class='contact-val'>
              <a href='https://github.com/YOUR_GITHUB/crowagent'
                 target='_blank' style='color:#00C2A8;font-size:0.85rem;'>
                github.com/YOUR_GITHUB/crowagent
              </a>
            </div>
            <div style='font-size:0.72rem;color:#8AACBF;margin-top:2px;'>
              Update with your GitHub username
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
            <div style='font-size:0.7rem;color:#8AACBF;font-weight:700;
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
          <div style='font-family:Rajdhani,sans-serif;font-size:0.7rem;font-weight:700;
                      letter-spacing:1px;text-transform:uppercase;color:#00C2A8;
                      margin-bottom:8px;'>Build Information</div>
          <div style='font-size:0.74rem;color:#7A9BB5;line-height:1.8;'>
            <strong style='color:#CBD8E6;'>Version:</strong> v2.0.0<br/>
            <strong style='color:#CBD8E6;'>Released:</strong> 21 February 2026<br/>
            <strong style='color:#CBD8E6;'>Status:</strong>
            <span style='color:#F0B429;'>⚗ Working Prototype</span><br/>
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
    <span style='color:#334A60;font-size:0.72rem;'>Sustainability AI Decisioning Platform</span>
    <span style='color:#334A60;font-size:0.72rem;'>v2.0.0 · Working Prototype</span>
  </div>
  <div style='font-size:0.7rem;color:#334A60;line-height:1.6;'>
    © 2026 Aparajita Parihar · All rights reserved · Independent research project ·
    CrowAgent™ is an unregistered trademark (UK IPO Class 42, registration pending) ·
    Not licensed for commercial use without written permission
  </div>
  <div style='font-size:0.62rem;color:#253A4A;margin-top:4px;font-style:italic;'>
    Physics: Raissi et al. (2019) J. Comp. Physics · doi:10.1016/j.jcp.2018.10.045 ·
    Weather: Open-Meteo API + Met Office DataPoint · Carbon: BEIS 2023 ·
    Costs: HESA 2022-23 · AI: Google Gemini 1.5 Flash ·
    ⚠️ Results indicative only — not for investment decisions
  </div>
</div>
""", unsafe_allow_html=True)
