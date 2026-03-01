import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.physics import calculate_thermal_load
from config.scenarios import SCENARIOS
from config.constants import ELEC_COST_PER_KWH

def render(handler, portfolio: list[dict]) -> None:
    """
    Render the Financial Analysis tab.
    """
    if not portfolio:
        st.info("Portfolio is empty. Add a building in the sidebar to begin.")
        return

    st.subheader("Investment & Return Analysis")
    
    # Controls
    c1, c2 = st.columns(2)
    with c1:
        discount_rate = st.slider("Discount Rate (%)", 1.0, 15.0, 5.0, 0.5) / 100.0
    with c2:
        term_years = st.slider("Analysis Term (Years)", 5, 25, 10)

    # Data Prep
    buildings = handler.building_registry
    scenarios = [s for s in handler.scenario_whitelist if s != "Baseline (No Intervention)"]
    
    if not buildings or not scenarios:
        st.info("Insufficient data for financial analysis.")
        return

    # ROI Table Construction
    roi_data = []
    
    # Dummy weather for steady-state annual calc (using annual avg approx 10.5C)
    avg_weather = {"temperature_c": 10.5}
    
    for b_name, b_data in buildings.items():
        # Get baseline first
        bl_res = calculate_thermal_load(b_data, SCENARIOS["Baseline (No Intervention)"], avg_weather)
        bl_cost = bl_res["annual_saving_gbp"] # This is saving vs itself (0), we need absolute cost
        # Re-calc absolute baseline cost
        bl_energy = bl_res["scenario_energy_mwh"]
        bl_annual_cost = bl_energy * 1000 * ELEC_COST_PER_KWH

        for s_name in scenarios:
            sc = SCENARIOS[s_name]
            res = calculate_thermal_load(b_data, sc, avg_weather)
            
            saving_gbp = res["annual_saving_gbp"]
            capex = res["install_cost_gbp"]
            payback = res["payback_years"]
            
            # Simple NPV
            cash_flows = [-capex] + [saving_gbp] * term_years
            npv = sum(cf / ((1 + discount_rate) ** t) for t, cf in enumerate(cash_flows))
            
            roi_data.append({
                "Building": b_name,
                "Intervention": s_name,
                "Capex (£)": capex,
                "Annual Saving (£)": saving_gbp,
                "Payback (Yrs)": payback if payback else 999,
                f"{term_years}-Yr NPV (£)": npv
            })

    df = pd.DataFrame(roi_data)
    
    # Display Table
    st.dataframe(
        df.style.format({
            "Capex (£)": "£{:,.0f}",
            "Annual Saving (£)": "£{:,.0f}",
            "Payback (Yrs)": "{:.1f}",
            f"{term_years}-Yr NPV (£)": "£{:,.0f}"
        }),
        use_container_width=True,
        hide_index=True
    )

    # Visualisation
    st.subheader("Payback Period Comparison")
    fig = go.Figure()
    for s_name in scenarios:
        subset = df[df["Intervention"] == s_name]
        fig.add_trace(go.Bar(x=subset["Building"], y=subset["Payback (Yrs)"], name=s_name))
    
    fig.update_layout(yaxis_title="Years", barmode='group', height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CBD8E6'))
    st.plotly_chart(fig, use_container_width=True)