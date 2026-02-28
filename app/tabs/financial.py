"""
Renders the 'Financial Analysis' tab.

This tab focuses on the economic implications of sustainability interventions,
including Return on Investment (ROI), Net Present Value (NPV), and payback periods.
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from app.segments.base import SegmentHandler
import core.agent
import core.physics
from config.scenarios import SCENARIOS

def render(handler: SegmentHandler, portfolio: list[dict]):
    """
    Renders the financial analysis content.

    Args:
        handler: The segment handler for the current user.
        portfolio: The list of all portfolio entries in session state.
    """
    st.header("📈 Financial Analysis")

    active_portfolio = [
        p for p in portfolio if p["id"] in st.session_state.get("active_analysis_ids", [])
    ]

    if not active_portfolio:
        st.info("Select one or more buildings from the sidebar to see financial analysis.")
        return

    # --- ROI Comparison Table ---
    st.subheader("Return on Investment (ROI) Comparison")
    rows = []
    with st.spinner("Calculating financial metrics..."):
        for entry in active_portfolio:
            building_data = handler.get_building(entry['display_name']) \
                if entry['display_name'] in handler.building_registry \
                else entry['building_data']
            
            for sc_name in handler.scenario_whitelist:
                if sc_name in SCENARIOS and SCENARIOS[sc_name]['install_cost_gbp'] > 0:
                    try:
                        res = core.physics.calculate_thermal_load(building_data, SCENARIOS[sc_name], {"temperature_c": 10.5})
                        rows.append({
                            "Building": entry['display_name'],
                            "Scenario": sc_name,
                            "Cost Saving (£/yr)": res.get('annual_saving_gbp', 0),
                            "Payback (yrs)": res.get('payback_years', 'N/A'),
                            "10yr ROI (£)": res.get('roi_10yr_gbp', 0)
                        })
                    except (ValueError, KeyError) as e: # Per Batch 6, harden calculations
                        st.warning(f"Could not calculate financial metrics for '{entry['display_name']}' with scenario '{sc_name}': {e}")
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.divider()

    # --- NPV Inputs ---
    st.subheader("Net Present Value (NPV) Analysis")
    c1, c2 = st.columns(2)
    with c1:
        st.slider("Discount Rate (%)", 1.0, 15.0, 5.0, 0.5, key="discount_rate")
    with c2:
        st.slider("Analysis Period (Years)", 5, 30, 10, 1, key="analysis_period_yrs")
    st.caption("NPV calculations will use these parameters in future versions.")

    st.divider()

    # --- Budget Optimizer ---
    st.subheader("Budget Optimizer")
    st.info("Find the best value-for-money intervention within a specific budget.")
    budget = st.number_input("Enter your maximum budget (£)", min_value=10000, value=100000, step=10000)
    if st.button("Find Best Investment"):
        with st.spinner("Searching for the optimal investment..."):
            tool_args = {"budget_gbp": budget}
            result = core.agent.execute_tool(
                name="find_best_for_budget",
                args=tool_args,
                buildings=handler.building_registry,
                scenarios=SCENARIOS
            )
            if result.get("error"):
                st.warning(result["error"]) # Per Batch 6, use st.warning for API/tool errors
            elif "top_recommendation" in result:
                rec = result["top_recommendation"]
                st.success(f"**Top Recommendation:** Implement **{rec['scenario']}** on **{rec['building']}**.")
                st.metric("Cost per Tonne CO₂ Saved", f"£{rec['cost_per_tonne_co2']:,.0f}", help="Lower is better.")
                st.metric("Carbon Saved", f"{rec['carbon_saving_t']:.1f} tCO₂e/yr")
                st.metric("Installation Cost", f"£{rec['install_cost_gbp']:,.0f}")
            else:
                st.warning("Could not determine a top recommendation.")