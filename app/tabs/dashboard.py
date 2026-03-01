import html as html_mod
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import app.branding as branding
from app.branding import render_card
from app.visualization_3d import render_campus_3d_map
from core.physics import calculate_thermal_load
from config.scenarios import SCENARIOS
from config.constants import CI_ELECTRICITY, ELEC_COST_PER_KWH

def render(handler, weather: dict, portfolio: list[dict]) -> None:
    """
    Render the main Dashboard tab.
    """
    if not portfolio:
        st.info("Portfolio is empty. Add a building in the sidebar to begin.")
        return

    # 1. KPI Cards
    # Calculate aggregate metrics for the active portfolio/segment
    total_energy_mwh = 0.0
    total_carbon_t = 0.0
    
    # Use the first available scenario for "potential" savings display, or baseline
    # For a real dashboard, we might sum up the 'Baseline' vs 'Selected Scenario'
    # Here we show Baseline totals for the current segment assets
    
    active_buildings = handler.building_registry
    
    # Simple aggregation for KPIs based on registry (simulating portfolio view)
    for b_name, b_data in active_buildings.items():
        total_energy_mwh += b_data.get("baseline_energy_mwh", 0)
    
    total_carbon_t = total_energy_mwh * CI_ELECTRICITY
    total_cost_k = (total_energy_mwh * 1000 * ELEC_COST_PER_KWH) / 1000

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_card("Portfolio Energy", f"{total_energy_mwh:,.0f}", "MWh/yr", "accent-teal")
    with c2:
        render_card("Carbon Footprint", f"{total_carbon_t:,.1f}", "tCO₂e/yr", "accent-gold")
    with c3:
        render_card("Est. Energy Cost", f"£{total_cost_k:,.0f}k", "per annum", "accent-navy")
    with c4:
        render_card("Active Assets", f"{len(active_buildings)}", "Buildings", "accent-green")

    # 2. Weather & Map Context
    st.markdown("---")
    col_map, col_wx = st.columns([3, 1])
    
    with col_wx:
        st.subheader("Live Conditions")
        _temp = html_mod.escape(str(weather.get('temperature_c', '--')))
        _cond = html_mod.escape(str(weather.get('condition', 'Unknown')))
        _wind = html_mod.escape(str(weather.get('wind_speed_mph', '--')))
        _hum  = html_mod.escape(str(weather.get('humidity_pct', '--')))
        _loc  = html_mod.escape(str(weather.get('location_name', 'Unknown')))
        branding.render_html(f"""
        <div class="wx-widget">
            <div class="wx-temp">{_temp}°C</div>
            <div class="wx-desc">{_cond}</div>
            <div class="wx-row">💨 Wind: {_wind} mph</div>
            <div class="wx-row">💧 Humidity: {_hum}%</div>
            <div class="wx-row">📍 {_loc}</div>
        </div>
        """)

        st.caption(f"Source: {weather.get('source', 'Unknown')}")

    with col_map:
        # Render the 3D map with scenario selector
        # We pass the handler's scenario whitelist
        render_campus_3d_map(handler.scenario_whitelist, weather)

    # 3. Portfolio Table
    st.subheader("Asset Performance Summary")
    
    if not active_buildings:
        st.info("No buildings in this segment registry.")
    else:
        rows = []
        for b_name, b_data in active_buildings.items():
            rows.append({
                "Building": b_name,
                "Type": b_data.get("building_type", "Unknown"),
                "Area (m²)": f"{b_data.get('floor_area_m2', 0):,}",
                "Baseline (MWh)": f"{b_data.get('baseline_energy_mwh', 0):,.0f}",
                "Built": b_data.get("built_year", "-")
            })
        
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # 4. Comparative Analysis (Thermal Load)
    st.subheader("Thermal Load Analysis")
    st.caption("Physics-based simulation of heating demand under current weather conditions.")
    
    # Compare Baseline vs First Upgrade for all buildings
    baseline_sc = SCENARIOS.get("Baseline (No Intervention)")
    upgrade_sc_name = handler.scenario_whitelist[1] if len(handler.scenario_whitelist) > 1 else handler.scenario_whitelist[0]
    upgrade_sc = SCENARIOS.get(upgrade_sc_name)

    if baseline_sc and upgrade_sc:
        fig = go.Figure()
        b_names = list(active_buildings.keys())
        
        # Calculate for each building
        base_vals = [calculate_thermal_load(active_buildings[b], baseline_sc, weather).get("scenario_energy_mwh", 0) for b in b_names]
        upg_vals = [calculate_thermal_load(active_buildings[b], upgrade_sc, weather).get("scenario_energy_mwh", 0) for b in b_names]

        fig.add_trace(go.Bar(name="Baseline", x=b_names, y=base_vals, marker_color="#5A7A90"))
        fig.add_trace(go.Bar(name=upgrade_sc_name, x=b_names, y=upg_vals, marker_color="#00C2A8"))
        
        fig.update_layout(barmode='group', height=350, margin=dict(t=20, b=20), 
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          font=dict(color='#CBD8E6'))
        st.plotly_chart(fig, use_container_width=True)