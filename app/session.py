"""
Manages the Streamlit session state, including initialization and secrets.
"""

import streamlit as st
import os
from config.constants import ELEC_COST_PER_KWH

MAX_CHAT_HISTORY = 20

# ── Default campus centre (Reading, Berkshire) ────────────────────────────────
_DEFAULT_LAT = 51.4543
_DEFAULT_LON = -0.9781


def _get_secret(key: str, default: str = "") -> str:
    """
    Safely retrieves a secret from st.secrets, with a fallback to os.environ
    for local development (e.g., using a .env file).
    """
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)


def init_session() -> None:
    """
    Initializes all required session state keys with their default values.
    This function is idempotent, using setdefault to avoid overwriting existing
    state. It should be called at the beginning of every app run.
    """
    # Restore segment + scenarios from URL query params on first load
    qp = st.query_params
    if "segment" in qp and "user_segment" not in st.session_state:
        st.session_state["user_segment"] = qp.get("segment")
    if "scenarios" in qp and "selected_scenario_names" not in st.session_state:
        _qp_sc = [s.strip() for s in str(qp.get("scenarios", "")).split(",") if s.strip()]
        if _qp_sc:
            st.session_state["selected_scenario_names"] = _qp_sc

    defaults = {
        # Onboarding / segment
        "user_segment": None,
        "onboarding_complete": False,

        # Portfolio
        "portfolio": [],
        "active_analysis_ids": [],

        # Portfolio management modal state
        "show_segment_switch_modal": False,
        "pending_segment_switch": None,
        "portfolio_search_results": [],
        "portfolio_search_postcode": "",
        "portfolio_epc_fallback": False,
        "viz3d_selected_building": None,

        # AI Advisor
        "chat_history": [],
        "agent_history": [],

        # API keys
        "gemini_key": _get_secret("GEMINI_API_KEY") or _get_secret("GEMINI_KEY"),
        "gemini_key_valid": False,
        "owm_key": _get_secret("OWM_KEY"),
        "met_office_key": _get_secret("MET_OFFICE_KEY"),
        "epc_key": _get_secret("EPC_API_KEY"),

        # Financial analysis parameters
        "energy_tariff_gbp_per_kwh": ELEC_COST_PER_KWH,
        "discount_rate": 5.0,
        "analysis_period_yrs": 10,

        # Scenarios
        "selected_scenario_names": [],

        # Building selection
        "selected_building_name": None,
        "building_names": {},

        # Active page (manual routing — replaces st.navigation)
        "_current_page": "dashboard",

        # Sidebar visibility toggle (True = visible)
        "sidebar_visible": True,

        # Location / weather
        "wx_city": "Reading, Berkshire",
        "wx_lat": _DEFAULT_LAT,
        "wx_lon": _DEFAULT_LON,
        "wx_location_name": "Reading, Berkshire, UK",
        "wx_provider": "open_meteo",
        "wx_enable_fallback": True,
        "manual_temp": 10.5,
        "force_weather_refresh": False,
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


# ─────────────────────────────────────────────────────────────────────────────
# Segment default asset data
# Offsets for university_he match visualization_3d.py _BUILDING_OFFSETS
# (metres → degrees; cos_lat ≈ 0.6249 for 51.4543°N)
#   lat_deg_per_m ≈ 1/111320;  lon_deg_per_m ≈ 1/(111320 * cos_lat)
# ─────────────────────────────────────────────────────────────────────────────

_UNIVERSITY_DEFAULTS: list[dict] = [
    {
        "id": "univ_lib_01",
        "segment": "university_he",
        "name": "Greenfield Library",
        "display_name": "Greenfield Library",
        "building_type": "Library / Resource Centre",
        "floor_area_m2": 8500,
        "baseline_energy_mwh": 1450,
        "epc_rating": "C",
        "built_year": 1995,
        # offset (60m N, -130m W) → lat+0.000539, lon-0.001869
        "latitude": _DEFAULT_LAT + 0.000539,
        "longitude": _DEFAULT_LON - 0.001869,
        "postcode": "RG1 8AG",
        "u_value_wall": 0.35,
        "u_value_roof": 0.25,
        "u_value_glazing": 2.8,
        "glazing_ratio": 0.40,
        "occupancy_hours": 3500,
        "height_m": 18.0,
        "is_default": True,
        "source": "registry",
    },
    {
        "id": "univ_sci_01",
        "segment": "university_he",
        "name": "Greenfield Science Block",
        "display_name": "Greenfield Science Block",
        "building_type": "Lab / Research",
        "floor_area_m2": 12500,
        "baseline_energy_mwh": 3200,
        "epc_rating": "B",
        "built_year": 2005,
        # offset (-150m S, 70m E) → lat-0.001348, lon+0.001006
        "latitude": _DEFAULT_LAT - 0.001348,
        "longitude": _DEFAULT_LON + 0.001006,
        "postcode": "RG1 8AG",
        "u_value_wall": 0.28,
        "u_value_roof": 0.20,
        "u_value_glazing": 1.8,
        "glazing_ratio": 0.30,
        "occupancy_hours": 4000,
        "height_m": 24.0,
        "is_default": True,
        "source": "registry",
    },
    {
        "id": "univ_arts_01",
        "segment": "university_he",
        "name": "Greenfield Arts Building",
        "display_name": "Greenfield Arts Building",
        "building_type": "Teaching / Studio",
        "floor_area_m2": 4200,
        "baseline_energy_mwh": 680,
        "epc_rating": "D",
        "built_year": 1988,
        # offset (170m N, 110m E) → lat+0.001527, lon+0.001582
        "latitude": _DEFAULT_LAT + 0.001527,
        "longitude": _DEFAULT_LON + 0.001582,
        "postcode": "RG1 8AG",
        "u_value_wall": 0.45,
        "u_value_roof": 0.30,
        "u_value_glazing": 2.8,
        "glazing_ratio": 0.55,
        "occupancy_hours": 2800,
        "height_m": 12.0,
        "is_default": True,
        "source": "registry",
    },
]

_SMB_LANDLORD_DEFAULTS: list[dict] = [
    {
        "id": "cl_meridian_01",
        "segment": "smb_landlord",
        "name": "Meridian House",
        "display_name": "Meridian House",
        "building_type": "Office",
        "floor_area_m2": 2400,
        "baseline_energy_mwh": 380,
        "epc_rating": "D",
        "built_year": 1999,
        "latitude": _DEFAULT_LAT + 0.004,
        "longitude": _DEFAULT_LON + 0.006,
        "postcode": "RG1 3BU",
        "u_value_wall": 0.55,
        "u_value_roof": 0.35,
        "u_value_glazing": 2.4,
        "glazing_ratio": 0.45,
        "occupancy_hours": 2600,
        "height_m": 14.0,
        "is_default": True,
        "source": "registry",
    },
    {
        "id": "cl_riverside_01",
        "segment": "smb_landlord",
        "name": "Riverside Retail Park — Unit 3",
        "display_name": "Riverside Retail Park — Unit 3",
        "building_type": "Retail",
        "floor_area_m2": 680,
        "baseline_energy_mwh": 95,
        "epc_rating": "E",
        "built_year": 2003,
        "latitude": _DEFAULT_LAT - 0.005,
        "longitude": _DEFAULT_LON + 0.003,
        "postcode": "RG1 7YB",
        "u_value_wall": 0.65,
        "u_value_roof": 0.42,
        "u_value_glazing": 2.9,
        "glazing_ratio": 0.70,
        "occupancy_hours": 3200,
        "height_m": 5.0,
        "is_default": True,
        "source": "registry",
    },
    {
        "id": "cl_granary_01",
        "segment": "smb_landlord",
        "name": "The Granary Business Centre",
        "display_name": "The Granary Business Centre",
        "building_type": "Mixed-Use",
        "floor_area_m2": 1150,
        "baseline_energy_mwh": 165,
        "epc_rating": "F",
        "built_year": 1987,
        "latitude": _DEFAULT_LAT + 0.007,
        "longitude": _DEFAULT_LON - 0.004,
        "postcode": "RG2 0SL",
        "u_value_wall": 0.90,
        "u_value_roof": 0.55,
        "u_value_glazing": 3.2,
        "glazing_ratio": 0.30,
        "occupancy_hours": 2000,
        "height_m": 8.0,
        "is_default": True,
        "source": "registry",
    },
]

_SMB_INDUSTRIAL_DEFAULTS: list[dict] = [
    {
        "id": "ind_king_01",
        "segment": "smb_industrial",
        "name": "Kingfisher Distribution Centre",
        "display_name": "Kingfisher Distribution Centre",
        "building_type": "Distribution",
        "floor_area_m2": 4800,
        "baseline_energy_mwh": 580,
        "epc_rating": "E",
        "built_year": 1992,
        "latitude": _DEFAULT_LAT - 0.008,
        "longitude": _DEFAULT_LON - 0.007,
        "postcode": "RG30 6AZ",
        "u_value_wall": 0.75,
        "u_value_roof": 0.55,
        "u_value_glazing": 3.0,
        "glazing_ratio": 0.06,
        "occupancy_hours": 4200,
        "height_m": 10.0,
        "is_default": True,
        "source": "registry",
    },
    {
        "id": "ind_park_01",
        "segment": "smb_industrial",
        "name": "Parkside Manufacturing Unit 7",
        "display_name": "Parkside Manufacturing Unit 7",
        "building_type": "Manufacturing",
        "floor_area_m2": 2100,
        "baseline_energy_mwh": 290,
        "epc_rating": "D",
        "built_year": 2001,
        "latitude": _DEFAULT_LAT + 0.005,
        "longitude": _DEFAULT_LON + 0.008,
        "postcode": "RG30 1PL",
        "u_value_wall": 0.60,
        "u_value_roof": 0.48,
        "u_value_glazing": 3.1,
        "glazing_ratio": 0.08,
        "occupancy_hours": 3800,
        "height_m": 8.0,
        "is_default": True,
        "source": "registry",
    },
    {
        "id": "ind_apex_01",
        "segment": "smb_industrial",
        "name": "Apex Logistics Hub — Bay 2",
        "display_name": "Apex Logistics Hub — Bay 2",
        "building_type": "Logistics",
        "floor_area_m2": 3600,
        "baseline_energy_mwh": 420,
        "epc_rating": "F",
        "built_year": 1978,
        "latitude": _DEFAULT_LAT - 0.003,
        "longitude": _DEFAULT_LON - 0.005,
        "postcode": "RG30 3DX",
        "u_value_wall": 0.85,
        "u_value_roof": 0.60,
        "u_value_glazing": 3.3,
        "glazing_ratio": 0.05,
        "occupancy_hours": 5000,
        "height_m": 9.0,
        "is_default": True,
        "source": "registry",
    },
]

_INDIVIDUAL_SELFBUILD_DEFAULTS: list[dict] = [
    {
        "id": "sb_ashwood_01",
        "segment": "individual_selfbuild",
        "name": "14 Ashwood Close",
        "display_name": "14 Ashwood Close",
        "building_type": "Detached",
        "floor_area_m2": 165,
        "baseline_energy_mwh": 28,
        "epc_rating": "E",
        "built_year": 1967,
        "latitude": _DEFAULT_LAT + 0.006,
        "longitude": _DEFAULT_LON + 0.004,
        "postcode": "RG4 5HT",
        "u_value_wall": 1.40,
        "u_value_roof": 0.90,
        "u_value_glazing": 2.8,
        "glazing_ratio": 0.22,
        "occupancy_hours": 5500,
        "height_m": 6.0,
        "is_default": True,
        "source": "registry",
    },
    {
        "id": "sb_mill_01",
        "segment": "individual_selfbuild",
        "name": "7 Millbrook Lane",
        "display_name": "7 Millbrook Lane",
        "building_type": "Semi-Detached",
        "floor_area_m2": 98,
        "baseline_energy_mwh": 19,
        "epc_rating": "F",
        "built_year": 1952,
        "latitude": _DEFAULT_LAT - 0.004,
        "longitude": _DEFAULT_LON - 0.003,
        "postcode": "RG4 6EW",
        "u_value_wall": 1.60,
        "u_value_roof": 1.10,
        "u_value_glazing": 3.0,
        "glazing_ratio": 0.18,
        "occupancy_hours": 5800,
        "height_m": 5.5,
        "is_default": True,
        "source": "registry",
    },
    {
        "id": "sb_bramble_01",
        "segment": "individual_selfbuild",
        "name": "Bramble Cottage",
        "display_name": "Bramble Cottage",
        "building_type": "Detached",
        "floor_area_m2": 210,
        "baseline_energy_mwh": 38,
        "epc_rating": "G",
        "built_year": 1935,
        "latitude": _DEFAULT_LAT + 0.003,
        "longitude": _DEFAULT_LON - 0.007,
        "postcode": "RG4 7NJ",
        "u_value_wall": 1.80,
        "u_value_roof": 1.30,
        "u_value_glazing": 3.2,
        "glazing_ratio": 0.15,
        "occupancy_hours": 6000,
        "height_m": 5.0,
        "is_default": True,
        "source": "registry",
    },
]

_SEGMENT_DEFAULTS: dict[str, list[dict]] = {
    "university_he": _UNIVERSITY_DEFAULTS,
    "smb_landlord": _SMB_LANDLORD_DEFAULTS,
    "smb_industrial": _SMB_INDUSTRIAL_DEFAULTS,
    "individual_selfbuild": _INDIVIDUAL_SELFBUILD_DEFAULTS,
}


def load_segment_defaults(segment: str) -> list[dict]:
    """
    Returns 3 realistic hardcoded default assets for the segment.
    Assets are drawn from the segment's building_registry and augmented
    with portfolio metadata fields.

    Each asset dict contains ALL of these keys:
      id, segment, name, display_name, building_type,
      floor_area_m2, baseline_energy_mwh, epc_rating,
      built_year, latitude, longitude, postcode,
      u_value_wall, u_value_roof, u_value_glazing,
      glazing_ratio, occupancy_hours, height_m,
      is_default (bool, True), source ("registry")
    """
    return [dict(asset) for asset in _SEGMENT_DEFAULTS.get(segment, [])]


def switch_segment_with_defaults(new_segment: str) -> None:
    """
    Called when user confirms a segment switch.
    Clears current portfolio and loads new segment defaults.
    Also resets scenario selections to new segment defaults.
    Does NOT trigger the PDF modal — that is handled in the UI.
    """
    from config.scenarios import SEGMENT_DEFAULT_SCENARIOS
    st.session_state.user_segment = new_segment
    st.session_state.portfolio = load_segment_defaults(new_segment)
    st.session_state.active_analysis_ids = [
        a["id"] for a in st.session_state.portfolio
    ]
    default_sc = SEGMENT_DEFAULT_SCENARIOS.get(new_segment, [])
    st.session_state.selected_scenario_names = default_sc
    st.session_state.viz3d_selected_building = None
    st.session_state.pending_segment_switch = None
    st.session_state.show_segment_switch_modal = False


def ensure_portfolio_defaults() -> None:
    """
    Called on every app run after init_session().
    If portfolio is empty and a segment is set,
    auto-populates with segment defaults.
    Idempotent — safe to call on every rerun.
    """
    segment = st.session_state.get("user_segment")
    portfolio = st.session_state.get("portfolio", [])
    if segment and not portfolio:
        st.session_state.portfolio = load_segment_defaults(segment)
        st.session_state.active_analysis_ids = [
            a["id"] for a in st.session_state.portfolio
        ]
