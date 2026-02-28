"""
Renders the Dashboard tab.

Shows segment-responsive KPI cards, energy/carbon charts, technical
parameters table, building specification expander, and the 3D campus map.
When a portfolio is loaded, shows aggregated portfolio KPIs, grouped bar
charts, and a PyDeck 3D spatial view.
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from app.segments.base import SegmentHandler
import core.physics as physics
import app.compliance as compliance
import services.location as loc
from config.scenarios import SCENARIOS

CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Nunito Sans, sans-serif", size=11, color="#071A2F"),
    margin=dict(t=20, b=10, l=0, r=0),
    height=300,
    yaxis=dict(gridcolor="#E8EEF4", zerolinecolor="#D0DAE4", tickfont=dict(size=10)),
    xaxis=dict(tickfont=dict(size=10)),
    showlegend=False,
)


def _card(label: str, value: str, subtext: str, accent_class: str = "") -> None:
    st.markdown(
        f'<div class="kpi-card {accent_class}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-sub">{subtext}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render(
    handler: SegmentHandler,
    weather: dict,
    portfolio: list[dict],
    results: dict | None = None,
    selected_building_name: str | None = None,
    selected_building: dict | None = None,
    baseline_result: dict | None = None,
    selected_scenario_names: list[str] | None = None,
):
    """Renders the dashboard tab content."""
    seg = st.session_state.get("user_segment", "university_he")
    temp_c = weather.get("temperature_c", st.session_state.get("manual_temp", 10.5))

    # ── Portfolio-mode section (when portfolio is populated) ──────────────────
    if portfolio:
        _render_portfolio_dashboard(handler, weather, portfolio, seg)
        st.markdown("---")

    # ── Single-building / scenario analysis (always shown) ────────────────────
    if not selected_building_name or not selected_building or not results:
        st.info(
            "Add a building to your portfolio and select it as active, or select scenarios "
            "in the sidebar to see the analysis dashboard."
        )
        return

    # ── Building heading ───────────────────────────────────────────────────────
    col_hdr, col_badge = st.columns([3, 1])
    with col_hdr:
        st.markdown(
            f"<h2 style='margin:0;padding:0;'>{selected_building_name}</h2>"
            f"<div style='font-size:0.78rem;color:#5A7A90;margin-top:2px;'>"
            f"{selected_building.get('description', '')}</div>",
            unsafe_allow_html=True,
        )
    with col_badge:
        built = selected_building.get("built_year", "")
        st.markdown(
            f"<div style='text-align:right;padding-top:4px;'>"
            f"<span class='chip'>{built}</span>"
            f"<span class='chip'>{temp_c}\u00b0C</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── KPI Cards (segment-responsive) ────────────────────────────────────────
    if results:
        baseline_energy = (baseline_result or {}).get(
            "baseline_energy_mwh", selected_building.get("baseline_energy_mwh", 0)
        )
        baseline_cost = baseline_energy * 1000 * 0.28 / 1000  # £k
        best_saving = max(results.values(), key=lambda r: r.get("energy_saving_pct", 0))
        best_carbon = max(results.values(), key=lambda r: r.get("carbon_saving_t", 0))
        best_saving_name = next(n for n, r in results.items() if r is best_saving)
        best_carbon_name = next(n for n, r in results.items() if r is best_carbon)

        k1, k2, k3, k4 = st.columns(4)

        if seg == "smb_landlord":
            baseline_kwh = baseline_energy * 1000
            try:
                epc = compliance.estimate_epc_rating(
                    selected_building["floor_area_m2"], baseline_kwh,
                    selected_building["u_value_wall"], selected_building["u_value_roof"],
                    selected_building["u_value_glazing"], selected_building["glazing_ratio"],
                )
                mees = compliance.mees_gap_analysis(epc["sap_score"], target_band="C")
                with k1:
                    _card("Current EPC / SAP", f"{epc['epc_band']} \u00b7 {epc['sap_score']:.1f}", "Estimated from baseline physics")
                with k2:
                    _card("MEES 2028 Gap", f"{mees['sap_gap']:.1f} SAP", "Gap to Band C threshold", "accent-gold")
                with k3:
                    _card("Target EPC Band", "C", f"Target SAP: {mees['target_sap']:.0f}", "accent-teal")
                with k4:
                    _card("Est. Upgrade Cost",
                          f"\u00a3{mees['estimated_cost_low']:,.0f}\u2013\u00a3{mees['estimated_cost_high']:,.0f}",
                          "Indicative MEES package", "accent-green")
            except Exception as exc:
                st.warning(f"Could not compute MEES KPIs: {exc}")

        elif seg == "smb_industrial":
            try:
                secr = compliance.calculate_carbon_baseline(
                    elec_kwh=baseline_energy * 1000,
                    gas_kwh=0.0, oil_kwh=0.0, lpg_kwh=0.0, fleet_miles=0.0,
                    floor_area_m2=selected_building["floor_area_m2"],
                )
                with k1:
                    _card("Scope 1 Total", f"{secr['scope1_tco2e']:.1f} t", "Fuel + fleet baseline")
                with k2:
                    _card("Scope 2 Total", f"{secr['scope2_tco2e']:.1f} t", "Purchased electricity", "accent-teal")
                with k3:
                    _card("SECR Combined", f"{secr['total_tco2e']:.1f} t", "Scope 1 + Scope 2", "accent-green")
                with k4:
                    _card("Carbon Intensity", f"{secr['intensity_kgco2_m2']:.1f} kg/m\u00b2", "Portfolio baseline", "accent-gold")
            except Exception as exc:
                st.warning(f"Could not compute SECR KPIs: {exc}")

        elif seg == "individual_selfbuild":
            try:
                part_l = compliance.part_l_compliance_check(
                    floor_area_m2=selected_building["floor_area_m2"],
                    annual_energy_kwh=baseline_energy * 1000,
                    u_wall=selected_building["u_value_wall"],
                    u_roof=selected_building["u_value_roof"],
                    u_glazing=selected_building["u_value_glazing"],
                    glazing_ratio=selected_building["glazing_ratio"],
                )
                from config.constants import PART_L_2021_U_WALL
                wall_gap = selected_building["u_value_wall"] - PART_L_2021_U_WALL
                with k1:
                    _card("Primary Energy", f"{part_l['primary_energy_est']:.1f} kWh/m\u00b2", "Estimated baseline")
                with k2:
                    _card("Part L Status", "PASS" if part_l["part_l_2021_pass"] else "FAIL",
                          part_l.get("regs_label", ""), "accent-teal")
                with k3:
                    _card("U-Value Deviation", f"{wall_gap:+.2f} W/m\u00b2K",
                          f"Wall target {PART_L_2021_U_WALL:.2f} W/m\u00b2K", "accent-gold")
                with k4:
                    _card("FHS Readiness", "READY" if part_l["fhs_ready"] else "NOT READY",
                          "Future Homes Standard indicator", "accent-green")
            except Exception as exc:
                st.warning(f"Could not compute Part L KPIs: {exc}")

        else:  # university_he (default)
            with k1:
                _card("Portfolio Baseline",
                      f"{baseline_energy:,.0f}<span class='kpi-unit'> MWh/yr</span>",
                      "Current energy consumption")
            with k2:
                _card("Best Saving %",
                      f"{best_saving.get('energy_saving_pct', 0)}<span class='kpi-unit'>%</span>",
                      best_saving_name.split("(")[0].strip(), "accent-green")
            with k3:
                _card("Best Reduction",
                      f"{best_carbon.get('carbon_saving_t', 0):,.0f}<span class='kpi-unit'> t CO\u2082e</span>",
                      best_carbon_name.split("(")[0].strip(), "accent-teal")
            with k4:
                _card("Baseline Cost",
                      f"\u00a3{baseline_cost:,.0f}<span class='kpi-unit'>k</span>",
                      "At \u00a30.28/kWh", "accent-gold")

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # ── Energy & Carbon Charts ─────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        st.markdown("<div class='chart-title'>\u26a1 Annual Energy Consumption</div>", unsafe_allow_html=True)
        fig_e = go.Figure()
        for sn, res in results.items():
            sc = SCENARIOS.get(sn, {})
            fig_e.add_trace(go.Bar(
                x=[sc.get("display_name", sn)[:25]],
                y=[res.get("scenario_energy_mwh", 0)],
                marker_color=sc.get("colour", "#4A6FA5"),
                text=[f"{res.get('scenario_energy_mwh', 0):,.0f}"],
                textposition="outside", name=sn,
            ))
        fig_e.update_layout(**CHART_LAYOUT, yaxis_title="MWh / year")
        st.plotly_chart(fig_e, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            "<div class='chart-caption'>CrowAgent\u2122 PINN thermal model \u00b7 "
            "CIBSE Guide A \u00b7 Cross-validated against US DoE EnergyPlus</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        st.markdown("<div class='chart-title'>\U0001f30d Annual Carbon Emissions</div>", unsafe_allow_html=True)
        fig_c = go.Figure()
        for sn, res in results.items():
            sc = SCENARIOS.get(sn, {})
            fig_c.add_trace(go.Bar(
                x=[sc.get("display_name", sn)[:25]],
                y=[res.get("scenario_carbon_t", 0)],
                marker_color=sc.get("colour", "#4A6FA5"),
                text=[f"{res.get('scenario_carbon_t', 0):,.1f} t"],
                textposition="outside", name=sn,
            ))
        fig_c.update_layout(**CHART_LAYOUT, yaxis_title="Tonnes CO\u2082e / year")
        st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            "<div class='chart-caption'>Carbon intensity: 0.20482 kgCO\u2082e/kWh \u00b7 "
            "Source: BEIS Greenhouse Gas Conversion Factors 2023</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Technical Parameters Table ─────────────────────────────────────────────
    st.markdown("<div class='sec-hdr'>Technical Parameters</div>", unsafe_allow_html=True)
    rows_tbl = []
    for sn, res in results.items():
        sc = SCENARIOS.get(sn, {})
        rows_tbl.append({
            "Scenario": f"{sc.get('icon','?')} {sc.get('display_name', sn)}",
            "U-Wall (W/m\u00b2K)": res.get("u_wall", ""),
            "U-Roof (W/m\u00b2K)": res.get("u_roof", ""),
            "U-Glaz (W/m\u00b2K)": res.get("u_glazing", ""),
            "Energy (MWh/yr)": res.get("scenario_energy_mwh", 0),
            "Saving (%)": f"{res.get('energy_saving_pct', 0)}%",
            "CO\u2082 Saving (t)": res.get("carbon_saving_t", 0),
            "Install Cost": f"\u00a3{res['install_cost_gbp']:,.0f}" if res.get("install_cost_gbp", 0) > 0 else "\u2014",
            "Payback (yrs)": res.get("payback_years") if res.get("payback_years") else "\u2014",
        })
    st.dataframe(pd.DataFrame(rows_tbl), use_container_width=True, hide_index=True)
    st.caption(
        "U-values: CIBSE Guide A \u00b7 Scenario factors: BSRIA / Green Roof Organisation UK \u00b7 "
        "\u26a0\ufe0f Indicative only"
    )

    # ── Building Specification Expander ────────────────────────────────────────
    with st.expander(f"\U0001f4d0 Building Specification \u2014 {selected_building_name}"):
        sp1, sp2 = st.columns(2)
        with sp1:
            st.markdown(f"**Floor Area:** {selected_building.get('floor_area_m2', 0):,} m\u00b2")
            st.markdown(f"**Floor-to-Floor Height:** {selected_building.get('height_m', 0)} m")
            st.markdown(f"**Glazing Ratio:** {selected_building.get('glazing_ratio', 0)*100:.0f}%")
            st.markdown(f"**Annual Occupancy:** ~{selected_building.get('occupancy_hours', 0):,} hours")
            st.markdown(f"**Approximate Build Year:** {selected_building.get('built_year', 'Unknown')}")
        with sp2:
            st.markdown(f"**Baseline U-wall:** {selected_building.get('u_value_wall', 0)} W/m\u00b2K")
            st.markdown(f"**Baseline U-roof:** {selected_building.get('u_value_roof', 0)} W/m\u00b2K")
            st.markdown(f"**Baseline U-glazing:** {selected_building.get('u_value_glazing', 0)} W/m\u00b2K")
            st.markdown(f"**Baseline Energy:** {selected_building.get('baseline_energy_mwh', 0)} MWh/yr")
            _bco2 = round(selected_building.get("baseline_energy_mwh", 0) * 1000 * 0.20482 / 1000, 1)
            st.markdown(f"**Baseline Carbon:** {_bco2} t CO\u2082e/yr")
        st.caption(
            "\u26a0\ufe0f Data is indicative and derived from published UK HE sector averages (HESA 2022-23). "
            "Not specific to any real institution."
        )

    # ── 3D Campus Map ──────────────────────────────────────────────────────────
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    try:
        from app.visualization_3d import render_campus_3d_map
        render_campus_3d_map(
            selected_scenario_names=selected_scenario_names or list(results.keys()),
            weather=weather,
        )
    except Exception as exc:
        st.info(f"3D campus map unavailable: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# PORTFOLIO DASHBOARD (aggregated view)
# ─────────────────────────────────────────────────────────────────────────────

def _render_portfolio_dashboard(handler: SegmentHandler, weather: dict, portfolio: list[dict], seg: str):
    st.markdown("<h2 style='margin:0;padding:0;'>Portfolio Performance Dashboard</h2>", unsafe_allow_html=True)
    temp_c = weather.get("temperature_c", 10.5)
    st.markdown(
        f"<div style='font-size:0.85rem;color:#5A7A90;margin-bottom:15px;'>"
        f"Analysing {len(portfolio)} assets under current weather conditions ({temp_c}\u00b0C).</div>",
        unsafe_allow_html=True,
    )

    # Aggregate portfolio results (use stored combined_results if available, else skip charts)
    has_results = all(
        p.get("baseline_results") and p.get("combined_results") for p in portfolio
    )

    if has_results:
        try:
            total_base_mwh = sum(p["baseline_results"].get("scenario_energy_mwh", 0) for p in portfolio)
            total_comb_mwh = sum(p["combined_results"].get("scenario_energy_mwh", 0) for p in portfolio)
            total_base_c = sum(p["baseline_results"].get("scenario_carbon_t", 0) for p in portfolio)
            total_comb_c = sum(p["combined_results"].get("scenario_carbon_t", 0) for p in portfolio)
            total_saving = sum(p["combined_results"].get("annual_saving_gbp", 0) for p in portfolio)
            total_install = sum(p["combined_results"].get("install_cost_gbp", 0) for p in portfolio)
            avg_area = sum(p.get("floor_area_m2", 1000) for p in portfolio) / len(portfolio)

            k1, k2, k3, k4 = st.columns(4)
            if seg == "university_he":
                intensity = (total_base_c * 1000) / avg_area if avg_area > 0 else 0
                with k1: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Portfolio MWh</div><div class='kpi-value'>{total_base_mwh:,.0f}<span class='kpi-unit'> MWh/yr</span></div></div>", unsafe_allow_html=True)
                with k2: st.markdown(f"<div class='kpi-card accent-green'><div class='kpi-label'>Carbon Intensity</div><div class='kpi-value'>{intensity:,.1f}<span class='kpi-unit'> kgCO\u2082e/m\u00b2</span></div></div>", unsafe_allow_html=True)
                with k3: st.markdown(f"<div class='kpi-card accent-gold'><div class='kpi-label'>Cost Exposure</div><div class='kpi-value'>\u00a3{total_base_mwh*1000*0.28/1000:,.1f}<span class='kpi-unit'>k</span></div></div>", unsafe_allow_html=True)
                with k4: st.markdown(f"<div class='kpi-card accent-navy'><div class='kpi-label'>Net Zero Gap</div><div class='kpi-value'>{total_base_c:,.1f}<span class='kpi-unit'> tCO\u2082e</span></div></div>", unsafe_allow_html=True)
            elif seg == "smb_landlord":
                roi = (total_saving / total_install * 100) if total_install > 0 else 0
                with k1: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Portfolio Energy</div><div class='kpi-value'>{total_base_mwh:,.0f}<span class='kpi-unit'> MWh/yr</span></div></div>", unsafe_allow_html=True)
                with k2: st.markdown(f"<div class='kpi-card accent-gold'><div class='kpi-label'>Upgrade Cost (Est)</div><div class='kpi-value'>\u00a3{total_install/1000:,.0f}<span class='kpi-unit'>k</span></div></div>", unsafe_allow_html=True)
                with k3: st.markdown(f"<div class='kpi-card accent-green'><div class='kpi-label'>Carbon Saving</div><div class='kpi-value'>{total_base_c-total_comb_c:,.1f}<span class='kpi-unit'> tCO\u2082e</span></div></div>", unsafe_allow_html=True)
                with k4: st.markdown(f"<div class='kpi-card accent-navy'><div class='kpi-label'>Projected ROI</div><div class='kpi-value'>{roi:,.1f}<span class='kpi-unit'>%</span></div></div>", unsafe_allow_html=True)
            elif seg == "smb_industrial":
                try:
                    secr = compliance.calculate_carbon_baseline(elec_kwh=total_base_mwh*1000, gas_kwh=total_base_mwh*500)
                    abatement = ((total_base_c - total_comb_c) / total_base_c * 100) if total_base_c > 0 else 0
                    with k1: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>SECR Scope 1</div><div class='kpi-value'>{secr['scope1_tco2e']:,.1f}<span class='kpi-unit'> tCO\u2082e</span></div></div>", unsafe_allow_html=True)
                    with k2: st.markdown(f"<div class='kpi-card accent-navy'><div class='kpi-label'>Scope 2</div><div class='kpi-value'>{secr['scope2_tco2e']:,.1f}<span class='kpi-unit'> tCO\u2082e</span></div></div>", unsafe_allow_html=True)
                    with k3: st.markdown(f"<div class='kpi-card accent-gold'><div class='kpi-label'>Carbon Liability</div><div class='kpi-value'>{secr['total_tco2e']:,.1f}<span class='kpi-unit'> tCO\u2082e</span></div></div>", unsafe_allow_html=True)
                    with k4: st.markdown(f"<div class='kpi-card accent-green'><div class='kpi-label'>Abatement Potential</div><div class='kpi-value'>{abatement:,.1f}<span class='kpi-unit'>%</span></div></div>", unsafe_allow_html=True)
                except Exception:
                    pass
            else:  # individual_selfbuild
                try:
                    pl = compliance.part_l_compliance_check(1.8, 2.0, 2.8, avg_area, (total_base_mwh/len(portfolio))*1000)
                    status_c = "#1DB87A" if pl["part_l_2021_pass"] else "#E84C4C"
                    with k1: st.markdown(f"<div class='kpi-card'><div class='kpi-label'>Part L Primary Energy</div><div class='kpi-value'>{pl['primary_energy_est']:,.1f}<span class='kpi-unit'> kWh/m\u00b2/yr</span></div></div>", unsafe_allow_html=True)
                    with k2: st.markdown(f"<div class='kpi-card accent-navy'><div class='kpi-label'>Fabric Heat Loss</div><div class='kpi-value'>High</div></div>", unsafe_allow_html=True)
                    with k3: st.markdown(f"<div class='kpi-card' style='border-top-color:{status_c}'><div class='kpi-label'>Compliance Status</div><div class='kpi-value' style='color:{status_c}'>{'Pass' if pl['part_l_2021_pass'] else 'Fail'}</div></div>", unsafe_allow_html=True)
                    with k4: st.markdown(f"<div class='kpi-card accent-gold'><div class='kpi-label'>Upgrade Cost</div><div class='kpi-value'>\u00a3{total_install/len(portfolio)/1000:,.0f}<span class='kpi-unit'>k / home</span></div></div>", unsafe_allow_html=True)
                except Exception:
                    pass

            st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

            # Portfolio Energy & Carbon charts
            c1, c2 = st.columns(2)
            x_labels = [f"{p['postcode'][:8]}" for p in portfolio]
            y_base = [p["baseline_results"].get("scenario_energy_mwh", 0) for p in portfolio]
            y_comb = [p["combined_results"].get("scenario_energy_mwh", 0) for p in portfolio]
            with c1:
                st.markdown("<div class='chart-card'><div class='chart-title'>\u26a1 Portfolio Energy (MWh/yr)</div>", unsafe_allow_html=True)
                fig_e = go.Figure()
                fig_e.add_trace(go.Bar(name="Baseline", x=x_labels, y=y_base, marker_color="#4A6FA5"))
                fig_e.add_trace(go.Bar(name="Post-Intervention", x=x_labels, y=y_comb, marker_color="#00C2A8"))
                fig_e.update_layout(**{**CHART_LAYOUT, "showlegend": True}, barmode="group", yaxis_title="MWh / year")
                st.plotly_chart(fig_e, use_container_width=True, config={"displayModeBar": False})
                st.markdown("</div>", unsafe_allow_html=True)
            y_base_c = [p["baseline_results"].get("scenario_carbon_t", 0) for p in portfolio]
            y_comb_c = [p["combined_results"].get("scenario_carbon_t", 0) for p in portfolio]
            with c2:
                st.markdown("<div class='chart-card'><div class='chart-title'>\U0001f30d Portfolio Carbon (t CO\u2082e/yr)</div>", unsafe_allow_html=True)
                fig_c = go.Figure()
                fig_c.add_trace(go.Bar(name="Baseline", x=x_labels, y=y_base_c, marker_color="#FFA500"))
                fig_c.add_trace(go.Bar(name="Post-Intervention", x=x_labels, y=y_comb_c, marker_color="#1DB87A"))
                fig_c.update_layout(**{**CHART_LAYOUT, "showlegend": True}, barmode="group", yaxis_title="Tonnes CO\u2082e / year")
                st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar": False})
                st.markdown("</div>", unsafe_allow_html=True)
        except Exception as exc:
            st.warning(f"Could not render portfolio KPIs: {exc}")

    # ── PyDeck 3D Spatial Map ──────────────────────────────────────────────────
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='sec-hdr'>\U0001f5fa\ufe0f Spatial View & Geo-Physics Mapping</div>", unsafe_allow_html=True)

    map_col_l, map_col_r = st.columns([1, 3])
    with map_col_l:
        st.markdown("<div style='font-size:0.85rem;font-weight:600;color:#071A2F;'>Asset Geo-Locator</div>", unsafe_allow_html=True)
        search_pc = st.text_input("Locate Postcode in Portfolio", placeholder="e.g. SW1A 1AA")
        if search_pc:
            if any(p["postcode"] == search_pc.upper() for p in portfolio):
                st.success("Asset found in active portfolio.")
            else:
                st.warning("Asset not in portfolio.")
        st.markdown(
            "<div style='margin-top:20px;font-size:0.8rem;color:#5A7A90;'>"
            "<b>Legend: Carbon Reduction</b><br/>"
            "\U0001f7e9 100% Reduction<br/>\U0001f7e8 50% Reduction<br/>\U0001f7e5 0% Reduction</div>",
            unsafe_allow_html=True,
        )
        st.caption("Polygons represent physical building bounds for PINN analysis.")

    with map_col_r:
        center_lat = st.session_state.get("wx_lat", 51.4543)
        center_lon = st.session_state.get("wx_lon", -0.9781)
        _map_data = []
        for i, p in enumerate(portfolio):
            a_lat = center_lat + (np.sin(i) * 0.01)
            a_lon = center_lon + (np.cos(i) * 0.01)
            comb_r = (p.get("combined_results") or {})
            reduction = comb_r.get("energy_saving_pct", 0)
            ratio = max(0.0, min(1.0, reduction / 100.0))
            r = int(220 - ratio * 220)
            g = int(50 + ratio * (194 - 50))
            b_val = int(50 + ratio * (168 - 50))
            _map_data.append({
                "name": p["postcode"],
                "lat": a_lat, "lon": a_lon,
                "energy_saving_pct": reduction,
                "carbon_saving_t": comb_r.get("carbon_saving_t", 0),
                "fill_color": [r, g, b_val, 210],
                "elevation": max(10.0, (p.get("floor_area_m2", 1000) * 0.15) / 10.0),
                "polygon": loc._synthetic_polygon(a_lat, a_lon, size_m=60.0),
            })
        if _map_data:
            try:
                import pydeck as pdk
                import pandas as _pd
                deck = pdk.Deck(
                    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                    initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=12, pitch=45),
                    layers=[pdk.Layer(
                        "PolygonLayer", data=_pd.DataFrame(_map_data),
                        get_polygon="polygon", get_elevation="elevation",
                        get_fill_color="fill_color", extruded=True, pickable=True, auto_highlight=True,
                    )],
                    tooltip={"html": "<b>{name}</b><br/>Reduction: {energy_saving_pct}%<br/>Carbon Saved: {carbon_saving_t} t"},
                )
                st.pydeck_chart(deck, use_container_width=True)
            except ImportError:
                st.info("Install pydeck for 3D map view: pip install pydeck")
            except Exception as exc:
                st.error(f"Map render error: {exc}")
        else:
            st.info("Add buildings to the portfolio to see the spatial map.")
