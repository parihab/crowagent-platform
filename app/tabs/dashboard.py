import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from app.branding import render_card
from core.physics import calculate_thermal_load
from app.visualization_3d import render_campus_3d_map
from config.scenarios import SCENARIOS

def render(handler, weather, portfolio):
    """
    Render the Dashboard tab.
    """
    # Filter active buildings
    active_ids = st.session_state.get("active_analysis_ids", [])
    active_buildings = [b for b in portfolio if b["id"] in active_ids]
    
    # If no portfolio items, use default registry from handler
    if not active_buildings:
        active_buildings = [{"name": k, **v} for k, v in handler.building_registry.items()]

    # ── KPI Cards ────────────────────────────────────────────────────────────
    # Calculate aggregate savings for the first default scenario vs baseline
    scenario_name = handler.default_scenarios[1] if len(handler.default_scenarios) > 1 else "Baseline (No Intervention)"
    scenario_cfg = SCENARIOS.get(scenario_name)
    
    total_energy_saved = 0.0
    total_carbon_saved = 0.0
    total_cost_saved = 0.0
    
    for b in active_buildings:
        try:
            res = calculate_thermal_load(b, scenario_cfg, weather)
            total_energy_saved += res.get("energy_saving_mwh", 0)
            total_carbon_saved += res.get("carbon_saving_t", 0)
            total_cost_saved += res.get("annual_saving_gbp", 0)
        except Exception:
            pass

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_card("Energy Saved", f"{total_energy_saved:,.0f}", "MWh/yr", "accent-teal")
    with k2:
        render_card("Carbon Saved", f"{total_carbon_saved:,.1f}", "tCO₂e/yr", "accent-gold")
    with k3:
        render_card("Cost Saved", f"£{total_cost_saved:,.0f}", "per year", "accent-green")
    with k4:
        render_card("Active Assets", str(len(active_buildings)), "Buildings", "accent-navy")

    # ── 3D Map ───────────────────────────────────────────────────────────────
    st.markdown("### 🗺️ Campus Digital Twin")
    # Convert list of dicts to dict of dicts for the map renderer
    buildings_map = {b["name"]: b for b in active_buildings}
    render_campus_3d_map(handler.default_scenarios, weather)

    # ── Thermal Load Chart ───────────────────────────────────────────────────
    st.markdown("### ⚡ Thermal Load Analysis")
    
    if not active_buildings:
        st.info("No active buildings to analyse.")
        return

    # Prepare data for chart
    chart_data = []
    for b in active_buildings:
        for s_name in handler.default_scenarios:
            s_cfg = SCENARIOS.get(s_name)
            if not s_cfg: continue
            try:
                res = calculate_thermal_load(b, s_cfg, weather)
                chart_data.append({
                    "Building": b["name"],
                    "Scenario": s_name,
                    "Energy (MWh)": res["scenario_energy_mwh"]
                })
            except Exception:
                pass
    
    if chart_data:
        df_chart = pd.DataFrame(chart_data)
        fig = go.Figure()
        for s_name in handler.default_scenarios:
            subset = df_chart[df_chart["Scenario"] == s_name]
            fig.add_trace(go.Bar(
                x=subset["Building"],
                y=subset["Energy (MWh)"],
                name=s_name
            ))
        
        fig.update_layout(barmode='group', yaxis_title="Annual Energy (MWh)")
        st.plotly_chart(fig, use_container_width=True)

    # ── Portfolio Summary ────────────────────────────────────────────────────
    st.markdown("### 📋 Portfolio Summary")
    if active_buildings:
        summary_rows = []
        for b in active_buildings:
            summary_rows.append({
                "Name": b["name"],
                "Type": b.get("building_type", "Unknown"),
                "Area (m²)": b.get("floor_area_m2"),
                "Built": b.get("built_year"),
                "EPC": b.get("epc_band", "-")
            })
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)