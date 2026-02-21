# app/main.py
import streamlit as st
import sys
import os
from dotenv import load_dotenv

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="CrowAgent™ Platform",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- ENTERPRISE PATH & SECRETS CHECK ---
# 1. Load your local .env file (ignored by Git for security)
load_dotenv()

# 2. Ensure the 'app' folder can see 'core' and 'services'
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# 3. Import your modular logic after the path check
import services.weather as wx
import core.agent as crow_agent
import core.physics as physics

# --- AUTO-LOAD SECRETS ---
def _get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

if "gemini_key" not in st.session_state:
    st.session_state.gemini_key = _get_secret("GEMINI_KEY", "")
if "met_office_key" not in st.session_state:
    st.session_state.met_office_key = _get_secret("MET_OFFICE_KEY", "")

# ═══════════════════════════════════════════════════════════════════════════════════
# MAIN APP INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════════

# --- HEADER ---
st.markdown("# 🏢 CrowAgent™ Platform")
st.markdown("### AI-Powered Campus Thermal Intelligence System")
st.markdown("""
Rapid sustainability investment analysis for UK university estate managers.
Using simplified PINN thermal modeling calibrated to HESA/CIBSE standards.
""")

# --- SIDEBAR CONTROLS ---
st.sidebar.markdown("## ⚙️ Configuration")
st.sidebar.markdown("---")

# Building selector
selected_building = st.sidebar.selectbox(
    "🏛️ Select Building",
    options=list(physics.BUILDINGS.keys()),
    help="Choose a campus building to analyze"
)

# Scenario selector
selected_scenario = st.sidebar.selectbox(
    "🔧 Select Intervention",
    options=list(physics.SCENARIOS.keys()),
    help="Choose an energy efficiency intervention to model"
)

# Weather input
st.sidebar.markdown("### 🌡️ Current Conditions")
temp_c = st.sidebar.slider(
    "Outdoor Temperature (°C)",
    min_value=-5.0,
    max_value=35.0,
    value=10.5,
    step=0.5,
    help="Current outdoor temperature (UK average: 10.5°C)"
)

# --- MAIN CONTENT ---
st.markdown("---")

# Get selected data
building_data = physics.BUILDINGS[selected_building]
scenario_data = physics.SCENARIOS[selected_scenario]

# Calculate results
weather_data = {"temperature_c": temp_c}
result = physics.calculate_thermal_load(building_data, scenario_data, weather_data)

# Display results in columns
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Baseline Energy",
        value=f"{result['baseline_energy_mwh']:.1f} MWh/yr",
        help="Energy consumption without intervention"
    )

with col2:
    st.metric(
        label="Scenario Energy",
        value=f"{result['scenario_energy_mwh']:.1f} MWh/yr",
        delta=f"-{result['energy_saving_mwh']:.1f} MWh ({result['energy_saving_pct']:.1f}%)",
        delta_color="inverse"
    )

with col3:
    st.metric(
        label="Install Cost",
        value=f"£{result['install_cost_gbp']:,.0f}",
        help="One-time installation cost"
    )

# Detailed results table
st.markdown("### 📊 Detailed Analysis")

detail_cols = st.columns(2)

with detail_cols[0]:
    st.markdown("**Energy & Carbon**")
    st.write(f"""
    • Baseline Carbon: **{result['baseline_carbon_t']:.1f} tCO₂e/yr**
    • Scenario Carbon: **{result['scenario_carbon_t']:.1f} tCO₂e/yr**
    • Carbon Savings: **{result['carbon_saving_t']:.1f} tCO₂e/yr**
    • Annual Cost Saving: **£{result['annual_saving_gbp']:,.0f}**
    """)

with detail_cols[1]:
    st.markdown("**Thermal Performance (U-values in W/m²K)**")
    st.write(f"""
    • Wall: **{result['u_wall']:.2f}** (baseline: {building_data['u_value_wall']:.2f})
    • Roof: **{result['u_roof']:.2f}** (baseline: {building_data['u_value_roof']:.2f})
    • Glazing: **{result['u_glazing']:.2f}** (baseline: {building_data['u_value_glazing']:.2f})
    """)

# Payback analysis
if result['payback_years']:
    st.markdown("---")
    st.markdown("### 💰 Financial Payback")
    st.write(f"""
    **Payback Period: {result['payback_years']:.1f} years**
    
    This intervention will pay for itself through energy savings in approximately {result['payback_years']:.1f} years.
    """)
    
    if result['cost_per_tonne_co2']:
        st.info(f"💡 **Cost per tonne CO₂ avoided: £{result['cost_per_tonne_co2']:,.1f}**")

# Building & scenario info
st.markdown("---")
st.markdown("### ℹ️ Building & Scenario Information")

info_cols = st.columns(2)

with info_cols[0]:
    st.markdown(f"**{selected_building}**")
    st.write(f"""
    • Floor Area: {building_data['floor_area_m2']:,} m²
    • Height: {building_data['height_m']} m
    • Glazing Ratio: {building_data['glazing_ratio']:.1%}
    • Building Type: {building_data['building_type']}
    • Built: {building_data['built_year']}
    """)

with info_cols[1]:
    st.markdown(f"**{selected_scenario}**")
    st.write(f"""
    {scenario_data['description']}
    
    • Wall Factor: {scenario_data['u_wall_factor']:.2f}x
    • Roof Factor: {scenario_data['u_roof_factor']:.2f}x
    • Glazing Factor: {scenario_data['u_glazing_factor']:.2f}x
    • Solar Gain Reduction: {scenario_data['solar_gain_reduction']:.1%}
    • Infiltration Reduction: {scenario_data['infiltration_reduction']:.1%}
    """)

# Disclaimer
st.markdown("---")
st.warning(
    "⚠️ **Disclaimer**: These results are indicative only based on simplified steady-state thermal "
    "modeling. They should not be used as the sole basis for investment decisions. Always commission "
    "a professional energy survey and detailed engineering assessment before proceeding with capital investment."
)