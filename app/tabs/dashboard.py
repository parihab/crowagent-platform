"""
Renders the 'Dashboard' tab.

This tab provides an at-a-glance overview of the portfolio, including
key performance indicators (KPIs), a 3D campus visualization, and
high-level energy/carbon analysis.
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from app.main import _card # As per spec, import shared component from main
from app.segments.base import SegmentHandler
import core.physics as physics

def render(handler: SegmentHandler, weather: dict, portfolio: list[dict]):
    """
    Renders the dashboard content.

    Args:
        handler: The segment handler for the current user.
        weather: The current weather data dictionary.
        portfolio: The list of all portfolio entries in session state.
    """
    st.header("📊 Portfolio Dashboard")

    active_portfolio = [
        p for p in portfolio if p["id"] in st.session_state.get("active_analysis_ids", [])
    ]

    if not active_portfolio:
        st.info("Select one or more buildings from the 'Portfolio Management' section in the sidebar to see the dashboard.")
        return

    # --- KPI Cards ---
    # In a real implementation, these would be calculated based on selected scenarios.
    # For this implementation, we show placeholder values.
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _card("Energy Saved", "1,250", "MWh/yr", "accent-green")
    with col2:
        _card("Carbon Saved", "255", "tCO₂e/yr", "accent-green")
    with col3:
        _card("Cost Saved", "£350k", "/yr", "accent-green")
    with col4:
        _card("Avg. Payback", "7.8", "Years", "")

    st.divider()

    # --- Portfolio Summary ---
    # Handler-agnostic: display for all segments (no segment branching permitted).
    st.subheader("Portfolio Summary")
    st.dataframe(pd.DataFrame(active_portfolio), use_container_width=True)

    st.divider()

    # --- Thermal Load Bar Chart ---
    st.subheader("Thermal Load Scenario Comparison")
    
    # For simplicity, we compare scenarios for the first active building
    building_to_chart = active_portfolio[0]
    building_data = handler.get_building(building_to_chart['display_name']) \
        if building_to_chart['display_name'] in handler.building_registry \
        else building_to_chart['building_data']

    scenarios_to_chart = handler.scenario_whitelist
    chart_data = []

    with st.spinner("Calculating thermal loads for chart..."):
        from config.scenarios import SCENARIOS
        for sc_name in scenarios_to_chart:
            if sc_name in SCENARIOS:
                try:
                    result = physics.calculate_thermal_load(building_data, SCENARIOS[sc_name], weather)
                    chart_data.append({"scenario": sc_name, "energy": result["scenario_energy_mwh"]})
                except (ValueError, KeyError) as e: # Per Batch 6, tighten exception clauses
                    st.warning(f"Could not calculate '{sc_name}': {e}")

    if chart_data:
        fig = go.Figure(data=[
            go.Bar(
                x=[d['scenario'] for d in chart_data],
                y=[d['energy'] for d in chart_data],
                text=[f"{d['energy']:.0f}" for d in chart_data],
                textposition='auto',
            )
        ])
        fig.update_layout(title=f"Annual Energy Consumption for '{building_to_chart['display_name']}'",
                          yaxis_title="Energy (MWh/yr)")
        st.plotly_chart(fig, use_container_width=True)