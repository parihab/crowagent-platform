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
from config.constants import FHS_MAX_PRIMARY_ENERGY


def _render_epc_mees(handler: SegmentHandler, building_data: dict):
    """Renders the EPC/MEES compliance panel."""
    st.subheader("EPC & MEES Compliance")
    try:
        epc_result = compliance.estimate_epc_rating(
            floor_area_m2=float(building_data.get("floor_area_m2", 1000)),
            annual_energy_kwh=float(building_data.get("baseline_energy_mwh", 100)) * 1000,
            u_wall=float(building_data.get("u_value_wall", 1.8)),
            u_roof=float(building_data.get("u_value_roof", 2.0)),
            u_glazing=float(building_data.get("u_value_glazing", 2.8)),
            glazing_ratio=float(building_data.get("glazing_ratio", 0.30)),
            building_type=building_data.get("building_type", "commercial"),
        )
    except (ValueError, KeyError) as e:
        st.warning(f"EPC estimation failed: {e}")
        return

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=epc_result["sap_score"],
        title={"text": f"Estimated EPC: Band {epc_result['epc_band']}"},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#00C2A8"}},
    ))
    st.plotly_chart(fig, use_container_width=True)

    try:
        mees_result = compliance.mees_gap_analysis(epc_result["sap_score"])
        st.write(epc_result["recommendation"])
        st.metric("SAP Gap to MEES 2028 (Band C)", f"{mees_result['sap_gap']:.1f} pts")
        if mees_result["recommended_measures"]:
            st.table([
                {"Measure": m["name"], "SAP Lift": m["sap_lift"],
                 "Cost Range (GBP)": f"{m['cost_low']:,}--{m['cost_high']:,}"}
                for m in mees_result["recommended_measures"]
            ])
    except (ValueError, KeyError) as e:
        st.warning(f"MEES gap analysis failed: {e}")


def _render_part_l(handler: SegmentHandler, building_data: dict):
    """Renders the Part L compliance panel."""
    st.subheader("Part L (New Buildings) U-Value Check")
    try:
        part_l_results = compliance.part_l_compliance_check(
            u_wall=float(building_data.get("u_value_wall", 1.8)),
            u_roof=float(building_data.get("u_value_roof", 2.0)),
            u_glazing=float(building_data.get("u_value_glazing", 2.8)),
            floor_area_m2=float(building_data.get("floor_area_m2", 1000)),
            annual_energy_kwh=float(building_data.get("baseline_energy_mwh", 100)) * 1000,
            building_type=building_data.get("building_type", "commercial"),
        )
    except (ValueError, KeyError) as e:
        st.warning(f"Part L check failed: {e}")
        return

    st.write(part_l_results["overall_verdict"])
    st.table([
        {
            "Element": item["element"],
            "Proposed (W/m2K)": item["proposed_u"],
            "Target (W/m2K)": item["target_u"],
            "Pass": "PASS" if item["pass"] else "FAIL",
            "Gap": item["gap"],
        }
        for item in part_l_results["compliance_items"]
    ])


def _render_fhs(handler: SegmentHandler, building_data: dict):
    """Renders the Future Homes Standard compliance panel."""
    st.subheader("Future Homes Standard (FHS) Check")
    try:
        fhs_results = compliance.part_l_compliance_check(
            u_wall=float(building_data.get("u_value_wall", 1.6)),
            u_roof=float(building_data.get("u_value_roof", 2.0)),
            u_glazing=float(building_data.get("u_value_glazing", 2.8)),
            floor_area_m2=float(building_data.get("floor_area_m2", 120)),
            annual_energy_kwh=float(building_data.get("baseline_energy_mwh", 18)) * 1000,
            building_type="residential",
        )
    except (ValueError, KeyError) as e:
        st.warning(f"FHS check failed: {e}")
        return

    compliant_symbol = "PASS" if fhs_results["fhs_ready"] else "FAIL"
    st.metric(
        "Primary Energy Intensity",
        f"{fhs_results['primary_energy_est']} kWh/m2/yr",
        delta=f"Target: <= {FHS_MAX_PRIMARY_ENERGY} kWh/m2/yr",
        delta_color="inverse",
    )
    st.write(f"FHS Ready: {compliant_symbol}")
    st.write(fhs_results["overall_verdict"])


def _render_secr(handler: SegmentHandler, building_data: dict):
    """Renders the SECR compliance panel."""
    st.subheader("SECR Carbon Baseline")
    try:
        secr_result = compliance.calculate_carbon_baseline(
            elec_kwh=float(building_data.get("baseline_energy_mwh", 100)) * 1000,
            floor_area_m2=float(building_data.get("floor_area_m2", 1000)),
        )
    except (ValueError, KeyError) as e:
        st.warning(f"SECR calculation failed: {e}")
        return

    st.metric("Total Baseline Emissions", f"{secr_result['total_tco2e']:.1f} tCO2e")
    st.write(f"Scope 1 (Gas/Oil): {secr_result['scope1_tco2e']:.1f} tCO2e")
    st.write(f"Scope 2 (Electricity): {secr_result['scope2_tco2e']:.1f} tCO2e")


def render(handler: SegmentHandler, portfolio: list[dict]):
    """
    Renders the compliance hub content by dispatching to panel renderers.
    """
    st.header("UK Compliance Hub")

    active_portfolio = [
        p for p in portfolio if p["id"] in st.session_state.get("active_analysis_ids", [])
    ]

    if not active_portfolio:
        st.info("Select a building from the sidebar to see compliance checks.")
        return

    entry = active_portfolio[0]
    building_data = handler.get_building(entry["display_name"]) \
        if entry["display_name"] in handler.building_registry \
        else entry["building_data"]

    st.subheader(f"Compliance for: {entry['display_name']}")

    RENDERER_MAP = {
        "epc_mees": _render_epc_mees,
        "part_l":   _render_part_l,
        "fhs":      _render_fhs,
        "secr":     _render_secr,
    }

    for check_key in handler.compliance_checks:
        if renderer := RENDERER_MAP.get(check_key):
            with st.container(border=True):
                renderer(handler, building_data)
        else:
            st.warning(f"No renderer found for compliance check: '{check_key}'")
