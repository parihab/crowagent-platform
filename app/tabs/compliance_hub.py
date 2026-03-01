import streamlit as st
import app.compliance as compliance
from app.branding import render_card

def render(handler, portfolio: list[dict]) -> None:
    """
    Render the UK Compliance Hub tab.
    Dynamically renders panels based on handler.compliance_checks.
    """
    if not portfolio:
        st.info("Portfolio is empty. Add a building in the sidebar to begin.")
        return

    st.header(f"Compliance: {handler.display_label}")
    
    checks = handler.compliance_checks
    buildings = handler.building_registry
    
    if not buildings:
        st.info("No buildings available for compliance checks.")
        return

    # 1. EPC / MEES Panel
    if "epc_mees" in checks:
        st.subheader("🏷️ EPC & MEES (Minimum Energy Efficiency Standards)")
        st.info("Target: EPC Band C by 2028 (Private Rented Sector)")
        
        for b_name, b_data in buildings.items():
            with st.expander(f"{b_name}", expanded=True):
                # Estimate EPC
                res = compliance.estimate_epc_rating(
                    floor_area_m2=b_data["floor_area_m2"],
                    annual_energy_kwh=b_data["baseline_energy_mwh"] * 1000,
                    u_wall=b_data["u_value_wall"],
                    u_roof=b_data["u_value_roof"],
                    u_glazing=b_data["u_value_glazing"],
                    glazing_ratio=b_data["glazing_ratio"]
                )
                
                c1, c2 = st.columns([1, 3])
                with c1:
                    st.metric("Est. Rating", f"{res['sap_score']} ({res['epc_band']})")
                    st.caption(f"EUI: {res['eui_kwh_m2']} kWh/m²")
                with c2:
                    if res["mees_2028_compliant"]:
                        st.success(f"✅ {res['recommendation']}")
                    else:
                        st.warning(f"⚠️ {res['recommendation']}")
                        
                        # Gap Analysis
                        gap = compliance.mees_gap_analysis(res["sap_score"], "C")
                        if gap["recommended_measures"]:
                            st.markdown("**Recommended Upgrades:**")
                            for m in gap["recommended_measures"]:
                                st.markdown(f"- {m['name']} (Lift: +{m['sap_lift']} pts)")

    # 2. SECR Panel
    if "secr" in checks:
        st.subheader("🏭 SECR Carbon Reporting")
        st.caption("Streamlined Energy and Carbon Reporting (Scope 1 & 2)")
        
        total_elec = sum(b["baseline_energy_mwh"] for b in buildings.values()) * 1000
        # Dummy gas/fleet for demonstration
        res = compliance.calculate_carbon_baseline(elec_kwh=total_elec, gas_kwh=total_elec*0.5, fleet_miles=5000)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Scope 1 & 2", f"{res['total_tco2e']} tCO₂e")
        c2.metric("Scope 1 (Gas/Fleet)", f"{res['scope1_tco2e']} tCO₂e")
        c3.metric("Scope 2 (Grid Elec)", f"{res['scope2_tco2e']} tCO₂e")
        
        if res["secr_threshold_check"]["supply_chain_pressure"]:
            st.warning("⚠️ Carbon footprint exceeds 50t. Supply chain reporting likely required.")