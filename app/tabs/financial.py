import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.physics import calculate_thermal_load
from config.scenarios import SCENARIOS

def render(handler, portfolio):
    """
    Render the Financial Analysis tab.
    """
    st.header("📈 Financial Analysis")
    
    # Inputs
    c1, c2 = st.columns(2)
    with c1:
        discount_rate = st.slider("Discount Rate (%)", 0.0, 15.0, 5.0, 0.5) / 100.0
    with c2:
        analysis_period = st.slider("Analysis Period (Years)", 5, 30, 10)

    # Filter active buildings
    active_ids = st.session_state.get("active_analysis_ids", [])
    active_buildings = [b for b in portfolio if b["id"] in active_ids]
    
    if not active_buildings:
        # Fallback to registry
        active_buildings = [{"name": k, **v} for k, v in handler.building_registry.items()]

    # Calculate ROI Table
    roi_data = []
    weather_stub = {"temperature_c": 10.0} # Use average for financial projection
    
    for b in active_buildings:
        for s_name in handler.scenario_whitelist:
            if s_name == "Baseline (No Intervention)": continue
            
            s_cfg = SCENARIOS.get(s_name)
            if not s_cfg: continue
            
            try:
                res = calculate_thermal_load(b, s_cfg, weather_stub)
                capex = res.get("install_cost_gbp", 0)
                annual_save = res.get("annual_saving_gbp", 0)
                
                # Simple NPV calculation
                npv = -capex
                for y in range(1, analysis_period + 1):
                    npv += annual_save / ((1 + discount_rate) ** y)
                
                roi_data.append({
                    "Building": b["name"],
                    "Scenario": s_name,
                    "Capex (£)": capex,
                    "Annual Saving (£)": annual_save,
                    "Payback (Yrs)": res.get("payback_years", 999),
                    f"NPV ({analysis_period}yr)": round(npv, 0)
                })
            except Exception:
                pass

    if roi_data:
        df = pd.DataFrame(roi_data)
        
        # ROI Table
        st.subheader("Investment Matrix")
        st.dataframe(
            df.style.format({
                "Capex (£)": "£{:,.0f}",
                "Annual Saving (£)": "£{:,.0f}",
                "Payback (Yrs)": "{:.1f}",
                f"NPV ({analysis_period}yr)": "£{:,.0f}"
            }),
            use_container_width=True
        )
        
        # Payback Chart
        st.subheader("Payback Comparison")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["Scenario"],
            y=df["Payback (Yrs)"],
            text=df["Building"],
            marker_color="#00C2A8"
        ))
        fig.update_layout(yaxis_title="Years to Payback")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No financial data available. Check building parameters.")