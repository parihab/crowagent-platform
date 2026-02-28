"""
Renders the 'UK Compliance Hub' tab.

This tab's content is dynamically generated based on the compliance checks
specified in the active segment handler, ensuring segment isolation.
"""
from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go

from app.segments.base import SegmentHandler
import app.compliance as compliance


def _render_epc_mees(handler: SegmentHandler, building_data: dict):
    """Renders the EPC/MEES compliance panel."""
    st.subheader("EPC & MEES Compliance")
    epc_result = compliance.estimate_epc_rating(building_data)
    mees_result = compliance.mees_gap_analysis(epc_result['sap_points'])

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=epc_result['sap_points'],
        title={'text': f"Estimated EPC: Band {epc_result['band']}"},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#00C2A8"}}
    ))
    st.plotly_chart(fig, use_container_width=True)
    st.table(mees_result)

def _render_part_l(handler: SegmentHandler, building_data: dict):
    """Renders the Part L compliance panel."""
    st.subheader("Part L (New Buildings) U-Value Check")
    part_l_results = compliance.part_l_check(building_data)
    st.table(part_l_results)

def _render_fhs(handler: SegmentHandler, building_data: dict):
    """Renders the Future Homes Standard compliance panel."""
    st.subheader("Future Homes Standard (FHS) Check")
    # This would call a dedicated FHS function in a real app
    fhs_results = compliance.part_l_check(building_data, is_fhs=True)
    st.metric("Primary Energy Target", f"{fhs_results[0]['Target']} kWh/m²/yr",
              delta=f"Actual: {fhs_results[0]['Actual']}",
              delta_color="inverse" if fhs_results[0]['Compliant'] == '✅' else 'normal')

def _render_secr(handler: SegmentHandler, building_data: dict):
    """Renders the SECR compliance panel."""
    st.subheader("SECR Carbon Baseline")
    secr_result = compliance.secr_carbon_baseline(building_data)
    st.metric("Total Baseline Emissions", f"{secr_result['total_tco2e']:.1f} tCO₂e")
    st.write(f"Scope 1 (Gas/Oil): {secr_result['scope1_tco2e']:.1f} tCO₂e")
    st.write(f"Scope 2 (Electricity): {secr_result['scope2_tco2e']:.1f} tCO₂e")


def render(handler: SegmentHandler, portfolio: list[dict]):
    """
    Renders the compliance hub content by dispatching to panel renderers.
    """
    st.header("🏛️ UK Compliance Hub")

    active_portfolio = [
        p for p in portfolio if p["id"] in st.session_state.get("active_analysis_ids", [])
    ]

    if not active_portfolio:
        st.info("Select a building from the sidebar to see compliance checks.")
        return

    # For simplicity, we run checks on the first selected building
    entry = active_portfolio[0]
    building_data = handler.get_building(entry['display_name']) \
        if entry['display_name'] in handler.building_registry \
        else entry['building_data']

    st.subheader(f"Compliance for: {entry['display_name']}")

    # Map check keys to renderer functions
    RENDERER_MAP = {
        "epc_mees": _render_epc_mees,
        "part_l": _render_part_l,
        "fhs": _render_fhs,
        "secr": _render_secr,
    }

    for check_key in handler.compliance_checks:
        if renderer := RENDERER_MAP.get(check_key):
            with st.container(border=True):
                renderer(handler, building_data)
        else:
            st.warning(f"No renderer found for compliance check: '{check_key}'")