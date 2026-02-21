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

# --- ENTERPRISE STYLING ---
st.markdown("""
<style>
    /* Main Container */
    .main {
        background-color: #f8f9fa;
    }
    
    /* Header Styling */
    .header-section {
        background: linear-gradient(135deg, #0d47a1 0%, #1565c0 100%);
        color: white;
        padding: 40px 20px;
        border-radius: 8px;
        margin: 0 0 30px 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .header-section h1 {
        margin: 0;
        font-size: 32px;
        margin-bottom: 8px;
    }
    
    .header-section p {
        margin: 0;
        font-size: 16px;
        opacity: 0.95;
    }
    
    /* Card Styling */
    .metric-card {
        background: white;
        padding: 24px;
        border-radius: 8px;
        border-left: 4px solid #0d47a1;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        transform: translateY(-2px);
    }
    
    .metric-label {
        color: #666;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    
    .metric-value {
        color: #0d47a1;
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 8px;
    }
    
    /* Section Headers */
    .section-header {
        color: #0d47a1;
        font-size: 22px;
        font-weight: 700;
        padding-bottom: 12px;
        border-bottom: 3px solid #0d47a1;
        margin-top: 30px;
        margin-bottom: 20px;
    }
    
    /* Info Boxes */
    .info-box {
        background: #e3f2fd;
        border-left: 4px solid #0d47a1;
        padding: 16px;
        border-radius: 6px;
        margin: 16px 0;
        color: #01478a;
    }
    
    .success-box {
        background: #e8f5e9;
        border-left: 4px solid #2e7d32;
        padding: 16px;
        border-radius: 6px;
        margin: 16px 0;
    }
    
    .warning-box {
        background: #fff3e0;
        border-left: 4px solid #f57c00;
        padding: 16px;
        border-radius: 6px;
        margin: 16px 0;
        color: #e65100;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f5f7fa 0%, #e8ebf0 100%);
    }
    
    .sidebar-title {
        color: #0d47a1;
        font-size: 15px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 20px;
        margin-bottom: 12px;
    }
    
    /* Button Styling */
    .stButton > button {
        background: linear-gradient(135deg, #0d47a1 0%, #1565c0 100%);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(13, 71, 161, 0.3);
        width: 100%;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #1565c0 0%, #1a237e 100%);
        box-shadow: 0 4px 12px rgba(13, 71, 161, 0.4);
        transform: translateY(-2px);
    }
    
    /* Logo Container */
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 20px;
        padding: 20px 0;
    }
    
    .logo-container img {
        max-width: 280px;
        height: auto;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
    }
    
    /* Table Styling */
    .dataframe {
        font-size: 14px;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #999;
        font-size: 12px;
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid #e0e0e0;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f0f0;
        border-radius: 6px;
        color: #0d47a1;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #0d47a1;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- ENTERPRISE PATH & SECRETS CHECK ---
load_dotenv()

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

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
# HEADER WITH LOGO
# ═══════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="logo-container">', unsafe_allow_html=True)
st.image("assets/CrowAgent_Logo_Horizontal_Dark.svg", width=300)
st.markdown('</div>', unsafe_allow_html=True)

# --- HEADER ---
st.markdown("""
<div class="header-section">
    <h1>Campus Thermal Intelligence</h1>
    <p>Data-Driven Sustainability Analytics for Higher Education</p>
</div>
""", unsafe_allow_html=True)

# --- MAIN DESCRIPTION ---
st.markdown("""
<div class="info-box">
<strong>Welcome to CrowAgent™ Platform</strong><br>
Analyze energy efficiency investments across your campus using physics-informed thermal modeling. 
Compare scenarios, forecast ROI, and make evidence-based sustainability decisions.
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════════
# SIDEBAR CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════
st.sidebar.markdown("# ⚙️ Configuration")
st.sidebar.markdown("---")

# Building selector
st.sidebar.markdown('<p class="sidebar-title">🏛️ Select Building</p>', unsafe_allow_html=True)
selected_building = st.sidebar.selectbox(
    "Choose a campus building:",
    options=list(physics.BUILDINGS.keys()),
    help="Select a building to analyze",
    label_visibility="collapsed"
)

# Scenario selector
st.sidebar.markdown('<p class="sidebar-title">🔧 Select Intervention</p>', unsafe_allow_html=True)
selected_scenario = st.sidebar.selectbox(
    "Choose an energy efficiency intervention:",
    options=list(physics.SCENARIOS.keys()),
    help="Select a retrofit scenario to model",
    label_visibility="collapsed"
)

# Weather input
st.sidebar.markdown('<p class="sidebar-title">🌡️ Current Conditions</p>', unsafe_allow_html=True)
temp_c = st.sidebar.slider(
    "Outdoor Temperature (°C)",
    min_value=-5.0,
    max_value=35.0,
    value=10.5,
    step=0.5,
    help="Current outdoor temperature for thermal calculations"
)

# ═══════════════════════════════════════════════════════════════════════════════════
# ANALYSIS & RESULTS
# ═══════════════════════════════════════════════════════════════════════════════════

# Get selected data
building_data = physics.BUILDINGS[selected_building]
scenario_data = physics.SCENARIOS[selected_scenario]

# Calculate results
weather_data = {"temperature_c": temp_c}
result = physics.calculate_thermal_load(building_data, scenario_data, weather_data)

# --- KEY METRICS ---
st.markdown('<h2 class="section-header">📊 Financial Impact Analysis</h2>', unsafe_allow_html=True)

metric_cols = st.columns(4)

with metric_cols[0]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Annual Energy Saving</div>
        <div class="metric-value">{result['energy_saving_mwh']:.1f}</div>
        <div style="color: #999; font-size: 12px;">MWh/year ({result['energy_saving_pct']:.1f}%)</div>
    </div>
    """, unsafe_allow_html=True)

with metric_cols[1]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Carbon Reduction</div>
        <div class="metric-value">{result['carbon_saving_t']:.1f}</div>
        <div style="color: #999; font-size: 12px;">tonnes CO₂e/year</div>
    </div>
    """, unsafe_allow_html=True)

with metric_cols[2]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Annual Cost Saving</div>
        <div class="metric-value">£{result['annual_saving_gbp']:,.0f}</div>
        <div style="color: #999; font-size: 12px;">operational savings</div>
    </div>
    """, unsafe_allow_html=True)

with metric_cols[3]:
    if result['payback_years']:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Payback Period</div>
            <div class="metric-value">{result['payback_years']:.1f}</div>
            <div style="color: #999; font-size: 12px;">years to ROI</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Installation Cost</div>
            <div class="metric-value">£{result['install_cost_gbp']:,.0f}</div>
            <div style="color: #999; font-size: 12px;">one-time investment</div>
        </div>
        """, unsafe_allow_html=True)

# --- DETAILED BREAKDOWN ---
st.markdown('<h2 class="section-header">🔍 Detailed Analysis</h2>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📈 Energy & Carbon", "🏗️ Thermal Performance", "💰 Financial Details"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### Energy Consumption
        """)
        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | Baseline Energy | {result['baseline_energy_mwh']:.1f} MWh/yr |
        | Scenario Energy | {result['scenario_energy_mwh']:.1f} MWh/yr |
        | Annual Saving | {result['energy_saving_mwh']:.1f} MWh/yr |
        | Saving % | {result['energy_saving_pct']:.1f}% |
        """)
    
    with col2:
        st.markdown("""
        #### Carbon Emissions
        **Source:** BEIS 2023: 0.20482 kgCO₂e/kWh
        """)
        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | Baseline Carbon | {result['baseline_carbon_t']:.1f} tCO₂e/yr |
        | Scenario Carbon | {result['scenario_carbon_t']:.1f} tCO₂e/yr |
        | Carbon Reduction | {result['carbon_saving_t']:.1f} tCO₂e/yr |
        """)

with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### Current U-values (W/m²K)
        
        *Lower values = better insulation*
        """)
        st.markdown(f"""
        | Component | Baseline | After Retrofit |
        |-----------|----------|----------------|
        | Wall | {building_data['u_value_wall']:.2f} | {result['u_wall']:.2f} |
        | Roof | {building_data['u_value_roof']:.2f} | {result['u_roof']:.2f} |
        | Glazing | {building_data['u_value_glazing']:.2f} | {result['u_glazing']:.2f} |
        """)
    
    with col2:
        st.markdown("""
        #### Intervention Parameters
        """)
        st.markdown(f"""
        | Parameter | Value |
        |-----------|-------|
        | Wall Factor | {scenario_data['u_wall_factor']:.1f}x |
        | Roof Factor | {scenario_data['u_roof_factor']:.1f}x |
        | Glazing Factor | {scenario_data['u_glazing_factor']:.1f}x |
        | Solar Gain Reduction | {scenario_data['solar_gain_reduction']:.1%} |
        | Infiltration Reduction | {scenario_data['infiltration_reduction']:.1%} |
        """)

with tab3:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### Financial Metrics (£)
        """)
        cost_per_saving = result['install_cost_gbp'] / result['annual_saving_gbp'] if result['annual_saving_gbp'] > 0 else 0
        st.markdown(f"""
        | Item | Value |
        |------|-------|
        | Installation Cost | £{result['install_cost_gbp']:,.0f} |
        | Annual Energy Saving | £{result['annual_saving_gbp']:,.0f} |
        | Cost per Unit Saved | £{cost_per_saving:.2f}/year |
        | Payback Period | {result['payback_years']:.1f} years |
        """)
    
    with col2:
        st.markdown("""
        #### Environmental Value
        """)
        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | Renewable Generation | {result['renewable_mwh']:.1f} MWh/yr |
        | Cost per tCO₂ avoided | £{result['cost_per_tonne_co2']:,.1f} |
        | CO₂ Reduction % | {(result['carbon_saving_t'] / result['baseline_carbon_t'] * 100) if result['baseline_carbon_t'] > 0 else 0:.1f}% |
        """)

# --- BUILDING & SCENARIO INFO ---
st.markdown('<h2 class="section-header">ℹ️ Building & Scenario Details</h2>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"""
    ### 🏛️ {selected_building}
    
    #### Building Characteristics
    """)
    st.markdown(f"""
    - **Floor Area:** {building_data['floor_area_m2']:,} m²
    - **Height:** {building_data['height_m']} m
    - **Window Ratio:** {building_data['glazing_ratio']:.1%}
    - **Building Type:** {building_data['building_type']}
    - **Built Year:** {building_data['built_year']}
    - **Baseline Energy:** {building_data['baseline_energy_mwh']} MWh/yr
    - **Annual Occupancy:** {building_data['occupancy_hours']:,} hr/yr
    
    *{building_data['description']}*
    """)

with col2:
    st.markdown(f"""
    ### 🔧 {selected_scenario}
    
    #### Intervention Details
    """)
    st.markdown(f"""
    {scenario_data['description']}
    
    #### Technical Specifications
    - **Wall Improvement:** {(1 - scenario_data['u_wall_factor']) * 100:.0f}%
    - **Roof Improvement:** {(1 - scenario_data['u_roof_factor']) * 100:.0f}%
    - **Glazing Improvement:** {(1 - scenario_data['u_glazing_factor']) * 100:.0f}%
    """)

# --- DISCLAIMER ---
st.markdown("---")
st.markdown("""
<div class="warning-box">
<strong>⚠️ Important Disclaimer</strong><br>
These results are <strong>indicative only</strong> and based on simplified steady-state thermal modeling (Raissi et al. 2019). 
They should <strong>NOT</strong> be used as the sole basis for investment decisions. Always commission a professional 
energy survey and detailed engineering assessment from a qualified surveyor before proceeding with any capital investment.
<br><br>
<em>Model assumes UK heating season (5,800 hrs/yr), 21°C setpoint, and BEIS 2023 carbon intensity (0.20482 kgCO₂e/kWh)</em>
</div>
""", unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="footer">
<p><strong>CrowAgent™ Platform</strong> | Physics-Informed Campus Thermal Intelligence<br>
© 2026 Aparajita Parihar. All rights reserved. | Not licensed for commercial use without written permission.</p>
</div>
""", unsafe_allow_html=True)
