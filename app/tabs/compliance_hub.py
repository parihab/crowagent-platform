"""
Compliance Hub Tab Renderer
===========================
Panels rendered dynamically based on handler.compliance_checks:
  Panel A — SECR & TCFD     ('secr')      university_he, smb_industrial
  Panel B — MEES & EPC      ('epc_mees')  commercial_landlord
  Panel C — Part L & FHS    ('part_l','fhs')  commercial_landlord, smb_industrial,
                                               individual_selfbuild

NOTE: Underlying carbon math, scope definitions, and baseline compliance logic
      are untouched — only the presentation layer is restructured.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import app.branding as branding
import app.compliance as compliance


def render(handler, portfolio: list[dict]) -> None:
    """Render the compliance hub tab for the active segment."""
    buildings = handler.building_registry   # dict[name → building dict]

    if not buildings:
        st.info("No buildings available for compliance checks.")
        return

    branding.render_html(
        f'<h2 style="font-family:Rajdhani,sans-serif;color:#071A2F;margin-bottom:4px;">'
        f"Compliance Hub — {handler.display_label}</h2>"
    )

    checks = handler.compliance_checks

    # Panel A — Carbon & Regulatory Compliance (SECR + TCFD)
    if "secr" in checks:
        _panel_secr_tcfd(buildings)

    # Panel B — MEES & EPC
    if "epc_mees" in checks:
        _panel_mees_epc(buildings)

    # Panel C — Part L 2021 & FHS
    if "part_l" in checks or "fhs" in checks:
        _panel_part_l_fhs(buildings, handler.segment_id, show_fhs="fhs" in checks)
        branding.render_html('<div class="main-section-divider"></div>')


# ─────────────────────────────────────────────────────────────────────────────
# PANEL A — SECR & TCFD
# ─────────────────────────────────────────────────────────────────────────────

def _panel_secr_tcfd(buildings: dict) -> None:
    """Carbon & Regulatory Compliance Overview — SECR reporting + TCFD alignment."""
    branding.render_html(
        '<div class="sec-hdr">Carbon &amp; Regulatory Compliance Overview</div>'
    )

    # Compute portfolio-level carbon baseline
    total_elec_kwh = sum(b["baseline_energy_mwh"] for b in buildings.values()) * 1000
    res = compliance.calculate_carbon_baseline(
        elec_kwh=total_elec_kwh,
        gas_kwh=total_elec_kwh * 0.5,
        fleet_miles=5000,
    )
    threshold = res.get("secr_threshold_check", {})

    # ── Section 1: Compliance Status Banner ──────────────────────────────────
    with st.container(border=True):
        if threshold.get("supply_chain_pressure"):
            branding.render_html(
                '<div style="background:#2A1010;border:1px solid #E84C4C;border-radius:6px;'
                'padding:12px;color:#F0B429;font-weight:600;">'
                "&#9888; Carbon footprint exceeds 50 t — supply chain reporting likely required."
                "</div>"
            )
        else:
            branding.render_html(
                '<div style="background:#071A2F;border:1px solid #00C2A8;border-radius:6px;'
                'padding:12px;color:#00C2A8;font-weight:600;">'
                "&#10004; SECR threshold met — no mandatory disclosure trigger at this time."
                "</div>"
            )

    branding.render_html(
        '<div style="font-size:0.82rem;color:#5A7A90;margin:8px 0 4px;">Emissions Summary</div>'
    )

    # ── Section 2: KPI Columns ───────────────────────────────────────────────
    with st.container(border=True):
        k1, k2, k3 = st.columns(3)
        k1.metric("Scope 1 (Direct)", f"{res['scope1_tco2e']:.1f} t",
                  help="Gas combustion + fleet fuel (proxy estimate)")
        k2.metric("Scope 2 (Grid Elec)", f"{res['scope2_tco2e']:.1f} t",
                  help="Grid electricity — BEIS 2023 carbon intensity factor")
        k3.metric("Total tCO\u2082e", f"{res['total_tco2e']:.1f} t",
                  help="Scope 1 + Scope 2 combined footprint")

    # ── Section 3: Carbon Breakdown Chart ────────────────────────────────────
    branding.render_html(
        '<div style="font-size:0.82rem;color:#5A7A90;margin:8px 0 4px;">Carbon Breakdown</div>'
    )
    with st.container(border=True):
        fig = go.Figure(go.Bar(
            x=["Scope 1 (Direct)", "Scope 2 (Grid Electricity)"],
            y=[res["scope1_tco2e"], res["scope2_tco2e"]],
            marker_color=["#F0B429", "#00C2A8"],
            text=[f"{res['scope1_tco2e']:.1f} t", f"{res['scope2_tco2e']:.1f} t"],
            textposition="auto",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10, b=30, l=50, r=20),
            height=280,
            yaxis_title="tCO\u2082e",
            font=dict(family="Nunito Sans"),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Section 4: TCFD Framework Alignment ──────────────────────────────────
    branding.render_html(
        '<div style="font-size:0.82rem;color:#5A7A90;margin:8px 0 4px;">'
        "TCFD Framework Alignment</div>"
    )
    with st.container(border=True):
        st.markdown(
            "**Governance** — Board-level oversight of climate-related risks and "
            "opportunities is recommended. Assign a senior responsible owner for "
            "net-zero delivery and embed climate risk into the annual reporting cycle.\n\n"
            "**Strategy** — Short-term: energy efficiency retrofits aligned to MEES "
            "Band C targets. Medium-term: transition to low-carbon heat (heat pumps, "
            "district heating). Long-term: net-zero by 2050 consistent with a 1.5 °C "
            "pathway under IPCC AR6.\n\n"
            "**Risk Management** — Physical risks (overheating, flood events, extreme "
            "cold) and transition risks (carbon pricing, tightening MEES, stranded "
            "assets) should be integrated into the asset register and scenario "
            "planning framework.\n\n"
            "**Metrics & Targets** — Report Scope 1, 2, and material Scope 3 emissions "
            "annually. Set Science-Based Targets (SBTi) aligned to sector pathways. "
            "Track progress against the Taskforce on Nature-related Financial Disclosures "
            "(TNFD) where biodiversity exposure is material."
        )

    branding.render_html('<div class="main-section-divider"></div>')


# ─────────────────────────────────────────────────────────────────────────────
# PANEL B — MEES & EPC
# ─────────────────────────────────────────────────────────────────────────────

def _panel_mees_epc(buildings: dict) -> None:
    """MEES & EPC Compliance Overview — status banner + per-asset gap analysis."""
    branding.render_html(
        '<div class="sec-hdr">MEES &amp; EPC Compliance Overview</div>'
    )

    # Pre-compute all building ratings for the portfolio-level banner
    results: dict[str, dict] = {}
    for b_name, b_data in buildings.items():
        results[b_name] = compliance.estimate_epc_rating(
            floor_area_m2=b_data["floor_area_m2"],
            annual_energy_kwh=b_data["baseline_energy_mwh"] * 1000,
            u_wall=b_data["u_value_wall"],
            u_roof=b_data["u_value_roof"],
            u_glazing=b_data["u_value_glazing"],
            glazing_ratio=b_data["glazing_ratio"],
        )

    below_target = [n for n, r in results.items() if not r["mees_2028_compliant"]]
    n_fail = len(below_target)

    # ── Section 1: Compliance Status Banner ──────────────────────────────────
    with st.container(border=True):
        if n_fail == 0:
            branding.render_html(
                '<div style="background:#071A2F;border:1px solid #00C2A8;border-radius:6px;'
                'padding:12px;color:#00C2A8;font-weight:600;">'
                "&#10004; Portfolio meets the 2028 MEES target — all assets rated Band C or above."
                "</div>"
            )
        else:
            asset_word = "asset" if n_fail == 1 else "assets"
            branding.render_html(
                f'<div style="background:#2A1010;border:1px solid #E84C4C;border-radius:6px;'
                f'padding:12px;">'
                f'<div style="color:#F0B429;font-weight:600;margin-bottom:4px;">'
                f"&#9888; {n_fail} {asset_word} below 2028 MEES target (Band C)</div>"
                f'<div style="font-size:0.78rem;color:#CBD8E6;">'
                f"Affected: {', '.join(below_target)}</div>"
                f"</div>"
            )

    # ── Section 2: Asset Gap Analysis ────────────────────────────────────────
    branding.render_html(
        '<div style="font-size:0.82rem;color:#5A7A90;margin:8px 0 4px;">'
        "Asset Gap Analysis</div>"
    )

    for b_name, res in results.items():
        compliant = res["mees_2028_compliant"]
        # Auto-expand non-compliant assets to draw attention
        with st.expander(f"Asset: {b_name}", expanded=not compliant):
            info_col, status_col = st.columns([1, 2])

            with info_col:
                st.metric("Est. EPC Band", f"Band {res['epc_band']}")
                st.metric("SAP Score", str(res["sap_score"]))
                st.caption(f"EUI: {res['eui_kwh_m2']} kWh/m\u00b2/yr")
                st.caption("Target: Band C by 2028")

            with status_col:
                if compliant:
                    st.success(res["recommendation"])
                else:
                    st.warning(res["recommendation"])

                    gap = compliance.mees_gap_analysis(res["sap_score"], "C")
                    measures = gap.get("recommended_measures", [])

                    if measures:
                        branding.render_html(
                            '<div style="font-size:0.78rem;color:#5A7A90;'
                            'margin:6px 0 4px;">Recommended Upgrades</div>'
                        )
                        rows = [
                            {
                                "Measure": m["name"],
                                "SAP Lift": f"+{m['sap_lift']} pts",
                                "Est. Cost": (
                                    f"£{m['cost_low']:,} – £{m['cost_high']:,}"
                                ),
                                "Regulation": m.get("regulation", "—"),
                            }
                            for m in measures
                        ]
                        st.dataframe(
                            pd.DataFrame(rows),
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Measure": st.column_config.TextColumn(width="medium"),
                                "SAP Lift": st.column_config.TextColumn(width="small"),
                                "Est. Cost": st.column_config.TextColumn(width="medium"),
                                "Regulation": st.column_config.TextColumn(width="large"),
                            },
                        )
                        sap_gap = gap.get("sap_gap", 0)
                        if sap_gap:
                            st.caption(
                                f"SAP gap to Band C: {sap_gap} pts — "
                                f"{len(measures)} measure(s) recommended."
                            )

    branding.render_html('<div class="main-section-divider"></div>')


# ─────────────────────────────────────────────────────────────────────────────
# PANEL C — Part L 2021 & FHS Readiness
# ─────────────────────────────────────────────────────────────────────────────

def _panel_part_l_fhs_stub() -> None:
    """Kept for import safety — delegates to the full implementation."""
    pass  # render() calls _panel_part_l_fhs directly; stub retained for safety


def _panel_part_l_fhs(buildings: dict, segment_id: str, show_fhs: bool) -> None:
    """Part L 2021 & FHS Readiness Overview — fabric check + primary energy proxy."""
    branding.render_html(
        '<div class="sec-hdr">Part L 2021 &amp; FHS Readiness Overview</div>'
    )

    # Select the correct building_type string for the compliance engine
    b_type = "individual_selfbuild" if segment_id == "individual_selfbuild" else "non-residential"

    # Run compliance check for every building; collect results
    checked: list[dict] = []
    for b_name, b_data in buildings.items():
        try:
            res = compliance.part_l_compliance_check(
                u_wall=b_data["u_value_wall"],
                u_roof=b_data["u_value_roof"],
                u_glazing=b_data["u_value_glazing"],
                floor_area_m2=b_data["floor_area_m2"],
                annual_energy_kwh=b_data["baseline_energy_mwh"] * 1000,
                building_type=b_type,
            )
            checked.append({"name": b_name, **res})
        except (ValueError, KeyError):
            continue

    if not checked:
        st.warning("Insufficient building data for Part L compliance check.")
        branding.render_html('<div class="main-section-divider"></div>')
        return

    any_fabric_fail = any(not c["part_l_2021_pass"] for c in checked)
    any_fhs_fail    = any(not c["fhs_ready"] for c in checked)

    # ── Section 1: Overall Status Banner ─────────────────────────────────────
    with st.container(border=True):
        if not any_fabric_fail and (not show_fhs or not any_fhs_fail):
            branding.render_html(
                '<div style="background:#071A2F;border:1px solid #00C2A8;border-radius:6px;'
                'padding:12px;color:#00C2A8;font-weight:600;">'
                "&#10004; Part L 2021 Fabric Targets Met across portfolio."
                + (" Future Homes Standard proxy threshold satisfied." if show_fhs else "")
                + "</div>"
            )
        else:
            lines = []
            if any_fabric_fail:
                lines.append("&#9888; One or more assets do not meet Part L 2021 U-value targets.")
            if show_fhs and any_fhs_fail:
                lines.append("&#9888; Primary energy exceeds the FHS proxy threshold on one or more assets.")
            branding.render_html(
                '<div style="background:#2A1010;border:1px solid #E84C4C;border-radius:6px;'
                'padding:12px;color:#F0B429;font-weight:600;">'
                + "<br>".join(lines)
                + "</div>"
            )

    # ── Section 2: Per-building fabric check + FHS proxy ─────────────────────
    branding.render_html(
        '<div style="font-size:0.82rem;color:#5A7A90;margin:8px 0 4px;">'
        "Fabric U-Value Check</div>"
    )

    for c in checked:
        b_pass = c["part_l_2021_pass"]
        with st.expander(f"Asset: {c['name']}", expanded=not b_pass):

            # Verdict sub-banner
            if b_pass:
                st.success(f"Part L 2021 — {c['regs_label']}: PASS")
            else:
                st.error(f"Part L 2021 — {c['regs_label']}: FAIL")

            # Fabric U-value table
            fabric_rows = [
                {
                    "Element":          item["element"],
                    "Proposed (W/m²K)": item["proposed_u"],
                    "Target (W/m²K)":   item["target_u"],
                    "Gap (W/m²K)":      item["gap"] if not item["pass"] else 0.0,
                    "Status":           "Pass" if item["pass"] else "Fail",
                }
                for item in c["compliance_items"]
            ]
            st.dataframe(
                pd.DataFrame(fabric_rows),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Element":          st.column_config.TextColumn(width="medium"),
                    "Proposed (W/m²K)": st.column_config.NumberColumn(format="%.2f"),
                    "Target (W/m²K)":   st.column_config.NumberColumn(format="%.2f"),
                    "Gap (W/m²K)":      st.column_config.NumberColumn(format="%.3f"),
                    "Status": st.column_config.TextColumn(width="small"),
                },
            )

            # Improvement actions (if any)
            if c["improvement_actions"]:
                with st.expander("Improvement Actions", expanded=False):
                    for action in c["improvement_actions"]:
                        st.markdown(f"- {action}")

            # FHS Proxy section
            if show_fhs or True:   # always show primary energy — useful for all segments
                fhs_label = "FHS Proxy" if show_fhs else "Primary Energy (Indicative)"
                branding.render_html(
                    f'<div style="font-size:0.78rem;color:#5A7A90;margin:8px 0 4px;">'
                    f"Future Homes Standard — {fhs_label}</div>"
                )
                fhs_col1, fhs_col2 = st.columns(2)
                delta_val = c["primary_energy_est"] - c["fhs_threshold"]
                fhs_col1.metric(
                    "Primary Energy Estimate",
                    f"{c['primary_energy_est']:.1f} kWh/m\u00b2/yr",
                    delta=f"{delta_val:+.1f} vs threshold",
                    delta_color="inverse",
                )
                fhs_col2.metric(
                    "FHS Threshold",
                    f"{c['fhs_threshold']} kWh/m\u00b2/yr",
                )
                status_icon = "On Track" if c["fhs_ready"] else "Exceeds Threshold"
                st.caption(f"FHS Status: {status_icon}")
