"""
📊 Dashboard Tab Renderer
=========================
Renders the main dashboard view for all segments.
Includes:
- KPI Cards (Energy, Carbon, Cost, Payback)
- 3D Digital Twin Map
- Live Weather Widget
- Thermal Load Analysis Chart
- Portfolio Asset Table
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import app.branding as branding
import core.physics as physics
from config.scenarios import SCENARIOS
from app.portfolio_modal import render_portfolio_modal


def render(handler, weather: dict, portfolio: list[dict]) -> None:
    """
    Renders the dashboard tab content.

    Args:
        handler: The active SegmentHandler instance.
        weather: Current weather data dictionary.
        portfolio: Full list of portfolio assets (will be filtered by segment).
    """
    # 0. Modal Trigger & Logic
    if st.session_state.get("show_portfolio_modal"):
        render_portfolio_modal()

    # Header Row with Portfolio Trigger
    h_col1, h_col2 = st.columns([4, 1])
    with h_col2:
        if st.button(f"📂 Manage Portfolio ({len(portfolio)})", key="btn_dash_manage_port", use_container_width=True):
            st.session_state.show_portfolio_modal = True
            st.rerun()

    # 1. Filter portfolio for this segment
    segment_portfolio = [p for p in portfolio if p.get("segment") == handler.segment_id]

    if not segment_portfolio:
        st.info("Portfolio is empty. Add a building in the sidebar to begin analysis.")
        return

    # 2. Resolve active scenarios
    selected_names = st.session_state.get("selected_scenario_names", [])
    if not selected_names:
        selected_names = handler.default_scenarios

    # Ensure Baseline is present for comparison
    if "Baseline (No Intervention)" not in selected_names:
        selected_names = ["Baseline (No Intervention)"] + selected_names

    # 3. Calculate results
    tariff = st.session_state.get("energy_tariff_gbp_per_kwh", 0.28)
    scenario_totals = {}

    for s_name in selected_names:
        if s_name not in SCENARIOS:
            continue

        s_data = SCENARIOS[s_name]
        totals = {
            "annual_energy_mwh": 0.0,
            "carbon_saving_tco2": 0.0,
            "cost_saving_gbp": 0.0,
            "install_cost_gbp": 0.0,
            "energy_saving_mwh": 0.0,
        }

        for building in segment_portfolio:
            r = physics.calculate_thermal_load(building, s_data, weather, tariff)
            totals["annual_energy_mwh"] += r["annual_energy_mwh"]
            totals["carbon_saving_tco2"] += r["carbon_saving_tco2"]
            totals["cost_saving_gbp"] += r["cost_saving_gbp"]
            totals["energy_saving_mwh"] += r["energy_saving_mwh"]
            totals["install_cost_gbp"] += s_data.get("install_cost_gbp", 0.0)

        scenario_totals[s_name] = totals

    # 4. Determine "Best" scenario for KPIs (max energy saving)
    comparison_scenarios = [s for s in selected_names if s != "Baseline (No Intervention)"]
    if comparison_scenarios:
        best_scenario = max(comparison_scenarios, key=lambda s: scenario_totals[s]["energy_saving_mwh"])
        kpi_data = scenario_totals[best_scenario]
    else:
        kpi_data = scenario_totals.get("Baseline (No Intervention)", {})

    # 5. Render KPIs
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        branding.render_card(
            label="Energy Saved",
            value=f"{kpi_data.get('energy_saving_mwh', 0):,.1f}",
            subtext="MWh / year",
            accent_class="accent-teal",
        )
    with col2:
        branding.render_card(
            label="Carbon Abated",
            value=f"{kpi_data.get('carbon_saving_tco2', 0):,.1f}",
            subtext="tCO₂e / year",
            accent_class="accent-green",
        )
    with col3:
        branding.render_card(
            label="Cost Saved",
            value=f"£{kpi_data.get('cost_saving_gbp', 0):,.0f}",
            subtext="per year",
            accent_class="accent-gold",
        )
    with col4:
        total_install = kpi_data.get("install_cost_gbp", 0)
        total_save = kpi_data.get("cost_saving_gbp", 0)
        payback_str = f"{(total_install / total_save):.1f}" if total_save > 0 else "-"
        branding.render_card(
            label="Est. Payback",
            value=payback_str,
            subtext="Years",
            accent_class="accent-navy",
        )

    st.markdown("---")

    # 6. Render 3D Map & Weather
    c_map, c_wx = st.columns([2, 1])

    with c_map:
        st.markdown('<div class="sec-hdr">Campus / Portfolio Digital Twin</div>', unsafe_allow_html=True)
        from app.visualization_3d import render_3d_building
        render_3d_building(segment_portfolio)

    with c_wx:
        st.markdown('<div class="sec-hdr">Live Conditions</div>', unsafe_allow_html=True)
        temp = weather.get("temperature_c", 0)
        desc = weather.get("description", "Unknown").title()
        loc = weather.get("location_name", "Unknown Location")

        st.markdown(
            f"""
            <div class="wx-widget">
                <div style="display:flex; justify-content:space-between; align-items:start;">
                    <div>
                        <div class="wx-desc">{desc}</div>
                        <div class="wx-temp">{temp:.1f}°C</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="color:#8FBCCE; font-size:1.5rem;">☁️</div>
                    </div>
                </div>
                <div class="wx-row">📍 {loc}</div>
                <div class="wx-row">💨 Wind: {weather.get('wind_speed_mph', 0)} mph</div>
                <div class="wx-row">💧 Humidity: {weather.get('humidity_pct', 0)}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 7. Render Thermal Load Chart
    st.markdown('<div class="sec-hdr">Thermal Load Analysis</div>', unsafe_allow_html=True)

    chart_data = []
    for s_name in selected_names:
        if s_name in scenario_totals:
            chart_data.append({
                "Scenario": s_name,
                "Energy (MWh)": scenario_totals[s_name]["annual_energy_mwh"]
            })

    if chart_data:
        df_chart = pd.DataFrame(chart_data)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_chart["Scenario"],
            y=df_chart["Energy (MWh)"],
            marker_color='#00C2A8',
            text=df_chart["Energy (MWh)"].apply(lambda x: f"{x:.1f}"),
            textposition='auto'
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=20, b=40, l=40, r=20),
            height=350,
            yaxis_title="Annual Energy (MWh)",
            font=dict(family="Nunito Sans")
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # 8. Portfolio Table
    st.markdown('<div class="sec-hdr">Portfolio Assets</div>', unsafe_allow_html=True)

    table_rows = []
    for b in segment_portfolio:
        table_rows.append({
            "Building Name": b.get("name", "Unknown"),
            "Postcode": b.get("postcode", "-"),
            "Floor Area (m²)": b.get("floor_area_m2", 0),
            "Baseline Energy (MWh)": b.get("baseline_energy_mwh", 0),
            "EPC Band": b.get("epc_band", "N/A"),
        })

    st.dataframe(
        pd.DataFrame(table_rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Floor Area (m²)": st.column_config.NumberColumn(format="%.0f"),
            "Baseline Energy (MWh)": st.column_config.NumberColumn(format="%.1f"),
        },
    )