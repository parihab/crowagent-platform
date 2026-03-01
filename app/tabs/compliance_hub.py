import streamlit as st
import plotly.graph_objects as go
import app.compliance as compliance

def render(handler, portfolio):
    """
    Render the Compliance Hub tab based on segment-specific checks.
    """
    st.header("🏛️ UK Compliance Hub")
    
    # Filter active buildings
    active_ids = st.session_state.get("active_analysis_ids", [])
    active_buildings = [b for b in portfolio if b["id"] in active_ids]
    
    if not active_buildings:
        active_buildings = [{"name": k, **v} for k, v in handler.building_registry.items()]

    checks = handler.compliance_checks
    
    # ── EPC / MEES ───────────────────────────────────────────────────────────
    if "epc_mees" in checks:
        st.subheader("EPC & MEES (Minimum Energy Efficiency Standards)")
        st.markdown("Target: **EPC C by 2028**, **EPC B by 2030** (Non-Domestic)")
        
        for b in active_buildings:
            with st.expander(f"{b['name']} - EPC Analysis", expanded=True):
                # Estimate EPC
                try:
                    est = compliance.estimate_epc_rating(
                        floor_area_m2=b.get("floor_area_m2", 100),
                        annual_energy_kwh=b.get("baseline_energy_mwh", 10) * 1000,
                        u_wall=b.get("u_value_wall", 1.0),
                        u_roof=b.get("u_value_roof", 0.5),
                        u_glazing=b.get("u_value_glazing", 2.0),
                        glazing_ratio=b.get("glazing_ratio", 0.3)
                    )
                    
                    c1, c2 = st.columns([1, 3])
                    with c1:
                        st.metric("Estimated Band", est["epc_band"], f"SAP {est['sap_score']}")
                        st.caption(est["recommendation"])
                    with c2:
                        # Gap Analysis
                        gap = compliance.mees_gap_analysis(est["sap_score"], target_band="C")
                        if gap["achievable"]:
                            st.success("MEES 2028 (Band C) is achievable.")
                            if gap["recommended_measures"]:
                                st.write("**Recommended Measures:**")
                                for m in gap["recommended_measures"]:
                                    st.write(f"- {m['name']} (Lift: +{m['sap_lift']} SAP)")
                        else:
                            st.error("Deep retrofit required to meet MEES 2028.")
                except Exception as e:
                    st.warning(f"Could not calculate EPC: {e}")

    # ── Part L / FHS ─────────────────────────────────────────────────────────
    if "part_l" in checks or "fhs" in checks:
        st.subheader("Part L 2021 & Future Homes Standard")
        for b in active_buildings:
            res = compliance.part_l_compliance_check(
                u_wall=b.get("u_value_wall", 1.0),
                u_roof=b.get("u_value_roof", 0.5),
                u_glazing=b.get("u_value_glazing", 2.0),
                floor_area_m2=b.get("floor_area_m2", 100),
                annual_energy_kwh=b.get("baseline_energy_mwh", 10) * 1000
            )
            st.markdown(f"**{b['name']}**: {res['overall_verdict']}")
            if res["improvement_actions"]:
                for action in res["improvement_actions"]:
                    st.warning(action)

    # ── SECR ─────────────────────────────────────────────────────────────────
    if "secr" in checks:
        st.subheader("SECR Carbon Reporting")
        st.info("Scope 1 & 2 Carbon Baseline calculation is available for this segment.")
        # (Simplified placeholder for SECR logic)
        total_mwh = sum(b.get("baseline_energy_mwh", 0) for b in active_buildings)
        st.metric("Total Portfolio Energy", f"{total_mwh:,.0f} MWh/yr")